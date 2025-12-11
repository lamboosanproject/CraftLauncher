"""
Authentication system for CraftLauncher
Supports multiple account types:
- Offline (local profile)
- Microsoft (official)
- Ely.by (alternative)
"""

import json
import time
import uuid as uuid_lib
import webbrowser
import hashlib
from dataclasses import dataclass, asdict, field
from typing import Optional, Callable, Literal
from pathlib import Path
from enum import Enum
import requests
import threading

from .logger import logger

# Microsoft OAuth endpoints
MS_CLIENT_ID = "00000000402b5328"  # Minecraft client ID
MS_AUTH_URL = "https://login.live.com/oauth20_authorize.srf"
MS_TOKEN_URL = "https://login.live.com/oauth20_token.srf"
MS_XBL_URL = "https://user.auth.xboxlive.com/user/authenticate"
MS_XSTS_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
MS_MC_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
MS_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"
MS_REDIRECT_URI = "https://login.live.com/oauth20_desktop.srf"

# Ely.by Authserver endpoints
ELYBY_AUTHSERVER = "https://authserver.ely.by"


class AccountType(Enum):
    OFFLINE = "offline"
    MICROSOFT = "microsoft"
    ELYBY = "elyby"


@dataclass
class Account:
    """User account data."""
    type: str  # "offline", "microsoft", "elyby"
    username: str
    uuid: str = ""
    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0  # Unix timestamp
    extra_data: dict = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.type == "offline":
            return False
        return time.time() >= self.expires_at - 60  # 1 minute buffer
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        # Handle missing fields for backwards compatibility
        data.setdefault("extra_data", {})
        data.setdefault("refresh_token", "")
        data.setdefault("expires_at", 0)
        return cls(**data)
    
    def get_display_type(self) -> str:
        """Get human-readable account type."""
        return {
            "offline": "Локальный",
            "microsoft": "Microsoft",
            "elyby": "Ely.by"
        }.get(self.type, self.type)


