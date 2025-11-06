# app/security.py
from cryptography.fernet import Fernet
import os
import base64
from typing import Optional
import secrets

class SecurityManager:
    def __init__(self):
        # Get or generate encryption key
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)

    def _get_or_create_encryption_key(self) -> bytes:
        """Get encryption key from env or generate a new one"""
        env_key = os.getenv('ENCRYPTION_KEY')
        
        if env_key:
            try:
                # Validate the key
                Fernet(env_key.encode())
                return env_key.encode()
            except Exception as e:
                print(f"Warning: Invalid ENCRYPTION_KEY from environment: {e}")
                print("Generating a new encryption key...")
        
        # Generate a new key
        new_key = Fernet.generate_key()
        print(f"Generated new encryption key: {new_key.decode()}")
        print("Please set this as ENCRYPTION_KEY environment variable for production")
        return new_key

    def encrypt_secret(self, secret: str) -> str:
        """Encrypt OTP secrets before storing in database"""
        try:
            encrypted = self.fernet.encrypt(secret.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt OTP secrets from database"""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_secret.encode())
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)

# Global instance
security_manager = SecurityManager()