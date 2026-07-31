"""
Token encryption/decryption service
"""

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TokenEncryption:
    """
    Encrypt/decrypt OAuth tokens for storage
    Uses Fernet symmetric encryption (AES-128-CBC)
    """
    
    def __init__(self, key: str):
        """
        Initialize encryption service
        
        Args:
            key: Base64-encoded encryption key (32 bytes)
        """
        try:
            # If key is provided as string, encode it
            if isinstance(key, str):
                # Derive a proper key using PBKDF2
                kdf = PBKDF2(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'optix_token_salt',  # In production, use unique salt
                    iterations=100000,
                    backend=default_backend()
                )
                derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
                self.cipher = Fernet(derived_key)
            else:
                self.cipher = Fernet(key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise ValueError("Invalid encryption key provided")
    
    def encrypt(self, token: str) -> str:
        """
        Encrypt token for storage
        
        Args:
            token: Plain text token
            
        Returns:
            Encrypted token as string
        """
        try:
            if not token:
                return ""
            encrypted = self.cipher.encrypt(token.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Token encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_token: str) -> str:
        """
        Decrypt token for use
        
        Args:
            encrypted_token: Encrypted token string
            
        Returns:
            Decrypted plain text token
        """
        try:
            if not encrypted_token:
                return ""
            decrypted = self.cipher.decrypt(encrypted_token.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            raise
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key
        
        Returns:
            Base64-encoded encryption key
        """
        return Fernet.generate_key().decode()


# Global encryption instance (initialized from settings)
_encryption_instance: Optional[TokenEncryption] = None


def get_token_encryption(key: Optional[str] = None) -> TokenEncryption:
    """
    Get or create token encryption instance
    
    Args:
        key: Optional encryption key (uses settings if not provided)
        
    Returns:
        TokenEncryption instance
    """
    global _encryption_instance
    
    if _encryption_instance is None:
        if key is None:
            from .settings import settings
            key = settings.token_encryption_key
        
        if not key:
            raise ValueError("Encryption key must be provided")
        
        _encryption_instance = TokenEncryption(key)
    
    return _encryption_instance
