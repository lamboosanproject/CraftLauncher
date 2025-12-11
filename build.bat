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

REM Run build
echo Building executable...
python build.py

echo.
echo Build complete!
echo Executable is in: dist\
pause

