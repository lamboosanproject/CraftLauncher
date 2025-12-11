#!/usr/bin/env python3
"""
Build script for CraftLauncher
Creates standalone executables for Windows, Linux, and macOS
"""

import subprocess
import sys
import platform
import shutil
from pathlib import Path


def get_platform_name() -> str:
    """Get the current platform name."""
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "macos"
    else:
        return "linux"


def get_output_name() -> str:
    """Get the output executable name based on platform."""
    system = platform.system()
    if system == "Windows":
        return "CraftLauncher.exe"
    elif system == "Darwin":
        return "CraftLauncher.app"
    else:
        return "CraftLauncher"


def clean_build_dirs():
    """Clean previous build directories."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_path)
    
    # Clean .pyc files
    for pyc in Path(".").rglob("*.pyc"):
        pyc.unlink()
    
    for pycache in Path(".").rglob("__pycache__"):
        shutil.rmtree(pycache)


def build_executable():
    """Build the standalone executable."""
    system = platform.system()
    platform_name = get_platform_name()
    
    print(f"\n{'='*50}")
    print(f"Building CraftLauncher for {platform_name}")
    print(f"{'='*50}\n")
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=CraftLauncher",
        "--onefile",
        "--windowed",
        "--clean",
        # Hidden imports for customtkinter
        "--hidden-import=PIL",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=customtkinter",
        # Collect all customtkinter data
        "--collect-all=customtkinter",
        # Add data files
        "--add-data", f"src{':' if system != 'Windows' else ';'}src",
    ]
    
    # Add icon if exists
    icon_path = Path("assets/icon.ico" if system == "Windows" else "assets/icon.png")
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])
    
    # Entry point
    cmd.append("run.py")
    
    print("Running PyInstaller...")
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        output_path = Path("dist") / get_output_name()
        print(f"\n{'='*50}")
        print("✅ Build successful!")
        print(f"Output: {output_path}")
        print(f"{'='*50}\n")
        
        # Show file size
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"File size: {size_mb:.1f} MB")
    else:
        print(f"\n❌ Build failed with code {result.returncode}")
        sys.exit(1)


def main():
    """Main build function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build CraftLauncher")
    parser.add_argument("--clean", action="store_true", help="Clean build directories only")
    parser.add_argument("--no-clean", action="store_true", help="Don't clean before building")
    args = parser.parse_args()
    
    if args.clean:
        clean_build_dirs()
        print("✅ Cleaned build directories")
        return
    
    if not args.no_clean:
        clean_build_dirs()
    
    build_executable()


if __name__ == "__main__":
    main()

