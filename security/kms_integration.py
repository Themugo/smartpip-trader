"""
KMS Integration for Cryptographic Governance
Provides hardware-backed secrets and envelope encryption
"""

import os
import base64
import json
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class KMSProvider:
    """Base class for KMS providers"""
    
    def encrypt(self, plaintext: str, key_id: str) -> str:
        """Encrypt plaintext using KMS"""
        raise NotImplementedError
    
    def decrypt(self, ciphertext: str, key_id: str) -> str:
        """Decrypt ciphertext using KMS"""
        raise NotImplementedError
    
    def generate_data_key(self, key_id: str) -> str:
        """Generate a data key"""
        raise NotImplementedError


class AWSKMSProvider(KMSProvider):
    """AWS KMS provider for envelope encryption"""
    
    def __init__(self, region: str = None, access_key: str = None, secret_key: str = None):
        """
        Initialize AWS KMS provider
        
        Args:
            region: AWS region
            access_key: AWS access key (optional, uses IAM role if not provided)
            secret_key: AWS secret key (optional, uses IAM role if not provided)
        """
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        
        try:
            import boto3
            if self.access_key and self.secret_key:
                self.client = boto3.client(
                    'kms',
                    region_name=self.region,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key
                )
            else:
                # Use IAM role
                self.client = boto3.client('kms', region_name=self.region)
            logger.info("AWS KMS provider initialized")
        except ImportError:
            logger.warning("boto3 not installed, AWS KMS unavailable")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize AWS KMS: {e}")
            self.client = None
    
    def encrypt(self, plaintext: str, key_id: str) -> str:
        """Encrypt plaintext using AWS KMS"""
        if not self.client:
            raise RuntimeError("AWS KMS client not available")
        
        try:
            response = self.client.encrypt(
                KeyId=key_id,
                Plaintext=plaintext.encode()
            )
            return base64.b64encode(response['CiphertextBlob']).decode()
        except Exception as e:
            logger.error(f"AWS KMS encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str, key_id: str) -> str:
        """Decrypt ciphertext using AWS KMS"""
        if not self.client:
            raise RuntimeError("AWS KMS client not available")
        
        try:
            response = self.client.decrypt(
                CiphertextBlob=base64.b64decode(ciphertext)
            )
            return response['Plaintext'].decode()
        except Exception as e:
            logger.error(f"AWS KMS decryption failed: {e}")
            raise
    
    def generate_data_key(self, key_id: str) -> str:
        """Generate a data key using AWS KMS"""
        if not self.client:
            raise RuntimeError("AWS KMS client not available")
        
        try:
            response = self.client.generate_data_key(
                KeyId=key_id,
                KeySpec='AES_256'
            )
            return base64.b64encode(response['Plaintext']).decode()
        except Exception as e:
            logger.error(f"AWS KMS data key generation failed: {e}")
            raise


class AzureKeyVaultProvider(KMSProvider):
    """Azure Key Vault provider for secrets management"""
    
    def __init__(self, vault_url: str = None, credential: Any = None):
        """
        Initialize Azure Key Vault provider
        
        Args:
            vault_url: Azure Key Vault URL
            credential: Azure credential (optional, uses DefaultAzureCredential if not provided)
        """
        self.vault_url = vault_url or os.getenv("AZURE_KEY_VAULT_URL")
        
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            
            self.credential = credential or DefaultAzureCredential()
            self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)
            logger.info("Azure Key Vault provider initialized")
        except ImportError:
            logger.warning("azure-identity or azure-keyvault-secrets not installed, Azure Key Vault unavailable")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Azure Key Vault: {e}")
            self.client = None
    
    def encrypt(self, plaintext: str, key_id: str) -> str:
        """Encrypt using Azure Key Vault (stores as secret)"""
        if not self.client:
            raise RuntimeError("Azure Key Vault client not available")
        
        try:
            # Azure Key Vault doesn't directly encrypt, but we can store encrypted data
            # For actual encryption, use Azure Key Vault keys
            from cryptography.fernet import Fernet
            import hashlib
            
            # Get encryption key from Key Vault
            key_response = self.client.get_secret(key_id)
            key = key_response.value
            
            # Encrypt
            f = Fernet(key.encode())
            encrypted = f.encrypt(plaintext.encode())
            
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Azure Key Vault encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str, key_id: str) -> str:
        """Decrypt using Azure Key Vault"""
        if not self.client:
            raise RuntimeError("Azure Key Vault client not available")
        
        try:
            from cryptography.fernet import Fernet
            
            # Get decryption key from Key Vault
            key_response = self.client.get_secret(key_id)
            key = key_response.value
            
            # Decrypt
            f = Fernet(key.encode())
            decrypted = f.decrypt(base64.b64decode(ciphertext))
            
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Azure Key Vault decryption failed: {e}")
            raise
    
    def generate_data_key(self, key_id: str) -> str:
        """Generate a data key using Azure Key Vault"""
        if not self.client:
            raise RuntimeError("Azure Key Vault client not available")
        
        try:
            import secrets
            data_key = secrets.token_urlsafe(32)
            
            # Store in Key Vault
            self.client.set_secret(key_id, data_key)
            
            return data_key
        except Exception as e:
            logger.error(f"Azure Key Vault data key generation failed: {e}")
            raise


