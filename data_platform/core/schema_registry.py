"""
Schema Registry Manager

Manages data schemas with versioning and validation.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from data_platform.models.schema import (
    Schema,
    SchemaField,
    SchemaRegistry,
    FieldType,
    FieldConstraint,
)

logger = logging.getLogger(__name__)


class SchemaRegistryManager:
    """
    Schema Registry Manager for managing data schemas.
    
    Features:
    - Schema versioning
    - Data validation against schemas
    - Schema compatibility checking
    - Schema history and lineage
    """
    
    def __init__(self, storage_path: str = "data_platform/schemas"):
        self._storage_path = storage_path
        self._registries: Dict[str, SchemaRegistry] = {}
        
        # Indexes
        self._by_name: Dict[str, str] = {}  # name -> registry_id
        self._by_domain: Dict[str, Set[str]] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_index()
    
    def _load_index(self) -> None:
        """Load schema registry index"""
        index_file = f"{self._storage_path}/index.json"
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    
                for registry_data in data.get("registries", []):
                    registry = self._load_registry(registry_data)
                    self._registries[registry.schema_id] = registry
                    self._update_indexes(registry)
                
                logger.info(f"Loaded {len(self._registries)} schema registries")
            except Exception as e:
                logger.warning(f"Could not load schema index: {e}")
    
    def _load_registry(self, data: Dict[str, Any]) -> SchemaRegistry:
        """Load a single registry from data"""
        registry = SchemaRegistry(
            name=data["name"],
            description=data.get("description", ""),
            domain=data.get("domain", "trading"),
            owner=data.get("owner", ""),
            team=data.get("team", ""),
        )
        registry.schema_id = data["schema_id"]
        registry.is_active = data.get("is_active", True)
        registry.is_frozen = data.get("is_frozen", False)
        registry.created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow())
        
        # Load versions
        for schema_data in data.get("versions", []):
            schema = Schema.from_dict(schema_data)
            registry.versions.append(schema)
            if schema.is_current:
                registry._current_schema = schema
        
        return registry
    
    def _save_index(self) -> None:
        """Save schema registry index"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "registries": [
                self._serialize_registry(r)
                for r in self._registries.values()
            ],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _serialize_registry(self, registry: SchemaRegistry) -> Dict[str, Any]:
        """Serialize a registry for storage"""
        return {
            "schema_id": registry.schema_id,
            "name": registry.name,
            "description": registry.description,
            "domain": registry.domain,
            "owner": registry.owner,
            "team": registry.team,
            "versions": [v.to_dict() for v in registry.versions],
            "current_version": registry.current_version,
            "created_at": registry.created_at.isoformat() if isinstance(registry.created_at, datetime) else registry.created_at,
            "updated_at": registry.updated_at.isoformat() if isinstance(registry.updated_at, datetime) else registry.updated_at,
            "is_active": registry.is_active,
            "is_frozen": registry.is_frozen,
        }
    
    def _update_indexes(self, registry: SchemaRegistry) -> None:
        """Update all indexes for a registry"""
        self._by_name[registry.name.lower()] = registry.schema_id
        
        if registry.domain not in self._by_domain:
            self._by_domain[registry.domain] = set()
        self._by_domain[registry.domain].add(registry.schema_id)
    
    def create_registry(
        self,
        name: str,
        description: str = "",
        domain: str = "trading",
        owner: str = "",
        team: str = "",
    ) -> SchemaRegistry:
        """Create a new schema registry"""
        registry = SchemaRegistry(
            name=name,
            description=description,
            domain=domain,
            owner=owner,
            team=team,
        )
        
        self._registries[registry.schema_id] = registry
        self._update_indexes(registry)
        self._save_index()
        
        logger.info(f"Created schema registry: {name} ({registry.schema_id})")
        return registry
    
    def get_registry(self, registry_id: str) -> Optional[SchemaRegistry]:
        """Get a schema registry by ID"""
        return self._registries.get(registry_id)
    
    def get_registry_by_name(self, name: str) -> Optional[SchemaRegistry]:
        """Get a schema registry by name"""
        registry_id = self._by_name.get(name.lower())
        return self._registries.get(registry_id) if registry_id else None
    
    def add_schema(
        self,
        registry_id: str,
        schema: Schema,
    ) -> bool:
        """Add a schema to a registry"""
        registry = self._registries.get(registry_id)
        if not registry:
            return False
        
        if registry.is_frozen:
            logger.warning(f"Cannot add schema to frozen registry: {registry_id}")
            return False
        
        # Check if previous version exists
        if registry.current_version:
            schema.previous_version = registry.current_version
        
        registry.add_schema(schema)
        self._save_index()
        
        logger.info(f"Added schema version {schema.version} to registry: {registry.name}")
        return True
    
    def create_schema(
        self,
        registry_id: str,
        name: str,
        fields: List[Dict[str, Any]],
        description: str = "",
        version_major: int = 1,
        version_minor: int = 0,
        created_by: str = "",
    ) -> Optional[Schema]:
        """Create a new schema in a registry"""
        registry = self._registries.get(registry_id)
        if not registry:
            return None
        
        # Create fields
        schema_fields = []
        for field_data in fields:
            if isinstance(field_data, dict):
                # Convert string field_type to enum
                if "field_type" in field_data and isinstance(field_data["field_type"], str):
                    field_data["field_type"] = FieldType(field_data["field_type"])
                schema_fields.append(SchemaField(**field_data))
            else:
                schema_fields.append(field_data)
        
        # Create schema
        schema = Schema(
            schema_id=str(uuid.uuid4()),
            name=name,
            version=f"{version_major}.{version_minor}",
            version_major=version_major,
            version_minor=version_minor,
            fields=schema_fields,
            description=description,
            domain=registry.domain,
            created_by=created_by,
        )
        
        if self.add_schema(registry_id, schema):
            return schema
        
        return None
    
    def validate_data(
        self,
        registry_id: str,
        data: List[Dict[str, Any]],
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate data against a schema registry's current schema.
        
        Returns:
            Tuple of (is_valid, errors, validation_summary)
        """
        registry = self._registries.get(registry_id)
        if not registry or not registry.current_schema:
            return False, ["No schema available in registry"], {}
        
        schema = registry.current_schema
        errors = []
        
        # Run validation
        is_valid, validation_errors = schema.validate(data)
        errors.extend(validation_errors)
        
        # Update statistics
        if is_valid:
            schema.validation_pass_count += len(data)
        else:
            schema.validation_fail_count += 1
        
        # Generate summary
        summary = {
            "schema_id": schema.schema_id,
            "schema_version": schema.version,
            "record_count": len(data),
            "is_valid": is_valid,
            "error_count": len(errors),
            "validation_pass_count": schema.validation_pass_count,
            "validation_fail_count": schema.validation_fail_count,
        }
        
        self._save_index()
        
        return is_valid, errors, summary
    
    def check_compatibility(
        self,
        registry_id: str,
        old_version: str,
        new_version: str,
    ) -> Dict[str, Any]:
        """Check compatibility between two schema versions"""
        registry = self._registries.get(registry_id)
        if not registry:
            return {"compatible": False, "reason": "Registry not found"}
        
        old_schema = registry.get_schema(old_version)
        new_schema = registry.get_schema(new_version)
        
        if not old_schema or not new_schema:
            return {"compatible": False, "reason": "Schema version not found"}
        
        compatibility_issues = []
        
        # Check for removed required fields
        old_fields = {f.name: f for f in old_schema.fields}
        new_fields = {f.name: f for f in new_schema.fields}
        
        for name, old_field in old_fields.items():
            if name not in new_fields:
                if old_field.is_required:
                    compatibility_issues.append(f"Removed required field: {name}")
            else:
                new_field = new_fields[name]
                
                # Check for type changes
                if old_field.field_type != new_field.field_type:
                    compatibility_issues.append(
                        f"Field {name} type changed: {old_field.field_type} -> {new_field.field_type}"
                    )
                
                # Check for stricter constraints
                if old_field.is_nullable and not new_field.is_nullable:
                    compatibility_issues.append(f"Field {name} changed from nullable to required")
        
        # Check for new required fields
        for name, new_field in new_fields.items():
            if name not in old_fields and new_field.is_required:
                compatibility_issues.append(f"Added required field: {name}")
        
        is_backward_compatible = len(compatibility_issues) == 0
        
        return {
            "compatible": is_backward_compatible,
            "issues": compatibility_issues,
            "old_version": old_version,
            "new_version": new_version,
        }
    
    def search_schemas(
        self,
        query: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for schemas"""
        results = []
        
        for registry in self._registries.values():
            if domain and registry.domain != domain:
                continue
            
            for schema in registry.versions:
                if query:
                    query_lower = query.lower()
                    if (query_lower not in schema.name.lower() and
                        query_lower not in schema.description.lower()):
                        continue
                
                results.append({
                    "registry_id": registry.schema_id,
                    "registry_name": registry.name,
                    "schema_id": schema.schema_id,
                    "schema_name": schema.name,
                    "version": schema.version,
                    "is_current": schema.is_current,
                    "field_count": len(schema.fields),
                    "description": schema.description,
                    "domain": schema.domain,
                })
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get schema registry statistics"""
        total_schemas = sum(len(r.versions) for r in self._registries.values())
        
        return {
            "total_registries": len(self._registries),
            "total_schemas": total_schemas,
            "by_domain": {
                domain: len(ids)
                for domain, ids in self._by_domain.items()
            },
            "total_validations_pass": sum(
                sum(s.validation_pass_count for s in r.versions)
                for r in self._registries.values()
            ),
            "total_validations_fail": sum(
                sum(s.validation_fail_count for s in r.versions)
                for r in self._registries.values()
            ),
        }


# Type alias for Set
from typing import Set
