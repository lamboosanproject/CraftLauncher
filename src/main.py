#!/usr/bin/env python3
"""
CraftLauncher - A modern Minecraft launcher
Entry point for the application
"""

import sys
import os

# Ensure the src directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from src.ui.main_window import MainWindow


def main():
    """Main entry point."""
    # Set appearance mode
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    
    # Create and run the application
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()

