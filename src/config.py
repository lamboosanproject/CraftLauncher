"""
Configuration management for CraftLauncher
"""

import json
import os
from pathlib import Path
from typing import Any
import platform


class Config:
    """Manages launcher configuration and settings."""
    
    DEFAULT_CONFIG = {
        "username": "Player",
        "ram_min": 2,
        "ram_max": 4,
        "java_path": "",  # Empty means auto-detect
        "game_directory": "",  # Empty means default
        "last_version": "",
        "theme": "dark",
        "language": "ru",
        "fullscreen": False,
        "window_width": 1280,
        "window_height": 720,
        "show_snapshots": False,
        "show_old_versions": False,
        "close_on_launch": False,
        "show_game_console": False,  # Show debug console when game runs
        "curseforge_api_key": "",  # CurseForge API key for mod downloads
    }
    
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.config: dict[str, Any] = {}
        self._load()
    
    def _get_config_dir(self) -> Path:
        """Get the configuration directory based on OS."""
        system = platform.system()
        
        if system == "Windows":
            base = Path(os.environ.get("APPDATA", Path.home()))
        elif system == "Darwin":  # macOS
            base = Path.home() / "Library" / "Application Support"
        else:  # Linux and others
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        
        config_dir = base / "CraftLauncher"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def _get_default_minecraft_dir(self) -> Path:
        """Get the default Minecraft directory based on OS."""
        system = platform.system()
        
        if system == "Windows":
            return Path(os.environ.get("APPDATA", Path.home())) / ".minecraft"
        elif system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "minecraft"
        else:  # Linux
            return Path.home() / ".minecraft"
    
    def get_minecraft_dir(self) -> Path:
        """Get the Minecraft directory (custom or default)."""
        if self.config.get("game_directory"):
            return Path(self.config["game_directory"])
        return self._get_default_minecraft_dir()
    
    def _load(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new config options
                    self.config = {**self.DEFAULT_CONFIG, **loaded}
            except (json.JSONDecodeError, IOError):
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            self.config = self.DEFAULT_CONFIG.copy()
        
        self.save()
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save."""
        self.config[key] = value
        self.save()
    
    def __getitem__(self, key: str) -> Any:
        return self.config[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

