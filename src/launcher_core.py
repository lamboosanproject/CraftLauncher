"""
Core launcher functionality - downloading, installing, and launching Minecraft
"""

import minecraft_launcher_lib as mll
import subprocess
import platform
import os
import shutil
from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum

from .logger import logger


class VersionType(Enum):
    RELEASE = "release"
    SNAPSHOT = "snapshot"
    OLD_BETA = "old_beta"
    OLD_ALPHA = "old_alpha"


@dataclass
class VersionInfo:
    """Information about a Minecraft version."""
    id: str
    type: str
    release_time: str
    installed: bool = False


@dataclass
class DownloadProgress:
    """Progress information for downloads."""
    status: str
    current: int
    total: int
    percentage: float


class LauncherCore:
    """Core functionality for the Minecraft launcher."""
    
    def __init__(self, minecraft_dir: Path):
        self.minecraft_dir = minecraft_dir
        self.minecraft_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"LauncherCore initialized with minecraft_dir: {minecraft_dir}")
        
        # Callbacks
        self.on_progress: Optional[Callable[[DownloadProgress], None]] = None
        self.on_status: Optional[Callable[[str], None]] = None
    
    def get_installed_versions(self) -> list[VersionInfo]:
        """Get list of installed Minecraft versions."""
        installed = mll.utils.get_installed_versions(str(self.minecraft_dir))
        logger.debug(f"Found {len(installed)} installed versions")
        return [
            VersionInfo(
                id=v["id"],
                type=v["type"],
                release_time=v.get("releaseTime", ""),
                installed=True
            )
            for v in installed
        ]
    
    def get_available_versions(
        self, 
        include_snapshots: bool = False,
        include_old: bool = False
    ) -> list[VersionInfo]:
        """Get list of all available Minecraft versions."""
        logger.info(f"Fetching available versions (snapshots={include_snapshots}, old={include_old})")
        all_versions = mll.utils.get_version_list()
        installed_ids = {v.id for v in self.get_installed_versions()}
        
        versions = []
        for v in all_versions:
            v_type = v["type"]
            
            # Filter based on preferences
            if v_type == "snapshot" and not include_snapshots:
                continue
            if v_type in ("old_beta", "old_alpha") and not include_old:
                continue
            
            versions.append(VersionInfo(
                id=v["id"],
                type=v_type,
                release_time=v.get("releaseTime", ""),
                installed=v["id"] in installed_ids
            ))
        
        logger.info(f"Found {len(versions)} available versions")
        return versions
    
    def get_latest_release(self) -> str:
        """Get the latest release version ID."""
        return mll.utils.get_latest_version()["release"]
    
    def get_latest_snapshot(self) -> str:
        """Get the latest snapshot version ID."""
        return mll.utils.get_latest_version()["snapshot"]
    
    def _progress_callback(self, progress: dict) -> None:
        """Internal callback for download progress."""
        if self.on_progress:
            current = progress.get("current", 0)
            total = progress.get("max", 1)
            percentage = (current / total * 100) if total > 0 else 0
            
            self.on_progress(DownloadProgress(
                status=progress.get("status", "Downloading..."),
                current=current,
                total=total,
                percentage=percentage
            ))
    
    def install_version(self, version_id: str) -> bool:
        """Install a Minecraft version."""
        logger.info(f"Installing Minecraft version: {version_id}")
        try:
            if self.on_status:
                self.on_status(f"Установка версии {version_id}...")
            
            # Set up progress callback
            callback = {
                "setStatus": lambda s: self._log_and_status(s),
                "setProgress": lambda c: self._progress_callback({"current": c, "max": 100, "status": "Загрузка..."}),
                "setMax": lambda m: None,
            }
            
            mll.install.install_minecraft_version(
                version_id,
                str(self.minecraft_dir),
                callback=callback
            )
            
            logger.info(f"Successfully installed version {version_id}")
            if self.on_status:
                self.on_status(f"Версия {version_id} успешно установлена!")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to install version {version_id}: {e}", exc_info=True)
            if self.on_status:
                self.on_status(f"Ошибка установки: {e}")
            return False
    
    def _log_and_status(self, message: str) -> None:
        """Log message and update status."""
        logger.debug(f"Install status: {message}")
        if self.on_status:
            self.on_status(message)
    
    def delete_version(self, version_id: str) -> bool:
        """
        Delete an installed Minecraft version.
        
        Args:
            version_id: Version ID to delete
            
        Returns:
            True if deletion was successful
        """
        import shutil
        
        logger.info(f"Deleting version {version_id}...")
        
        try:
            version_dir = self.minecraft_dir / "versions" / version_id
            
            if not version_dir.exists():
                logger.warning(f"Version directory not found: {version_dir}")
                return False
            
            # Delete the version directory
            shutil.rmtree(version_dir)
            
            logger.info(f"Successfully deleted version {version_id}")
            if self.on_status:
                self.on_status(f"Версия {version_id} удалена")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete version {version_id}: {e}")
            if self.on_status:
                self.on_status(f"Ошибка удаления: {e}")
            return False
    
    def get_version_size(self, version_id: str) -> int:
        """
        Get the size of an installed version in bytes.
        
        Args:
            version_id: Version ID
            
        Returns:
            Size in bytes, or 0 if not found
        """
        version_dir = self.minecraft_dir / "versions" / version_id
        
        if not version_dir.exists():
            return 0
        
        total_size = 0
        for path in version_dir.rglob("*"):
            if path.is_file():
                total_size += path.stat().st_size
        
        return total_size
    
    def is_version_installed(self, version_id: str) -> bool:
        """Check if a version is installed."""
        installed = self.get_installed_versions()
        return any(v.id == version_id for v in installed)
    
    def find_java(self) -> Optional[str]:
        """Find Java installation."""
        logger.info("Searching for Java installation...")
        
        system = platform.system()
        
        # Method 1: Check PATH using 'which' or 'where'
        java_in_path = shutil.which("java")
        if java_in_path:
            logger.info(f"Found Java in PATH: {java_in_path}")
            if self._verify_java(java_in_path):
                return java_in_path
        
        # Method 2: Check JAVA_HOME environment variable
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            java_bin = Path(java_home) / "bin" / ("java.exe" if system == "Windows" else "java")
            if java_bin.exists():
                logger.info(f"Found Java via JAVA_HOME: {java_bin}")
                if self._verify_java(str(java_bin)):
                    return str(java_bin)
        
        # Method 3: Try minecraft-launcher-lib
        try:
            java_info = mll.utils.find_java_executable()
            if java_info:
                logger.info(f"Found Java via minecraft-launcher-lib: {java_info}")
                return java_info
        except Exception as e:
            logger.debug(f"minecraft-launcher-lib find_java failed: {e}")
        
        # Method 4: Check common installation paths
        possible_paths = self._get_java_search_paths(system)
        
        for base_path in possible_paths:
            logger.debug(f"Searching in: {base_path}")
            if not base_path.exists():
                continue
            
            # Search for java binary
            java_executable = "java.exe" if system == "Windows" else "java"
            
            # Direct check in bin
            direct_java = base_path / "bin" / java_executable
            if direct_java.exists():
                logger.info(f"Found Java: {direct_java}")
                if self._verify_java(str(direct_java)):
                    return str(direct_java)
            
            # Search subdirectories (for /usr/lib/jvm/java-XX-openjdk/bin/java pattern)
            try:
                for subdir in base_path.iterdir():
                    if subdir.is_dir():
                        java_bin = subdir / "bin" / java_executable
                        if java_bin.exists():
                            logger.info(f"Found Java: {java_bin}")
                            if self._verify_java(str(java_bin)):
                                return str(java_bin)
            except PermissionError:
                continue
        
        logger.warning("No Java installation found!")
        return None
    
    def _get_java_search_paths(self, system: str) -> list[Path]:
        """Get list of paths to search for Java."""
        paths = []
        
        if system == "Windows":
            program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            
            paths = [
                Path(program_files) / "Java",
                Path(program_files_x86) / "Java",
                Path(program_files) / "Eclipse Adoptium",
                Path(program_files) / "Eclipse Foundation",
                Path(program_files) / "Microsoft",
                Path(program_files) / "Zulu",
                Path(program_files) / "BellSoft",
                Path(program_files) / "Amazon Corretto",
            ]
            if local_app_data:
                paths.append(Path(local_app_data) / "Programs" / "Eclipse Adoptium")
                
        elif system == "Darwin":  # macOS
            paths = [
                Path("/Library/Java/JavaVirtualMachines"),
                Path.home() / "Library/Java/JavaVirtualMachines",
                Path("/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home"),
                Path("/opt/homebrew/opt/openjdk"),
                Path("/usr/local/opt/openjdk"),
            ]
        else:  # Linux
            paths = [
                Path("/usr/lib/jvm"),
                Path("/usr/lib64/jvm"),
                Path("/usr/java"),
                Path("/opt/java"),
                Path("/opt/jdk"),
                Path.home() / ".sdkman/candidates/java/current",
                Path.home() / ".jdks",
                Path.home() / ".local/share/JetBrains/Toolbox/apps",
                # Arch Linux / Manjaro specific
                Path("/usr/lib/jvm/default"),
                Path("/usr/lib/jvm/default-runtime"),
                # Common distro paths
                Path("/etc/alternatives"),
            ]
            
            # Add any java* directories in /usr/lib/jvm
            jvm_dir = Path("/usr/lib/jvm")
            if jvm_dir.exists():
                try:
                    for item in jvm_dir.iterdir():
                        if item.is_dir() and "java" in item.name.lower():
                            paths.append(item)
                except PermissionError:
                    pass
        
        return paths
    
    def _verify_java(self, java_path: str) -> bool:
        """Verify that Java executable works."""
        try:
            result = subprocess.run(
                [java_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Java outputs version to stderr
            version_output = result.stderr or result.stdout
            logger.debug(f"Java version check: {version_output.splitlines()[0] if version_output else 'unknown'}")
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Java verification failed for {java_path}: {e}")
            return False
    
    def launch_game(
        self,
        version_id: str,
        username: str,
        java_path: Optional[str] = None,
        ram_min: int = 2,
        ram_max: int = 4,
        extra_jvm_args: Optional[list[str]] = None,
        game_directory: Optional[Path] = None,
        use_elyby: bool = True,
        uuid: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> subprocess.Popen:
        """Launch Minecraft with the specified options."""
        logger.info(f"Launching Minecraft {version_id} for user {username}")
        logger.info(f"RAM: {ram_min}G - {ram_max}G")
        logger.info(f"Auth mode: {'Online (Ely.by)' if access_token else 'Offline'}")
        
        # Find Java if not specified
        if not java_path:
            java_path = self.find_java()
            if not java_path:
                error_msg = "Java не найдена! Пожалуйста, установите Java или укажите путь в настройках."
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        logger.info(f"Using Java: {java_path}")
        
        # Build launch options
        options = mll.utils.generate_test_options()
        options["username"] = username
        options["uuid"] = uuid or ""
        options["token"] = access_token or ""
        
        # Set game directory
        if game_directory:
            options["gameDirectory"] = str(game_directory)
        
        # JVM arguments
        jvm_args = [
            f"-Xms{ram_min}G",
            f"-Xmx{ram_max}G",
            "-XX:+UseG1GC",
            "-XX:+ParallelRefProcEnabled",
            "-XX:MaxGCPauseMillis=200",
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+DisableExplicitGC",
            "-XX:+AlwaysPreTouch",
            "-XX:G1NewSizePercent=30",
            "-XX:G1MaxNewSizePercent=40",
            "-XX:G1HeapRegionSize=8M",
            "-XX:G1ReservePercent=20",
            "-XX:G1HeapWastePercent=5",
            "-XX:G1MixedGCCountTarget=4",
            "-XX:InitiatingHeapOccupancyPercent=15",
            "-XX:G1MixedGCLiveThresholdPercent=90",
            "-XX:G1RSetUpdatingPauseTimePercent=5",
            "-XX:SurvivorRatio=32",
            "-XX:+PerfDisableSharedMem",
            "-XX:MaxTenuringThreshold=1",
        ]
        
        if extra_jvm_args:
            jvm_args.extend(extra_jvm_args)
        
        # Add Ely.by authlib-injector if enabled
        if use_elyby:
            try:
                from .elyby import elyby
                elyby_args = elyby.get_jvm_args_for_injection()
                if elyby_args:
                    jvm_args = elyby_args + jvm_args
                    logger.info("Ely.by authlib-injector enabled for skin support")
            except Exception as e:
                logger.warning(f"Failed to setup Ely.by integration: {e}")
        
        options["jvmArguments"] = jvm_args
        
        # Get launch command
        command = mll.command.get_minecraft_command(
            version_id,
            str(self.minecraft_dir),
            options
        )
        
        # Replace java with custom path
        command[0] = java_path
        
        logger.debug(f"Launch command: {' '.join(command[:5])}...")  # Log first 5 parts
        logger.debug(f"Ely.by enabled: {use_elyby}")
        
        if self.on_status:
            self.on_status(f"Запуск Minecraft {version_id}...")
        
        # Launch the game
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(game_directory or self.minecraft_dir)
        )
        
        logger.info(f"Minecraft launched with PID: {process.pid}")
        
        return process