class AuthManager:
    """Manages authentication for the launcher."""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.accounts_file = config_dir / "accounts.json"
        self.accounts: list[Account] = []
        self.active_account: Optional[Account] = None
        self._client_token = self._get_or_create_client_token()
        
        self._load_accounts()
    
    def _get_or_create_client_token(self) -> str:
        """Get existing client token or create new one."""
        token_file = self.config_dir / "client_token"
        if token_file.exists():
            return token_file.read_text().strip()
        else:
            token = str(uuid_lib.uuid4())
            token_file.write_text(token)
            return token
    
    def _load_accounts(self) -> None:
        """Load saved accounts from disk."""
        if self.accounts_file.exists():
            try:
                with open(self.accounts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.accounts = [Account.from_dict(acc) for acc in data.get("accounts", [])]
                    
                    # Load active account
                    active_uuid = data.get("active")
                    if active_uuid:
                        for acc in self.accounts:
                            if acc.uuid == active_uuid:
                                self.active_account = acc
                                break
                    
                    logger.info(f"Loaded {len(self.accounts)} accounts")
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Failed to load accounts: {e}")
    
    def _save_accounts(self) -> None:
        """Save accounts to disk."""
        try:
            data = {
                "accounts": [acc.to_dict() for acc in self.accounts],
                "active": self.active_account.uuid if self.active_account else None
            }
            with open(self.accounts_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Accounts saved")
        except IOError as e:
            logger.error(f"Failed to save accounts: {e}")
    
    def is_logged_in(self) -> bool:
        """Check if there's an active account."""
        return self.active_account is not None
    
    def get_active_account(self) -> Optional[Account]:
        """Get the active account."""
        return self.active_account
    
    def get_username(self) -> Optional[str]:
        """Get current username."""
        return self.active_account.username if self.active_account else None
    
    def get_uuid(self) -> Optional[str]:
        """Get current user UUID."""
        return self.active_account.uuid if self.active_account else None
    
    def get_accounts(self) -> list[Account]:
        """Get all accounts."""
        return self.accounts
    
    def set_active_account(self, account: Account) -> None:
        """Set the active account."""
        self.active_account = account
        self._save_accounts()
    
    # ==================== OFFLINE AUTH ====================
    
    def add_offline_account(self, username: str) -> Account:
        """Add an offline (local) account."""
        # Generate offline UUID
        uuid = self._generate_offline_uuid(username)
        
        # Check if account already exists
        for acc in self.accounts:
            if acc.type == "offline" and acc.username.lower() == username.lower():
                self.active_account = acc
                self._save_accounts()
                return acc
        
        account = Account(
            type="offline",
            username=username,
            uuid=uuid,
            access_token="",
        )
        
        self.accounts.append(account)
        self.active_account = account
        self._save_accounts()
        
        logger.info(f"Added offline account: {username}")
        return account
    
    @staticmethod
    def _generate_offline_uuid(username: str) -> str:
        """Generate offline UUID from username."""
        data = f"OfflinePlayer:{username}".encode("utf-8")
        md5 = hashlib.md5(data).hexdigest()
        return f"{md5[:8]}-{md5[8:12]}-3{md5[13:16]}-{md5[16:20]}-{md5[20:32]}"
    
    # ==================== ELY.BY AUTH ====================
    
    def login_elyby(
        self, 
        username: str, 
        password: str,
        on_complete: Optional[Callable[[bool, str], None]] = None
    ) -> bool:
        """Login with Ely.by account."""
        logger.info(f"Attempting Ely.by login for: {username}")
        
        try:
            response = requests.post(
                f"{ELYBY_AUTHSERVER}/auth/authenticate",
                json={
                    "username": username,
                    "password": password,
                    "clientToken": self._client_token,
                    "requestUser": True,
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                selected_profile = data.get("selectedProfile", {})
                
                account = Account(
                    type="elyby",
                    username=selected_profile.get("name", username),
                    uuid=selected_profile.get("id", ""),
                    access_token=data["accessToken"],
                    extra_data={"client_token": data.get("clientToken", self._client_token)}
                )
                
                # Remove existing Ely.by account with same UUID
                self.accounts = [a for a in self.accounts if not (a.type == "elyby" and a.uuid == account.uuid)]
                self.accounts.append(account)
                self.active_account = account
                self._save_accounts()
                
                logger.info(f"Ely.by login successful: {account.username}")
                if on_complete:
                    on_complete(True, f"Добро пожаловать, {account.username}!")
                return True
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("errorMessage", "Неизвестная ошибка")
                
                if "Invalid credentials" in error_msg:
                    error_msg = "Неверный логин или пароль"
                
                logger.warning(f"Ely.by login failed: {error_msg}")
                if on_complete:
                    on_complete(False, error_msg)
                return False
                
        except requests.RequestException as e:
            error_msg = f"Ошибка сети: {e}"
            logger.error(error_msg)
            if on_complete:
                on_complete(False, error_msg)
            return False
    
    def refresh_elyby(self, account: Account) -> bool:
        """Refresh Ely.by access token."""
        try:
            response = requests.post(
                f"{ELYBY_AUTHSERVER}/auth/refresh",
                json={
                    "accessToken": account.access_token,
                    "clientToken": account.extra_data.get("client_token", self._client_token),
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                account.access_token = data["accessToken"]
                self._save_accounts()
                logger.info("Ely.by token refreshed")
                return True
            return False
        except:
            return False
    
    # ==================== MICROSOFT AUTH ====================
    
    def login_microsoft(self, on_complete: Optional[Callable[[bool, str], None]] = None) -> None:
        """Start Microsoft OAuth login flow."""
        logger.info("Starting Microsoft login flow...")
        
        # Use minecraft-launcher-lib for Microsoft auth
        try:
            import minecraft_launcher_lib as mll
            
            # Get login URL
            login_url, state, code_verifier = mll.microsoft_account.get_secure_login_data(
                MS_CLIENT_ID,
                MS_REDIRECT_URI
            )
            
            def auth_thread():
                try:
                    # Open browser for login
                    logger.info("Opening browser for Microsoft login...")
                    webbrowser.open(login_url)
                    
                    if on_complete:
                        on_complete(False, "WAITING_FOR_CODE")
                        
                except Exception as e:
                    logger.error(f"Microsoft auth error: {e}")
                    if on_complete:
                        on_complete(False, f"Ошибка: {e}")
            
            # Store for later use
            self._ms_state = state
            self._ms_code_verifier = code_verifier
            
            thread = threading.Thread(target=auth_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start Microsoft auth: {e}")
            if on_complete:
                on_complete(False, f"Ошибка: {e}")
    
    def complete_microsoft_login(
        self, 
        auth_code: str,
        on_complete: Optional[Callable[[bool, str], None]] = None
    ) -> None:
        """Complete Microsoft login with authorization code."""
        
        def auth_thread():
            try:
                import minecraft_launcher_lib as mll
                
                logger.info("Exchanging Microsoft auth code...")
                
                # Get the full auth info
                login_data = mll.microsoft_account.complete_login(
                    MS_CLIENT_ID,
                    None,  # client_secret
                    MS_REDIRECT_URI,
                    auth_code,
                    getattr(self, '_ms_code_verifier', None)
                )
                
                account = Account(
                    type="microsoft",
                    username=login_data["name"],
                    uuid=login_data["id"],
                    access_token=login_data["access_token"],
                    refresh_token=login_data.get("refresh_token", ""),
                    expires_at=time.time() + 86400,  # 24 hours
                )
                
                # Remove existing Microsoft account with same UUID
                self.accounts = [a for a in self.accounts if not (a.type == "microsoft" and a.uuid == account.uuid)]
                self.accounts.append(account)
                self.active_account = account
                self._save_accounts()
                
                logger.info(f"Microsoft login successful: {account.username}")
                if on_complete:
                    on_complete(True, f"Добро пожаловать, {account.username}!")
                    
            except Exception as e:
                logger.error(f"Microsoft auth completion failed: {e}")
                if on_complete:
                    on_complete(False, f"Ошибка авторизации: {e}")
        
        thread = threading.Thread(target=auth_thread, daemon=True)
        thread.start()
    
    def refresh_microsoft(self, account: Account) -> bool:
        """Refresh Microsoft access token."""
        if not account.refresh_token:
            return False
        
        try:
            import minecraft_launcher_lib as mll
            
            login_data = mll.microsoft_account.complete_refresh(
                MS_CLIENT_ID,
                None,
                MS_REDIRECT_URI,
                account.refresh_token
            )
            
            account.access_token = login_data["access_token"]
            account.refresh_token = login_data.get("refresh_token", account.refresh_token)
            account.expires_at = time.time() + 86400
            self._save_accounts()
            
            logger.info("Microsoft token refreshed")
            return True
        except Exception as e:
            logger.error(f"Microsoft refresh failed: {e}")
            return False
    
    # ==================== COMMON ====================
    
    def remove_account(self, account: Account) -> None:
        """Remove an account."""
        self.accounts = [a for a in self.accounts if a.uuid != account.uuid]
        
        if self.active_account and self.active_account.uuid == account.uuid:
            self.active_account = self.accounts[0] if self.accounts else None
        
        self._save_accounts()
        logger.info(f"Removed account: {account.username}")
    
    def logout(self) -> None:
        """Clear active account (but keep in list)."""
        self.active_account = None
        self._save_accounts()
    
    def ensure_valid_token(self, account: Optional[Account] = None) -> bool:
        """Ensure account has valid token, refreshing if needed."""
        account = account or self.active_account
        if not account:
            return False
        
        if account.type == "offline":
            return True
        
        if not account.is_expired():
            return True
        
        # Try to refresh
        if account.type == "microsoft":
            return self.refresh_microsoft(account)
        elif account.type == "elyby":
            return self.refresh_elyby(account)
        
        return False
    
    def get_minecraft_auth_data(self) -> dict:
        """Get authentication data for Minecraft launch."""
        if not self.active_account:
            return {
                "username": "Player",
                "uuid": "",
                "token": "",
                "user_type": "legacy",
            }
        
        acc = self.active_account
        self.ensure_valid_token(acc)
        
        return {
            "username": acc.username,
            "uuid": acc.uuid.replace("-", ""),
            "token": acc.access_token,
            "user_type": "msa" if acc.type == "microsoft" else "mojang" if acc.type == "elyby" else "legacy",
        }
