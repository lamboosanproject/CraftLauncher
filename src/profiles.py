"""
Custom profiles/versions management for CraftLauncher
Allows creating custom game configurations with specific MC version and mod loader
"""

import json
import zipfile
import shutil
import base64
import gzip
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Callable, List
from datetime import datetime
import uuid

from .logger import logger

# Export format version for compatibility
EXPORT_FORMAT_VERSION = "1.0"
MANIFEST_CODE_VERSION = 1


@dataclass
class InstalledMod:
    """Tracks an installed mod with its source."""
    filename: str  # Local filename
    source: str  # "modrinth", "curseforge", "local"
    mod_id: Optional[str] = None  # ID on source platform
    version_id: Optional[str] = None  # Version ID on source platform
    name: Optional[str] = None  # Display name


@dataclass
class Profile:
    """A custom game profile/version."""
    id: str
    name: str
    minecraft_version: str
    loader_type: Optional[str] = None  # "fabric", "forge", "neoforge", "quilt", "optifine", None for vanilla
    loader_version: Optional[str] = None
    game_directory: Optional[str] = None  # Custom game directory, None = default
    created_at: str = ""
    last_played: Optional[str] = None
    icon: str = "🎮"  # Custom icon/emoji
    installed_mods: List[dict] = field(default_factory=list)  # List of InstalledMod as dicts
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    @property
    def display_name(self) -> str:
        """Get display name with loader info."""
        if self.loader_type:
            return f"{self.name} ({self.loader_type.capitalize()})"
        return f"{self.name} (Vanilla)"
    
    @property
    def version_id(self) -> str:
        """Get the actual version ID to launch."""
        if self.loader_type and self.loader_version:
            if self.loader_type == "fabric":
                return f"fabric-loader-{self.loader_version}-{self.minecraft_version}"
            elif self.loader_type == "quilt":
                return f"quilt-loader-{self.loader_version}-{self.minecraft_version}"
            elif self.loader_type == "forge" or self.loader_type == "forge+optifine":
                # Forge version is like "1.21.10-forge-60.1.5"
                # loader_version stored as "1.21.10-60.1.5", need to add "forge"
                parts = self.loader_version.split("-", 1)
                if len(parts) == 2:
                    return f"{parts[0]}-forge-{parts[1]}"
                return self.loader_version
            elif self.loader_type == "neoforge":
                return f"neoforge-{self.loader_version}"
            elif self.loader_type == "optifine":
                # OptiFine version is like "1.21_HD_U_J1" -> version "1.21-OptiFine_HD_U_J1"
                return f"{self.minecraft_version}-OptiFine_{self.loader_version}"
        return self.minecraft_version


