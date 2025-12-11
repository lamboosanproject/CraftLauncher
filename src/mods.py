"""
Mod loader support for CraftLauncher
Supports Forge, NeoForge, Fabric and Quilt installation
"""

import minecraft_launcher_lib as mll
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import requests
import subprocess
import tempfile

from .logger import logger


@dataclass
class ModLoaderVersion:
    """Information about a mod loader version."""
    id: str
    minecraft_version: str
    loader_version: str
    stable: bool = True


class ModManager:
    """Manages mod loaders (Forge/Fabric) installation."""
    
    def __init__(self, minecraft_dir: Path, launcher_core=None):
        self.minecraft_dir = minecraft_dir
        self.mods_dir = minecraft_dir / "mods"
        self.mods_dir.mkdir(parents=True, exist_ok=True)
        self.launcher_core = launcher_core  # For finding Java
    
    # ==================== FABRIC ====================
    
    def get_fabric_versions(self, minecraft_version: str) -> list[ModLoaderVersion]:
        """Get available Fabric loader versions for a Minecraft version."""
        try:
            loaders = mll.fabric.get_all_loader_versions()
            
            versions = []
            for loader in loaders:
                versions.append(ModLoaderVersion(
                    id=f"fabric-loader-{loader['version']}-{minecraft_version}",
                    minecraft_version=minecraft_version,
                    loader_version=loader['version'],
                    stable=loader.get('stable', True)
                ))
            
            return versions
        except Exception as e:
            logger.error(f"Failed to get Fabric versions: {e}")
            return []
    
    def is_fabric_supported(self, minecraft_version: str) -> bool:
        """Check if Fabric supports a Minecraft version."""
        try:
            supported = mll.fabric.get_all_minecraft_versions()
            return any(v['version'] == minecraft_version for v in supported)
        except:
            return False
    
    def install_fabric(
        self,
        minecraft_version: str,
        loader_version: Optional[str] = None,
        callback: Optional[dict] = None
    ) -> Optional[str]:
        """
        Install Fabric mod loader.
        
        Args:
            minecraft_version: Minecraft version
            loader_version: Fabric loader version (latest if None)
            callback: Progress callback dict
            
        Returns:
            Installed version ID or None on failure
        """
        try:
            logger.info(f"Installing Fabric for Minecraft {minecraft_version}")
            
            # Get latest loader version if not specified
            if not loader_version:
                loaders = mll.fabric.get_all_loader_versions()
                if not loaders:
                    raise RuntimeError("No Fabric loader versions available")
                loader_version = loaders[0]['version']
            
            # Install Fabric
            mll.fabric.install_fabric(
                minecraft_version,
                str(self.minecraft_dir),
                loader_version=loader_version,
                callback=callback
            )
            
            version_id = f"fabric-loader-{loader_version}-{minecraft_version}"
            logger.info(f"Fabric installed: {version_id}")
            return version_id
            
        except Exception as e:
            logger.error(f"Failed to install Fabric: {e}")
            return None
    
    # ==================== FORGE ====================
    
    def get_forge_versions(self, minecraft_version: str) -> list[ModLoaderVersion]:
        """Get available Forge versions for a Minecraft version."""
        try:
            forge_versions = mll.forge.list_forge_versions()
            
            if not forge_versions:
                return []
            
            versions = []
            for forge_ver in forge_versions:
                # Forge versions are like "1.21-51.0.33"
                if forge_ver.startswith(f"{minecraft_version}-"):
                    # Extract just the loader part for display
                    loader_part = forge_ver.split('-')[-1] if '-' in forge_ver else forge_ver
                    versions.append(ModLoaderVersion(
                        id=forge_ver,  # Full ID for installation
                        minecraft_version=minecraft_version,
                        loader_version=forge_ver,  # Store full ID
                        stable=True
                    ))
            
            # Sort by version (newest first)
            versions.sort(key=lambda v: v.id, reverse=True)
            return versions[:20]  # Limit to 20
        except Exception as e:
            logger.error(f"Failed to get Forge versions: {e}")
            return []
    
    def is_forge_supported(self, minecraft_version: str) -> bool:
        """Check if Forge supports a Minecraft version."""
        try:
            return mll.forge.find_forge_version(minecraft_version) is not None
        except:
            return False
    
    def install_forge(
        self,
        minecraft_version: str,
        forge_version: Optional[str] = None,
        callback: Optional[dict] = None
    ) -> Optional[str]:
        """
        Install Forge mod loader.
        
        Args:
            minecraft_version: Minecraft version
            forge_version: Forge version (latest if None)
            callback: Progress callback dict
            
        Returns:
            Installed version ID or None on failure
        """
        try:
            logger.info(f"Installing Forge for Minecraft {minecraft_version}")
            
            # Get forge version
            if not forge_version:
                forge_version = mll.forge.find_forge_version(minecraft_version)
                if not forge_version:
                    raise RuntimeError(f"No Forge version found for {minecraft_version}")
            
            # Install Forge
            mll.forge.install_forge_version(
                forge_version,
                str(self.minecraft_dir),
                callback=callback
            )
            
            logger.info(f"Forge installed: {forge_version}")
            return forge_version
            
        except Exception as e:
            logger.error(f"Failed to install Forge: {e}")
            return None
    
    # ==================== NEOFORGE ====================
    
    NEOFORGE_API = "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"
    NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge"
    
    def get_neoforge_versions(self, minecraft_version: str) -> list[ModLoaderVersion]:
        """
        Get available NeoForge versions for a Minecraft version.
        
        NeoForge version scheme: MAJOR.MINOR.PATCH[-beta]
        - MAJOR = MC major version (20 for 1.20.x, 21 for 1.21.x)
        - MINOR = MC minor/patch version (e.g., 4 for 1.20.4, 1 for 1.21.1)
        
        Examples:
        - MC 1.20.1 -> NeoForge 20.1.x
        - MC 1.20.4 -> NeoForge 20.4.x
        - MC 1.21   -> NeoForge 21.0.x (or 21.1.x for first release)
        - MC 1.21.1 -> NeoForge 21.1.x
        - MC 1.21.4 -> NeoForge 21.4.x
        """
        try:
            response = requests.get(self.NEOFORGE_API, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            versions = []
            
            # Parse MC version (e.g., "1.20.4" -> major=20, minor=4)
            mc_parts = minecraft_version.split('.')
            if len(mc_parts) < 2:
                return []
            
            mc_major = int(mc_parts[1])  # "1.20.4" -> 20
            mc_minor = int(mc_parts[2]) if len(mc_parts) > 2 else 0  # -> 4 (or 0 for "1.21")
            
            # NeoForge version prefix to match
            nf_prefix = f"{mc_major}.{mc_minor}."
            
            for ver in data.get("versions", []):
                # Skip snapshot/craftmine versions
                if "craftmine" in ver.lower() or ver.startswith("0."):
                    continue
                    
                # Check if version matches MC version
                if ver.startswith(nf_prefix):
                    versions.append(ModLoaderVersion(
                        id=ver,
                        minecraft_version=minecraft_version,
                        loader_version=ver,
                        stable="beta" not in ver.lower()
                    ))
            
            # Sort: stable first, then by version number (newest first)
            def version_sort_key(v):
                # Extract patch number for sorting
                try:
                    parts = v.loader_version.replace("-beta", "").split(".")
                    patch = int(parts[2]) if len(parts) > 2 else 0
                    return (not v.stable, -patch)  # stable first, then by patch descending
                except:
                    return (not v.stable, 0)
            
            versions.sort(key=version_sort_key)
            return versions
            
        except Exception as e:
            logger.error(f"Failed to get NeoForge versions: {e}")
            return []
    
    def is_neoforge_supported(self, minecraft_version: str) -> bool:
        """
        Check if NeoForge supports a Minecraft version.
        NeoForge supports Minecraft 1.20.1 and newer.
        """
        try:
            parts = minecraft_version.split('.')
            if len(parts) >= 2:
                major = int(parts[0])
                minor = int(parts[1])
                # NeoForge only supports 1.20.1+
                if major == 1 and minor >= 20:
                    return True
            return False
        except Exception:
            return False
    
    def install_neoforge(
        self,
        minecraft_version: str,
        neoforge_version: Optional[str] = None,
        callback: Optional[dict] = None
    ) -> Optional[str]:
        """
        Install NeoForge mod loader.
        
        Args:
            minecraft_version: Minecraft version
            neoforge_version: NeoForge version (latest if None)
            callback: Progress callback dict
            
        Returns:
            Installed version ID or None on failure
        """
        try:
            logger.info(f"Installing NeoForge for Minecraft {minecraft_version}")
            
            # Ensure launcher_profiles.json exists (required by NeoForge installer)
            profiles_file = self.minecraft_dir / "launcher_profiles.json"
            if not profiles_file.exists():
                import json
                profiles_data = {
                    "profiles": {},
                    "selectedProfile": "(Default)",
                    "authenticationDatabase": {},
                    "launcherVersion": {
                        "name": "CraftLauncher",
                        "format": 21
                    }
                }
                profiles_file.write_text(json.dumps(profiles_data, indent=2))
                logger.info(f"Created launcher_profiles.json for NeoForge installer")
            
            # Get neoforge version
            if not neoforge_version:
                versions = self.get_neoforge_versions(minecraft_version)
                if not versions:
                    raise RuntimeError(f"No NeoForge version found for {minecraft_version}")
                # Get latest stable or first available
                stable_versions = [v for v in versions if v.stable]
                neoforge_version = stable_versions[0].id if stable_versions else versions[0].id
            
            if callback and "setStatus" in callback:
                callback["setStatus"](f"Скачивание NeoForge {neoforge_version}...")
            
            # Download installer
            installer_url = f"{self.NEOFORGE_MAVEN}/{neoforge_version}/neoforge-{neoforge_version}-installer.jar"
            logger.info(f"Downloading NeoForge installer from {installer_url}")
            
            response = requests.get(installer_url, timeout=120, stream=True)
            response.raise_for_status()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                installer_path = tmp.name
            
            if callback and "setStatus" in callback:
                callback["setStatus"](f"Установка NeoForge {neoforge_version}...")
            
            # Run installer in headless mode
            logger.info(f"Running NeoForge installer: {installer_path}")
            
            # Find Java using launcher_core if available
            java_path = "java"
            if self.launcher_core:
                java_path = self.launcher_core.find_java() or "java"
            else:
                # Fallback: try to find java in PATH
                import shutil
                java_in_path = shutil.which("java")
                if java_in_path:
                    java_path = java_in_path
            
            result = subprocess.run(
                [java_path, "-jar", installer_path, "--installClient", str(self.minecraft_dir)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Log output for debugging
            if result.stdout:
                logger.debug(f"NeoForge installer stdout: {result.stdout[:500]}")
            if result.stderr:
                logger.debug(f"NeoForge installer stderr: {result.stderr[:500]}")
            
            # Clean up installer
            Path(installer_path).unlink(missing_ok=True)
            
            if result.returncode != 0:
                error_output = result.stderr or result.stdout or "Unknown error"
                logger.error(f"NeoForge installer failed (code {result.returncode}): {error_output[:500]}")
                raise RuntimeError(f"Installer failed: {error_output[:200]}")
            
            version_id = f"neoforge-{neoforge_version}"
            logger.info(f"NeoForge installed: {version_id}")
            return version_id
            
        except Exception as e:
            logger.error(f"Failed to install NeoForge: {e}")
            return None
    
    # ==================== QUILT ====================
    
    def get_quilt_versions(self, minecraft_version: str) -> list[ModLoaderVersion]:
        """Get available Quilt loader versions for a Minecraft version."""
        try:
            loaders = mll.quilt.get_all_loader_versions()
            
            versions = []
            for loader in loaders:
                versions.append(ModLoaderVersion(
                    id=f"quilt-loader-{loader['version']}-{minecraft_version}",
                    minecraft_version=minecraft_version,
                    loader_version=loader['version'],
                    stable=True
                ))
            
            return versions
        except Exception as e:
            logger.error(f"Failed to get Quilt versions: {e}")
            return []
    
    def is_quilt_supported(self, minecraft_version: str) -> bool:
        """Check if Quilt supports a Minecraft version."""
        try:
            supported = mll.quilt.get_all_minecraft_versions()
            return any(v['version'] == minecraft_version for v in supported)
        except:
            return False
    
    def install_quilt(
        self,
        minecraft_version: str,
        loader_version: Optional[str] = None,
        callback: Optional[dict] = None
    ) -> Optional[str]:
        """
        Install Quilt mod loader.
        
        Args:
            minecraft_version: Minecraft version
            loader_version: Quilt loader version (latest if None)
            callback: Progress callback dict
            
        Returns:
            Installed version ID or None on failure
        """
        try:
            logger.info(f"Installing Quilt for Minecraft {minecraft_version}")
            
            # Get latest loader version if not specified
            if not loader_version:
                loaders = mll.quilt.get_all_loader_versions()
                if not loaders:
                    raise RuntimeError("No Quilt loader versions available")
                loader_version = loaders[0]['version']
            
            # Install Quilt
            mll.quilt.install_quilt(
                minecraft_version,
                str(self.minecraft_dir),
                loader_version=loader_version,
                callback=callback
            )
            
            version_id = f"quilt-loader-{loader_version}-{minecraft_version}"
            logger.info(f"Quilt installed: {version_id}")
            return version_id
            
        except Exception as e:
            logger.error(f"Failed to install Quilt: {e}")
            return None
    
    # ==================== OPTIFINE ====================
    
    OPTIFINE_DOWNLOADS = "https://optifine.net/downloads"
    OPTIFINE_ADLOADX = "https://optifine.net/adloadx"
    
    def get_optifine_versions(self, minecraft_version: str) -> list[ModLoaderVersion]:
        """Get available OptiFine versions for a Minecraft version."""
        try:
            # OptiFine page needs to be parsed
            response = requests.get(self.OPTIFINE_DOWNLOADS, timeout=15)
            response.raise_for_status()
            
            versions = []
            html = response.text
            
            # Parse OptiFine download links
            # Format: OptiFine_1.21_HD_U_J1.jar or similar
            import re
            pattern = rf'OptiFine_{re.escape(minecraft_version)}[._]([A-Za-z0-9_]+)\.jar'
            matches = re.findall(pattern, html)
            
            seen = set()
            for match in matches:
                version_str = match.replace("_", " ").strip()
                if version_str not in seen:
                    seen.add(version_str)
                    # Store as HD_U_J1 format
                    versions.append(ModLoaderVersion(
                        id=f"OptiFine_{minecraft_version}_{match}",
                        minecraft_version=minecraft_version,
                        loader_version=match,  # e.g., "HD_U_J1"
                        stable="preview" not in match.lower()
                    ))
            
            return versions
        except Exception as e:
            logger.error(f"Failed to get OptiFine versions: {e}")
            return []
    
    def is_optifine_supported(self, minecraft_version: str) -> bool:
        """Check if OptiFine supports a Minecraft version."""
        try:
            versions = self.get_optifine_versions(minecraft_version)
            return len(versions) > 0
        except Exception:
            return False
    
    def install_optifine(
        self,
        minecraft_version: str,
        optifine_version: Optional[str] = None,
        callback: Optional[dict] = None
    ) -> Optional[str]:
        """
        Install OptiFine.
        
        Args:
            minecraft_version: Minecraft version
            optifine_version: OptiFine version (e.g., "HD_U_J1")
            callback: Progress callback dict
            
        Returns:
            Installed version ID or None on failure
        """
        try:
            logger.info(f"Installing OptiFine for Minecraft {minecraft_version}")
            
            # Get optifine version if not specified
            if not optifine_version:
                versions = self.get_optifine_versions(minecraft_version)
                if not versions:
                    raise RuntimeError(f"No OptiFine version found for {minecraft_version}")
                optifine_version = versions[0].loader_version
            
            if callback and "setStatus" in callback:
                callback["setStatus"](f"Скачивание OptiFine {optifine_version}...")
            
            # OptiFine requires downloading through their adloadx page
            # First, get the download page
            filename = f"OptiFine_{minecraft_version}_{optifine_version}.jar"
            download_page_url = f"{self.OPTIFINE_ADLOADX}?f={filename}"
            
            logger.info(f"Getting OptiFine download page: {download_page_url}")
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # Get the download page to find actual download link
            response = session.get(download_page_url, timeout=15)
            response.raise_for_status()
            
            # Parse the actual download link
            import re
            match = re.search(r"href='(downloadx\?f=[^']+)'", response.text)
            if not match:
                # Try alternate pattern
                match = re.search(r'href="(https://[^"]*optifine[^"]*\.jar)"', response.text, re.I)
            
            if not match:
                raise RuntimeError("Could not find OptiFine download link")
            
            download_url = match.group(1)
            if not download_url.startswith("http"):
                download_url = f"https://optifine.net/{download_url}"
            
            logger.info(f"Downloading OptiFine from: {download_url}")
            
            response = session.get(download_url, timeout=120, stream=True)
            response.raise_for_status()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                installer_path = tmp.name
            
            if callback and "setStatus" in callback:
                callback["setStatus"](f"Установка OptiFine {optifine_version}...")
            
            # Run OptiFine installer
            logger.info(f"Running OptiFine installer: {installer_path}")
            
            from .launcher_core import LauncherCore
            java_path = LauncherCore.find_java(None) or "java"
            
            # OptiFine installer needs to run in the minecraft directory
            result = subprocess.run(
                [java_path, "-jar", installer_path],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.minecraft_dir)
            )
            
            # Clean up installer
            Path(installer_path).unlink(missing_ok=True)
            
            # OptiFine installer is interactive, but we can also just copy the jar
            # to versions folder manually if needed
            version_id = f"{minecraft_version}-OptiFine_{optifine_version}"
            
            # Check if version was created
            version_dir = self.minecraft_dir / "versions" / version_id
            if not version_dir.exists():
                logger.warning("OptiFine installer didn't create version, trying manual install...")
                # Manual install - copy jar and create json
                version_dir.mkdir(parents=True, exist_ok=True)
                
                # Re-download the jar for manual install
                response = session.get(download_url, timeout=120)
                jar_path = version_dir / f"{version_id}.jar"
                jar_path.write_bytes(response.content)
                
                # Create minimal version JSON
                import json
                version_json = {
                    "id": version_id,
                    "inheritsFrom": minecraft_version,
                    "type": "release",
                    "mainClass": "net.minecraft.launchwrapper.Launch",
                    "minecraftArguments": "--tweakClass optifine.OptiFineTweaker"
                }
                json_path = version_dir / f"{version_id}.json"
                json_path.write_text(json.dumps(version_json, indent=2))
            
            logger.info(f"OptiFine installed: {version_id}")
            return version_id
            
        except Exception as e:
            logger.error(f"Failed to install OptiFine: {e}")
            return None
    
    def install_optifine_as_mod(
        self,
        minecraft_version: str,
        optifine_version: Optional[str] = None,
        game_directory: Optional[Path] = None
    ) -> Optional[str]:
        """
        Install OptiFine as a mod (for use with Forge).
        Downloads OptiFine jar and places it in the mods folder.
        
        Args:
            minecraft_version: Minecraft version
            optifine_version: OptiFine version (e.g., "HD_U_J1")
            game_directory: Custom game directory (uses default mods_dir if None)
            
        Returns:
            Path to installed mod or None on failure
        """
        try:
            logger.info(f"Installing OptiFine as mod for Minecraft {minecraft_version}")
            
            # Get optifine version if not specified
            if not optifine_version:
                versions = self.get_optifine_versions(minecraft_version)
                if not versions:
                    raise RuntimeError(f"No OptiFine version found for {minecraft_version}")
                optifine_version = versions[0].loader_version
            
            # Download OptiFine jar
            filename = f"OptiFine_{minecraft_version}_{optifine_version}.jar"
            download_page_url = f"{self.OPTIFINE_ADLOADX}?f={filename}"
            
            logger.info(f"Getting OptiFine download page: {download_page_url}")
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # Get the download page
            response = session.get(download_page_url, timeout=15)
            response.raise_for_status()
            
            # Parse the actual download link
            import re
            match = re.search(r"href='(downloadx\?f=[^']+)'", response.text)
            if not match:
                match = re.search(r'href="(https://[^"]*optifine[^"]*\.jar)"', response.text, re.I)
            
            if not match:
                raise RuntimeError("Could not find OptiFine download link")
            
            download_url = match.group(1)
            if not download_url.startswith("http"):
                download_url = f"https://optifine.net/{download_url}"
            
            logger.info(f"Downloading OptiFine from: {download_url}")
            
            response = session.get(download_url, timeout=120)
            response.raise_for_status()
            
            # Determine mods folder - use custom game_directory if provided
            if game_directory:
                target_mods_dir = Path(game_directory) / "mods"
            else:
                target_mods_dir = self.mods_dir
            
            # Create mods folder if it doesn't exist
            target_mods_dir.mkdir(parents=True, exist_ok=True)
            
            # Save to mods folder
            mod_path = target_mods_dir / filename
            mod_path.write_bytes(response.content)
            
            logger.info(f"OptiFine mod installed: {mod_path}")
            return str(mod_path)
            
        except Exception as e:
            logger.error(f"Failed to install OptiFine as mod: {e}")
            return None
    
    # ==================== MODS FOLDER ====================
    
    def get_mods_list(self) -> list[dict]:
        """Get list of installed mods."""
        mods = []
        
        if not self.mods_dir.exists():
            return mods
        
        for mod_file in self.mods_dir.glob("*.jar"):
            mods.append({
                "name": mod_file.stem,
                "filename": mod_file.name,
                "path": str(mod_file),
                "size": mod_file.stat().st_size,
                "enabled": True
            })
        
        # Check for disabled mods
        for mod_file in self.mods_dir.glob("*.jar.disabled"):
            mods.append({
                "name": mod_file.stem.replace(".jar", ""),
                "filename": mod_file.name,
                "path": str(mod_file),
                "size": mod_file.stat().st_size,
                "enabled": False
            })
        
        return sorted(mods, key=lambda m: m["name"].lower())
    
    def toggle_mod(self, mod_path: str) -> bool:
        """Enable/disable a mod by renaming its file."""
        path = Path(mod_path)
        
        if not path.exists():
            return False
        
        if path.suffix == ".disabled":
            # Enable mod
            new_path = path.with_suffix("")
        else:
            # Disable mod
            new_path = path.with_suffix(path.suffix + ".disabled")
        
        try:
            path.rename(new_path)
            logger.info(f"Toggled mod: {path.name} -> {new_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to toggle mod: {e}")
            return False
    
    def delete_mod(self, mod_path: str) -> bool:
        """Delete a mod file."""
        path = Path(mod_path)
        
        if not path.exists():
            return False
        
        try:
            path.unlink()
            logger.info(f"Deleted mod: {path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete mod: {e}")
            return False
    
    def open_mods_folder(self):
        """Open the mods folder in file manager."""
        self._open_folder(self.mods_dir)
    
    def open_minecraft_folder(self):
        """Open the minecraft folder in file manager."""
        self._open_folder(self.minecraft_dir)
    
    def _open_folder(self, folder: Path):
        """Open a folder in the system file manager."""
        import platform
        
        system = platform.system()
        
        try:
            if system == "Windows":
                subprocess.run(["explorer", str(folder)], check=False)
            elif system == "Darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:  # Linux
                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception as e:
            logger.error("Failed to open folder: %s", e)

