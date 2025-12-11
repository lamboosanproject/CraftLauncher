#!/bin/bash
# Build script for Linux/macOS

set -e

echo "======================================"
echo "  CraftLauncher Build Script"
echo "======================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run build
echo "Building executable..."
python build.py

echo ""
echo "✅ Build complete!"
echo "Executable is in: dist/"

