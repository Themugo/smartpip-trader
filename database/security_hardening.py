import sqlite3
import json
import hashlib
import hmac
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseSecurity:
    """Database security hardening with encryption and audit trails"""
    
    def __init__(self, db_path: str = "trading.db", encryption_key: str = None):
        """
        Initialize database security
        
        Args:
            db_path: Path to SQLite database
            encryption_key: Encryption key for sensitive columns
        """
        self.db_path = db_path
        self.encryption_key = encryption_key or os.getenv("DB_ENCRYPTION_KEY")
        if not self.encryption_key:
            raise ValueError("DB_ENCRYPTION_KEY environment variable must be set in production")
        self._initialize_database()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with security settings"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Initialize database with security tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Create audit trail table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    user_id TEXT,
                    ip_address TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    old_values TEXT,
                    new_values TEXT,
                    changes TEXT
                )
            """)
            
            # Create index for audit trail
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_trail_table 
                ON audit_trail(table_name, timestamp)
            """)
            
            # Create index for user actions
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_trail_user 
                ON audit_trail(user_id, timestamp)
            """)
            
            # Create tenant isolation table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tenant_isolation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    access_level TEXT DEFAULT 'read',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_id, resource_type, resource_id)
                )
            """)
            
            # Create index for tenant isolation
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tenant_isolation_tenant 
                ON tenant_isolation(tenant_id, resource_type)
            """)
            
            conn.commit()
            logger.info("Database security tables initialized")
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        from cryptography.fernet import Fernet
        import base64
        
        # Generate key from encryption key
        key = base64.urlsafe_b64encode(hashlib.sha256(self.encryption_key.encode()).digest())
        f = Fernet(key)
        
        encrypted = f.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        from cryptography.fernet import Fernet
        import base64
        
        # Generate key from encryption key
        key = base64.urlsafe_b64encode(hashlib.sha256(self.encryption_key.encode()).digest())
        f = Fernet(key)
        
        decrypted = f.decrypt(encrypted_data.encode())
        return decrypted.decode()
    
    def log_audit_trail(self, table_name: str, record_id: str, action: str,
                       user_id: str = None, ip_address: str = None,
                       old_values: Dict = None, new_values: Dict = None):
        """
        Log action to audit trail
        
        Args:
            table_name: Name of the table
            record_id: ID of the record
            action: Action performed (insert, update, delete)
            user_id: User who performed the action
            ip_address: IP address of the user
            old_values: Previous values (for updates)
            new_values: New values
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            changes = None
            if old_values and new_values:
                changes = json.dumps({
                    k: {"old": v, "new": new_values.get(k)}
                    for k in set(old_values.keys()) | set(new_values.keys())
                    if old_values.get(k) != new_values.get(k)
                })
            
            cursor.execute("""
                INSERT INTO audit_trail 
                (table_name, record_id, action, user_id, ip_address, old_values, new_values, changes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                table_name,
                record_id,
                action,
                user_id,
                ip_address,
                json.dumps(old_values) if old_values else None,
                json.dumps(new_values) if new_values else None,
                changes
            ))
            
            conn.commit()
    
    def add_tenant_isolation(self, tenant_id: str, resource_type: str, 
                            resource_id: str, access_level: str = "read"):
        """
        Add tenant isolation rule
        
        Args:
            tenant_id: Tenant/user ID
            resource_type: Type of resource (trade, account, etc.)
            resource_id: ID of the resource
            access_level: Access level (read, write, admin)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO tenant_isolation 
                (tenant_id, resource_type, resource_id, access_level)
                VALUES (?, ?, ?, ?)
            """, (tenant_id, resource_type, resource_id, access_level))
            
            conn.commit()
    
    def check_tenant_access(self, tenant_id: str, resource_type: str, 
                          resource_id: str, required_access: str = "read") -> bool:
        """
        Check if tenant has access to resource
        
        Args:
            tenant_id: Tenant/user ID
            resource_type: Type of resource
            resource_id: ID of the resource
            required_access: Required access level
            
        Returns:
            True if access is granted, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT access_level FROM tenant_isolation
                WHERE tenant_id = ? AND resource_type = ? AND resource_id = ?
            """, (tenant_id, resource_type, resource_id))
            
            result = cursor.fetchone()
            
            if not result:
                return False
            
            access_levels = {"read": 1, "write": 2, "admin": 3}
            return access_levels.get(result["access_level"], 0) >= access_levels.get(required_access, 0)
    
    def get_audit_trail(self, table_name: str = None, user_id: str = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get audit trail entries
        
        Args:
            table_name: Filter by table name
            user_id: Filter by user ID
            limit: Maximum number of entries
            
        Returns:
            List of audit trail entries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_trail"
            params = []
            
            if table_name:
                query += " WHERE table_name = ?"
                params.append(table_name)
            
            if user_id:
                if table_name:
                    query += " AND user_id = ?"
                else:
                    query += " WHERE user_id = ?"
                params.append(user_id)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def create_encrypted_column(self, table_name: str, column_name: str):
        """
        Create an encrypted column (store as TEXT, decrypt on access)
        
        Args:
            table_name: Name of the table
            column_name: Name of the column to encrypt
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Add column if it doesn't exist
            cursor.execute(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN {column_name}_encrypted TEXT
            """)
            
            conn.commit()
            logger.info(f"Created encrypted column: {table_name}.{column_name}_encrypted")
    
    def migrate_to_encrypted(self, table_name: str, column_name: str):
        """
        Migrate existing data to encrypted format
        
        Args:
            table_name: Name of the table
            column_name: Name of the column to encrypt
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get existing data
            cursor.execute(f"SELECT id, {column_name} FROM {table_name}")
            rows = cursor.fetchall()
            
            for row in rows:
                record_id = row[0]
                value = row[1]
                
                if value:
                    encrypted = self.encrypt_sensitive_data(str(value))
                    cursor.execute(f"""
                        UPDATE {table_name} 
                        SET {column_name}_encrypted = ? 
                        WHERE id = ?
                    """, (encrypted, record_id))
            
            conn.commit()
            logger.info(f"Migrated {len(rows)} records to encrypted format")
    
    def get_decrypted_value(self, table_name: str, column_name: str, record_id: int) -> str:
        """
        Get decrypted value from encrypted column
        
        Args:
            table_name: Name of the table
            column_name: Name of the column
            record_id: ID of the record
            
        Returns:
            Decrypted value
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT {column_name}_encrypted FROM {table_name} 
                WHERE id = ?
            """, (record_id,))
            
            result = cursor.fetchone()
            
            if result and result[f"{column_name}_encrypted"]:
                return self.decrypt_sensitive_data(result[f"{column_name}_encrypted"])
            
            return None


class AdminAuditLogger:
    """Audit logger for admin actions"""
    
    def __init__(self, db_security: DatabaseSecurity):
        """
        Initialize admin audit logger
        
        Args:
            db_security: DatabaseSecurity instance
        """
        self.db_security = db_security
    
    def log_admin_action(self, admin_id: str, action: str, resource_type: str,
                       resource_id: str, details: Dict = None, ip_address: str = None):
        """
        Log admin action
        
        Args:
            admin_id: Admin user ID
            action: Action performed
            resource_type: Type of resource
            resource_id: ID of the resource
            details: Additional details
            ip_address: IP address
        """
        self.db_security.log_audit_trail(
            table_name=f"admin_{resource_type}",
            record_id=resource_id,
            action=action,
            user_id=admin_id,
            ip_address=ip_address,
            new_values=details
        )
        
        logger.info(f"Admin action logged: {admin_id} - {action} on {resource_type}:{resource_id}")
    
    def get_admin_actions(self, admin_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get admin actions from audit trail
        
        Args:
            admin_id: Filter by admin ID
            limit: Maximum number of entries
            
        Returns:
            List of admin actions
        """
        return self.db_security.get_audit_trail(
            table_name="admin_trades",
            user_id=admin_id,
            limit=limit
        )