class HashiCorpVaultProvider(KMSProvider):
    """HashiCorp Vault provider for secrets management"""
    
    def __init__(self, vault_url: str = None, token: str = None):
        """
        Initialize HashiCorp Vault provider
        
        Args:
            vault_url: Vault URL
            token: Vault token
        """
        self.vault_url = vault_url or os.getenv("VAULT_ADDR", "http://localhost:8200")
        self.token = token or os.getenv("VAULT_TOKEN")
        
        try:
            import hvac
            self.client = hvac.Client(url=self.vault_url, token=self.token)
            self.client.is_authenticated()
            logger.info("HashiCorp Vault provider initialized")
        except ImportError:
            logger.warning("hvac not installed, HashiCorp Vault unavailable")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize HashiCorp Vault: {e}")
            self.client = None
    
    def encrypt(self, plaintext: str, key_id: str) -> str:
        """Encrypt using HashiCorp Vault Transit engine"""
        if not self.client:
            raise RuntimeError("HashiCorp Vault client not available")
        
        try:
            response = self.client.secrets.transit.encrypt_data(
                name=key_id,
                plaintext=plaintext
            )
            return response['data']['ciphertext']
        except Exception as e:
            logger.error(f"HashiCorp Vault encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str, key_id: str) -> str:
        """Decrypt using HashiCorp Vault Transit engine"""
        if not self.client:
            raise RuntimeError("HashiCorp Vault client not available")
        
        try:
            response = self.client.secrets.transit.decrypt_data(
                name=key_id,
                ciphertext=ciphertext
            )
            return response['data']['plaintext']
        except Exception as e:
            logger.error(f"HashiCorp Vault decryption failed: {e}")
            raise
    
    def generate_data_key(self, key_id: str) -> str:
        """Generate a data key using HashiCorp Vault"""
        if not self.client:
            raise RuntimeError("HashiCorp Vault client not available")
        
        try:
            response = self.client.secrets.transit.generate_data_key(
                name=key_id,
                key_type="aes256-gcm"
            )
            return response['data']['plaintext']
        except Exception as e:
            logger.error(f"HashiCorp Vault data key generation failed: {e}")
            raise


class EnvelopeEncryption:
    """Envelope encryption using KMS"""
    
    def __init__(self, kms_provider: KMSProvider, master_key_id: str):
        """
        Initialize envelope encryption
        
        Args:
            kms_provider: KMS provider instance
            master_key_id: ID of the master key in KMS
        """
        self.kms_provider = kms_provider
        self.master_key_id = master_key_id
    
    def encrypt(self, plaintext: str) -> Dict[str, str]:
        """
        Encrypt using envelope encryption
        
        Args:
            plaintext: Data to encrypt
            
        Returns:
            Dictionary with encrypted data key and encrypted plaintext
        """
        try:
            # Generate data key
            data_key = self.kms_provider.generate_data_key(self.master_key_id)
            
            # Encrypt plaintext with data key
            from cryptography.fernet import Fernet
            f = Fernet(data_key.encode())
            encrypted_plaintext = f.encrypt(plaintext.encode())
            
            return {
                "encrypted_data_key": data_key,
                "encrypted_plaintext": base64.b64encode(encrypted_plaintext).decode()
            }
        except Exception as e:
            logger.error(f"Envelope encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data_key: str, encrypted_plaintext: str) -> str:
        """
        Decrypt using envelope encryption
        
        Args:
            encrypted_data_key: Encrypted data key
            encrypted_plaintext: Encrypted plaintext
            
        Returns:
            Decrypted plaintext
        """
        try:
            # Decrypt data key with KMS
            data_key = self.kms_provider.decrypt(encrypted_data_key, self.master_key_id)
            
            # Decrypt plaintext with data key
            from cryptography.fernet import Fernet
            f = Fernet(data_key.encode())
            decrypted = f.decrypt(base64.b64decode(encrypted_plaintext))
            
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Envelope decryption failed: {e}")
            raise


class SecretsManager:
    """Unified secrets manager with KMS integration"""
    
    def __init__(self, provider: str = "hashicorp"):
        """
        Initialize secrets manager
        
        Args:
            provider: KMS provider (aws, azure, hashicorp)
        """
        self.provider = provider
        self.kms_provider = None
        self.envelope_encryption = None
        
        if provider == "aws":
            self.kms_provider = AWSKMSProvider()
        elif provider == "azure":
            self.kms_provider = AzureKeyVaultProvider()
        elif provider == "hashicorp":
            self.kms_provider = HashiCorpVaultProvider()
        else:
            logger.warning(f"Unknown provider: {provider}, using fallback")
            self.kms_provider = None
        
        if self.kms_provider:
            master_key_id = os.getenv("KMS_MASTER_KEY_ID", "master-key")
            self.envelope_encryption = EnvelopeEncryption(self.kms_provider, master_key_id)
    
    def store_secret(self, secret_name: str, secret_value: str, encrypt: bool = True):
        """
        Store a secret
        
        Args:
            secret_name: Name of the secret
            secret_value: Value of the secret
            encrypt: Whether to encrypt the secret
        """
        if encrypt and self.envelope_encryption:
            encrypted = self.envelope_encryption.encrypt(secret_value)
            # Store encrypted data (implementation depends on storage backend)
            logger.info(f"Stored encrypted secret: {secret_name}")
        else:
            # Store plaintext (not recommended for production)
            logger.info(f"Stored plaintext secret: {secret_name}")
    
    def retrieve_secret(self, secret_name: str, encrypted: bool = True) -> str:
        """
        Retrieve a secret
        
        Args:
            secret_name: Name of the secret
            encrypted: Whether the secret is encrypted
            
        Returns:
            Secret value
        """
        if encrypted and self.envelope_encryption:
            # Retrieve and decrypt (implementation depends on storage backend)
            logger.info(f"Retrieved encrypted secret: {secret_name}")
            # Return decrypted value
        else:
            # Retrieve plaintext
            logger.info(f"Retrieved plaintext secret: {secret_name}")
            # Return value
    
    def rotate_secret(self, secret_name: str):
        """Rotate a secret"""
        logger.info(f"Rotating secret: {secret_name}")
        # Implementation depends on provider


# Global instance
secrets_manager = SecretsManager(provider=os.getenv("KMS_PROVIDER", "hashicorp"))
