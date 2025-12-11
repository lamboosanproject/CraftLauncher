"""
Custom profiles/versions management for CraftLauncher
Allows creating custom game configurations with specific MC version and mod loader
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime
import uuid

from .logger import logger


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

