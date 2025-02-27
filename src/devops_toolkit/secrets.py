"""
DevOps Toolkit - Secrets Management Module

This module provides functionality for securely storing and retrieving
sensitive information like API keys, passwords, and tokens.
"""
import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

# For encryption/decryption
import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Local imports
from devops_toolkit.config import get_config
from devops_toolkit.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class SecretsError(Exception):
    """Raised when secrets operations encounter an error."""
    pass


class SecretsManager:
    """
    Manager for handling secrets securely.
    """

    def __init__(self, secrets_dir: Optional[str] = None, auto_unlock: bool = False):
        """
        Initialize secrets manager.

        Args:
            secrets_dir: Directory to store secrets (optional)
                Defaults to config value or ~/.devops-toolkit/secrets
            auto_unlock: Whether to automatically prompt for password to unlock secrets
        """
        # Get secrets directory from config if not provided
        if secrets_dir is None:
            config = get_config()
            secrets_dir = config.get_global().secrets_dir
        
        self.secrets_dir = os.path.expanduser(secrets_dir)
        self.key_file = os.path.join(self.secrets_dir, ".keyinfo")
        self.secrets_file = os.path.join(self.secrets_dir, "secrets.enc")
        
        # Ensure secrets directory exists with secure permissions
        os.makedirs(self.secrets_dir, exist_ok=True)
        try:
            os.chmod(self.secrets_dir, 0o700)  # Only owner can access
        except Exception as e:
            logger.warning(f"Could not set permissions on secrets directory: {str(e)}")
        
        # Encryption key
        self._encryption_key = None
        self._salt = None
        self._secrets_data: Dict[str, Dict[str, Any]] = {}
        self._unlocked = False
        
        # Initialize or load key information
        self._init_key_info()
        
        # Auto-unlock if requested
        if auto_unlock:
            self.unlock()

    def _init_key_info(self) -> None:
        """
        Initialize or load key information.
        """
        if not os.path.exists(self.key_file):
            # Generate new salt
            self._salt = os.urandom(16)
            
            # Save salt to key file
            with open(self.key_file, 'wb') as f:
                f.write(self._salt)
        else:
            # Load existing salt
            with open(self.key_file, 'rb') as f:
                self._salt = f.read(16)

    def _derive_key(self, password: str) -> bytes:
        """
        Derive encryption key from password.

        Args:
            password: User password

        Returns:
            Derived encryption key
        """
        if not self._salt:
            raise SecretsError("Salt not initialized")
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def unlock(self, password: Optional[str] = None) -> bool:
        """
        Unlock secrets with password.

        Args:
            password: Password to unlock secrets (optional)
                If not provided, will prompt for password

        Returns:
            True if unlock successful, False otherwise
        """
        if self._unlocked:
            return True
        
        # Prompt for password if not provided
        if password is None:
            password = getpass.getpass("Enter password to unlock secrets: ")
        
        try:
            # Derive key from password
            self._encryption_key = self._derive_key(password)
            
            # Try to decrypt secrets file
            if os.path.exists(self.secrets_file):
                self._load_secrets()
            else:
                # Initialize empty secrets data
                self._secrets_data = {}
                self._save_secrets()
            
            self._unlocked = True
            return True
        except Exception as e:
            logger.error(f"Failed to unlock secrets: {str(e)}")
            self._encryption_key = None
            return False

    def _load_secrets(self) -> None:
        """
        Load secrets from file.

        Raises:
            SecretsError: If secrets file cannot be loaded
        """
        if not self._encryption_key:
            raise SecretsError("Secrets not unlocked")
        
        try:
            # Read encrypted data
            with open(self.secrets_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt data
            fernet = Fernet(self._encryption_key)
            decrypted_data = fernet.decrypt(encrypted_data)
            
            # Parse JSON
            self._secrets_data = json.loads(decrypted_data.decode())
        except FileNotFoundError:
            # Initialize empty secrets if file doesn't exist
            self._secrets_data = {}
        except Exception as e:
            raise SecretsError(f"Failed to load secrets: {str(e)}")

    def _save_secrets(self) -> None:
        """
        Save secrets to file.

        Raises:
            SecretsError: If secrets file cannot be saved
        """
        if not self._encryption_key:
            raise SecretsError("Secrets not unlocked")
        
        try:
            # Convert to JSON
            data_json = json.dumps(self._secrets_data).encode()
            
            # Encrypt data
            fernet = Fernet(self._encryption_key)
            encrypted_data = fernet.encrypt(data_json)
            
            # Write to file
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set secure permissions
            os.chmod(self.secrets_file, 0o600)  # Only owner can read/write
        except Exception as e:
            raise SecretsError(f"Failed to save secrets: {str(e)}")

    def is_initialized(self) -> bool:
        """
        Check if secrets storage is initialized.

        Returns:
            True if initialized, False otherwise
        """
        return os.path.exists(self.secrets_file)

    def is_unlocked(self) -> bool:
        """
        Check if secrets are unlocked.

        Returns:
            True if unlocked, False otherwise
        """
        return self._unlocked

    def change_password(self, old_password: str, new_password: str) -> bool:
        """
        Change the encryption password.

        Args:
            old_password: Current password
            new_password: New password

        Returns:
            True if password change successful, False otherwise

        Raises:
            SecretsError: If password change fails
        """
        # Verify old password
        old_key = self._derive_key(old_password)
        
        try:
            # Read encrypted data
            with open(self.secrets_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Try to decrypt with old key
            fernet = Fernet(old_key)
            decrypted_data = fernet.decrypt(encrypted_data)
            
            # Set new key
            new_key = self._derive_key(new_password)
            self._encryption_key = new_key
            
            # Re-encrypt with new key
            fernet = Fernet(new_key)
            encrypted_data = fernet.encrypt(decrypted_data)
            
            # Write to file
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted_data)
            
            return True
        except Exception as e:
            raise SecretsError(f"Failed to change password: {str(e)}")

    def set_secret(self, namespace: str, key: str, value: Any) -> None:
        """
        Set a secret value.

        Args:
            namespace: Namespace for the secret
            key: Secret key
            value: Secret value

        Raises:
            SecretsError: If setting secret fails
        """
        if not self._unlocked:
            raise SecretsError("Secrets not unlocked")
        
        # Initialize namespace if it doesn't exist
        if namespace not in self._secrets_data:
            self._secrets_data[namespace] = {}
        
        # Set value
        self._secrets_data[namespace][key] = value
        
        # Save secrets
        self._save_secrets()
        logger.debug(f"Set secret: {namespace}/{key}")

    def get_secret(self, namespace: str, key: str, default: Any = None) -> Any:
        """
        Get a secret value.

        Args:
            namespace: Namespace for the secret
            key: Secret key
            default: Default value if secret not found

        Returns:
            Secret value or default if not found

        Raises:
            SecretsError: If getting secret fails
        """
        if not self._unlocked:
            raise SecretsError("Secrets not unlocked")
        
        # Get value from namespace
        if namespace in self._secrets_data and key in self._secrets_data[namespace]:
            return self._secrets_data[namespace][key]
        
        return default

    def list_secrets(self, namespace: Optional[str] = None) -> Union[List[str], Dict[str, List[str]]]:
        """
        List available secrets.

        Args:
            namespace: Namespace to list secrets for (optional)
                If not provided, will list all namespaces

        Returns:
            List of secret keys if namespace provided, otherwise dict of namespaces to lists of keys

        Raises:
            SecretsError: If listing secrets fails
        """
        if not self._unlocked:
            raise SecretsError("Secrets not unlocked")
        
        if namespace:
            # Return keys for specific namespace
            if namespace in self._secrets_data:
                return list(self._secrets_data[namespace].keys())
            return []
        
        # Return all namespaces and keys
        return {ns: list(secrets.keys()) for ns, secrets in self._secrets_data.items()}

    def delete_secret(self, namespace: str, key: str) -> bool:
        """
        Delete a secret.

        Args:
            namespace: Namespace for the secret
            key: Secret key

        Returns:
            True if secret was deleted, False if not found

        Raises:
            SecretsError: If deleting secret fails
        """
        if not self._unlocked:
            raise SecretsError("Secrets not unlocked")
        
        # Check if secret exists
        if namespace in self._secrets_data and key in self._secrets_data[namespace]:
            # Delete secret
            del self._secrets_data[namespace][key]
            
            # Delete namespace if empty
            if not self._secrets_data[namespace]:
                del self._secrets_data[namespace]
            
            # Save secrets
            self._save_secrets()
            logger.debug(f"Deleted secret: {namespace}/{key}")
            return True
        
        return False

    def delete_namespace(self, namespace: str) -> bool:
        """
        Delete all secrets in a namespace.

        Args:
            namespace: Namespace to delete

        Returns:
            True if namespace was deleted, False if not found

        Raises:
            SecretsError: If deleting namespace fails
        """
        if not self._unlocked:
            raise SecretsError("Secrets not unlocked")
        
        # Check if namespace exists
        if namespace in self._secrets_data:
            # Delete namespace
            del self._secrets_data[namespace]
            
            # Save secrets
            self._save_secrets()
            logger.debug(f"Deleted namespace: {namespace}")
            return True
        
        return False

    def generate_password(self, length: int = 16, 
                         use_uppercase: bool = True, 
                         use_lowercase: bool = True,
                         use_digits: bool = True, 
                         use_special: bool = True) -> str:
        """
        Generate a strong random password.

        Args:
            length: Length of password
            use_uppercase: Include uppercase letters
            use_lowercase: Include lowercase letters
            use_digits: Include digits
            use_special: Include special characters

        Returns:
            Generated password
        """
        chars = ""
        if use_uppercase:
            chars += "ABCDEFGHJKLMNPQRSTUVWXYZ"  # Removed confusable characters I, O
        if use_lowercase:
            chars += "abcdefghijkmnopqrstuvwxyz"  # Removed confusable characters l
        if use_digits:
            chars += "23456789"  # Removed confusable characters 0, 1
        if use_special:
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        if not chars:
            raise ValueError("Must include at least one character type")
        
        # Generate password
        password = "".join(secrets.choice(chars) for _ in range(length))
        return password


# Global secrets manager instance
_secrets_manager_instance = None


def get_secrets_manager() -> SecretsManager:
    """
    Get the global secrets manager instance.

    Returns:
        SecretsManager object
    """
    global _secrets_manager_instance
    if _secrets_manager_instance is None:
        _secrets_manager_instance = SecretsManager()
    return _secrets_manager_instance
