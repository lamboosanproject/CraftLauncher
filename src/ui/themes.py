"""
Theme configuration for CraftLauncher
"""

# Color schemes
THEMES = {
    "dark": {
        "bg_primary": "#0f0f0f",
        "bg_secondary": "#1a1a1a",
        "bg_tertiary": "#252525",
        "bg_card": "#1e1e1e",
        "bg_hover": "#2d2d2d",
        
        "accent": "#10b981",  # Emerald green
        "accent_hover": "#059669",
        "accent_light": "#34d399",
        
        "text_primary": "#ffffff",
        "text_secondary": "#a3a3a3",
        "text_muted": "#6b6b6b",
        
        "border": "#333333",
        "border_light": "#404040",
        
        "success": "#22c55e",
        "warning": "#f59e0b",
        "error": "#ef4444",
        "info": "#3b82f6",
        
        "version_release": "#10b981",
        "version_snapshot": "#f59e0b",
        "version_old": "#6b7280",
    },
    "light": {
        "bg_primary": "#fafafa",
        "bg_secondary": "#f5f5f5",
        "bg_tertiary": "#e5e5e5",
        "bg_card": "#ffffff",
        "bg_hover": "#f0f0f0",
        
        "accent": "#059669",
        "accent_hover": "#047857",
        "accent_light": "#10b981",
        
        "text_primary": "#171717",
        "text_secondary": "#525252",
        "text_muted": "#a3a3a3",
        
        "border": "#e5e5e5",
        "border_light": "#d4d4d4",
        
        "success": "#16a34a",
        "warning": "#d97706",
        "error": "#dc2626",
        "info": "#2563eb",
        
        "version_release": "#059669",
        "version_snapshot": "#d97706",
        "version_old": "#6b7280",
    },
    "midnight": {
        "bg_primary": "#0c0a1d",
        "bg_secondary": "#13102a",
        "bg_tertiary": "#1a1635",
        "bg_card": "#171330",
        "bg_hover": "#211c40",
        
        "accent": "#8b5cf6",  # Purple
        "accent_hover": "#7c3aed",
        "accent_light": "#a78bfa",
        
        "text_primary": "#f5f3ff",
        "text_secondary": "#c4b5fd",
        "text_muted": "#7c7c9a",
        
        "border": "#2e2854",
        "border_light": "#3d3666",
        
        "success": "#4ade80",
        "warning": "#fbbf24",
        "error": "#f87171",
        "info": "#60a5fa",
        
        "version_release": "#8b5cf6",
        "version_snapshot": "#fbbf24",
        "version_old": "#7c7c9a",
    },
}


def get_theme(name: str = "dark") -> dict:
    """Get a theme by name, defaulting to dark."""
    return THEMES.get(name, THEMES["dark"])

