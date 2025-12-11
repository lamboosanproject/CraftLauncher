"""
Main window for CraftLauncher
"""

import customtkinter as ctk
from typing import Optional, Callable
import threading
from pathlib import Path

from ..config import Config
from ..launcher_core import LauncherCore, VersionInfo
from ..logger import logger
from ..auth import AuthManager
from ..mods import ModManager
from ..profiles import ProfileManager, Profile
from ..i18n import get_i18n, set_language, t, LANGUAGES
from .themes import get_theme


class VersionCard(ctk.CTkFrame):
    """A card displaying a Minecraft version."""
    
    def __init__(
        self,
        parent,
        version: VersionInfo,
        theme: dict,
        on_select: Optional[Callable[[str], None]] = None,
        on_delete: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.version = version
        self.theme = theme
        self.on_select = on_select
        self.on_delete = on_delete
        self.is_selected = False
        
        self.configure(
            fg_color=theme["bg_card"],
            corner_radius=8,
            border_width=1,
            border_color=theme["border"]
        )
        
        self._create_widgets()
        self._bind_events()
    
    def _create_widgets(self):
        # Main container
        self.grid_columnconfigure(0, weight=1)
        
        # Top row with name and delete button
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, padx=12, pady=(10, 2), sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)
        
        # Version ID
        self.name_label = ctk.CTkLabel(
            top_frame,
            text=self.version.id,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme["text_primary"],
            anchor="w"
        )
        self.name_label.grid(row=0, column=0, sticky="w")
        
        # Delete button (only for installed versions)
        if self.version.installed:
            self.delete_btn = ctk.CTkButton(
                top_frame,
                text="🗑",
                width=28,
                height=28,
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                hover_color=self.theme["error"],
                text_color=self.theme["text_muted"],
                command=self._on_delete_click
            )
            self.delete_btn.grid(row=0, column=1, sticky="e")
            # Initially hidden, show on hover
            self.delete_btn.grid_remove()
        
        # Type badge
        type_color = {
            "release": self.theme["version_release"],
            "snapshot": self.theme["version_snapshot"],
            "old_beta": self.theme["version_old"],
            "old_alpha": self.theme["version_old"],
        }.get(self.version.type, self.theme["text_muted"])
        
        type_text = {
            "release": t("release"),
            "snapshot": t("snapshot"),
            "old_beta": t("old_beta"),
            "old_alpha": t("old_alpha"),
        }.get(self.version.type, self.version.type)
        
        # Info row
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")
        
        self.type_label = ctk.CTkLabel(
            info_frame,
            text=type_text,
            font=ctk.CTkFont(size=11),
            text_color=type_color,
        )
        self.type_label.pack(side="left")
        
        # Installed indicator
        if self.version.installed:
            self.installed_label = ctk.CTkLabel(
                info_frame,
                text=f"  •  {t('installed')}",
                font=ctk.CTkFont(size=11),
                text_color=self.theme["success"],
            )
            self.installed_label.pack(side="left")
    
    def _bind_events(self):
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        
        # Bind to all children too
        for child in self.winfo_children():
            child.bind("<Enter>", self._on_enter)
            child.bind("<Leave>", self._on_leave)
            child.bind("<Button-1>", self._on_click)
            # Recursive binding for nested children
            for subchild in child.winfo_children():
                subchild.bind("<Enter>", self._on_enter)
                subchild.bind("<Leave>", self._on_leave)
                if not isinstance(subchild, ctk.CTkButton):  # Don't override button click
                    subchild.bind("<Button-1>", self._on_click)
    
    def _on_enter(self, event):
        if not self.is_selected:
            self.configure(
                fg_color=self.theme["bg_hover"],
                border_color=self.theme["border_light"]
            )
        # Show delete button on hover
        if self.version.installed and hasattr(self, 'delete_btn'):
            self.delete_btn.grid()
    
    def _on_leave(self, event):
        # Check if mouse is still within the card
        x, y = self.winfo_pointerxy()
        widget_x = self.winfo_rootx()
        widget_y = self.winfo_rooty()
        widget_w = self.winfo_width()
        widget_h = self.winfo_height()
        
        if not (widget_x <= x < widget_x + widget_w and widget_y <= y < widget_y + widget_h):
            if not self.is_selected:
                self.configure(
                    fg_color=self.theme["bg_card"],
                    border_color=self.theme["border"]
                )
            # Hide delete button
            if self.version.installed and hasattr(self, 'delete_btn'):
                self.delete_btn.grid_remove()
    
    def _on_click(self, event):
        if self.on_select:
            self.on_select(self.version.id)
    
    def _on_delete_click(self):
        if self.on_delete:
            self.on_delete(self.version.id)
    
    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.configure(
                fg_color=self.theme["bg_hover"],
                border_color=self.theme["accent"]
            )
        else:
            self.configure(
                fg_color=self.theme["bg_card"],
                border_color=self.theme["border"]
            )


class ProfileCard(ctk.CTkFrame):
    """A card displaying a custom profile."""
    
    def __init__(
        self,
        parent,
        profile: Profile,
        theme: dict,
        on_select: Optional[Callable[[str], None]] = None,
        on_delete: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.profile = profile
        self.theme = theme
        self.on_select = on_select
        self.on_delete = on_delete
        self.is_selected = False
        
        self.configure(
            fg_color=theme["bg_card"],
            corner_radius=8,
            border_width=2,
            border_color=theme["accent"]  # Profiles have accent border
        )
        
        self._create_widgets()
        self._bind_events()
    
    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        
        # Top row with name and delete button
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, padx=12, pady=(10, 2), sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)
        
        # Profile icon and name
        name_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        name_frame.grid(row=0, column=0, sticky="w")
        
        icon_label = ctk.CTkLabel(
            name_frame,
            text=self.profile.icon,
            font=ctk.CTkFont(size=16),
        )
        icon_label.pack(side="left", padx=(0, 5))
        
        self.name_label = ctk.CTkLabel(
            name_frame,
            text=self.profile.name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme["text_primary"],
            anchor="w"
        )
        self.name_label.pack(side="left")
        
        # Delete button
        self.delete_btn = ctk.CTkButton(
            top_frame,
            text="🗑",
            width=28,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=self.theme["error"],
            text_color=self.theme["text_muted"],
            command=self._on_delete_click
        )
        self.delete_btn.grid(row=0, column=1, sticky="e")
        self.delete_btn.grid_remove()
        
        # Info row
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")
        
        # MC version badge
        mc_badge = ctk.CTkLabel(
            info_frame,
            text=f"MC {self.profile.minecraft_version}",
            font=ctk.CTkFont(size=11),
            text_color=self.theme["version_release"],
            fg_color=self.theme["bg_tertiary"],
            corner_radius=4,
            padx=6,
            pady=2
        )
        mc_badge.pack(side="left")
        
        # Loader badge
        if self.profile.loader_type:
            loader_colors = {
                "fabric": "#dbb78a",
                "forge": "#e35f48",
                "forge+optifine": "#e35f48",
                "neoforge": "#f59e0b",
                "quilt": "#9b59b6",
                "optifine": "#ad1d1d"
            }
            loader_color = loader_colors.get(self.profile.loader_type, self.theme["text_muted"])
            
            # Display name for loader
            loader_display = {
                "forge+optifine": "Forge+OF",
                "optifine": "OptiFine"
            }.get(self.profile.loader_type, self.profile.loader_type.capitalize())
            
            loader_badge = ctk.CTkLabel(
                info_frame,
                text=loader_display,
                font=ctk.CTkFont(size=11),
                text_color=loader_color,
                fg_color=self.theme["bg_tertiary"],
                corner_radius=4,
                padx=6,
                pady=2
            )
            loader_badge.pack(side="left", padx=(5, 0))
        else:
            vanilla_badge = ctk.CTkLabel(
                info_frame,
                text="Vanilla",
                font=ctk.CTkFont(size=11),
                text_color=self.theme["text_muted"],
                fg_color=self.theme["bg_tertiary"],
                corner_radius=4,
                padx=6,
                pady=2
            )
            vanilla_badge.pack(side="left", padx=(5, 0))
    
    def _bind_events(self):
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        
        for child in self.winfo_children():
            child.bind("<Button-1>", self._on_click)
            for subchild in child.winfo_children():
                subchild.bind("<Button-1>", self._on_click)
    
    def _on_enter(self, event):
        if not self.is_selected:
            self.configure(fg_color=self.theme["bg_hover"])
        self.delete_btn.grid()
    
    def _on_leave(self, event):
        x, y = self.winfo_pointerxy()
        widget_x = self.winfo_rootx()
        widget_y = self.winfo_rooty()
        widget_w = self.winfo_width()
        widget_h = self.winfo_height()
        
        if not (widget_x <= x < widget_x + widget_w and widget_y <= y < widget_y + widget_h):
            if not self.is_selected:
                self.configure(fg_color=self.theme["bg_card"])
            self.delete_btn.grid_remove()
    
    def _on_click(self, event):
        if self.on_select:
            self.on_select(self.profile.id)
    
    def _on_delete_click(self):
        if self.on_delete:
            self.on_delete(self.profile.id)
    
    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.configure(
                fg_color=self.theme["bg_hover"],
                border_color=self.theme["success"]
            )
        else:
            self.configure(
                fg_color=self.theme["bg_card"],
                border_color=self.theme["accent"]
            )


class GameConsole(ctk.CTkToplevel):
    """Game debug console window."""
    
    def __init__(self, parent, theme: dict, version_id: str):
        super().__init__(parent)
        
        self.theme = theme
        self.version_id = version_id
        self.process = None
        self.running = False
        
        self.title(f"Консоль - Minecraft {version_id}")
        self.geometry("800x500")
        self.minsize(600, 300)
        self.configure(fg_color=theme["bg_primary"])
        
        self._create_widgets()
    
    def _create_widgets(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=self.theme["bg_secondary"], height=50)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(
            header,
            text=f"🖥️ Консоль Minecraft {self.version_id}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme["text_primary"]
        )
        title.pack(side="left", padx=15, pady=10)
        
        # Clear button
        clear_btn = ctk.CTkButton(
            header,
            text="🗑️ Очистить",
            width=100,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=self.theme["bg_tertiary"],
            hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self._clear_console
        )
        clear_btn.pack(side="right", padx=10)
        
        # Console output
        self.console_frame = ctk.CTkFrame(self, fg_color=self.theme["bg_secondary"])
        self.console_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.console_text = ctk.CTkTextbox(
            self.console_frame,
            font=ctk.CTkFont(family="Consolas, monospace", size=11),
            fg_color="#0d0d0d",
            text_color="#00ff00",
            wrap="word",
            state="disabled"
        )
        self.console_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Status bar
        self.status_label = ctk.CTkLabel(
            self,
            text="⏳ Ожидание запуска...",
            font=ctk.CTkFont(size=11),
            text_color=self.theme["text_muted"]
        )
        self.status_label.pack(pady=(0, 10))
    
    def set_process(self, process):
        """Set the game process to monitor."""
        self.process = process
        self.running = True
        self.status_label.configure(text="🟢 Игра запущена")
        
        # Start reading output
        import threading
        self.stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self.stdout_thread.start()
        self.stderr_thread.start()
        
        # Monitor process
        self.monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
        self.monitor_thread.start()
    
    def _read_stdout(self):
        """Read stdout from the game process."""
        try:
            for line in iter(self.process.stdout.readline, b''):
                if not self.running:
                    break
                text = line.decode('utf-8', errors='replace')
                self.after(0, lambda t=text: self._append_text(t, "white"))
        except:
            pass
    
    def _read_stderr(self):
        """Read stderr from the game process."""
        try:
            for line in iter(self.process.stderr.readline, b''):
                if not self.running:
                    break
                text = line.decode('utf-8', errors='replace')
                # Color code based on content
                if "ERROR" in text or "Exception" in text:
                    color = "#ff5555"
                elif "WARN" in text:
                    color = "#ffaa00"
                else:
                    color = "#00ff00"
                self.after(0, lambda t=text, c=color: self._append_text(t, c))
        except:
            pass
    
    def _monitor_process(self):
        """Monitor the game process."""
        if self.process:
            self.process.wait()
            self.running = False
            exit_code = self.process.returncode
            self.after(0, lambda: self._on_game_exit(exit_code))
    
    def _on_game_exit(self, exit_code: int):
        """Called when the game exits."""
        if exit_code == 0:
            self.status_label.configure(text="✅ Игра завершена нормально")
            self._append_text(f"\n[Игра завершена с кодом {exit_code}]\n", "#888888")
        else:
            self.status_label.configure(text=f"❌ Игра завершена с ошибкой (код {exit_code})")
            self._append_text(f"\n[Игра завершена с кодом {exit_code}]\n", "#ff5555")
    
    def _append_text(self, text: str, color: str = "white"):
        """Append text to console."""
        self.console_text.configure(state="normal")
        self.console_text.insert("end", text)
        self.console_text.configure(state="disabled")
        self.console_text.see("end")
    
    def _clear_console(self):
        """Clear console output."""
        self.console_text.configure(state="normal")
        self.console_text.delete("1.0", "end")
        self.console_text.configure(state="disabled")
    
    def destroy(self):
        """Clean up when closing."""
        self.running = False
        super().destroy()


