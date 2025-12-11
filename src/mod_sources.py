"""
Mod sources integration for CraftLauncher
Supports CurseForge and Modrinth APIs
"""

import requests
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Callable
from datetime import datetime
import hashlib
import json

from .logger import logger


@dataclass
class ModInfo:
    """Information about a mod."""
    id: str
    name: str
    slug: str
    description: str
    author: str
    downloads: int
    icon_url: Optional[str]
    source: str  # "curseforge" or "modrinth"
    categories: List[str]
    url: str
    
    # For display
    @property
    def downloads_formatted(self) -> str:
        if self.downloads >= 1_000_000:
            return f"{self.downloads / 1_000_000:.1f}M"
        elif self.downloads >= 1_000:
            return f"{self.downloads / 1_000:.1f}K"
        return str(self.downloads)


@dataclass
class ModVersion:
    """A specific version of a mod."""
    id: str
    mod_id: str
    name: str
    version_number: str
    minecraft_versions: List[str]
    loaders: List[str]
    download_url: str
    file_name: str
    file_size: int
    date_published: str
    source: str
    dependencies: List[dict]  # List of dependency info


class ModrinthAPI:
    """Modrinth API client - Open API, no key required."""
    
    BASE_URL = "https://api.modrinth.com/v2"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CraftLauncher/1.0 (https://github.com/craftlauncher)"
        })
    
    def search_mods(
        self,
        query: str,
        minecraft_version: Optional[str] = None,
        loader: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[ModInfo]:
        """Search for mods on Modrinth."""
        try:
            params = {
                "query": query,
                "limit": limit,
                "offset": offset,
                "facets": []
            }
            
            facets = []
            if minecraft_version:
                facets.append([f"versions:{minecraft_version}"])
            if loader:
                facets.append([f"categories:{loader}"])
            facets.append(["project_type:mod"])
            
            if facets:
                params["facets"] = json.dumps(facets)
            
            response = self.session.get(f"{self.BASE_URL}/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            mods = []
            for hit in data.get("hits", []):
                mods.append(ModInfo(
                    id=hit["project_id"],
                    name=hit["title"],
                    slug=hit["slug"],
                    description=hit.get("description", ""),
                    author=hit.get("author", "Unknown"),
                    downloads=hit.get("downloads", 0),
                    icon_url=hit.get("icon_url"),
                    source="modrinth",
                    categories=hit.get("categories", []),
                    url=f"https://modrinth.com/mod/{hit['slug']}"
                ))
            
            logger.info(f"Modrinth search '{query}': found {len(mods)} mods")
            return mods
            
        except Exception as e:
            logger.error(f"Modrinth search error: {e}")
            return []
    
    def get_mod(self, mod_id: str) -> Optional[ModInfo]:
        """Get detailed mod info."""
        try:
            response = self.session.get(f"{self.BASE_URL}/project/{mod_id}")
            response.raise_for_status()
            data = response.json()
            
            # Get team/author info
            team_response = self.session.get(f"{self.BASE_URL}/project/{mod_id}/members")
            team_data = team_response.json() if team_response.ok else []
            author = team_data[0]["user"]["username"] if team_data else "Unknown"
            
            return ModInfo(
                id=data["id"],
                name=data["title"],
                slug=data["slug"],
                description=data.get("description", ""),
                author=author,
                downloads=data.get("downloads", 0),
                icon_url=data.get("icon_url"),
                source="modrinth",
                categories=data.get("categories", []),
                url=f"https://modrinth.com/mod/{data['slug']}"
            )
            
        except Exception as e:
            logger.error(f"Modrinth get mod error: {e}")
            return None
    
    def get_mod_versions(
        self,
        mod_id: str,
        minecraft_version: Optional[str] = None,
        loader: Optional[str] = None
    ) -> List[ModVersion]:
        """Get available versions for a mod."""
        try:
            params = {}
            if minecraft_version:
                params["game_versions"] = json.dumps([minecraft_version])
            if loader:
                params["loaders"] = json.dumps([loader])
            
            response = self.session.get(
                f"{self.BASE_URL}/project/{mod_id}/version",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            versions = []
            for ver in data:
                if ver.get("files"):
                    primary_file = ver["files"][0]
                    for f in ver["files"]:
                        if f.get("primary"):
                            primary_file = f
                            break
                    
                    versions.append(ModVersion(
                        id=ver["id"],
                        mod_id=mod_id,
                        name=ver.get("name", ver["version_number"]),
                        version_number=ver["version_number"],
                        minecraft_versions=ver.get("game_versions", []),
                        loaders=ver.get("loaders", []),
                        download_url=primary_file["url"],
                        file_name=primary_file["filename"],
                        file_size=primary_file.get("size", 0),
                        date_published=ver.get("date_published", ""),
                        source="modrinth",
                        dependencies=[
                            {"id": dep["project_id"], "type": dep["dependency_type"]}
                            for dep in ver.get("dependencies", [])
                            if dep.get("project_id")
                        ]
                    ))
            
            return versions
            
        except Exception as e:
            logger.error(f"Modrinth get versions error: {e}")
            return []
    
    def download_mod(
        self,
        version: ModVersion,
        destination: Path,
        callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[Path]:
        """Download a mod version to destination folder."""
        try:
            destination.mkdir(parents=True, exist_ok=True)
            file_path = destination / version.file_name
            
            response = self.session.get(version.download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if callback:
                        callback(downloaded, total_size)
            
            logger.info(f"Downloaded mod: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Modrinth download error: {e}")
            return None


class CurseForgeAPI:
    """CurseForge API client - Requires API key."""
    
    BASE_URL = "https://api.curseforge.com/v1"
    MINECRAFT_GAME_ID = 432
    MOD_CLASS_ID = 6
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "x-api-key": api_key
        })
    
    def _loader_to_type(self, loader: str) -> Optional[int]:
        """Convert loader name to CurseForge modLoaderType."""
        loaders = {
            "forge": 1,
            "cauldron": 2,
            "liteloader": 3,
            "fabric": 4,
            "quilt": 5,
            "neoforge": 6
        }
        return loaders.get(loader.lower())
    
    def search_mods(
        self,
        query: str,
        minecraft_version: Optional[str] = None,
        loader: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[ModInfo]:
        """Search for mods on CurseForge."""
        try:
            params = {
                "gameId": self.MINECRAFT_GAME_ID,
                "classId": self.MOD_CLASS_ID,
                "searchFilter": query,
                "pageSize": limit,
                "index": offset,
                "sortField": 2,  # Popularity
                "sortOrder": "desc"
            }
            
            if minecraft_version:
                params["gameVersion"] = minecraft_version
            if loader:
                loader_type = self._loader_to_type(loader)
                if loader_type:
                    params["modLoaderType"] = loader_type
            
            response = self.session.get(f"{self.BASE_URL}/mods/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            mods = []
            for mod in data.get("data", []):
                authors = [a["name"] for a in mod.get("authors", [])]
                
                mods.append(ModInfo(
                    id=str(mod["id"]),
                    name=mod["name"],
                    slug=mod["slug"],
                    description=mod.get("summary", ""),
                    author=authors[0] if authors else "Unknown",
                    downloads=mod.get("downloadCount", 0),
                    icon_url=mod.get("logo", {}).get("url"),
                    source="curseforge",
                    categories=[c["name"] for c in mod.get("categories", [])],
                    url=mod.get("links", {}).get("websiteUrl", f"https://www.curseforge.com/minecraft/mc-mods/{mod['slug']}")
                ))
            
            logger.info(f"CurseForge search '{query}': found {len(mods)} mods")
            return mods
            
        except Exception as e:
            logger.error(f"CurseForge search error: {e}")
            return []
    
    def get_mod(self, mod_id: str) -> Optional[ModInfo]:
        """Get detailed mod info."""
        try:
            response = self.session.get(f"{self.BASE_URL}/mods/{mod_id}")
            response.raise_for_status()
            data = response.json().get("data", {})
            
            authors = [a["name"] for a in data.get("authors", [])]
            
            return ModInfo(
                id=str(data["id"]),
                name=data["name"],
                slug=data["slug"],
                description=data.get("summary", ""),
                author=authors[0] if authors else "Unknown",
                downloads=data.get("downloadCount", 0),
                icon_url=data.get("logo", {}).get("url"),
                source="curseforge",
                categories=[c["name"] for c in data.get("categories", [])],
                url=data.get("links", {}).get("websiteUrl", "")
            )
            
        except Exception as e:
            logger.error(f"CurseForge get mod error: {e}")
            return None
    
    def get_mod_versions(
        self,
        mod_id: str,
        minecraft_version: Optional[str] = None,
        loader: Optional[str] = None
    ) -> List[ModVersion]:
        """Get available versions for a mod."""
        try:
            params = {"pageSize": 50}
            
            if minecraft_version:
                params["gameVersion"] = minecraft_version
            if loader:
                loader_type = self._loader_to_type(loader)
                if loader_type:
                    params["modLoaderType"] = loader_type
            
            response = self.session.get(
                f"{self.BASE_URL}/mods/{mod_id}/files",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            versions = []
            for file in data.get("data", []):
                versions.append(ModVersion(
                    id=str(file["id"]),
                    mod_id=mod_id,
                    name=file.get("displayName", file["fileName"]),
                    version_number=file.get("displayName", ""),
                    minecraft_versions=file.get("gameVersions", []),
                    loaders=[],  # CurseForge includes loaders in gameVersions
                    download_url=file.get("downloadUrl", ""),
                    file_name=file["fileName"],
                    file_size=file.get("fileLength", 0),
                    date_published=file.get("fileDate", ""),
                    source="curseforge",
                    dependencies=[
                        {"id": str(dep["modId"]), "type": self._dep_type(dep["relationType"])}
                        for dep in file.get("dependencies", [])
                    ]
                ))
            
            return versions
            
        except Exception as e:
            logger.error(f"CurseForge get versions error: {e}")
            return []
    
    def _dep_type(self, relation_type: int) -> str:
        """Convert CurseForge dependency type to string."""
        types = {
            1: "embedded",
            2: "optional",
            3: "required",
            4: "tool",
            5: "incompatible",
            6: "include"
        }
        return types.get(relation_type, "unknown")
    
    def download_mod(
        self,
        version: ModVersion,
        destination: Path,
        callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[Path]:
        """Download a mod version to destination folder."""
        try:
            if not version.download_url:
                # Some mods require getting download URL from API
                response = self.session.get(
                    f"{self.BASE_URL}/mods/{version.mod_id}/files/{version.id}/download-url"
                )
                if response.ok:
                    version.download_url = response.json().get("data", "")
                
                if not version.download_url:
                    logger.error("CurseForge: Could not get download URL (mod may require manual download)")
                    return None
            
            destination.mkdir(parents=True, exist_ok=True)
            file_path = destination / version.file_name
            
            response = self.session.get(version.download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if callback:
                        callback(downloaded, total_size)
            
            logger.info(f"Downloaded mod: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"CurseForge download error: {e}")
            return None


class ModSourceManager:
    """
    Unified manager for mod sources.
    Combines Modrinth and CurseForge into single interface.
    """
    
    def __init__(self, curseforge_api_key: Optional[str] = None):
        self.modrinth = ModrinthAPI()
        self.curseforge = CurseForgeAPI(curseforge_api_key) if curseforge_api_key else None
        
        if curseforge_api_key:
            logger.info("ModSourceManager initialized with CurseForge + Modrinth")
        else:
            logger.info("ModSourceManager initialized with Modrinth only")
    
    def search_mods(
        self,
        query: str,
        minecraft_version: Optional[str] = None,
        loader: Optional[str] = None,
        source: str = "all",  # "all", "modrinth", "curseforge"
        limit: int = 20
    ) -> List[ModInfo]:
        """
        Search for mods across sources.
        
        Args:
            query: Search query
            minecraft_version: Filter by MC version
            loader: Filter by mod loader (fabric, forge, etc.)
            source: Which source to search
            limit: Max results per source
            
        Returns:
            List of ModInfo sorted by downloads
        """
        mods = []
        
        if source in ("all", "modrinth"):
            mods.extend(self.modrinth.search_mods(
                query, minecraft_version, loader, limit
            ))
        
        if source in ("all", "curseforge") and self.curseforge:
            mods.extend(self.curseforge.search_mods(
                query, minecraft_version, loader, limit
            ))
        
        # Sort by downloads
        mods.sort(key=lambda m: m.downloads, reverse=True)
        
        return mods
    
    def get_mod(self, mod_id: str, source: str) -> Optional[ModInfo]:
        """Get mod info from specific source."""
        if source == "modrinth":
            return self.modrinth.get_mod(mod_id)
        elif source == "curseforge" and self.curseforge:
            return self.curseforge.get_mod(mod_id)
        return None
    
    def get_mod_versions(
        self,
        mod_id: str,
        source: str,
        minecraft_version: Optional[str] = None,
        loader: Optional[str] = None
    ) -> List[ModVersion]:
        """Get mod versions from specific source."""
        if source == "modrinth":
            return self.modrinth.get_mod_versions(mod_id, minecraft_version, loader)
        elif source == "curseforge" and self.curseforge:
            return self.curseforge.get_mod_versions(mod_id, minecraft_version, loader)
        return []
    
    def download_mod(
        self,
        version: ModVersion,
        destination: Path,
        callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[Path]:
        """Download mod version to destination."""
        if version.source == "modrinth":
            return self.modrinth.download_mod(version, destination, callback)
        elif version.source == "curseforge" and self.curseforge:
            return self.curseforge.download_mod(version, destination, callback)
        return None
    
    def install_mod_with_dependencies(
        self,
        version: ModVersion,
        destination: Path,
        minecraft_version: str,
        loader: str,
        callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[Path]:
        """
        Install mod and its required dependencies.
        
        Args:
            version: Mod version to install
            destination: Mods folder path
            minecraft_version: MC version for dependency resolution
            loader: Mod loader type
            callback: Progress callback (mod_name, downloaded, total)
            
        Returns:
            List of installed file paths
        """
        installed = []
        
        # Download main mod
        if callback:
            callback(version.name, 0, 1)
        
        path = self.download_mod(version, destination)
        if path:
            installed.append(path)
        
        # Download required dependencies
        for dep in version.dependencies:
            if dep.get("type") == "required":
                dep_versions = self.get_mod_versions(
                    dep["id"],
                    version.source,
                    minecraft_version,
                    loader
                )
                
                if dep_versions:
                    # Get latest compatible version
                    dep_version = dep_versions[0]
                    
                    if callback:
                        callback(dep_version.name, 0, 1)
                    
                    dep_path = self.download_mod(dep_version, destination)
                    if dep_path:
                        installed.append(dep_path)
                        logger.info(f"Installed dependency: {dep_version.name}")
        
        return installed