class ProfileManager:
    """Manages custom game profiles."""
    
    def __init__(self, config_dir: Path, minecraft_dir: Path = None):
        self.config_dir = config_dir
        self.minecraft_dir = minecraft_dir or Path.home() / ".minecraft"
        self.profiles_dir = self.minecraft_dir / "profiles"  # Base folder for profile data
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_file = config_dir / "profiles.json"
        self.profiles: dict[str, Profile] = {}
        self._load_profiles()
    
    def _load_profiles(self):
        """Load profiles from file."""
        if self.profiles_file.exists():
            try:
                data = json.loads(self.profiles_file.read_text())
                for profile_data in data.get("profiles", []):
                    profile = Profile(**profile_data)
                    self.profiles[profile.id] = profile
                logger.info(f"Loaded {len(self.profiles)} profiles")
            except Exception as e:
                logger.error(f"Failed to load profiles: {e}")
                self.profiles = {}
        else:
            self.profiles = {}
    
    def _save_profiles(self):
        """Save profiles to file."""
        try:
            data = {
                "profiles": [asdict(p) for p in self.profiles.values()]
            }
            self.profiles_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            logger.info(f"Saved {len(self.profiles)} profiles")
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")
    
    def _sanitize_folder_name(self, name: str) -> str:
        """Convert profile name to safe folder name."""
        import re
        # Replace spaces with underscores, remove special chars
        safe_name = re.sub(r'[^\w\-]', '_', name)
        # Remove consecutive underscores
        safe_name = re.sub(r'_+', '_', safe_name)
        return safe_name.strip('_')
    
    def get_profile_directory(self, profile_name: str) -> Path:
        """Get the game directory for a profile (creates if not exists)."""
        folder_name = self._sanitize_folder_name(profile_name)
        profile_dir = self.profiles_dir / folder_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir
    
    def create_profile(
        self,
        name: str,
        minecraft_version: str,
        loader_type: Optional[str] = None,
        loader_version: Optional[str] = None,
        game_directory: Optional[str] = None,
        icon: str = "🎮"
    ) -> Profile:
        """Create a new profile."""
        profile_id = str(uuid.uuid4())[:8]
        
        # Auto-generate game directory if not provided
        if not game_directory:
            game_directory = str(self.get_profile_directory(name))
        
        profile = Profile(
            id=profile_id,
            name=name,
            minecraft_version=minecraft_version,
            loader_type=loader_type,
            loader_version=loader_version,
            game_directory=game_directory,
            icon=icon
        )
        
        self.profiles[profile_id] = profile
        self._save_profiles()
        
        # Create profile folder structure
        profile_path = Path(game_directory)
        (profile_path / "mods").mkdir(parents=True, exist_ok=True)
        (profile_path / "saves").mkdir(parents=True, exist_ok=True)
        (profile_path / "resourcepacks").mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created profile: {name} (MC {minecraft_version}, {loader_type or 'vanilla'})")
        logger.info(f"Profile directory: {game_directory}")
        return profile
    
    def get_profile(self, profile_id: str) -> Optional[Profile]:
        """Get a profile by ID."""
        return self.profiles.get(profile_id)
    
    def get_all_profiles(self) -> list[Profile]:
        """Get all profiles sorted by last played."""
        profiles = list(self.profiles.values())
        profiles.sort(key=lambda p: p.last_played or "", reverse=True)
        return profiles
    
    def update_profile(self, profile_id: str, **kwargs) -> Optional[Profile]:
        """Update a profile."""
        profile = self.profiles.get(profile_id)
        if profile:
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            self._save_profiles()
            logger.info(f"Updated profile: {profile.name}")
        return profile
    
    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile."""
        if profile_id in self.profiles:
            name = self.profiles[profile_id].name
            del self.profiles[profile_id]
            self._save_profiles()
            logger.info(f"Deleted profile: {name}")
            return True
        return False
    
    def mark_played(self, profile_id: str):
        """Update last played timestamp."""
        profile = self.profiles.get(profile_id)
        if profile:
            profile.last_played = datetime.now().isoformat()
            self._save_profiles()
    
    def export_profile(
        self,
        profile_id: str,
        export_path: Path,
        include_mods: bool = True,
        include_resourcepacks: bool = False,
        include_shaderpacks: bool = False,
        include_config: bool = False,
        callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Optional[Path]:
        """
        Export a profile to a ZIP file.
        
        Args:
            profile_id: Profile ID to export
            export_path: Path to save the ZIP file
            include_mods: Include mods folder
            include_resourcepacks: Include resourcepacks folder
            include_shaderpacks: Include shaderpacks folder
            include_config: Include config folder (mod configs)
            callback: Progress callback (status, current, total)
            
        Returns:
            Path to the created ZIP file or None on error
        """
        profile = self.get_profile(profile_id)
        if not profile:
            logger.error(f"Profile not found: {profile_id}")
            return None
        
        game_dir = Path(profile.game_directory) if profile.game_directory else None
        if not game_dir or not game_dir.exists():
            logger.error(f"Profile game directory not found: {game_dir}")
            return None
        
        try:
            # Prepare manifest
            manifest = {
                "format_version": EXPORT_FORMAT_VERSION,
                "profile": {
                    "name": profile.name,
                    "minecraft_version": profile.minecraft_version,
                    "loader_type": profile.loader_type,
                    "loader_version": profile.loader_version,
                    "icon": profile.icon,
                },
                "export_date": datetime.now().isoformat(),
                "included": {
                    "mods": include_mods,
                    "resourcepacks": include_resourcepacks,
                    "shaderpacks": include_shaderpacks,
                    "config": include_config,
                }
            }
            
            # Collect files to include
            files_to_add = []
            folders_to_include = []
            
            if include_mods:
                folders_to_include.append("mods")
            if include_resourcepacks:
                folders_to_include.append("resourcepacks")
            if include_shaderpacks:
                folders_to_include.append("shaderpacks")
            if include_config:
                folders_to_include.append("config")
            
            for folder_name in folders_to_include:
                folder_path = game_dir / folder_name
                if folder_path.exists():
                    for file_path in folder_path.rglob("*"):
                        if file_path.is_file():
                            rel_path = file_path.relative_to(game_dir)
                            files_to_add.append((file_path, str(rel_path)))
            
            total_files = len(files_to_add) + 1  # +1 for manifest
            
            if callback:
                callback("Создание архива...", 0, total_files)
            
            # Create ZIP
            export_file = export_path
            if not export_file.suffix.lower() == ".zip":
                export_file = export_file.with_suffix(".zip")
            
            with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add manifest
                zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
                
                if callback:
                    callback("Добавление manifest.json", 1, total_files)
                
                # Add files
                for i, (file_path, arc_name) in enumerate(files_to_add):
                    zf.write(file_path, arc_name)
                    if callback:
                        callback(f"Добавление {arc_name}", i + 2, total_files)
            
            logger.info(f"Exported profile '{profile.name}' to {export_file}")
            logger.info(f"Included: {len(files_to_add)} files")
            return export_file
            
        except Exception as e:
            logger.error(f"Failed to export profile: {e}")
            return None
    
    def import_profile(
        self,
        import_path: Path,
        new_name: Optional[str] = None,
        callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Optional[Profile]:
        """
        Import a profile from a ZIP file.
        
        Args:
            import_path: Path to the ZIP file
            new_name: Optional new name for the profile (uses original if None)
            callback: Progress callback (status, current, total)
            
        Returns:
            Created Profile or None on error
        """
        if not import_path.exists():
            logger.error(f"Import file not found: {import_path}")
            return None
        
        try:
            with zipfile.ZipFile(import_path, 'r') as zf:
                # Read manifest
                if "manifest.json" not in zf.namelist():
                    logger.error("Invalid profile archive: manifest.json not found")
                    return None
                
                manifest = json.loads(zf.read("manifest.json"))
                
                # Check format version
                format_version = manifest.get("format_version", "1.0")
                if format_version != EXPORT_FORMAT_VERSION:
                    logger.warning(f"Profile format version mismatch: {format_version} vs {EXPORT_FORMAT_VERSION}")
                
                profile_data = manifest.get("profile", {})
                profile_name = new_name or profile_data.get("name", "Imported Profile")
                
                # Check if profile with this name exists
                existing_names = [p.name for p in self.profiles.values()]
                if profile_name in existing_names:
                    # Add suffix
                    counter = 1
                    base_name = profile_name
                    while profile_name in existing_names:
                        profile_name = f"{base_name} ({counter})"
                        counter += 1
                
                if callback:
                    callback("Чтение архива...", 0, 100)
                
                # Create the profile
                profile = self.create_profile(
                    name=profile_name,
                    minecraft_version=profile_data.get("minecraft_version", "1.20.1"),
                    loader_type=profile_data.get("loader_type"),
                    loader_version=profile_data.get("loader_version"),
                    icon=profile_data.get("icon", "🎮")
                )
                
                game_dir = Path(profile.game_directory)
                
                # Extract files
                files_to_extract = [f for f in zf.namelist() if f != "manifest.json"]
                total_files = len(files_to_extract)
                
                if callback:
                    callback("Извлечение файлов...", 0, total_files)
                
                for i, file_name in enumerate(files_to_extract):
                    target_path = game_dir / file_name
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Extract file
                    with zf.open(file_name) as src, open(target_path, 'wb') as dst:
                        dst.write(src.read())
                    
                    if callback:
                        callback(f"Извлечение {file_name}", i + 1, total_files)
                
                logger.info(f"Imported profile '{profile_name}' from {import_path}")
                logger.info(f"Extracted: {total_files} files to {game_dir}")
                return profile
                
        except zipfile.BadZipFile:
            logger.error(f"Invalid ZIP file: {import_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to import profile: {e}")
            return None
    
    def get_export_info(self, profile_id: str) -> Optional[dict]:
        """
        Get information about what can be exported for a profile.
        
        Returns dict with folder sizes and file counts.
        """
        profile = self.get_profile(profile_id)
        if not profile or not profile.game_directory:
            return None
        
        game_dir = Path(profile.game_directory)
        if not game_dir.exists():
            return None
        
        def get_folder_info(folder_name: str) -> dict:
            folder_path = game_dir / folder_name
            if not folder_path.exists():
                return {"exists": False, "files": 0, "size": 0}
            
            files = list(folder_path.rglob("*"))
            file_count = sum(1 for f in files if f.is_file())
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            return {
                "exists": True,
                "files": file_count,
                "size": total_size,
                "size_mb": round(total_size / (1024 * 1024), 2)
            }
        
        return {
            "mods": get_folder_info("mods"),
            "resourcepacks": get_folder_info("resourcepacks"),
            "shaderpacks": get_folder_info("shaderpacks"),
            "config": get_folder_info("config"),
        }
    
    def add_installed_mod(
        self,
        profile_id: str,
        filename: str,
        source: str,
        mod_id: Optional[str] = None,
        version_id: Optional[str] = None,
        name: Optional[str] = None
    ):
        """Add a mod to profile's installed mods list."""
        profile = self.get_profile(profile_id)
        if not profile:
            return
        
        # Check if already exists
        for mod in profile.installed_mods:
            if mod.get("filename") == filename:
                # Update existing
                mod["source"] = source
                mod["mod_id"] = mod_id
                mod["version_id"] = version_id
                mod["name"] = name
                self._save_profiles()
                return
        
        # Add new
        profile.installed_mods.append({
            "filename": filename,
            "source": source,
            "mod_id": mod_id,
            "version_id": version_id,
            "name": name
        })
        self._save_profiles()
        logger.info(f"Added mod {filename} to profile {profile.name}")
    
    def remove_installed_mod(self, profile_id: str, filename: str):
        """Remove a mod from profile's installed mods list."""
        profile = self.get_profile(profile_id)
        if not profile:
            return
        
        profile.installed_mods = [
            m for m in profile.installed_mods 
            if m.get("filename") != filename
        ]
        self._save_profiles()
    
    def generate_manifest_code(self, profile_id: str) -> Optional[str]:
        """
        Generate a shareable manifest code for a profile.
        Only includes mods from Modrinth/CurseForge (not local mods).
        
        Returns:
            Base64-encoded manifest code or None
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        
        # Filter only mods with known sources
        shareable_mods = []
        for mod in profile.installed_mods:
            source = mod.get("source", "")
            mod_id = mod.get("mod_id")
            if source in ("modrinth", "curseforge") and mod_id:
                shareable_mods.append({
                    "id": mod_id,
                    "src": "mr" if source == "modrinth" else "cf",
                    "v": mod.get("version_id"),
                    "n": mod.get("name", "")[:30]  # Truncate name
                })
        
        manifest = {
            "v": MANIFEST_CODE_VERSION,
            "name": profile.name[:50],
            "mc": profile.minecraft_version,
            "loader": profile.loader_type,
            "loader_v": profile.loader_version,
            "mods": shareable_mods
        }
        
        try:
            # Compact JSON -> gzip -> base64
            json_str = json.dumps(manifest, separators=(',', ':'), ensure_ascii=False)
            compressed = gzip.compress(json_str.encode('utf-8'))
            code = base64.urlsafe_b64encode(compressed).decode('ascii')
            
            # Add prefix for identification
            return f"CL1-{code}"
        except Exception as e:
            logger.error(f"Failed to generate manifest code: {e}")
            return None
    
    @staticmethod
    def parse_manifest_code(code: str) -> Optional[dict]:
        """
        Parse a manifest code back to profile data.
        
        Returns:
            Dict with profile info or None if invalid
        """
        try:
            # Remove prefix
            if code.startswith("CL1-"):
                code = code[4:]
            elif code.startswith("CL"):
                # Try to find version
                parts = code.split("-", 1)
                if len(parts) == 2:
                    code = parts[1]
            
            # Decode: base64 -> gunzip -> JSON
            compressed = base64.urlsafe_b64decode(code)
            json_str = gzip.decompress(compressed).decode('utf-8')
            manifest = json.loads(json_str)
            
            # Validate
            if manifest.get("v") != MANIFEST_CODE_VERSION:
                logger.warning(f"Manifest version mismatch: {manifest.get('v')}")
            
            # Expand mod sources
            mods = []
            for mod in manifest.get("mods", []):
                source = "modrinth" if mod.get("src") == "mr" else "curseforge"
                mods.append({
                    "mod_id": mod.get("id"),
                    "source": source,
                    "version_id": mod.get("v"),
                    "name": mod.get("n", "")
                })
            
            return {
                "name": manifest.get("name", "Imported Profile"),
                "minecraft_version": manifest.get("mc"),
                "loader_type": manifest.get("loader"),
                "loader_version": manifest.get("loader_v"),
                "mods": mods
            }
        except Exception as e:
            logger.error(f"Failed to parse manifest code: {e}")
            return None
    
    def get_local_mods_count(self, profile_id: str) -> int:
        """Count mods that cannot be shared (local only)."""
        profile = self.get_profile(profile_id)
        if not profile:
            return 0
        
        return sum(
            1 for mod in profile.installed_mods
            if mod.get("source") == "local" or not mod.get("mod_id")
        )