class AccountWindow(ctk.CTkToplevel):
    """Account management window with multiple auth options."""
    
    def __init__(self, parent, auth_manager, theme: dict, on_complete: Callable):
        super().__init__(parent)
        
        self.auth = auth_manager
        self.theme = theme
        self.on_complete = on_complete
        self.is_busy = False
        
        self.title("Добавить аккаунт")
        self.geometry("450x500")
        self.resizable(False, False)
        self.configure(fg_color=theme["bg_primary"])
        
        self.transient(parent)
        
        self._create_widgets()
        self.after(10, self._grab_focus)
    
    def _grab_focus(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass
    
    def _create_widgets(self):
        # Title
        title = ctk.CTkLabel(
            self,
            text="👤 Добавить аккаунт",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.theme["text_primary"]
        )
        title.pack(pady=(25, 5))
        
        subtitle = ctk.CTkLabel(
            self,
            text=t("account_title"),
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"]
        )
        subtitle.pack(pady=(0, 20))
        
        # Tab view for different auth types
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=self.theme["bg_secondary"],
            segmented_button_fg_color=self.theme["bg_tertiary"],
            segmented_button_selected_color=self.theme["accent"],
            segmented_button_unselected_color=self.theme["bg_tertiary"],
            text_color=self.theme["text_primary"]
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Create tabs
        self.tab_offline = self.tabview.add(f"{t('local_profile')}")
        self.tab_microsoft = self.tabview.add(f"{t('microsoft_account')}")
        self.tab_elyby = self.tabview.add(f"{t('elyby_account')}")
        
        self._create_offline_tab()
        self._create_microsoft_tab()
        self._create_elyby_tab()
    
    def _create_offline_tab(self):
        """Create offline (local profile) tab."""
        frame = ctk.CTkFrame(self.tab_offline, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Icon and description
        icon = ctk.CTkLabel(
            frame,
            text="🎮",
            font=ctk.CTkFont(size=48)
        )
        icon.pack(pady=(10, 10))
        
        desc = ctk.CTkLabel(
            frame,
            text=t("local_profile"),
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"],
            justify="center"
        )
        desc.pack(pady=(0, 20))
        
        # Username input
        label = ctk.CTkLabel(
            frame,
            text=t("username"),
            font=ctk.CTkFont(size=13),
            text_color=self.theme["text_secondary"]
        )
        label.pack(anchor="w", pady=(0, 5))
        
        self.offline_username = ctk.CTkEntry(
            frame,
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.theme["bg_tertiary"],
            border_color=self.theme["border"],
            text_color=self.theme["text_primary"],
            placeholder_text="Steve"
        )
        self.offline_username.pack(fill="x", pady=(0, 15))
        self.offline_username.bind("<Return>", lambda e: self._add_offline())
        
        # Add button
        self.offline_button = ctk.CTkButton(
            frame,
            text=t("add_profile"),
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            text_color="#ffffff",
            command=self._add_offline
        )
        self.offline_button.pack(fill="x")
    
    def _create_microsoft_tab(self):
        """Create Microsoft auth tab."""
        frame = ctk.CTkFrame(self.tab_microsoft, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Icon and description
        icon = ctk.CTkLabel(
            frame,
            text="🪟",
            font=ctk.CTkFont(size=48)
        )
        icon.pack(pady=(10, 10))
        
        desc = ctk.CTkLabel(
            frame,
            text=t("microsoft_desc"),
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"],
            justify="center"
        )
        desc.pack(pady=(0, 20))
        
        # Login button
        self.ms_button = ctk.CTkButton(
            frame,
            text=t("microsoft_login"),
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0078D4",
            hover_color="#106EBE",
            text_color="#ffffff",
            command=self._login_microsoft
        )
        self.ms_button.pack(fill="x", pady=(0, 15))
        
        # Code input (for completing auth)
        self.ms_code_frame = ctk.CTkFrame(frame, fg_color="transparent")
        
        code_label = ctk.CTkLabel(
            self.ms_code_frame,
            text=t("microsoft_code_hint"),
            font=ctk.CTkFont(size=11),
            text_color=self.theme["text_muted"],
            wraplength=300
        )
        code_label.pack(pady=(0, 5))
        
        self.ms_code_entry = ctk.CTkEntry(
            self.ms_code_frame,
            height=40,
            font=ctk.CTkFont(size=12),
            fg_color=self.theme["bg_tertiary"],
            border_color=self.theme["border"],
            text_color=self.theme["text_primary"],
            placeholder_text=t("microsoft_code_placeholder")
        )
        self.ms_code_entry.pack(fill="x", pady=(0, 10))
        
        self.ms_complete_button = ctk.CTkButton(
            self.ms_code_frame,
            text=t("microsoft_complete"),
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            text_color="#ffffff",
            command=self._complete_microsoft
        )
        self.ms_complete_button.pack(fill="x")
        
        # Status
        self.ms_status = ctk.CTkLabel(
            frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"]
        )
        self.ms_status.pack(pady=(10, 0))
    
    def _create_elyby_tab(self):
        """Create Ely.by auth tab."""
        frame = ctk.CTkFrame(self.tab_elyby, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Icon and description  
        icon = ctk.CTkLabel(
            frame,
            text="🎨",
            font=ctk.CTkFont(size=48)
        )
        icon.pack(pady=(5, 5))
        
        desc = ctk.CTkLabel(
            frame,
            text=t("elyby_desc"),
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"],
            justify="center"
        )
        desc.pack(pady=(0, 15))
        
        # Username
        self.elyby_username = ctk.CTkEntry(
            frame,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme["bg_tertiary"],
            border_color=self.theme["border"],
            text_color=self.theme["text_primary"],
            placeholder_text="Email или имя пользователя"
        )
        self.elyby_username.pack(fill="x", pady=(0, 10))
        
        # Password
        self.elyby_password = ctk.CTkEntry(
            frame,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme["bg_tertiary"],
            border_color=self.theme["border"],
            text_color=self.theme["text_primary"],
            placeholder_text=t("password"),
            show="•"
        )
        self.elyby_password.pack(fill="x", pady=(0, 10))
        self.elyby_password.bind("<Return>", lambda e: self._login_elyby())
        
        # Status
        self.elyby_status = ctk.CTkLabel(
            frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.theme["error"]
        )
        self.elyby_status.pack(pady=(0, 5))
        
        # Login button
        self.elyby_button = ctk.CTkButton(
            frame,
            text=t("login"),
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            text_color="#ffffff",
            command=self._login_elyby
        )
        self.elyby_button.pack(fill="x", pady=(0, 10))
        
        # Register link
        register = ctk.CTkLabel(
            frame,
            text=t("elyby_no_account"),
            font=ctk.CTkFont(size=10),
            text_color=self.theme["accent"],
            cursor="hand2"
        )
        register.pack()
        register.bind("<Button-1>", lambda e: self._open_url("https://account.ely.by/register"))
    
    def _open_url(self, url: str):
        import webbrowser
        webbrowser.open(url)
    
    def _add_offline(self):
        """Add offline account."""
        username = self.offline_username.get().strip()
        if not username:
            return
        
        if len(username) < 3 or len(username) > 16:
            return
        
        self.auth.add_offline_account(username)
        self.on_complete(True, f"{t('profile')} {username} {t('added')}")
        self.destroy()
    
    def _login_microsoft(self):
        """Start Microsoft login."""
        if self.is_busy:
            return
        
        self.is_busy = True
        self.ms_button.configure(text=f"⏳ {t('opening_browser')}...", state="disabled")
        self.ms_status.configure(text="")
        
        def on_result(success: bool, message: str):
            def update():
                if message == "WAITING_FOR_CODE":
                    # Show code input
                    self.ms_code_frame.pack(fill="x", pady=(10, 0))
                    self.ms_button.configure(text=t("microsoft_browser_open"), state="disabled")
                    self.ms_status.configure(
                        text=t("microsoft_login_browser"),
                        text_color=self.theme["info"]
                    )
                    self.is_busy = False
                elif success:
                    self.on_complete(True, message)
                    self.destroy()
                else:
                    self.ms_button.configure(text=t("microsoft_login"), state="normal")
                    self.ms_status.configure(text=message, text_color=self.theme["error"])
                    self.is_busy = False
            
            self.after(0, update)
        
        self.auth.login_microsoft(on_complete=on_result)
    
    def _complete_microsoft(self):
        """Complete Microsoft login with code."""
        code = self.ms_code_entry.get().strip()
        if not code:
            return
        
        self.ms_complete_button.configure(text=f"⏳ {t('checking')}...", state="disabled")
        
        def on_result(success: bool, message: str):
            def update():
                if success:
                    self.on_complete(True, message)
                    self.destroy()
                else:
                    self.ms_complete_button.configure(text=t("microsoft_complete"), state="normal")
                    self.ms_status.configure(text=message, text_color=self.theme["error"])
            
            self.after(0, update)
        
        self.auth.complete_microsoft_login(code, on_complete=on_result)
    
    def _login_elyby(self):
        """Login with Ely.by."""
        if self.is_busy:
            return
        
        username = self.elyby_username.get().strip()
        password = self.elyby_password.get()
        
        if not username:
            self.elyby_status.configure(text=t("enter_email"))
            return
        if not password:
            self.elyby_status.configure(text=t("enter_password"))
            return
        
        self.is_busy = True
        self.elyby_button.configure(text=f"⏳ {t('logging_in')}...", state="disabled")
        self.elyby_status.configure(text="")
        
        def on_result(success: bool, message: str):
            def update():
                self.is_busy = False
                self.elyby_button.configure(text=t("login"), state="normal")
                
                if success:
                    self.on_complete(True, message)
                    self.destroy()
                else:
                    self.elyby_status.configure(text=message, text_color=self.theme["error"])
            
            self.after(0, update)
        
        import threading
        thread = threading.Thread(
            target=lambda: self.auth.login_elyby(username, password, on_result),
            daemon=True
        )
        thread.start()


class CreateProfileWindow(ctk.CTkToplevel):
    """Window for creating custom game profiles."""
    
    def __init__(self, parent, mod_manager, launcher, profile_manager, theme: dict, on_create):
        super().__init__(parent)
        
        self.mod_manager = mod_manager
        self.launcher = launcher
        self.profile_manager = profile_manager
        self.theme = theme
        self.on_create = on_create
        self.loader_versions_cache = {}
        
        self.title(t("create_profile_title"))
        self.geometry("550x700")
        self.minsize(500, 450)
        self.configure(fg_color=theme["bg_primary"])
        
        self.transient(parent)
        
        self._create_widgets()
        self._load_mc_versions()
        self.after(10, self._grab_focus)
    
    def _grab_focus(self):
        try:
            self.grab_set()
            self.focus_force()
        except:
            pass
    
    def _create_widgets(self):
        # Title
        title = ctk.CTkLabel(
            self,
            text=f"✨ {t('create_new_profile')}",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.theme["text_primary"]
        )
        title.pack(pady=(20, 5))
        
        subtitle = ctk.CTkLabel(
            self,
            text=t("create_profile_desc"),
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"]
        )
        subtitle.pack(pady=(0, 20))
        
        # Form frame
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=30)
        form.grid_columnconfigure(1, weight=1)
        
        row = 0
        
        # Profile name
        ctk.CTkLabel(
            form,
            text=t("profile_name"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_primary"]
        ).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1
        
        self.name_entry = ctk.CTkEntry(
            form,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=self.theme["bg_secondary"],
            border_color=self.theme["border"],
            text_color=self.theme["text_primary"],
            placeholder_text=t("profile_name_placeholder")
        )
        self.name_entry.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row += 1
        
        # Minecraft version
        ctk.CTkLabel(
            form,
            text=t("minecraft_version"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_primary"]
        ).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1
        
        self.mc_version_var = ctk.StringVar(value=t("loading"))
        self.mc_version_menu = ctk.CTkOptionMenu(
            form,
            variable=self.mc_version_var,
            values=[t("loading")],
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=self.theme["bg_secondary"],
            button_color=self.theme["accent"],
            button_hover_color=self.theme["accent_hover"],
            dropdown_fg_color=self.theme["bg_secondary"],
            dropdown_hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self._on_mc_version_changed
        )
        self.mc_version_menu.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row += 1
        
        # Mod loader type
        ctk.CTkLabel(
            form,
            text=t("mod_loader"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_primary"]
        ).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1
        
        self.loader_type_var = ctk.StringVar(value="vanilla")
        self.loader_type_menu = ctk.CTkOptionMenu(
            form,
            variable=self.loader_type_var,
            values=["vanilla", "fabric", "forge", "forge+optifine", "neoforge", "quilt", "optifine"],
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=self.theme["bg_secondary"],
            button_color=self.theme["accent"],
            button_hover_color=self.theme["accent_hover"],
            dropdown_fg_color=self.theme["bg_secondary"],
            dropdown_hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self._on_loader_type_changed
        )
        self.loader_type_menu.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row += 1
        
        # Loader version
        self.loader_version_label = ctk.CTkLabel(
            form,
            text=t("mod_loader_version"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_primary"]
        )
        self.loader_version_label.grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1
        
        self.loader_version_var = ctk.StringVar(value="—")
        self.loader_version_menu = ctk.CTkOptionMenu(
            form,
            variable=self.loader_version_var,
            values=["—"],
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=self.theme["bg_secondary"],
            button_color=self.theme["accent"],
            button_hover_color=self.theme["accent_hover"],
            dropdown_fg_color=self.theme["bg_secondary"],
            dropdown_hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"]
        )
        self.loader_version_menu.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row += 1
        
        # Hide loader version by default (vanilla)
        self.loader_version_label.grid_remove()
        self.loader_version_menu.grid_remove()
        
        # OptiFine version (for forge+optifine)
        self.optifine_version_label = ctk.CTkLabel(
            form,
            text=t("optifine_version"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_primary"]
        )
        self.optifine_version_label.grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1
        
        self.optifine_version_var = ctk.StringVar(value="—")
        self.optifine_version_menu = ctk.CTkOptionMenu(
            form,
            variable=self.optifine_version_var,
            values=["—"],
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=self.theme["bg_secondary"],
            button_color=self.theme["accent"],
            button_hover_color=self.theme["accent_hover"],
            dropdown_fg_color=self.theme["bg_secondary"],
            dropdown_hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"]
        )
        self.optifine_version_menu.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row += 1
        
        # Hide OptiFine version by default
        self.optifine_version_label.grid_remove()
        self.optifine_version_menu.grid_remove()
        
        # Game directory (optional override)
        ctk.CTkLabel(
            form,
            text=t("game_folder"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_primary"]
        ).grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1
        
        dir_frame = ctk.CTkFrame(form, fg_color="transparent")
        dir_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        dir_frame.grid_columnconfigure(0, weight=1)
        
        self.game_dir_entry = ctk.CTkEntry(
            dir_frame,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme["bg_secondary"],
            border_color=self.theme["border"],
            text_color=self.theme["text_primary"],
            placeholder_text=t("game_folder_auto")
        )
        self.game_dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        browse_btn = ctk.CTkButton(
            dir_frame,
            text="📂",
            width=45,
            height=40,
            font=ctk.CTkFont(size=16),
            fg_color=self.theme["bg_tertiary"],
            hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self._browse_game_dir
        )
        browse_btn.grid(row=0, column=1)
        row += 1
        
        # Status
        self.status_label = ctk.CTkLabel(
            form,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"]
        )
        self.status_label.grid(row=row, column=0, columnspan=2, pady=10)
        row += 1
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=20)
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.cancel_btn = ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.theme["bg_tertiary"],
            hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self.destroy
        )
        self.cancel_btn.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        self.create_btn = ctk.CTkButton(
            btn_frame,
            text=f"✨ {t('create_profile')}",
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            text_color="#ffffff",
            command=self._create_profile
        )
        self.create_btn.grid(row=0, column=1, sticky="ew", padx=(10, 0))
    
    def _load_mc_versions(self):
        """Load Minecraft versions in background."""
        def load():
            try:
                versions = self.launcher.get_available_versions(
                    include_snapshots=False,
                    include_old=False
                )
                # Get release versions only
                release_versions = [v.id for v in versions if v.type == "release"]
                
                def update_ui():
                    if release_versions:
                        self.mc_version_menu.configure(values=release_versions)
                        self.mc_version_var.set(release_versions[0])
                        self._on_mc_version_changed(release_versions[0])
                    else:
                        self.mc_version_var.set("Нет версий")
                
                self.after(0, update_ui)
            except Exception as e:
                self.after(0, lambda: self.mc_version_var.set(f"Ошибка: {e}"))
        
        import threading
        threading.Thread(target=load, daemon=True).start()
    
    def _browse_game_dir(self):
        """Open folder browser for game directory."""
        from tkinter import filedialog
        
        # Temporarily release grab to allow file dialog
        self.grab_release()
        
        folder = filedialog.askdirectory(
            parent=self,
            title=f"{t('select_game_directory')}",
            initialdir=str(Path.home())
        )
        
        # Restore grab and focus
        self.grab_set()
        self.focus_force()
        self.lift()
        
        if folder:
            self.game_dir_entry.delete(0, "end")
            self.game_dir_entry.insert(0, folder)
    
    def _on_mc_version_changed(self, version: str):
        """Called when MC version is selected."""
        self.status_label.configure(text="")
        # Reset loader version when MC version changes
        if self.loader_type_var.get() != "vanilla":
            self._load_loader_versions()
    
    def _on_loader_type_changed(self, loader_type: str):
        """Called when loader type is selected."""
        if loader_type == "vanilla":
            self.loader_version_label.grid_remove()
            self.loader_version_menu.grid_remove()
            self.loader_version_var.set("—")
            self.optifine_version_label.grid_remove()
            self.optifine_version_menu.grid_remove()
            self.optifine_version_var.set("—")
        else:
            self.loader_version_label.grid()
            self.loader_version_menu.grid()
            self._load_loader_versions()
            
            # Show OptiFine version selector for forge+optifine
            if loader_type == "forge+optifine":
                self.optifine_version_label.grid()
                self.optifine_version_menu.grid()
                self._load_optifine_versions()
            else:
                self.optifine_version_label.grid_remove()
                self.optifine_version_menu.grid_remove()
                self.optifine_version_var.set("—")
    
    def _load_loader_versions(self):
        """Load loader versions for selected MC version and loader type."""
        mc_version = self.mc_version_var.get()
        loader_type = self.loader_type_var.get()
        
        if loader_type == "vanilla" or not mc_version or mc_version == t("loading"):
            return
        
        self.loader_version_var.set(t("loading"))
        self.loader_version_menu.configure(values=[t("loading")])
        
        cache_key = f"{mc_version}_{loader_type}"
        
        def load():
            try:
                versions = []
                
                if loader_type == "fabric":
                    versions = self.mod_manager.get_fabric_versions(mc_version)
                elif loader_type == "forge" or loader_type == "forge+optifine":
                    versions = self.mod_manager.get_forge_versions(mc_version)
                elif loader_type == "neoforge":
                    versions = self.mod_manager.get_neoforge_versions(mc_version)
                elif loader_type == "quilt":
                    versions = self.mod_manager.get_quilt_versions(mc_version)
                elif loader_type == "optifine":
                    versions = self.mod_manager.get_optifine_versions(mc_version)
                
                version_strings = [v.loader_version for v in versions[:20]]  # Limit to 20
                
                self.loader_versions_cache[cache_key] = version_strings
                
                def update_ui():
                    if version_strings:
                        self.loader_version_menu.configure(values=version_strings)
                        self.loader_version_var.set(version_strings[0])
                        self.status_label.configure(
                            text=f"✓ {t('found')} {len(versions)} {t('versions')} {loader_type}",
                            text_color=self.theme["success"]
                        )
                    else:
                        self.loader_version_menu.configure(values=[t("not_supported")])
                        self.loader_version_var.set(t("not_supported"))
                        self.status_label.configure(
                            text=f"⚠ {loader_type.capitalize()} {t('not_supported')} {mc_version}",
                            text_color=self.theme["warning"] if "warning" in self.theme else self.theme["error"]
                        )
                
                self.after(0, update_ui)
                
            except Exception as e:
                self.after(0, lambda: self.status_label.configure(
                    text=f"Ошибка загрузки версий: {e}",
                    text_color=self.theme["error"]
                ))
        
        import threading
        threading.Thread(target=load, daemon=True).start()
    
    def _load_optifine_versions(self):
        """Load OptiFine versions for selected MC version (for forge+optifine)."""
        mc_version = self.mc_version_var.get()
        
        if not mc_version or mc_version == t("loading"):
            return
        
        self.optifine_version_var.set(t("loading"))
        self.optifine_version_menu.configure(values=[t("loading")])
        
        def load():
            try:
                versions = self.mod_manager.get_optifine_versions(mc_version)
                version_strings = [v.loader_version for v in versions[:10]]  # Limit to 10
                
                def update_ui():
                    if version_strings:
                        self.optifine_version_menu.configure(values=version_strings)
                        self.optifine_version_var.set(version_strings[0])
                    else:
                        self.optifine_version_menu.configure(values=[t("not_found")])
                        self.optifine_version_var.set(t("not_found"))
                
                self.after(0, update_ui)
                
            except Exception as e:
                logger.debug(f"Failed to load OptiFine versions: {e}")
                self.after(0, lambda: self.optifine_version_var.set("Ошибка"))
        
        import threading
        threading.Thread(target=load, daemon=True).start()
    
    def _create_profile(self):
        """Create the profile."""
        name = self.name_entry.get().strip()
        mc_version = self.mc_version_var.get()
        loader_type = self.loader_type_var.get()
        loader_version = self.loader_version_var.get()
        optifine_version = self.optifine_version_var.get()  # For forge+optifine
        
        if not name:
            self.status_label.configure(
                text=f"⚠ {t('enter_profile_name')}",
                text_color=self.theme["error"]
            )
            return
        
        # Validate name - only allow letters, numbers, spaces, underscore, hyphen
        import re
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9_\- ]+$', name):
            self.status_label.configure(
                text=f"⚠ {t('name_contains_invalid_characters')}",
                text_color=self.theme["error"]
            )
            return
        
        if len(name) > 50:
            self.status_label.configure(
                text=f"⚠ {t('name_too_long')}",
                text_color=self.theme["error"]
            )
            return
        
        if mc_version in [t("loading"), t("no_versions"), t("error")]:
            self.status_label.configure(
                text=f"⚠ {t('select_minecraft_version')}",
                text_color=self.theme["error"]
            )
            return
        
        if loader_type != "vanilla" and loader_version in ["—", t("loading"), t("not_supported")]:
            self.status_label.configure(
                text=f"⚠ {t('select_loader_version')}",
                text_color=self.theme["error"]
            )
            return
        
        # Get game directory - auto-generate if not specified
        game_directory = self.game_dir_entry.get().strip()
        if not game_directory:
            # Auto-generate based on profile name
            game_directory = str(self.profile_manager.get_profile_directory(name))
        
        # Disable UI during installation (including cancel button)
        self.create_btn.configure(state="disabled", text="⏳ Создание...")
        self.cancel_btn.configure(state="disabled")
        self.name_entry.configure(state="disabled")
        self.mc_version_menu.configure(state="disabled")
        self.loader_type_menu.configure(state="disabled")
        self.loader_version_menu.configure(state="disabled")
        self.optifine_version_menu.configure(state="disabled")
        self.game_dir_entry.configure(state="disabled")
        
        # Show progress
        self.progress_bar = ctk.CTkProgressBar(
            self,
            width=300,
            height=10,
            fg_color=self.theme["bg_tertiary"],
            progress_color=self.theme["accent"]
        )
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)
        self.progress_bar.start()
        
        self.status_label.configure(
            text=f"⏳ {t('creating_profile')}...",
            text_color=self.theme["accent"]
        )
        
        # Install in background
        def install():
            try:
                # Install base MC version first
                self.after(0, lambda: self.status_label.configure(
                    text=f"⏳ {t('installing')} {mc_version}..."
                ))
                
                success = self.launcher.install_version(mc_version)
                if not success:
                    raise RuntimeError("Failed to install Minecraft")
                
                # Install loader if needed
                result = None
                if loader_type != "vanilla":
                    self.after(0, lambda: self.status_label.configure(
                        text=f"⏳ {t('installing')} {loader_type.capitalize()}..."
                    ))
                    
                    if loader_type == "fabric":
                        result = self.mod_manager.install_fabric(mc_version, loader_version)
                    elif loader_type == "forge":
                        result = self.mod_manager.install_forge(mc_version, loader_version)
                    elif loader_type == "forge+optifine":
                        # Install Forge first
                        result = self.mod_manager.install_forge(mc_version, loader_version)
                        if result:
                            # Then install OptiFine as a mod in the profile's mods folder
                            self.after(0, lambda: self.status_label.configure(
                                text=f"⏳ {t('installing')} OptiFine {optifine_version}..."
                            ))
                            # Use profile's game directory for mods
                            mods_game_dir = Path(game_directory)
                            # Use selected OptiFine version
                            of_ver = optifine_version if optifine_version and optifine_version not in ("—", t("loading"), t("not_found"), t("error")) else None
                            optifine_result = self.mod_manager.install_optifine_as_mod(
                                mc_version,
                                optifine_version=of_ver,
                                game_directory=mods_game_dir
                            )
                            if not optifine_result:
                                logger.warning("OptiFine mod installation failed, but Forge is ready")
                    elif loader_type == "neoforge":
                        result = self.mod_manager.install_neoforge(mc_version, loader_version)
                    elif loader_type == "quilt":
                        result = self.mod_manager.install_quilt(mc_version, loader_version)
                    elif loader_type == "optifine":
                        result = self.mod_manager.install_optifine(mc_version, loader_version)
                
                # Success - create profile and close
                def on_success():
                    self.progress_bar.stop()
                    self.progress_bar.set(1)
                    self.status_label.configure(
                        text=f"✅ {t('profile_created')}",
                        text_color=self.theme["success"]
                    )
                    
                    # Call the callback to actually save the profile
                    self.on_create(
                        name=name,
                        minecraft_version=mc_version,
                        loader_type=loader_type if loader_type != "vanilla" else None,
                        loader_version=loader_version if loader_type != "vanilla" else None,
                        game_directory=game_directory
                    )
                    
                    # Close window after short delay
                    self.after(1000, self.destroy)
                
                self.after(0, on_success)
                
            except Exception as e:
                error_msg = str(e)
                def on_error():
                    self.progress_bar.stop()
                    self.progress_bar.set(0)
                    self.status_label.configure(
                        text=f"❌ Ошибка: {error_msg[:50]}",
                        text_color=self.theme["error"]
                    )
                    # Re-enable UI
                    self.create_btn.configure(state="normal", text=f"✨ {t('create_profile')}")
                    self.cancel_btn.configure(state="normal")
                    self.name_entry.configure(state="normal")
                    self.mc_version_menu.configure(state="normal")
                    self.loader_type_menu.configure(state="normal")
                    self.loader_version_menu.configure(state="normal")
                    self.optifine_version_menu.configure(state="normal")
                    self.game_dir_entry.configure(state="normal")
                
                self.after(0, on_error)
        
        import threading
        threading.Thread(target=install, daemon=True).start()


class ModsWindow(ctk.CTkToplevel):
    """Mods and mod loaders management window."""
    
    def __init__(self, parent, mod_manager, launcher, theme: dict, selected_version: str):
        super().__init__(parent)
        
        self.mod_manager = mod_manager
        self.launcher = launcher
        self.theme = theme
        self.selected_version = selected_version
        self.is_installing = False
        
        self.title(t("mods_window_title"))
        self.geometry("600x550")
        self.minsize(500, 400)
        self.configure(fg_color=theme["bg_primary"])
        
        self.transient(parent)
        
        self._create_widgets()
        self.after(10, self._grab_focus)
    
    def _grab_focus(self):
        try:
            self.grab_set()
            self.focus_force()
        except:
            pass
    
    def _bind_mousewheel(self, widget):
        """Bind mouse wheel scrolling to widget and all children."""
        def _on_mousewheel(event):
            try:
                canvas = widget._parent_canvas
                if event.num == 4:  # Linux scroll up
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:  # Linux scroll down
                    canvas.yview_scroll(1, "units")
                elif event.delta:  # Windows/macOS
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except:
                pass
        
        widget.bind("<Button-4>", _on_mousewheel)
        widget.bind("<Button-5>", _on_mousewheel)
        widget.bind("<MouseWheel>", _on_mousewheel)
        
        def bind_children(w):
            for child in w.winfo_children():
                child.bind("<Button-4>", _on_mousewheel)
                child.bind("<Button-5>", _on_mousewheel)
                child.bind("<MouseWheel>", _on_mousewheel)
                bind_children(child)
        
        bind_children(widget)
    
    def _create_widgets(self):
        # Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title = ctk.CTkLabel(
            title_frame,
            text=f"🧩 {t('mods_window_title')}",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.theme["text_primary"]
        )
        title.pack(anchor="w")
        
        version_info = ctk.CTkLabel(
            title_frame,
            text=f"{t('version')}: {self.selected_version or t('not_selected')}",
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"]
        )
        version_info.pack(anchor="w")
        
        # Tab view
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=self.theme["bg_secondary"],
            segmented_button_fg_color=self.theme["bg_tertiary"],
            segmented_button_selected_color=self.theme["accent"],
            segmented_button_unselected_color=self.theme["bg_tertiary"],
            text_color=self.theme["text_primary"]
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.tab_loaders = self.tabview.add(f"{t('loaders')}")
        self.tab_mods = self.tabview.add(f"{t('mods')}")
        
        self._create_loaders_tab()
        self._create_mods_tab()
    
    def _create_loaders_tab(self):
        """Create mod loaders installation tab."""
        self.loader_buttons = []  # Store buttons to disable during install
        
        # Status panel at top (always visible)
        status_frame = ctk.CTkFrame(
            self.tab_loaders,
            fg_color=self.theme["bg_secondary"],
            corner_radius=10,
            height=60
        )
        status_frame.pack(fill="x", padx=10, pady=(10, 5))
        status_frame.pack_propagate(False)
        
        self.loader_status = ctk.CTkLabel(
            status_frame,
            text=t("select_loader"),
            font=ctk.CTkFont(size=13),
            text_color=self.theme["text_muted"]
        )
        self.loader_status.pack(pady=(10, 5))
        
        self.loader_progress = ctk.CTkProgressBar(
            status_frame,
            width=300,
            height=8,
            fg_color=self.theme["bg_tertiary"],
            progress_color=self.theme["accent"]
        )
        self.loader_progress.pack(pady=(0, 10))
        self.loader_progress.set(0)
        
        # Scrollable loaders list
        self.loaders_scroll = ctk.CTkScrollableFrame(
            self.tab_loaders,
            fg_color="transparent",
            scrollbar_button_color=self.theme["bg_tertiary"]
        )
        self.loaders_scroll.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.loaders_scroll.grid_columnconfigure(0, weight=1)
        
        if not self.selected_version:
            label = ctk.CTkLabel(
                self.loaders_scroll,
                text=t("select_mc_first"),
                font=ctk.CTkFont(size=14),
                text_color=self.theme["text_muted"]
            )
            label.pack(pady=50)
            return
        
        # Fabric
        fabric_frame = self._create_loader_card(
            self.loaders_scroll,
            "🪡 Fabric",
            t("fabric_desc"),
            self.mod_manager.is_fabric_supported(self.selected_version),
            lambda: self._install_fabric()
        )
        fabric_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Forge
        forge_frame = self._create_loader_card(
            self.loaders_scroll,
            "🔨 Forge",
            t("forge_desc"),
            self.mod_manager.is_forge_supported(self.selected_version),
            lambda: self._install_forge()
        )
        forge_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        # NeoForge
        neoforge_frame = self._create_loader_card(
            self.loaders_scroll,
            "⚡ NeoForge",
            t("neoforge_desc"),
            self.mod_manager.is_neoforge_supported(self.selected_version),
            lambda: self._install_neoforge()
        )
        neoforge_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        # Quilt
        quilt_frame = self._create_loader_card(
            self.loaders_scroll,
            "🧵 Quilt",
            t("quilt_desc"),
            self.mod_manager.is_quilt_supported(self.selected_version),
            lambda: self._install_quilt()
        )
        quilt_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        
        # Bind mouse wheel scrolling
        self._bind_mousewheel(self.loaders_scroll)
    
    def _create_loader_card(self, parent, name: str, desc: str, supported: bool, install_cmd):
        """Create a mod loader card."""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.theme["bg_card"],
            corner_radius=10
        )
        card.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        header.grid_columnconfigure(0, weight=1)
        
        title = ctk.CTkLabel(
            header,
            text=name,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme["text_primary"]
        )
        title.grid(row=0, column=0, sticky="w")
        
        # Description
        desc_label = ctk.CTkLabel(
            card,
            text=desc,
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"]
        )
        desc_label.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 10))
        
        # Install button
        if supported:
            btn = ctk.CTkButton(
                card,
                text=t("install_btn"),
                height=35,
                font=ctk.CTkFont(size=13),
                fg_color=self.theme["accent"],
                hover_color=self.theme["accent_hover"],
                text_color="#ffffff",
                command=install_cmd
            )
            self.loader_buttons.append(btn)  # Save for disabling during install
        else:
            btn = ctk.CTkButton(
                card,
                text=t("not_supported"),
                height=35,
                font=ctk.CTkFont(size=13),
                fg_color=self.theme["bg_tertiary"],
                text_color=self.theme["text_muted"],
                state="disabled"
            )
        btn.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        return card
    
    def _create_mods_tab(self):
        """Create installed mods tab."""
        frame = ctk.CTkFrame(self.tab_mods, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Header with Open Folder buttons
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(2, weight=1)  # Push refresh button to right
        
        open_mods_btn = ctk.CTkButton(
            header,
            text=f"📂 {t('mods_folder')}",
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color=self.theme["bg_tertiary"],
            hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self.mod_manager.open_mods_folder
        )
        open_mods_btn.grid(row=0, column=0, sticky="w")
        
        open_mc_btn = ctk.CTkButton(
            header,
            text=f"📁 {t('minecraft_folder')}",
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color=self.theme["bg_tertiary"],
            hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self.mod_manager.open_minecraft_folder
        )
        open_mc_btn.grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        refresh_btn = ctk.CTkButton(
            header,
            text="🔄",
            width=35,
            height=35,
            font=ctk.CTkFont(size=14),
            fg_color=self.theme["bg_tertiary"],
            hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self._refresh_mods
        )
        refresh_btn.grid(row=0, column=2, sticky="e", padx=(10, 0))
        
        # Mods list
        self.mods_scroll = ctk.CTkScrollableFrame(
            frame,
            fg_color=self.theme["bg_secondary"],
            corner_radius=10,
            scrollbar_button_color=self.theme["bg_tertiary"]
        )
        self.mods_scroll.grid(row=1, column=0, sticky="nsew")
        self.mods_scroll.grid_columnconfigure(0, weight=1)
        
        # Bind mouse wheel scrolling
        self._bind_mousewheel(self.mods_scroll)
        
        self._refresh_mods()
    
    def _refresh_mods(self):
        """Refresh the mods list."""
        # Clear existing
        for widget in self.mods_scroll.winfo_children():
            widget.destroy()
        
        mods = self.mod_manager.get_mods_list()
        
        if not mods:
            empty_label = ctk.CTkLabel(
                self.mods_scroll,
                text=t("mods_not_found"),
                font=ctk.CTkFont(size=13),
                text_color=self.theme["text_muted"],
                justify="center"
            )
            empty_label.grid(row=0, column=0, pady=50)
            return
        
        for i, mod in enumerate(mods):
            self._create_mod_row(mod, i)
        
        # Rebind mouse wheel after recreating widgets
        self._bind_mousewheel(self.mods_scroll)
    
    def _create_mod_row(self, mod: dict, row: int):
        """Create a row for a mod."""
        frame = ctk.CTkFrame(
            self.mods_scroll,
            fg_color=self.theme["bg_card"] if mod["enabled"] else self.theme["bg_tertiary"],
            corner_radius=8
        )
        frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        frame.grid_columnconfigure(0, weight=1)
        
        # Mod name
        name_label = ctk.CTkLabel(
            frame,
            text=mod["name"],
            font=ctk.CTkFont(size=13, weight="bold" if mod["enabled"] else "normal"),
            text_color=self.theme["text_primary"] if mod["enabled"] else self.theme["text_muted"],
            anchor="w"
        )
        name_label.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        
        # Size
        size_mb = mod["size"] / (1024 * 1024)
        size_label = ctk.CTkLabel(
            frame,
            text=f"{size_mb:.1f} MB" + (" • Отключён" if not mod["enabled"] else ""),
            font=ctk.CTkFont(size=11),
            text_color=self.theme["text_muted"]
        )
        size_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))
        
        # Toggle button
        toggle_btn = ctk.CTkButton(
            frame,
            text="✓" if mod["enabled"] else "✗",
            width=30,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=self.theme["success"] if mod["enabled"] else self.theme["bg_tertiary"],
            hover_color=self.theme["bg_hover"],
            text_color="#ffffff" if mod["enabled"] else self.theme["text_muted"],
            command=lambda p=mod["path"]: self._toggle_mod(p)
        )
        toggle_btn.grid(row=0, column=1, rowspan=2, padx=(5, 5), pady=5)
        
        # Delete button
        delete_btn = ctk.CTkButton(
            frame,
            text="🗑",
            width=30,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=self.theme["error"],
            text_color=self.theme["text_muted"],
            command=lambda p=mod["path"], n=mod["name"]: self._delete_mod(p, n)
        )
        delete_btn.grid(row=0, column=2, rowspan=2, padx=(0, 10), pady=5)
    
    def _toggle_mod(self, path: str):
        """Toggle mod enabled/disabled."""
        self.mod_manager.toggle_mod(path)
        self._refresh_mods()
    
    def _delete_mod(self, path: str, name: str):
        """Delete a mod."""
        from tkinter import messagebox
        
        if messagebox.askyesno("Удаление мода", f"Удалить мод {name}?", parent=self):
            self.mod_manager.delete_mod(path)
            self._refresh_mods()
    
    def _start_install(self, loader_name: str):
        """Start installation - disable buttons and show progress."""
        self.is_installing = True
        self.loader_status.configure(
            text=f"⏳ {t('installing')} {loader_name}...",
            text_color=self.theme["accent"]
        )
        self.loader_progress.set(0)
        self.loader_progress.start()
        
        # Disable all install buttons
        for btn in self.loader_buttons:
            btn.configure(state="disabled")
    
    def _finish_install(self, success: bool, loader_name: str, version_id: str = ""):
        """Finish installation - enable buttons and show result."""
        self.is_installing = False
        self.loader_progress.stop()
        self.loader_progress.set(1 if success else 0)
        
        if success:
            self.loader_status.configure(
                text=f"✅ {loader_name} {t('installed')}: {version_id}",
                text_color=self.theme["success"]
            )
        else:
            self.loader_status.configure(
                text=f"❌ {t('error_installing')} {loader_name}",
                text_color=self.theme["error"]
            )
        
        # Enable all install buttons
        for btn in self.loader_buttons:
            btn.configure(state="normal")
    
    def _install_fabric(self):
        """Install Fabric."""
        if self.is_installing:
            return
        
        self._start_install("Fabric")
        
        def install():
            result = self.mod_manager.install_fabric(
                self.selected_version,
                callback={
                    "setStatus": lambda s: self.after(0, lambda: self.loader_status.configure(text=f"⏳ {s}"))
                }
            )
            self.after(0, lambda: self._finish_install(bool(result), "Fabric", result or ""))
        
        import threading
        threading.Thread(target=install, daemon=True).start()
    
    def _install_forge(self):
        """Install Forge."""
        if self.is_installing:
            return
        
        self._start_install("Forge")
        
        def install():
            result = self.mod_manager.install_forge(
                self.selected_version,
                callback={
                    "setStatus": lambda s: self.after(0, lambda: self.loader_status.configure(text=f"⏳ {s}"))
                }
            )
            self.after(0, lambda: self._finish_install(bool(result), "Forge", result or ""))
        
        import threading
        threading.Thread(target=install, daemon=True).start()
    
    def _install_neoforge(self):
        """Install NeoForge."""
        if self.is_installing:
            return
        
        self._start_install("NeoForge")
        
        def install():
            result = self.mod_manager.install_neoforge(
                self.selected_version,
                callback={
                    "setStatus": lambda s: self.after(0, lambda: self.loader_status.configure(text=f"⏳ {s}"))
                }
            )
            self.after(0, lambda: self._finish_install(bool(result), "NeoForge", result or ""))
        
        import threading
        threading.Thread(target=install, daemon=True).start()
    
    def _install_quilt(self):
        """Install Quilt."""
        if self.is_installing:
            return
        
        self._start_install("Quilt")
        
        def install():
            result = self.mod_manager.install_quilt(
                self.selected_version,
                callback={
                    "setStatus": lambda s: self.after(0, lambda: self.loader_status.configure(text=f"⏳ {s}"))
                }
            )
            self.after(0, lambda: self._finish_install(bool(result), "Quilt", result or ""))
        
        import threading
        threading.Thread(target=install, daemon=True).start()


