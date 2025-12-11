"""
Ely.by API integration for CraftLauncher
Documentation: https://docs.ely.by/ru/api.html

Ely.by provides:
- Mojang API simulation
- Custom skins system
- OAuth2 authorization
- Authlib-injector support for game integration
"""

import requests
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import hashlib
import os

from .logger import logger

# Base URLs
ELYBY_AUTH_SERVER = "https://authserver.ely.by"
ELYBY_SKINS_SERVER = "https://skinsystem.ely.by"
ELYBY_ACCOUNT_SERVER = "https://account.ely.by"

# Authlib-injector GitHub releases
# https://github.com/yushijinhun/authlib-injector/releases
AUTHLIB_INJECTOR_GITHUB_API = "https://api.github.com/repos/yushijinhun/authlib-injector/releases/latest"
AUTHLIB_INJECTOR_FALLBACK_URL = "https://github.com/yushijinhun/authlib-injector/releases/download/v1.2.6/authlib-injector-1.2.6.jar"


@dataclass
class ElybyProfile:
    """Ely.by user profile."""
    uuid: str
    username: str
    skin_url: Optional[str] = None
    cape_url: Optional[str] = None
    skin_model: str = "default"  # "default" or "slim"


class ElybyAPI:
    """Client for Ely.by API."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize Ely.by API client.
        
        Args:
            cache_dir: Directory for caching skins and authlib-injector
        """
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CraftLauncher/1.0"
        })
        
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            self.cache_dir = Path.home() / ".config" / "CraftLauncher" / "cache"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.skins_cache = self.cache_dir / "skins"
        self.skins_cache.mkdir(exist_ok=True)
    
    def get_uuid_by_username(self, username: str) -> Optional[str]:
        """
        Get UUID by username.
        
        Args:
            username: Minecraft username
            
        Returns:
            UUID string or None if not found
        """
        try:
            url = f"{ELYBY_AUTH_SERVER}/api/users/profiles/minecraft/{username}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 204:
                logger.debug(f"User {username} not found on Ely.by")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            uuid = data.get("id")
            logger.info(f"Found Ely.by UUID for {username}: {uuid}")
            return uuid
            
        except requests.RequestException as e:
            logger.error(f"Failed to get UUID for {username}: {e}")
            return None
    
    def get_profile_by_uuid(self, uuid: str) -> Optional[ElybyProfile]:
        """
        Get full profile information by UUID.
        
        Args:
            uuid: User UUID (with or without dashes)
            
        Returns:
            ElybyProfile or None if not found
        """
        # Remove dashes from UUID
        uuid = uuid.replace("-", "")
        
        try:
            url = f"{ELYBY_AUTH_SERVER}/api/user/profiles/{uuid}/names"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 204:
                return None
            
            response.raise_for_status()
            names_history = response.json()
            
            if not names_history:
                return None
            
            # Get the current username (last in history)
            current_name = names_history[-1]["name"]
            
            # Get skin information
            skin_url, cape_url, skin_model = self._get_skin_info(current_name)
            
            return ElybyProfile(
                uuid=uuid,
                username=current_name,
                skin_url=skin_url,
                cape_url=cape_url,
                skin_model=skin_model
            )
            
        except requests.RequestException as e:
            logger.error(f"Failed to get profile for UUID {uuid}: {e}")
            return None
    
    def get_profile_by_username(self, username: str) -> Optional[ElybyProfile]:
        """
        Get full profile by username.
        
        Args:
            username: Minecraft username
            
        Returns:
            ElybyProfile or None if not found
        """
        uuid = self.get_uuid_by_username(username)
        if uuid:
            return self.get_profile_by_uuid(uuid)
        
        # Return basic profile for users not registered on Ely.by
        return ElybyProfile(
            uuid="",
            username=username,
            skin_url=None,
            cape_url=None
        )
    
    def _get_skin_info(self, username: str) -> tuple[Optional[str], Optional[str], str]:
        """
        Get skin and cape URLs for a user.
        
        Returns:
            Tuple of (skin_url, cape_url, skin_model)
        """
        skin_url = f"{ELYBY_SKINS_SERVER}/skins/{username}.png"
        cape_url = f"{ELYBY_SKINS_SERVER}/cloaks/{username}.png"
        
        # Check if skin exists
        try:
            skin_response = self.session.head(skin_url, timeout=5)
            if skin_response.status_code != 200:
                skin_url = None
        except:
            skin_url = None
        
        # Check if cape exists
        try:
            cape_response = self.session.head(cape_url, timeout=5)
            if cape_response.status_code != 200:
                cape_url = None
        except:
            cape_url = None
        
        # Get skin model (slim/default)
        skin_model = "default"
        try:
            # Ely.by provides textures endpoint with model info
            textures_url = f"{ELYBY_SKINS_SERVER}/textures/{username}"
            textures_response = self.session.get(textures_url, timeout=5)
            if textures_response.status_code == 200:
                textures_data = textures_response.json()
                if textures_data.get("SKIN", {}).get("metadata", {}).get("model") == "slim":
                    skin_model = "slim"
        except:
            pass
        
        return skin_url, cape_url, skin_model
    
    def download_skin(self, username: str) -> Optional[Path]:
        """
        Download and cache user's skin.
        
        Args:
            username: Minecraft username
            
        Returns:
            Path to cached skin file or None
        """
        cache_file = self.skins_cache / f"{username.lower()}.png"
        
        # Check cache (valid for 1 hour)
        if cache_file.exists():
            age = os.path.getmtime(cache_file)
            import time
            if time.time() - age < 3600:  # 1 hour
                logger.debug(f"Using cached skin for {username}")
                return cache_file
        
        skin_url = f"{ELYBY_SKINS_SERVER}/skins/{username}.png"
        
        try:
            response = self.session.get(skin_url, timeout=10)
            if response.status_code == 200:
                cache_file.write_bytes(response.content)
                logger.info(f"Downloaded skin for {username}")
                return cache_file
            else:
                logger.debug(f"No skin found for {username} on Ely.by")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Failed to download skin for {username}: {e}")
            return None
    
    def download_head_render(self, username: str, size: int = 100) -> Optional[Path]:
        """
        Download rendered head image (for display in launcher).
        
        Args:
            username: Minecraft username
            size: Image size in pixels
            
        Returns:
            Path to cached head render or None
        """
        cache_file = self.skins_cache / f"{username.lower()}_head_{size}.png"
        
        # Check cache
        if cache_file.exists():
            age = os.path.getmtime(cache_file)
            import time
            if time.time() - age < 3600:
                return cache_file
        
        # Ely.by provides rendered heads
        head_url = f"{ELYBY_SKINS_SERVER}/skins/{username}.png"
        # Alternative: Use skin and crop head ourselves
        
        # Try to get the 3D head render from crafatar (works with Ely.by skins too via UUID)
        uuid = self.get_uuid_by_username(username)
        if uuid:
            # Use crafatar or similar service for 3D render
            render_url = f"https://crafatar.com/renders/head/{uuid}?size={size}&overlay"
        else:
            # Fallback to Steve head
            render_url = f"https://crafatar.com/renders/head/8667ba71-b85a-4004-af54-457a9734eed7?size={size}&overlay"
        
        try:
            response = self.session.get(render_url, timeout=10)
            if response.status_code == 200:
                cache_file.write_bytes(response.content)
                logger.info(f"Downloaded head render for {username}")
                return cache_file
                
        except requests.RequestException as e:
            logger.debug(f"Failed to download head render for {username}: {e}")
        
        return None
    
    def get_bulk_uuids(self, usernames: list[str]) -> dict[str, str]:
        """
        Get UUIDs for multiple usernames at once.
        
        Args:
            usernames: List of usernames (max 100)
            
        Returns:
            Dict mapping usernames to UUIDs
        """
        if len(usernames) > 100:
            raise ValueError("Maximum 100 usernames per request")
        
        try:
            url = f"{ELYBY_AUTH_SERVER}/api/profiles/minecraft"
            response = self.session.post(url, json=usernames, timeout=15)
            response.raise_for_status()
            
            result = {}
            for item in response.json():
                result[item["name"]] = item["id"]
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"Failed to get bulk UUIDs: {e}")
            return {}
    
    def download_authlib_injector(self) -> Optional[Path]:
        """
        Download authlib-injector for game integration from GitHub.
        This allows the game to use Ely.by for authentication and skins.
        
        Returns:
            Path to authlib-injector.jar or None
        """
        injector_path = self.cache_dir / "authlib-injector.jar"
        
        # Check if already downloaded and not too old (check weekly)
        if injector_path.exists():
            age = os.path.getmtime(injector_path)
            import time
            if time.time() - age < 7 * 24 * 3600:  # 1 week
                logger.debug("Using cached authlib-injector")
                return injector_path
        
        download_url = None
        
        # Try to get latest release from GitHub API
        try:
            logger.info("Checking latest authlib-injector release...")
            response = self.session.get(
                AUTHLIB_INJECTOR_GITHUB_API,
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=15
            )
            
            if response.status_code == 200:
                release_data = response.json()
                # Find the .jar asset
                for asset in release_data.get("assets", []):
                    if asset["name"].endswith(".jar"):
                        download_url = asset["browser_download_url"]
                        logger.info(f"Found latest version: {release_data.get('tag_name', 'unknown')}")
                        break
        except Exception as e:
            logger.warning(f"Failed to get latest release info: {e}")
        
        # Fallback to known version
        if not download_url:
            logger.info("Using fallback authlib-injector URL")
            download_url = AUTHLIB_INJECTOR_FALLBACK_URL
        
        # Download the file
        try:
            logger.info(f"Downloading authlib-injector from GitHub...")
            response = self.session.get(download_url, timeout=120, stream=True)
            response.raise_for_status()
            
            # Write to file
            with open(injector_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded authlib-injector to {injector_path}")
            return injector_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to download authlib-injector: {e}")
            return None
    
    def get_jvm_args_for_injection(self) -> list[str]:
        """
        Get JVM arguments needed to use Ely.by with the game.
        
        Returns:
            List of JVM arguments
        """
        injector_path = self.download_authlib_injector()
        
        if not injector_path or not injector_path.exists():
            logger.warning("authlib-injector not available, skins won't work in game")
            return []
        
        return [
            f"-javaagent:{injector_path}={ELYBY_AUTH_SERVER}",
            "-Dauthlibinjector.side=client",
        ]


# Global instance
elyby = ElybyAPI()

