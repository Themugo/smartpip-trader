import os
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError


class SecretsManager:
    """Secrets manager for secure storage and retrieval of sensitive data"""
    
    def __init__(self, vault_type: str = "env"):
        """
        Initialize secrets manager
        
        Args:
            vault_type: Type of vault ('env', 'aws', 'hashicorp')
        """
        self.vault_type = vault_type
        self.client = None
        
        if vault_type == "aws":
            self._init_aws_secrets()
        elif vault_type == "hashicorp":
            self._init_hashicorp_vault()
    
    def _init_aws_secrets(self):
        """Initialize AWS Secrets Manager client"""
        try:
            region = os.getenv("AWS_REGION", "us-east-1")
            self.client = boto3.client('secretsmanager', region_name=region)
        except Exception as e:
            raise Exception(f"Failed to initialize AWS Secrets Manager: {e}")
    
    def _init_hashicorp_vault(self):
        """Initialize HashiCorp Vault client"""
        try:
            import hvac
            vault_addr = os.getenv("VAULT_ADDR", "http://localhost:8200")
            vault_token = os.getenv("VAULT_TOKEN")
            
            if not vault_token:
                raise Exception("VAULT_TOKEN environment variable not set")
            
            self.client = hvac.Client(url=vault_addr, token=vault_token)
        except ImportError:
            raise Exception("hvac package not installed. Install with: pip install hvac")
        except Exception as e:
            raise Exception(f"Failed to initialize HashiCorp Vault: {e}")
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Get secret value
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            Secret value or None if not found
        """
        if self.vault_type == "env":
            return os.getenv(secret_name)
        elif self.vault_type == "aws":
            return self._get_aws_secret(secret_name)
        elif self.vault_type == "hashicorp":
            return self._get_hashicorp_secret(secret_name)
        else:
            return None
    
    def _get_aws_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            
            if 'SecretString' in response:
                return response['SecretString']
            else:
                return response['SecretBinary']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            raise Exception(f"AWS Secrets Manager error: {e}")
    
    def _get_hashicorp_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from HashiCorp Vault"""
        try:
            # Assume secrets are stored in secret/ path
            secret_path = f"secret/{secret_name}"
            response = self.client.secrets.kv.v2.read_secret_version(path=secret_path)
            
            if response and 'data' in response and 'data' in response['data']:
                return response['data']['data'].get('value')
            return None
        except Exception as e:
            raise Exception(f"HashiCorp Vault error: {e}")
    
    def set_secret(self, secret_name: str, secret_value: str):
        """
        Set secret value
        
        Args:
            secret_name: Name of the secret
            secret_value: Secret value
        """
        if self.vault_type == "env":
            os.environ[secret_name] = secret_value
        elif self.vault_type == "aws":
            self._set_aws_secret(secret_name, secret_value)
        elif self.vault_type == "hashicorp":
            self._set_hashicorp_secret(secret_name, secret_value)
    
    def _set_aws_secret(self, secret_name: str, secret_value: str):
        """Set secret in AWS Secrets Manager"""
        try:
            self.client.create_secret(
                Name=secret_name,
                SecretString=secret_value
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                # Update existing secret
                self.client.update_secret(
                    SecretId=secret_name,
                    SecretString=secret_value
                )
            else:
                raise Exception(f"AWS Secrets Manager error: {e}")
    
    def _set_hashicorp_secret(self, secret_name: str, secret_value: str):
        """Set secret in HashiCorp Vault"""
        try:
            secret_path = f"secret/{secret_name}"
            self.client.secrets.kv.v2.create_or_update_secret(
                path=secret_path,
                secret={'value': secret_value}
            )
        except Exception as e:
            raise Exception(f"HashiCorp Vault error: {e}")
    
    def delete_secret(self, secret_name: str):
        """
        Delete secret
        
        Args:
            secret_name: Name of the secret
        """
        if self.vault_type == "env":
            if secret_name in os.environ:
                del os.environ[secret_name]
        elif self.vault_type == "aws":
            self._delete_aws_secret(secret_name)
        elif self.vault_type == "hashicorp":
            self._delete_hashicorp_secret(secret_name)
    
    def _delete_aws_secret(self, secret_name: str):
        """Delete secret from AWS Secrets Manager"""
        try:
            self.client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)
        except ClientError as e:
            raise Exception(f"AWS Secrets Manager error: {e}")
    
    def _delete_hashicorp_secret(self, secret_name: str):
        """Delete secret from HashiCorp Vault"""
        try:
            secret_path = f"secret/{secret_name}"
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(path=secret_path)
        except Exception as e:
            raise Exception(f"HashiCorp Vault error: {e}")
    
    def rotate_secret(self, secret_name: str, new_value: str):
        """
        Rotate secret value
        
        Args:
            secret_name: Name of the secret
            new_value: New secret value
        """
        # Store old value for rollback
        old_value = self.get_secret(secret_name)
        
        try:
            self.set_secret(secret_name, new_value)
        except Exception as e:
            # Rollback on failure
            if old_value:
                self.set_secret(secret_name, old_value)
            raise Exception(f"Secret rotation failed: {e}")
    
    def get_all_secrets(self) -> Dict[str, str]:
        """
        Get all secrets
        
        Returns:
            Dictionary of all secrets
        """
        if self.vault_type == "env":
            return dict(os.environ)
        elif self.vault_type == "aws":
            return self._get_all_aws_secrets()
        elif self.vault_type == "hashicorp":
            return self._get_all_hashicorp_secrets()
        else:
            return {}
    
    def _get_all_aws_secrets(self) -> Dict[str, str]:
        """Get all secrets from AWS Secrets Manager"""
        try:
            secrets = {}
            paginator = self.client.get_paginator('list_secrets')
            
            for page in paginator.paginate():
                for secret in page['SecretList']:
                    secret_name = secret['Name']
                    secret_value = self.get_secret(secret_name)
                    if secret_value:
                        secrets[secret_name] = secret_value
            
            return secrets
        except ClientError as e:
            raise Exception(f"AWS Secrets Manager error: {e}")
    
    def _get_all_hashicorp_secrets(self) -> Dict[str, str]:
        """Get all secrets from HashiCorp Vault"""
        try:
            secrets = {}
            response = self.client.secrets.kv.v2.list_secrets(path='secret/')
            
            if response and 'data' in response and 'keys' in response['data']:
                for key in response['data']['keys']:
                    secret_value = self.get_secret(key)
                    if secret_value:
                        secrets[key] = secret_value
            
            return secrets
        except Exception as e:
            raise Exception(f"HashiCorp Vault error: {e}")


# Global secrets manager instance
secrets_manager = SecretsManager(vault_type=os.getenv("VAULT_TYPE", "env"))


def get_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get secret with fallback to default
    
    Args:
        secret_name: Name of the secret
        default: Default value if secret not found
        
    Returns:
        Secret value or default
    """
    value = secrets_manager.get_secret(secret_name)
    return value if value is not None else default


def require_secret(secret_name: str) -> str:
    """
    Get secret and raise error if not found
    
    Args:
        secret_name: Name of the secret
        
    Returns:
        Secret value
        
    Raises:
        Exception if secret not found
    """
    value = secrets_manager.get_secret(secret_name)
    if value is None:
        raise Exception(f"Required secret '{secret_name}' not found")
    return value