class SettingsWindow(ctk.CTkToplevel):
    """Settings window."""
    
    def __init__(self, parent, config: Config, theme: dict, on_save: Callable):
        super().__init__(parent)
        
        self.config = config
        self.theme = theme
        self.on_save = on_save
        
        self.title(t("settings_title"))
        self.geometry("500x600")
        self.minsize(450, 400)
        self.configure(fg_color=theme["bg_primary"])
        
        # Make modal
        self.transient(parent)
        
        self._create_widgets()
        self._load_values()
        
        # Grab focus after window is visible
        self.after(10, self._grab_focus)
    
    def _grab_focus(self):
        """Grab focus after window is visible."""
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass  # Ignore if grab fails
    
    def _create_widgets(self):
        # Title (outside scrollable area)
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title = ctk.CTkLabel(
            title_frame,
            text=f"⚙️ {t('settings')}",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.theme["text_primary"]
        )
        title.pack(anchor="w")
        
        # Scrollable container for settings
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.theme["bg_tertiary"],
            scrollbar_button_hover_color=self.theme["bg_hover"]
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Bind mousewheel for Linux
        self._bind_scroll_mousewheel()
        
        container = self.scroll_frame
        row = 0
        
        # RAM Settings
        self._add_section_label(container, f"{t('ram')} ({t('ram_gb')})", row)
        row += 1
        
        ram_frame = ctk.CTkFrame(container, fg_color="transparent")
        ram_frame.grid(row=row, column=0, sticky="ew", pady=(0, 15))
        ram_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Min RAM
        min_label = ctk.CTkLabel(
            ram_frame,
            text=t("ram_min"),
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_secondary"]
        )
        min_label.grid(row=0, column=0, sticky="w")
        
        self.ram_min_slider = ctk.CTkSlider(
            ram_frame,
            from_=1,
            to=16,
            number_of_steps=15,
            fg_color=self.theme["bg_tertiary"],
            progress_color=self.theme["accent"],
            button_color=self.theme["accent"],
            button_hover_color=self.theme["accent_hover"]
        )
        self.ram_min_slider.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        
        self.ram_min_label = ctk.CTkLabel(
            ram_frame,
            text="2 GB",
            font=ctk.CTkFont(size=12),
            text_color=self.theme["accent"]
        )
        self.ram_min_label.grid(row=1, column=1, sticky="w")
        
        self.ram_min_slider.configure(command=self._update_ram_min_label)
        
        # Max RAM
        max_label = ctk.CTkLabel(
            ram_frame,
            text=t("ram_max"),
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_secondary"]
        )
        max_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
        
        self.ram_max_slider = ctk.CTkSlider(
            ram_frame,
            from_=1,
            to=32,
            number_of_steps=31,
            fg_color=self.theme["bg_tertiary"],
            progress_color=self.theme["accent"],
            button_color=self.theme["accent"],
            button_hover_color=self.theme["accent_hover"]
        )
        self.ram_max_slider.grid(row=3, column=0, sticky="ew", padx=(0, 10))
        
        self.ram_max_label = ctk.CTkLabel(
            ram_frame,
            text="4 GB",
            font=ctk.CTkFont(size=12),
            text_color=self.theme["accent"]
        )
        self.ram_max_label.grid(row=3, column=1, sticky="w")
        
        self.ram_max_slider.configure(command=self._update_ram_max_label)
        row += 1
        
        # Java Path
        self._add_section_label(container, "Путь к Java (оставьте пустым для автопоиска)", row)
        row += 1
        
        java_frame = ctk.CTkFrame(container, fg_color="transparent")
        java_frame.grid(row=row, column=0, sticky="ew", pady=(0, 15))
        java_frame.grid_columnconfigure(0, weight=1)
        
        self.java_entry = ctk.CTkEntry(
            java_frame,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=self.theme["bg_secondary"],
            border_color=self.theme["border"],
            text_color=self.theme["text_primary"],
            placeholder_text=t("java_auto")
        )
        self.java_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        browse_btn = ctk.CTkButton(
            java_frame,
            text="📁",
            width=40,
            height=40,
            fg_color=self.theme["bg_secondary"],
            hover_color=self.theme["bg_tertiary"],
            text_color=self.theme["text_primary"],
            command=self._browse_java
        )
        browse_btn.grid(row=0, column=1)
        row += 1
        
        # Theme
        self._add_section_label(container, "Тема оформления", row)
        row += 1
        
        self.theme_var = ctk.StringVar(value="dark")
        self.theme_menu = ctk.CTkOptionMenu(
            container,
            values=["dark", "light", "midnight"],
            variable=self.theme_var,
            height=40,
            fg_color=self.theme["bg_secondary"],
            button_color=self.theme["bg_tertiary"],
            button_hover_color=self.theme["bg_hover"],
            dropdown_fg_color=self.theme["bg_secondary"],
            dropdown_hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"]
        )
        self.theme_menu.grid(row=row, column=0, sticky="ew", pady=(0, 15))
        row += 1
        
        # Language
        self._add_section_label(container, t("language"), row)
        row += 1
        
        self.language_var = ctk.StringVar(value=self.config.get("language", "ru"))
        # Build language options with names
        lang_values = [f"{code} - {name}" for code, name in LANGUAGES.items()]
        self.language_menu = ctk.CTkOptionMenu(
            container,
            values=lang_values,
            variable=self.language_var,
            height=40,
            fg_color=self.theme["bg_secondary"],
            button_color=self.theme["bg_tertiary"],
            button_hover_color=self.theme["bg_hover"],
            dropdown_fg_color=self.theme["bg_secondary"],
            dropdown_hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self._on_language_preview
        )
        # Set current language display
        current_lang = self.config.get("language", "ru")
        if current_lang in LANGUAGES:
            self.language_var.set(f"{current_lang} - {LANGUAGES[current_lang]}")
        self.language_menu.grid(row=row, column=0, sticky="ew", pady=(0, 15))
        row += 1
        
        # Checkboxes
        self.show_snapshots_var = ctk.BooleanVar()
        self.show_snapshots_cb = ctk.CTkCheckBox(
            container,
            text=t("show_snapshots"),
            variable=self.show_snapshots_var,
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_primary"],
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            border_color=self.theme["border"]
        )
        self.show_snapshots_cb.grid(row=row, column=0, sticky="w", pady=(0, 10))
        row += 1
        
        self.show_old_var = ctk.BooleanVar()
        self.show_old_cb = ctk.CTkCheckBox(
            container,
            text=t("show_old_versions"),
            variable=self.show_old_var,
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_primary"],
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            border_color=self.theme["border"]
        )
        self.show_old_cb.grid(row=row, column=0, sticky="w", pady=(0, 10))
        row += 1
        
        self.close_on_launch_var = ctk.BooleanVar()
        self.close_on_launch_cb = ctk.CTkCheckBox(
            container,
            text=t("close_on_launch"),
            variable=self.close_on_launch_var,
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_primary"],
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            border_color=self.theme["border"]
        )
        self.close_on_launch_cb.grid(row=row, column=0, sticky="w", pady=(0, 10))
        row += 1
        
        self.show_console_var = ctk.BooleanVar()
        self.show_console_cb = ctk.CTkCheckBox(
            container,
            text=t("debug_console"),
            variable=self.show_console_var,
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_primary"],
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            border_color=self.theme["border"]
        )
        self.show_console_cb.grid(row=row, column=0, sticky="w", pady=(0, 10))
        row += 1
        
        # Buttons (outside scrollable area)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=self.theme["bg_secondary"],
            hover_color=self.theme["bg_tertiary"],
            text_color=self.theme["text_primary"],
            command=self.destroy
        )
        cancel_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        save_btn = ctk.CTkButton(
            btn_frame,
            text=t("save"),
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            text_color="#ffffff",
            command=self._save
        )
        save_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))
    
    def _bind_scroll_mousewheel(self):
        """Bind mouse wheel scrolling for Linux."""
        def _on_mousewheel(event):
            try:
                canvas = self.scroll_frame._parent_canvas
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
                elif event.delta:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except:
                pass
        
        self.scroll_frame.bind("<Button-4>", _on_mousewheel)
        self.scroll_frame.bind("<Button-5>", _on_mousewheel)
        self.scroll_frame.bind("<MouseWheel>", _on_mousewheel)
        
        def bind_children(w):
            for child in w.winfo_children():
                child.bind("<Button-4>", _on_mousewheel)
                child.bind("<Button-5>", _on_mousewheel)
                child.bind("<MouseWheel>", _on_mousewheel)
                bind_children(child)
        
        self.after(100, lambda: bind_children(self.scroll_frame))
    
    def _add_section_label(self, parent, text: str, row: int):
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color=self.theme["text_secondary"]
        )
        label.grid(row=row, column=0, sticky="w", pady=(0, 5))
    
    def _update_ram_min_label(self, value):
        self.ram_min_label.configure(text=f"{int(value)} GB")
    
    def _update_ram_max_label(self, value):
        self.ram_max_label.configure(text=f"{int(value)} GB")
    
    def _browse_java(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self,
            title="Выберите Java",
            filetypes=[("Java", "java*"), ("All files", "*.*")]
        )
        if path:
            self.java_entry.delete(0, "end")
            self.java_entry.insert(0, path)
    
    def _load_values(self):
        self.ram_min_slider.set(self.config["ram_min"])
        self.ram_max_slider.set(self.config["ram_max"])
        self._update_ram_min_label(self.config["ram_min"])
        self._update_ram_max_label(self.config["ram_max"])
        
        if self.config["java_path"]:
            self.java_entry.insert(0, self.config["java_path"])
        
        self.theme_var.set(self.config["theme"])
        self.show_snapshots_var.set(self.config["show_snapshots"])
        self.show_old_var.set(self.config["show_old_versions"])
        self.close_on_launch_var.set(self.config["close_on_launch"])
        self.show_console_var.set(self.config.get("show_game_console", False))
    
    def _on_language_preview(self, value: str):
        """Preview language change."""
        # Extract language code from "code - Name" format
        lang_code = value.split(" - ")[0]
        # Note: actual language change requires restart
        pass
    
    def _save(self):
        self.config["ram_min"] = int(self.ram_min_slider.get())
        self.config["ram_max"] = int(self.ram_max_slider.get())
        self.config["java_path"] = self.java_entry.get()
        self.config["theme"] = self.theme_var.get()
        self.config["show_snapshots"] = self.show_snapshots_var.get()
        self.config["show_old_versions"] = self.show_old_var.get()
        self.config["close_on_launch"] = self.close_on_launch_var.get()
        self.config["show_game_console"] = self.show_console_var.get()
        
        # Save language (extract code from "code - Name" format)
        lang_value = self.language_var.get()
        lang_code = lang_value.split(" - ")[0] if " - " in lang_value else lang_value
        old_lang = self.config.get("language", "ru")
        self.config["language"] = lang_code
        
        self.on_save()
        self.destroy()
        
        # If language changed, restart the launcher automatically
        if lang_code != old_lang:
            import sys
            import os
            python = sys.executable
            os.execl(python, python, *sys.argv)


