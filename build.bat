@echo off
REM Build script for Windows

echo ======================================
echo   CraftLauncher Build Script
echo ======================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python is required but not installed.
    exit /b 1
)

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM Clean previous builds
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Run build
echo Building executable...
python -m PyInstaller ^
    --name=CraftLauncher ^
    --onefile ^
    --windowed ^
    --clean ^
    --hidden-import=PIL ^
    --hidden-import=PIL._tkinter_finder ^
    --hidden-import=customtkinter ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.ttk ^
    --collect-all=customtkinter ^
    --add-data "src;src" ^
    run.py

echo.
if exist "dist\CraftLauncher.exe" (
    echo ✅ Build successful!
    echo Executable: dist\CraftLauncher.exe
    for %%I in (dist\CraftLauncher.exe) do echo Size: %%~zI bytes
) else (
    echo ❌ Build failed!
)
echo.
pause
