"""
Schema Model

Schema registry for data validation and type checking.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FieldType(Enum):
    """Data field types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    ARRAY = "array"
    OBJECT = "object"
    CATEGORICAL = "categorical"


class FieldConstraint(Enum):
    """Field constraints"""
    REQUIRED = "required"
    UNIQUE = "unique"
    NOT_NULL = "not_null"
    INDEXED = "indexed"
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"


@dataclass
class SchemaField:
    """A field in a schema"""
    name: str
    field_type: FieldType
    description: str = ""
    
    # Constraints
    constraints: List[FieldConstraint] = field(default_factory=list)
    is_required: bool = True
    is_nullable: bool = True
    is_primary_key: bool = False
    is_indexed: bool = False
    
    # Value constraints
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None
    
    # Metadata
    default_value: Optional[Any] = None
    example_value: Optional[Any] = None
    unit: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Statistics (populated after analysis)
    null_count: int = 0
    null_percentage: float = 0.0
    unique_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "field_type": self.field_type.value if isinstance(self.field_type, FieldType) else self.field_type,
            "description": self.description,
            "constraints": [c.value if isinstance(c, FieldConstraint) else c for c in self.constraints],
            "is_required": self.is_required,
            "is_nullable": self.is_nullable,
            "is_primary_key": self.is_primary_key,
            "is_indexed": self.is_indexed,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "allowed_values": self.allowed_values,
            "pattern": self.pattern,
            "default_value": self.default_value,
            "example_value": self.example_value,
            "unit": self.unit,
            "tags": self.tags,
            "null_count": self.null_count,
            "null_percentage": self.null_percentage,
            "unique_count": self.unique_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemaField":
        """Create from dictionary"""
        if "field_type" in data and isinstance(data["field_type"], str):
            data["field_type"] = FieldType(data["field_type"])
        if "constraints" in data:
            data["constraints"] = [
                FieldConstraint(c) if isinstance(c, str) else c
                for c in data["constraints"]
            ]
        return cls(**data)


@dataclass
class SchemaRegistry:
    """
    Schema Registry for managing data schemas.
    
    Tracks schema versions, validates data against schemas,
    and maintains schema history.
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        domain: str = "trading",
        owner: str = "",
        team: str = "",
    ):
        self.schema_id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.domain = domain
        self.owner = owner
        self.team = team
        
        # Schema versions
        self.versions: List["Schema"] = []
        self._current_schema: Optional["Schema"] = None
        
        # Timestamps
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Status
        self.is_active = True
        self.is_frozen = False
    
    @property
    def current_version(self) -> Optional[str]:
        return self._current_schema.version if self._current_schema else None
    
    @property
    def current_schema(self) -> Optional["Schema"]:
        return self._current_schema
    
    def add_schema(self, schema: "Schema") -> None:
        """Add a schema version"""
        if self._current_schema:
            self._current_schema.is_current = False
        schema.is_current = True
        schema.created_at = datetime.utcnow()
        self.versions.append(schema)
        self._current_schema = schema
        self.updated_at = datetime.utcnow()
    
    def get_schema(self, version: str) -> Optional["Schema"]:
        """Get schema by version"""
        for schema in self.versions:
            if schema.version == version:
                return schema
        return None
    
    def validate(self, data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate data against current schema"""
        if not self._current_schema:
            return False, ["No schema available"]
        return self._current_schema.validate(data)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "owner": self.owner,
            "team": self.team,
            "versions": [v.to_dict() for v in self.versions],
            "current_version": self.current_version,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "is_active": self.is_active,
            "is_frozen": self.is_frozen,
        }