class MainWindow(ctk.CTk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize config and core
        self.config = Config()
        self.theme = get_theme(self.config["theme"])
        
        # Initialize i18n with saved language
        set_language(self.config.get("language", "ru"))
        
        self.launcher = LauncherCore(self.config.get_minecraft_dir())
        self.mod_manager = ModManager(self.config.get_minecraft_dir(), launcher_core=self.launcher)
        self.profile_manager = ProfileManager(self.config.config_dir, minecraft_dir=self.config.get_minecraft_dir())
        self.auth = AuthManager(self.config.config_dir)
        
        # State
        self.selected_version: Optional[str] = None
        self.selected_profile: Optional[Profile] = None
        self.version_cards: dict[str, VersionCard] = {}
        self.is_downloading = False
        self.is_logging_in = False
        
        # Window setup
        self.title(f"CraftLauncher")
        self.geometry("1000x700")
        self.minsize(800, 600)
        self.configure(fg_color=self.theme["bg_primary"])
        
        # Set up callbacks
        self.launcher.on_status = self._update_status
        self.launcher.on_progress = self._update_progress
        
        # Create UI
        self._create_widgets()
        
        # Load versions
        self.after(100, self._load_versions)
    
    def _create_widgets(self):
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self._create_sidebar()
        
        # Main content
        self._create_main_content()
    
    def _create_sidebar(self):
        sidebar = ctk.CTkFrame(
            self,
            width=280,
            fg_color=self.theme["bg_secondary"],
            corner_radius=0
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)
        
        # Logo/Title
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        title = ctk.CTkLabel(
            logo_frame,
            text="⛏️ CraftLauncher",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.theme["text_primary"]
        )
        title.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(
            logo_frame,
            text=f"{t('minecraft_launcher')}",
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"]
        )
        subtitle.pack(anchor="w")
        
        # User info
        user_frame = ctk.CTkFrame(
            sidebar,
            fg_color=self.theme["bg_tertiary"],
            corner_radius=10
        )
        user_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        user_inner = ctk.CTkFrame(user_frame, fg_color="transparent")
        user_inner.pack(padx=12, pady=12, fill="x")
        
        # Player head image placeholder
        self.player_head_label = ctk.CTkLabel(
            user_inner,
            text="👤",
            font=ctk.CTkFont(size=32),
            width=48,
            height=48
        )
        self.player_head_label.pack(side="left", padx=(0, 10))
        
        user_text_frame = ctk.CTkFrame(user_inner, fg_color="transparent")
        user_text_frame.pack(side="left", fill="x", expand=True)
        
        # Username label - show logged in user or config username
        display_name = self.auth.get_username() or self.config['username']
        self.username_label = ctk.CTkLabel(
            user_text_frame,
            text=display_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme["text_primary"],
            anchor="w"
        )
        self.username_label.pack(anchor="w")
        
        self.skin_status_label = ctk.CTkLabel(
            user_text_frame,
            text=t("loading"),
            font=ctk.CTkFont(size=11),
            text_color=self.theme["text_muted"],
            anchor="w"
        )
        self.skin_status_label.pack(anchor="w")
        
        # Auth button (Login/Logout)
        self.auth_button = ctk.CTkButton(
            user_frame,
            text="👤 Добавить аккаунт" if not self.auth.is_logged_in() else "Выйти",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=self.theme["accent"] if not self.auth.is_logged_in() else self.theme["bg_secondary"],
            hover_color=self.theme["accent_hover"] if not self.auth.is_logged_in() else self.theme["bg_hover"],
            text_color="#ffffff" if not self.auth.is_logged_in() else self.theme["text_secondary"],
            command=self._toggle_auth
        )
        self.auth_button.pack(padx=12, pady=(0, 12), fill="x")
        
        # Update UI based on auth state
        self._update_auth_ui()
        
        # Load skin in background
        self._load_player_skin()
        
        # Version list (scrollable)
        version_container = ctk.CTkFrame(sidebar, fg_color="transparent")
        version_container.grid(row=2, column=0, sticky="nsew", padx=15)
        version_container.grid_rowconfigure(1, weight=1)
        version_container.grid_columnconfigure(0, weight=1)
        
        version_title = ctk.CTkLabel(
            version_container,
            text=t("versions"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme["text_secondary"]
        )
        version_title.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        self.version_scroll = ctk.CTkScrollableFrame(
            version_container,
            fg_color="transparent",
            scrollbar_button_color=self.theme["bg_tertiary"],
            scrollbar_button_hover_color=self.theme["bg_hover"]
        )
        self.version_scroll.grid(row=1, column=0, sticky="nsew")
        self.version_scroll.grid_columnconfigure(0, weight=1)
        
        # Bind mouse wheel scrolling for Linux
        self._bind_mousewheel(self.version_scroll)
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        buttons_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=15)
        buttons_frame.grid_columnconfigure(0, weight=1)
        
        # Create profile button
        create_btn = ctk.CTkButton(
            buttons_frame,
            text=f"✨ {t('create_profile')}",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            text_color="#ffffff",
            command=self._open_create_profile
        )
        create_btn.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        
        # Mods button
        mods_btn = ctk.CTkButton(
            buttons_frame,
            text=f"🧩 {t('mods')}",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme["bg_tertiary"],
            hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self._open_mods
        )
        mods_btn.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        
        # Settings button
        settings_btn = ctk.CTkButton(
            buttons_frame,
            text=f"⚙️ {t('settings')}",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme["bg_tertiary"],
            hover_color=self.theme["bg_hover"],
            text_color=self.theme["text_primary"],
            command=self._open_settings
        )
        settings_btn.grid(row=2, column=0, sticky="ew")
    
    def _create_main_content(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        
        # Header
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header.grid_columnconfigure(0, weight=1)
        
        welcome = ctk.CTkLabel(
            header,
            text=t("welcome"),
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=self.theme["text_primary"]
        )
        welcome.grid(row=0, column=0, sticky="w")
        
        desc = ctk.CTkLabel(
            header,
            text=t("select_version"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_secondary"]
        )
        desc.grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        # Selected version card
        self.selected_card = ctk.CTkFrame(
            main,
            fg_color=self.theme["bg_card"],
            corner_radius=15,
            border_width=2,
            border_color=self.theme["accent"]
        )
        self.selected_card.grid(row=1, column=0, sticky="nsew")
        self.selected_card.grid_columnconfigure(0, weight=1)
        self.selected_card.grid_rowconfigure(0, weight=1)
        
        # Content inside selected card
        card_content = ctk.CTkFrame(self.selected_card, fg_color="transparent")
        card_content.place(relx=0.5, rely=0.5, anchor="center")
        
        self.selected_icon = ctk.CTkLabel(
            card_content,
            text="🎮",
            font=ctk.CTkFont(size=64)
        )
        self.selected_icon.pack(pady=(0, 15))
        
        self.selected_version_label = ctk.CTkLabel(
            card_content,
            text=t("no_version_selected"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.theme["text_primary"]
        )
        self.selected_version_label.pack(pady=(0, 5))
        
        self.selected_type_label = ctk.CTkLabel(
            card_content,
            text=t("select_version_hint"),
            font=ctk.CTkFont(size=14),
            text_color=self.theme["text_muted"]
        )
        self.selected_type_label.pack(pady=(0, 25))
        
        # Progress bar (hidden by default)
        self.progress_frame = ctk.CTkFrame(card_content, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(0, 15))
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            height=8,
            fg_color=self.theme["bg_tertiary"],
            progress_color=self.theme["accent"]
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        self.progress_frame.pack_forget()
        
        # Status label
        self.status_label = ctk.CTkLabel(
            card_content,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.theme["text_muted"]
        )
        self.status_label.pack(pady=(0, 20))
        
        # Play button
        self.play_button = ctk.CTkButton(
            card_content,
            text=f"▶  {t('play')}",
            width=250,
            height=60,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            text_color="#ffffff",
            corner_radius=12,
            command=self._play
        )
        self.play_button.pack()
        self.play_button.configure(state="disabled")
    
    def _bind_mousewheel(self, widget):
        """Bind mouse wheel scrolling to widget and all children."""
        def _on_mousewheel(event):
            # Get the scrollable frame's canvas
            try:
                canvas = widget._parent_canvas
                if event.num == 4:  # Linux scroll up
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:  # Linux scroll down
                    canvas.yview_scroll(1, "units")
                elif event.delta:  # Windows/macOS
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except:
                pass
        
        # Bind to the widget itself
        widget.bind("<Button-4>", _on_mousewheel)  # Linux scroll up
        widget.bind("<Button-5>", _on_mousewheel)  # Linux scroll down
        widget.bind("<MouseWheel>", _on_mousewheel)  # Windows/macOS
        
        # Bind to all children recursively
        def bind_children(w):
            for child in w.winfo_children():
                child.bind("<Button-4>", _on_mousewheel)
                child.bind("<Button-5>", _on_mousewheel)
                child.bind("<MouseWheel>", _on_mousewheel)
                bind_children(child)
        
        bind_children(widget)
    
    def _update_auth_ui(self):
        """Update UI elements based on authentication state."""
        account = self.auth.get_active_account()
        
        if account:
            self.username_label.configure(text=account.username)
            
            # Show account type with appropriate styling
            type_info = {
                "offline": ("Локальный", self.theme["text_muted"]),
                "microsoft": ("Microsoft ✓", self.theme["info"]),
                "elyby": ("Ely.by ✓", self.theme["success"]),
            }
            type_text, type_color = type_info.get(account.type, ("", self.theme["text_muted"]))
            
            self.skin_status_label.configure(text=type_text, text_color=type_color)
            self.auth_button.configure(
                text=t("logout"),
                fg_color=self.theme["bg_secondary"],
                hover_color=self.theme["bg_hover"],
                text_color=self.theme["text_secondary"]
            )
        else:
            self.username_label.configure(text=t("not_authorized"))
            self.skin_status_label.configure(
                text=t("click_to_login"),
                text_color=self.theme["text_muted"]
            )
            self.auth_button.configure(
                text="👤 Добавить аккаунт",
                fg_color=self.theme["accent"],
                hover_color=self.theme["accent_hover"],
                text_color="#ffffff"
            )
    
    def _toggle_auth(self):
        """Handle login/logout button click."""
        if self.auth.is_logged_in():
            # Logout
            self.auth.logout()
            self._update_auth_ui()
            self._update_status("Вы вышли из аккаунта")
            self._load_player_skin()
        else:
            # Open account window
            def on_complete(success: bool, message: str):
                self._update_auth_ui()
                self._update_status(message)
                if success:
                    self._load_player_skin()
            
            AccountWindow(self, self.auth, self.theme, on_complete)
    
    def _load_player_skin(self):
        """Load player skin from Ely.by in background."""
        account = self.auth.get_active_account()
        
        # Only load skin for Ely.by accounts
        if not account or account.type != "elyby":
            return
        
        username = account.username
        
        def load():
            try:
                from ..elyby import elyby
                from PIL import Image
                
                # Try to get head render
                head_path = elyby.download_head_render(username, size=96)
                
                if head_path and head_path.exists():
                    # Load and display image
                    img = Image.open(head_path)
                    ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))
                    
                    def update_ui():
                        self.player_head_label.configure(image=ctk_image, text="")
                        self.player_head_label.image = ctk_image  # Keep reference
                        
                        # Check if user exists on Ely.by
                        profile = elyby.get_profile_by_username(username)
                        if profile and profile.uuid:
                            self.skin_status_label.configure(
                                text="Ely.by ✓",
                                text_color=self.theme["success"]
                            )
                        else:
                            self.skin_status_label.configure(
                                text=t("skin_default"),
                                text_color=self.theme["text_muted"]
                            )
                    
                    self.after(0, update_ui)
                else:
                    self.after(0, lambda: self.skin_status_label.configure(
                        text=t("skin_not_found"),
                        text_color=self.theme["text_muted"]
                    ))
                    
            except Exception as e:
                logger.debug(f"Failed to load player skin: {e}")
                self.after(0, lambda: self.skin_status_label.configure(
                    text=t("offline_mode"),
                    text_color=self.theme["text_muted"]
                ))
        
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
    
    def _load_versions(self):
        """Load available versions in background."""
        self._update_status(f"⏳ {t('loading_version_list')}...")
        
        def load():
            try:
                versions = self.launcher.get_available_versions(
                    include_snapshots=self.config["show_snapshots"],
                    include_old=self.config["show_old_versions"]
                )
                self.after(0, lambda: self._display_versions(versions))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: self._update_status(f"Ошибка загрузки: {msg}"))
        
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
    
    def _display_versions(self, versions: list[VersionInfo]):
        """Display versions in the sidebar."""
        # Clear existing
        for widget in self.version_scroll.winfo_children():
            widget.destroy()
        self.version_cards.clear()
        
        row = 0
        
        # Display custom profiles first
        profiles = self.profile_manager.get_all_profiles()
        if profiles:
            # Profiles header
            profiles_header = ctk.CTkLabel(
                self.version_scroll,
                text=f"📦 {t('my_profiles')}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=self.theme["text_muted"],
                anchor="w"
            )
            profiles_header.grid(row=row, column=0, sticky="ew", pady=(0, 5))
            row += 1
            
            for profile in profiles:
                card = ProfileCard(
                    self.version_scroll,
                    profile,
                    self.theme,
                    on_select=self._select_profile,
                    on_delete=self._delete_profile
                )
                card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
                self.version_cards[f"profile:{profile.id}"] = card
                row += 1
            
            # Separator
            separator = ctk.CTkFrame(
                self.version_scroll,
                height=1,
                fg_color=self.theme["border"]
            )
            separator.grid(row=row, column=0, sticky="ew", pady=10)
            row += 1
        
        # Versions header
        versions_header = ctk.CTkLabel(
            self.version_scroll,
            text=f"🎮 {t('versions')}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.theme["text_muted"],
            anchor="w"
        )
        versions_header.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1
        
        for version in versions:
            card = VersionCard(
                self.version_scroll,
                version,
                self.theme,
                on_select=self._select_version,
                on_delete=self._delete_version
            )
            card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
            self.version_cards[version.id] = card
            row += 1
        
        # Rebind mouse wheel to new cards
        self._bind_mousewheel(self.version_scroll)
        
        # Select last used version or latest
        last_version = self.config["last_version"]
        if last_version and last_version in self.version_cards:
            # Check if it's a profile or regular version
            if last_version.startswith("profile:"):
                profile_id = last_version.replace("profile:", "")
                self._select_profile(profile_id)
            else:
                self._select_version(last_version)
        elif profiles:
            # Select first profile
            self._select_profile(profiles[0].id)
        elif versions:
            # Find latest release
            for v in versions:
                if v.type == "release":
                    self._select_version(v.id)
                    break
        
        self._update_status(t("done"))
    
    def _select_version(self, version_id: str):
        """Select a version."""
        # Deselect previous
        if self.selected_version and self.selected_version in self.version_cards:
            self.version_cards[self.selected_version].set_selected(False)
        
        # Select new
        self.selected_version = version_id
        if version_id in self.version_cards:
            card = self.version_cards[version_id]
            card.set_selected(True)
            
            # Update main display
            self.selected_version_label.configure(text=version_id)
            
            type_text = {
                "release": t("release"),
                "snapshot": t("snapshot"),
                "old_beta": t("old_beta"),
                "old_alpha": t("old_alpha"),
            }.get(card.version.type, card.version.type)
            
            installed_text = f" • {t('installed')} ✓" if card.version.installed else ""
            self.selected_type_label.configure(text=f"{type_text}{installed_text}")
            
            # Update button
            if card.version.installed:
                self.play_button.configure(text=f"▶  {t('play')}", state="normal")
            else:
                self.play_button.configure(text=f"📥  {t('install')}", state="normal")
        
        # Save selection
        self.config["last_version"] = version_id
        self.config.save()
    
    def _select_profile(self, profile_id: str):
        """Select a profile."""
        profile = self.profile_manager.get_profile(profile_id)
        if not profile:
            return
        
        # Deselect previous
        if self.selected_version and self.selected_version in self.version_cards:
            self.version_cards[self.selected_version].set_selected(False)
        
        # Select new
        card_id = f"profile:{profile_id}"
        self.selected_version = card_id
        self.selected_profile = profile
        
        if card_id in self.version_cards:
            card = self.version_cards[card_id]
            card.set_selected(True)
            
            # Update main display
            self.selected_version_label.configure(text=profile.name)
            
            loader_info = profile.loader_type.capitalize() if profile.loader_type else "Vanilla"
            self.selected_type_label.configure(
                text=f"MC {profile.minecraft_version} • {loader_info}"
            )
            
            # Check if version is installed using direct method
            is_installed = self.launcher.is_version_installed(profile.version_id)
            
            if is_installed:
                self.play_button.configure(text=f"▶  {t('play')}", state="normal")
            else:
                self.play_button.configure(text=f"📥  {t('install')}", state="normal")
        
        # Save selection
        self.config["last_version"] = card_id
        self.config.save()
    
    def _delete_profile(self, profile_id: str):
        """Delete a profile."""
        from tkinter import messagebox
        import shutil
        
        profile = self.profile_manager.get_profile(profile_id)
        if not profile:
            return
        
        # Check if this version is used by other profiles
        version_id = profile.version_id
        other_profiles_using_version = [
            p for p in self.profile_manager.get_all_profiles()
            if p.id != profile_id and p.version_id == version_id
        ]
        version_in_use = len(other_profiles_using_version) > 0
        
        # Check if version is installed
        version_installed = self.launcher.is_version_installed(version_id)
        
        # Build message
        has_custom_dir = profile.game_directory and Path(profile.game_directory).exists()
        
        msg = f"{t('delete_profile_confirm')}: {profile.name}?\n\n"
        
        if has_custom_dir:
            msg += f"📁 {t('profile_folder')}: {profile.game_directory}\n"
        
        if version_installed:
            msg += f"📦 {t('version')}: {version_id}\n"
            if version_in_use:
                msg += f"⚠️ {t('version_is_used_by_other_profiles')}\n"
        
        msg += "\n"
        
        # Determine what can be deleted
        can_delete_version = version_installed and not version_in_use
        
        if has_custom_dir and can_delete_version:
            msg += f"{t('yes')} — {t('delete_profile_and_game_version')}\n"
            msg += f"{t('no')} — {t('delete_profile_only')}\n"
            msg += f"{t('cancel')} — {t('do_not_delete')}"
            result = messagebox.askyesnocancel(t("delete_profile_title"), msg, parent=self)
            delete_all = result
        elif has_custom_dir:
            msg += f"{t('yes')} — {t('delete_profile_and_folder')}\n"
            msg += f"{t('no')} — {t('delete_profile_only')}\n"
            msg += f"{t('cancel')} — {t('do_not_delete')}"
            result = messagebox.askyesnocancel(t("delete_profile_title"), msg, parent=self)
            delete_all = result
        elif can_delete_version:
            msg += f"{t('yes')} — {t('delete_profile_and_game_version')}\n"
            msg += f"{t('no')} — {t('delete_profile_only')}\n"
            msg += f"{t('cancel')} — {t('do_not_delete')}"
            result = messagebox.askyesnocancel(t("delete_profile_title"), msg, parent=self)
            delete_all = result
        else:
            if not messagebox.askyesno(t("delete_profile_title"), msg + f"{t('delete')}", parent=self):
                return
            delete_all = False
            result = False
        
        if result is None:  # Cancel
            return
        
        # Delete game folder if requested
        if delete_all and profile.game_directory:
            game_dir = Path(profile.game_directory)
            if game_dir.exists():
                try:
                    shutil.rmtree(game_dir)
                    logger.info(f"Deleted game directory: {game_dir}")
                    self._update_status(f"{t('folder')} {game_dir} {t('deleted')}")
                except Exception as e:
                    logger.error(f"Failed to delete game directory: {e}")
                    messagebox.showerror(t("error"), f"{t('failed_to_delete_folder')}: {e}", parent=self)
        
        # Delete version if requested and not in use
        if delete_all and can_delete_version:
            try:
                self.launcher.delete_version(version_id)
                logger.info(f"Deleted version: {version_id}")
                self._update_status(f"Версия {version_id} удалена")
            except Exception as e:
                logger.error(f"Failed to delete version: {e}")
                messagebox.showerror(t("error"), f"{t('failed_to_delete_version')}: {e}", parent=self)
        
        # Delete the profile
        self.profile_manager.delete_profile(profile_id)
        self._update_status(f"{t('profile')} '{profile.name}' {t('deleted')}")
        
        # Clear selection if deleted profile was selected
        if self.selected_version == f"profile:{profile_id}":
            self.selected_version = None
            self.config["last_version"] = ""
            self.config.save()
        
        self._load_versions()
    
    def _delete_version(self, version_id: str):
        """Delete an installed version."""
        from tkinter import messagebox
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Удаление версии",
            f"Вы уверены, что хотите удалить версию {version_id}?\n\nЭто действие нельзя отменить.",
            icon="warning",
            parent=self
        )
        
        if not result:
            return
        
        self._update_status(f"Удаление версии {version_id}...")
        
        def delete():
            success = self.launcher.delete_version(version_id)
            
            def on_complete():
                if success:
                    self._update_status(f"✓ Версия {version_id} удалена")
                    # Reload versions list
                    self._load_versions()
                else:
                    self._update_status(f"Ошибка удаления версии {version_id}")
            
            self.after(0, on_complete)
        
        thread = threading.Thread(target=delete, daemon=True)
        thread.start()
    
    def _play(self):
        """Install (if needed) and launch the game."""
        if not self.selected_version or self.is_downloading:
            return
        
        # Check if this is a profile
        if self.selected_version.startswith("profile:"):
            profile_id = self.selected_version.replace("profile:", "")
            profile = self.profile_manager.get_profile(profile_id)
            if profile:
                self._play_profile(profile)
            return
        
        version_id = self.selected_version
        card = self.version_cards.get(version_id)
        
        if not card:
            return
        
        if not card.version.installed:
            # Need to install first
            self._install_version(version_id)
        else:
            # Launch directly
            self._launch_game(version_id)
    
    def _play_profile(self, profile: Profile):
        """Install (if needed) and launch a profile."""
        version_to_launch = profile.version_id
        
        # Check if installed using direct method
        is_installed = self.launcher.is_version_installed(version_to_launch)
        
        if not is_installed:
            # Need to install base MC version first, then loader
            self._install_profile(profile)
        else:
            # Launch directly with custom game directory if set
            self._launch_game(version_to_launch, profile.game_directory)
            self.profile_manager.mark_played(profile.id)
    
    def _install_profile(self, profile: Profile):
        """Install a profile (MC version + loader)."""
        self.is_downloading = True
        self.play_button.configure(state="disabled", text=f"⏳  {t('installing')}...")
        self.progress_frame.pack(fill="x", pady=(0, 15))
        self.progress_bar.set(0)
        
        def install():
            try:
                # First install base MC version
                self._update_status(f"{t('installing')} {profile.minecraft_version}...")
                success = self.launcher.install_version(profile.minecraft_version)
                
                if not success:
                    raise RuntimeError("Failed to install MC")
                
                # Then install loader if needed
                if profile.loader_type and profile.loader_version:
                    self._update_status(f"{t('installing')} {profile.loader_type}...")
                    
                    if profile.loader_type == "fabric":
                        self.mod_manager.install_fabric(
                            profile.minecraft_version,
                            profile.loader_version
                        )
                    elif profile.loader_type == "forge":
                        self.mod_manager.install_forge(
                            profile.minecraft_version,
                            profile.loader_version
                        )
                    elif profile.loader_type == "neoforge":
                        self.mod_manager.install_neoforge(
                            profile.minecraft_version,
                            profile.loader_version
                        )
                    elif profile.loader_type == "quilt":
                        self.mod_manager.install_quilt(
                            profile.minecraft_version,
                            profile.loader_version
                        )
                
                def on_complete():
                    self.is_downloading = False
                    self.progress_frame.pack_forget()
                    self.play_button.configure(text=f"▶  {t('play')}", state="normal")
                    self._update_status(f"✅ {t('profile')} '{profile.name}' {t('installed')}!")
                    self._load_versions()
                    
                    # Ask to launch
                    from tkinter import messagebox
                    if messagebox.askyesno(f"{t('ready')}", f"{t('profile')} '{profile.name}' {t('ready')}! {t('launch_game')}?", parent=self):
                        self._launch_game(profile.version_id)
                        self.profile_manager.mark_played(profile.id)
                
                self.after(0, on_complete)
                
            except Exception as e:
                error_msg = str(e)
                def on_error():
                    self.is_downloading = False
                    self.progress_frame.pack_forget()
                    self.play_button.configure(state="normal", text=f"📥  {t('install')}")
                    self._update_status(f"❌ {t('error')}: {error_msg}")
                
                self.after(0, on_error)
        
        import threading
        threading.Thread(target=install, daemon=True).start()
    
    def _install_version(self, version_id: str):
        """Install a version."""
        self.is_downloading = True
        self.play_button.configure(state="disabled", text=f"⏳  {t('installing')}...")
        self.progress_frame.pack(fill="x", pady=(0, 15))
        self.progress_bar.set(0)
        
        def install():
            try:
                success = self.launcher.install_version(version_id)
                
                def on_complete():
                    self.is_downloading = False
                    self.progress_frame.pack_forget()
                    
                    if success:
                        # Update card
                        if version_id in self.version_cards:
                            self.version_cards[version_id].version.installed = True
                        
                        # Refresh display
                        self._select_version(version_id)
                        self._update_status(f"✓ {t('version')} {version_id} {t('installed')}!")
                        
                        # Auto-launch
                        self._launch_game(version_id)
                    else:
                        self.play_button.configure(state="normal", text=f"📥  {t('install')}")
                
                self.after(0, on_complete)
                
            except Exception:
                import traceback
                error_msg = traceback.format_exc()
                self.after(0, lambda m=error_msg: self._handle_install_error(m))
        
        thread = threading.Thread(target=install, daemon=True)
        thread.start()
    
    def _launch_game(self, version_id: str, custom_game_dir: Optional[str] = None):
        """Launch the game."""
        self.play_button.configure(state="disabled", text=f"🚀  {t('launching')}...")
        
        # Create console window if enabled
        show_console = self.config.get("show_game_console", False)
        console_window = None
        if show_console:
            console_window = GameConsole(self, self.theme, version_id)
        
        def launch():
            try:
                java_path = self.config["java_path"] or None
                
                # Get auth data from active account
                auth_data = self.auth.get_minecraft_auth_data()
                username = auth_data["username"]
                uuid = auth_data["uuid"]
                access_token = auth_data["token"]
                
                account = self.auth.get_active_account()
                account_type = account.type if account else "offline"
                logger.info(f"Launching as {username} ({account_type})")
                
                # Use Ely.by only for Ely.by accounts
                use_elyby = account_type == "elyby"
                
                # Use custom game directory if provided
                game_dir = Path(custom_game_dir) if custom_game_dir else self.config.get_minecraft_dir()
                
                # Create directory if it doesn't exist
                if not game_dir.exists():
                    game_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created game directory: {game_dir}")
                
                process = self.launcher.launch_game(
                    version_id=version_id,
                    username=username,
                    java_path=java_path,
                    ram_min=self.config["ram_min"],
                    ram_max=self.config["ram_max"],
                    game_directory=game_dir,
                    use_elyby=use_elyby,
                    uuid=uuid,
                    access_token=access_token
                )
                
                def on_launched():
                    self._update_status(f"✓ Minecraft {version_id} {t('status_game_running')}!")
                    self.play_button.configure(state="normal", text=f"▶  {t('play')}")
                    
                    # Attach console to process
                    if console_window:
                        console_window.set_process(process)
                    
                    if self.config["close_on_launch"] and not show_console:
                        self.after(1000, self.destroy)
                
                self.after(0, on_launched)
                
            except Exception:
                import traceback
                error_msg = traceback.format_exc()
                self.after(0, lambda m=error_msg: self._handle_launch_error(m))
        
        thread = threading.Thread(target=launch, daemon=True)
        thread.start()
    
    def _handle_install_error(self, error_msg: str):
        """Handle installation error on main thread."""
        logger.error(f"Installation error:\n{error_msg}")
        self.is_downloading = False
        self.progress_frame.pack_forget()
        self.play_button.configure(state="normal", text=f"📥  {t('install')}")
        # Get just the last line of the error for display
        short_error = error_msg.strip().split('\n')[-1] if error_msg else t("unknown_error")
        self._update_status(f"Ошибка: {short_error}")
    
    def _handle_launch_error(self, error_msg: str):
        """Handle launch error on main thread."""
        logger.error(f"Launch error:\n{error_msg}")
        self.play_button.configure(state="normal", text=f"▶  {t('play')}")
        # Get just the last line of the error for display
        short_error = error_msg.strip().split('\n')[-1] if error_msg else t("unknown_error")
        self._update_status(f"Ошибка запуска: {short_error}")
    
    def _update_status(self, message: str):
        """Update status label."""
        self.status_label.configure(text=message)
    
    def _update_progress(self, progress):
        """Update progress bar."""
        self.progress_bar.set(progress.percentage / 100)
        self._update_status(f"{progress.status} ({progress.percentage:.0f}%)")
    
    def _open_create_profile(self):
        """Open create profile window."""
        CreateProfileWindow(
            self,
            self.mod_manager,
            self.launcher,
            self.profile_manager,
            self.theme,
            self._on_profile_created
        )
    
    def _on_profile_created(self, name: str, minecraft_version: str, loader_type: Optional[str], loader_version: Optional[str], game_directory: Optional[str] = None):
        """Called when a profile is created (installation already done in CreateProfileWindow)."""
        profile = self.profile_manager.create_profile(
            name=name,
            minecraft_version=minecraft_version,
            loader_type=loader_type,
            loader_version=loader_version,
            game_directory=game_directory
        )
        
        self._update_status(f"✨ {t('profile')} '{profile.name}' {t('ready')}!")
        
        # Reload versions to show the profile
        self._load_versions()
    
    def _install_profile_loader(self, profile: Profile):
        """Install mod loader for a profile."""
        self._update_status(f"⏳ {t('installing')} {profile.loader_type} {t('for_profile')} '{profile.name}'...")
        
        def install():
            try:
                result = None
                if profile.loader_type == "fabric":
                    result = self.mod_manager.install_fabric(
                        profile.minecraft_version,
                        profile.loader_version
                    )
                elif profile.loader_type == "forge":
                    result = self.mod_manager.install_forge(
                        profile.minecraft_version,
                        profile.loader_version
                    )
                elif profile.loader_type == "neoforge":
                    result = self.mod_manager.install_neoforge(
                        profile.minecraft_version,
                        profile.loader_version
                    )
                elif profile.loader_type == "quilt":
                    result = self.mod_manager.install_quilt(
                        profile.minecraft_version,
                        profile.loader_version
                    )
                
                def on_complete():
                    if result:
                        self._update_status(f"✅ {t('profile')} '{profile.name}' {t('ready')}!")
                    else:
                        self._update_status(f"⚠ {t('profile')} '{profile.name}' {t('created')} {t('but')} {t('loader')} {t('not')} {t('installed')}")
                    self._load_versions()
                
                self.after(0, on_complete)
                
            except Exception as e:
                self.after(0, lambda: self._update_status(f"❌ {t('error_installing')}: {e}"))
                self.after(0, self._load_versions)
        
        import threading
        threading.Thread(target=install, daemon=True).start()
    
    def _open_mods(self):
        """Open mods management window."""
        ModsWindow(
            self,
            self.mod_manager,
            self.launcher,
            self.theme,
            self.selected_version or ""
        )
    
    def _open_settings(self):
        """Open settings window."""
        SettingsWindow(self, self.config, self.theme, self._on_settings_saved)
    
    def _on_settings_saved(self):
        """Called when settings are saved."""
        # Reload versions list if snapshot/old settings changed
        # Check if theme changed
        new_theme = get_theme(self.config["theme"])
        if new_theme != self.theme:
            self.theme = new_theme
            # Would need to recreate UI for full theme change
            self._update_status(f"{t('restart_launcher')} {t('to_apply_theme')}")
        
        # Reload versions if filter changed
        self._load_versions()

