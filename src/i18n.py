"""
Internationalization (i18n) module for CraftLauncher
Supports multiple languages with JSON translation files
"""

import json
from pathlib import Path
from typing import Optional

from .logger import logger


# Available languages
LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "uk": "Українська",
}

# Default language
DEFAULT_LANGUAGE = "ru"


class I18n:
    """Internationalization manager."""
    
    def __init__(self, lang: str = DEFAULT_LANGUAGE):
        self.translations_dir = Path(__file__).parent / "translations"
        self.translations_dir.mkdir(parents=True, exist_ok=True)
        self.current_lang = lang
        self.translations: dict = {}
        self.fallback_translations: dict = {}
        
        # Load translations
        self._load_translations(lang)
        
        # Load fallback (default language) if different
        if lang != DEFAULT_LANGUAGE:
            self._load_fallback()
    
    def _load_translations(self, lang: str) -> bool:
        """Load translations for specified language."""
        lang_file = self.translations_dir / f"{lang}.json"
        
        if not lang_file.exists():
            logger.warning(f"Translation file not found: {lang_file}")
            # Try to create default translations
            if lang == DEFAULT_LANGUAGE:
                self._create_default_translations()
                return self._load_translations(lang)
            return False
        
        try:
            self.translations = json.loads(lang_file.read_text(encoding="utf-8"))
            logger.info(f"Loaded translations for '{lang}' ({len(self.translations)} keys)")
            return True
        except Exception as e:
            logger.error(f"Failed to load translations: {e}")
            return False
    
    def _load_fallback(self):
        """Load fallback translations."""
        lang_file = self.translations_dir / f"{DEFAULT_LANGUAGE}.json"
        if lang_file.exists():
            try:
                self.fallback_translations = json.loads(lang_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to load fallback translations: {e}")
    
    def _create_default_translations(self):
        """Create default Russian translations file."""
        translations = {
            # Main window
            "app_title": "CraftLauncher",
            "loading": "Загрузка...",
            "play": "ИГРАТЬ",
            "install": "УСТАНОВИТЬ",
            "installing": "Установка...",
            "launching": "Запуск...",
            
            # Sidebar
            "my_profiles": "Мои профили",
            "available_versions": "Доступные версии",
            "installed": "Установлена",
            "release": "Релиз",
            "snapshot": "Снапшот",
            "old_beta": "Бета",
            "old_alpha": "Альфа",
            
            # Buttons
            "settings": "Настройки",
            "create_profile": "Создать профиль",
            "add_account": "Добавить аккаунт",
            "logout": "Выйти",
            "save": "Сохранить",
            "cancel": "Отмена",
            "delete": "Удалить",
            "refresh": "Обновить",
            "browse": "Обзор",
            "open_folder": "Открыть папку",
            
            # Settings window
            "settings_title": "Настройки",
            "game_settings": "Настройки игры",
            "ram_min": "Минимум RAM (ГБ)",
            "ram_max": "Максимум RAM (ГБ)",
            "java_path": "Путь к Java",
            "java_auto": "Автоматически",
            "game_directory": "Папка игры",
            "extra_jvm_args": "Дополнительные JVM аргументы",
            "close_on_launch": "Закрывать лаунчер при запуске",
            "show_snapshots": "Показывать снапшоты",
            "show_old_versions": "Показывать старые версии",
            "debug_console": "Debug консоль игры",
            "interface": "Интерфейс",
            "theme": "Тема",
            "language": "Язык",
            
            # Create profile window
            "create_profile_title": "Создать профиль",
            "profile_name": "Название профиля",
            "profile_name_placeholder": "Мой профиль",
            "minecraft_version": "Версия Minecraft",
            "mod_loader": "Загрузчик модов",
            "mod_loader_version": "Версия загрузчика",
            "optifine_version": "Версия OptiFine",
            "game_folder": "Папка игры (авто или своя)",
            "game_folder_auto": "Авто: .minecraft/profiles/{имя}",
            "vanilla": "Без модов (Vanilla)",
            "creating_profile": "Создание...",
            "profile_created": "Профиль создан!",
            
            # Account window
            "account_title": "Добавить аккаунт",
            "local_profile": "Локальный профиль",
            "microsoft_account": "Microsoft аккаунт",
            "elyby_account": "Ely.by аккаунт",
            "username": "Имя игрока",
            "username_placeholder": "Steve",
            "email": "Email",
            "password": "Пароль",
            "login": "Войти",
            "logging_in": "Вход...",
            "login_success": "Успешный вход!",
            "login_error": "Ошибка входа",
            
            # Delete dialogs
            "delete_profile_title": "Удаление профиля",
            "delete_profile_confirm": "Удалить профиль '{name}'?",
            "delete_version_title": "Удаление версии",
            "delete_version_confirm": "Удалить версию {version}?",
            "delete_all": "Да — удалить всё",
            "delete_profile_only": "Нет — только профиль",
            "version_used_by_others": "Версия используется другими профилями!",
            "profile_folder": "Папка профиля",
            "game_version": "Версия",
            
            # Status messages
            "status_loading_versions": "Загрузка списка версий...",
            "status_installing": "Установка {version}...",
            "status_installed": "Версия {version} установлена",
            "status_launching": "Запуск игры...",
            "status_game_running": "Игра запущена",
            "status_game_closed": "Игра закрыта (код: {code})",
            "status_error": "Ошибка: {error}",
            "status_deleted": "Удалено: {name}",
            
            # Errors
            "error": "Ошибка",
            "error_install": "Ошибка установки",
            "error_launch": "Ошибка запуска",
            "error_no_java": "Java не найдена",
            "error_no_account": "Выберите аккаунт",
            "error_invalid_name": "Недопустимое имя",
            "error_name_too_long": "Имя слишком длинное (макс. {max})",
            "error_name_special_chars": "Имя содержит недопустимые символы",
            
            # Mod loaders
            "loader_fabric": "Fabric",
            "loader_forge": "Forge",
            "loader_forge_optifine": "Forge + OptiFine",
            "loader_neoforge": "NeoForge",
            "loader_quilt": "Quilt",
            "loader_optifine": "OptiFine",
            
            # Misc
            "yes": "Да",
            "no": "Нет",
            "ok": "ОК",
            "warning": "Предупреждение",
            "info": "Информация",
            "not_found": "Не найдено",
            "not_supported": "Не поддерживается",
            "found_versions": "Найдено {count} версий",
            "skin_default": "Скин по умолчанию",
            "skin_not_found": "Скин не найден",
            "offline_mode": "Оффлайн режим",
        }
        
        lang_file = self.translations_dir / f"{DEFAULT_LANGUAGE}.json"
        lang_file.write_text(json.dumps(translations, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Created default translations file: {lang_file}")
    
    def set_language(self, lang: str) -> bool:
        """Change current language."""
        if lang not in LANGUAGES:
            logger.warning(f"Unknown language: {lang}")
            return False
        
        if self._load_translations(lang):
            self.current_lang = lang
            if lang != DEFAULT_LANGUAGE:
                self._load_fallback()
            return True
        return False
    
    def get(self, key: str, **kwargs) -> str:
        """
        Get translated string by key.
        
        Args:
            key: Translation key
            **kwargs: Format arguments for the string
            
        Returns:
            Translated string or key if not found
        """
        # Try current language
        text = self.translations.get(key)
        
        # Fallback to default language
        if text is None:
            text = self.fallback_translations.get(key)
        
        # Return key if not found
        if text is None:
            logger.debug(f"Translation not found: {key}")
            return key
        
        # Format with arguments
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format key in translation '{key}': {e}")
                return text
        
        return text
    
    def __call__(self, key: str, **kwargs) -> str:
        """Shortcut for get()."""
        return self.get(key, **kwargs)


# Global instance
_i18n: Optional[I18n] = None


def get_i18n() -> I18n:
    """Get global i18n instance."""
    global _i18n
    if _i18n is None:
        _i18n = I18n()
    return _i18n


def set_language(lang: str) -> bool:
    """Set language for global i18n instance."""
    return get_i18n().set_language(lang)


def t(key: str, **kwargs) -> str:
    """Translate key using global i18n instance."""
    return get_i18n().get(key, **kwargs)