@dataclass
class Schema:
    """
    A schema definition with fields and validation rules.
    """
    
    schema_id: str
    name: str
    version: str
    version_major: int = 1
    version_minor: int = 0
    
    # Fields
    fields: List[SchemaField] = field(default_factory=list)
    
    # Metadata
    description: str = ""
    domain: str = "trading"
    
    # Status
    is_current: bool = False
    is_stable: bool = False
    is_frozen: bool = False
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    # Compatibility
    previous_version: Optional[str] = None
    breaking_changes: List[str] = field(default_factory=list)
    backward_compatible: bool = True
    
    # Statistics
    record_count: int = 0
    validation_pass_count: int = 0
    validation_fail_count: int = 0
    
    def __post_init__(self):
        self._fields_by_name: Dict[str, SchemaField] = {
            f.name: f for f in self.fields
        }
        if not self.version:
            self.version = f"{self.version_major}.{self.version_minor}"
    
    def get_field(self, name: str) -> Optional[SchemaField]:
        """Get field by name"""
        return self._fields_by_name.get(name)
    
    def add_field(self, field: SchemaField) -> None:
        """Add a field to the schema"""
        if field.name in self._fields_by_name:
            raise ValueError(f"Field {field.name} already exists")
        self.fields.append(field)
        self._fields_by_name[field.name] = field
    
    def remove_field(self, name: str) -> bool:
        """Remove a field from the schema"""
        if name not in self._fields_by_name:
            return False
        field = self._fields_by_name.pop(name)
        self.fields.remove(field)
        return True
    
    def validate_value(self, field_name: str, value: Any) -> Tuple[bool, str]:
        """Validate a single value against a field"""
        field = self.get_field(field_name)
        if not field:
            return False, f"Unknown field: {field_name}"
        
        # Null check
        if value is None:
            if field.is_required or FieldConstraint.NOT_NULL in field.constraints:
                return False, f"Field {field_name} cannot be null"
            return True, ""
        
        # Type check
        try:
            if field.field_type == FieldType.STRING:
                if not isinstance(value, str):
                    return False, f"Field {field_name} must be string"
            elif field.field_type == FieldType.INTEGER:
                if not isinstance(value, int) or isinstance(value, bool):
                    return False, f"Field {field_name} must be integer"
            elif field.field_type == FieldType.FLOAT:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    return False, f"Field {field_name} must be numeric"
            elif field.field_type == FieldType.BOOLEAN:
                if not isinstance(value, bool):
                    return False, f"Field {field_name} must be boolean"
            elif field.field_type == FieldType.DATETIME:
                if not isinstance(value, (str, datetime)):
                    return False, f"Field {field_name} must be datetime"
        except Exception as e:
            return False, f"Type validation error for {field_name}: {str(e)}"
        
        # Value constraints
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if field.min_value is not None and value < field.min_value:
                return False, f"Field {field_name} value {value} below minimum {field.min_value}"
            if field.max_value is not None and value > field.max_value:
                return False, f"Field {field_name} value {value} above maximum {field.max_value}"
        
        if isinstance(value, str):
            if field.min_length is not None and len(value) < field.min_length:
                return False, f"Field {field_name} length below minimum {field.min_length}"
            if field.max_length is not None and len(value) > field.max_length:
                return False, f"Field {field_name} length above maximum {field.max_length}"
        
        # Allowed values
        if field.allowed_values and value not in field.allowed_values:
            return False, f"Field {field_name} value not in allowed values"
        
        return True, ""
    
    def validate(self, data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate a list of records against the schema"""
        errors = []
        
        # Check required fields
        for record in data:
            for field in self.fields:
                if field.is_required and field.name not in record:
                    errors.append(f"Missing required field: {field.name}")
        
        # Validate each record
        for i, record in enumerate(data):
            for field_name, value in record.items():
                valid, error = self.validate_value(field_name, value)
                if not valid:
                    errors.append(f"Row {i}: {error}")
        
        return len(errors) == 0, errors
    
    def compute_hash(self) -> str:
        """Compute schema hash for comparison"""
        schema_data = {
            "name": self.name,
            "version": self.version,
            "fields": [f.to_dict() for f in sorted(self.fields, key=lambda x: x.name)],
        }
        return hashlib.sha256(json.dumps(schema_data, sort_keys=True).encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "name": self.name,
            "version": self.version,
            "version_major": self.version_major,
            "version_minor": self.version_minor,
            "fields": [f.to_dict() for f in self.fields],
            "description": self.description,
            "domain": self.domain,
            "is_current": self.is_current,
            "is_stable": self.is_stable,
            "is_frozen": self.is_frozen,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "created_by": self.created_by,
            "previous_version": self.previous_version,
            "breaking_changes": self.breaking_changes,
            "backward_compatible": self.backward_compatible,
            "record_count": self.record_count,
            "validation_pass_count": self.validation_pass_count,
            "validation_fail_count": self.validation_fail_count,
            "hash": self.compute_hash(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Schema":
        """Create from dictionary"""
        fields = [
            SchemaField.from_dict(f) if isinstance(f, dict) else f
            for f in data.get("fields", [])
        ]
        data["fields"] = fields
        return cls(**data)
