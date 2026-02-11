"""
Cryptographic Utilities
Secure hashing, token generation, encryption
"""

import hashlib
import hmac
import secrets
import base64
from typing import Optional


class SecureHasher:
    """
    Secure hashing with timing attack protection using HMAC.
    """
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Hash a password with salt using PBKDF2.
        
        Args:
            password: Password to hash
            salt: Salt (auto-generated if not provided)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)
        
        # PBKDF2 with SHA256, 100000 iterations
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        
        return base64.b64encode(hashed).decode('utf-8'), salt
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Password to verify
            hashed_password: Previously hashed password
            salt: Salt used in original hash
            
        Returns:
            True if password matches
        """
        new_hash, _ = SecureHasher.hash_password(password, salt)
        return hmac.compare_digest(new_hash, hashed_password)
    
    @staticmethod
    def hmac_sign(message: str, key: str) -> str:
        """
        Sign a message with HMAC-SHA256.
        
        Args:
            message: Message to sign
            key: Secret key
            
        Returns:
            HMAC signature
        """
        signature = hmac.new(
            key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    def hmac_verify(message: str, signature: str, key: str) -> bool:
        """
        Verify HMAC signature.
        
        Args:
            message: Original message
            signature: Signature to verify
            key: Secret key
            
        Returns:
            True if signature valid
        """
        expected_signature = SecureHasher.hmac_sign(message, key)
        return hmac.compare_digest(signature, expected_signature)


class SecureTokenGenerator:
    """
    Generate cryptographically secure tokens.
    """
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate a secure random token.
        
        Args:
            length: Token length in bytes (default: 32)
            
        Returns:
            Hex-encoded token
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_url_safe_token(length: int = 32) -> str:
        """
        Generate a URL-safe secure random token.
        
        Args:
            length: Token length in bytes (default: 32)
            
        Returns:
            URL-safe base64-encoded token
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_api_key(prefix: str = "sk") -> str:
        """
        Generate an API key with prefix.
        
        Args:
            prefix: Key prefix (default: "sk")
            
        Returns:
            API key string
        """
        token = secrets.token_urlsafe(32)
        return f"{prefix}_{token}"


class SecureEncryption:
    """
    Symmetric encryption utilities using Fernet (AES-128-CBC).
    Note: For production, use AWS KMS or similar key management service.
    """
    
    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a Fernet encryption key.
        
        Returns:
            Encryption key bytes
        """
        try:
            from cryptography.fernet import Fernet
            return Fernet.generate_key()
        except ImportError:
            # Fallback: Generate random key
            return base64.urlsafe_b64encode(secrets.token_bytes(32))
    
    @staticmethod
    def encrypt(data: str, key: bytes) -> str:
        """
        Encrypt data with Fernet.
        
        Args:
            data: Data to encrypt
            key: Encryption key
            
        Returns:
            Encrypted data (base64-encoded)
        """
        try:
            from cryptography.fernet import Fernet
            f = Fernet(key)
            encrypted = f.encrypt(data.encode('utf-8'))
            return encrypted.decode('utf-8')
        except ImportError:
            # Fallback: Return data with warning
            return f"WARNING_UNENCRYPTED:{data}"
    
    @staticmethod
    def decrypt(encrypted_data: str, key: bytes) -> str:
        """
        Decrypt Fernet-encrypted data.
        
        Args:
            encrypted_data: Encrypted data
            key: Encryption key
            
        Returns:
            Decrypted data
        """
        try:
            from cryptography.fernet import Fernet
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_data.encode('utf-8'))
            return decrypted.decode('utf-8')
        except ImportError:
            # Fallback: Return warning
            if encrypted_data.startswith("WARNING_UNENCRYPTED:"):
                return encrypted_data.replace("WARNING_UNENCRYPTED:", "")
            return "ERROR: cryptography library not available"
