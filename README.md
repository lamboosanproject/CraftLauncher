# ⛏️ CraftLauncher

A modern cross-platform Minecraft launcher built with Python.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey)

## ✨ Features

### 🎮 Version Management
- Download and launch **any Minecraft version** (releases, snapshots, alpha/beta)
- Automatic library and asset installation
- Delete installed versions

### 📁 Profile System
- Create **custom profiles** with MC version and mod loader
- Supported loaders: **Fabric**, **Forge**, **NeoForge**, **Quilt**, **OptiFine**
- Combined **Forge + OptiFine** profiles
- Isolated folders per profile (mods, saves, resource packs)
- **Export/Import profiles** via Manifest-code — share modpacks instantly!

### 🧩 Mod Management
- Built-in **mod browser** with Modrinth & CurseForge search
- Automatic dependency installation
- Per-profile mod manager (enable/disable/delete)
- Async icon loading for mods

### 👤 Account System
- **Local Profile** — offline mode
- **Microsoft Account** — official authentication
- **Ely.by Account** — free in-game skins via authlib-injector

### 🎨 Interface
- Modern UI with **CustomTkinter**
- Themes: **Dark**, **Light**, **Midnight**
- Multi-language: 🇷🇺 Russian, 🇬🇧 English, 🇺🇦 Ukrainian
- Player skin display
- Debug console

## 📦 Installation

### For Users (Pre-built)

Download the executable for your platform from [Releases](../../releases).

| Platform | File |
|----------|------|
| 🪟 Windows | `CraftLauncher-Windows.exe` |
| 🐧 Linux | `CraftLauncher-Linux` |
| 🍎 macOS | `CraftLauncher-macOS` |

### For Developers

```bash
# Clone the repository
git clone https://github.com/your-username/CraftLauncher.git
cd CraftLauncher

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the launcher
python run.py
```

## 🔨 Building

### Linux / macOS

```bash
chmod +x build.sh
./build.sh
```

### Windows

```cmd
build.bat
```

### Via Python

```bash
python build.py
```

The executable will be created in the `dist/` folder.

## 📁 Project Structure

```
CraftLauncher/
├── src/
│   ├── main.py              # Entry point
│   ├── config.py            # Settings management
│   ├── launcher_core.py     # Launcher core
│   ├── profiles.py          # Profile management
│   ├── auth.py              # Authentication
│   ├── mods.py              # Mod loaders
│   ├── mod_sources.py       # Modrinth/CurseForge API
│   ├── elyby.py             # Ely.by integration
│   ├── i18n.py              # Internationalization
│   ├── translations/        # Language files
│   │   ├── en.json
│   │   ├── ru.json
│   │   └── uk.json
│   └── ui/
│       ├── main_window.py   # Main window
│       └── themes.py        # UI themes
├── requirements.txt
├── build.py
├── build.sh
├── build.bat
└── run.py
```

## ⚙️ Configuration

Settings are automatically saved to:

| Platform | Path |
|----------|------|
| Windows | `%APPDATA%\CraftLauncher\config.json` |
| Linux | `~/.config/CraftLauncher/config.json` |
| macOS | `~/Library/Application Support/CraftLauncher/config.json` |

### Parameters

- **ram_min/ram_max** — allocated RAM (in GB)
- **java_path** — path to Java (empty = auto-detect)
- **theme** — UI theme (dark, light, midnight)
- **language** — interface language (en, ru, uk)
- **show_snapshots** — show snapshot versions
- **show_old_versions** — show alpha/beta versions
- **close_on_launch** — close launcher when game starts
- **show_game_console** — show debug console

## 🎨 Themes

Three themes available:

- **Dark** — dark theme with green accent
- **Light** — light theme
- **Midnight** — night theme with purple accent

## 🔧 Requirements

- **Python 3.10+** (for development)
- **Java 8+** (for Minecraft)

## 📝 License

MIT License — use freely!

## 🤝 Contributing

Pull Requests are welcome! Before submitting:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🙏 Credits

- [minecraft-launcher-lib](https://github.com/JakobDev/minecraft-launcher-lib) — Minecraft library
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — Modern UI widgets
- [Ely.by](https://ely.by/) — Skin system
- [Modrinth](https://modrinth.com/) & [CurseForge](https://curseforge.com/) — Mod catalogs

---

Made with ❤️ and Python
