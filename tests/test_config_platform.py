"""
Tests for Configuration Platform
=================================

Tests for configuration service, profiles, secrets, flags, and workflows.
"""

import pytest
import time


class TestConfigService:
    """Tests for ConfigService"""
    
    def test_set_and_get_value(self):
        """Test setting and getting config values"""
        from config.core import ConfigService, ConfigParameter, ParameterType
        
        # Create a new instance for testing
        service = ConfigService()
        
        # Register a parameter
        param = ConfigParameter(
            name="test.param",
            param_type=ParameterType.STRING,
            default_value="default"
        )
        service.register_parameter(param)
        
        # Set value
        service.set("test.param", "value1", user="test")
        
        # Get value
        assert service.get("test.param") == "value1"
    
    def test_validation_integer_range(self):
        """Test integer range validation"""
        from config.core import ConfigService, ConfigParameter, ParameterType, ValidationError
        
        service = ConfigService()
        
        param = ConfigParameter(
            name="test.int",
            param_type=ParameterType.INTEGER,
            min_value=0,
            max_value=100
        )
        service.register_parameter(param)
        
        # Valid value
        service.set("test.int", 50, user="test")
        assert service.get("test.int") == 50
        
        # Invalid value
        with pytest.raises(ValidationError):
            service.set("test.int", 150, user="test")
    
    def test_validation_allowed_values(self):
        """Test allowed values validation"""
        from config.core import ConfigService, ConfigParameter, ParameterType, ValidationError
        
        service = ConfigService()
        
        param = ConfigParameter(
            name="test.allowed",
            param_type=ParameterType.STRING,
            allowed_values=["a", "b", "c"]
        )
        service.register_parameter(param)
        
        # Valid value
        service.set("test.allowed", "a", user="test")
        assert service.get("test.allowed") == "a"
        
        # Invalid value
        with pytest.raises(ValidationError):
            service.set("test.allowed", "d", user="test")
    
    def test_override(self):
        """Test temporary override"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        service.set("test.override", "original", user="test")
        service.set_override("test.override", "override", duration_seconds=60)
        
        assert service.get("test.override") == "override"
        
        service.clear_override("test.override")
        assert service.get("test.override") == "original"


class TestVersioning:
    """Tests for configuration versioning"""
    
    def test_version_creation(self):
        """Test version is created on config change"""
        from config.core import ConfigService
        
        service = ConfigService()
        initial_version = service.get_current_version()
        
        service.set("version.test", "value1", user="test")
        new_version = service.get_current_version()
        
        assert new_version is not None
        if initial_version:
            assert new_version.version_number > initial_version.version_number
    
    def test_version_history(self):
        """Test version history"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        # Create multiple versions
        for i in range(3):
            service.set("version.history", f"value{i}", user="test")
        
        versions = service.get_versions(limit=10)
        assert len(versions) >= 3


class TestProfiles:
    """Tests for configuration profiles"""
    
    def test_create_profile(self):
        """Test profile creation"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        profile = service.create_profile(
            name="test-strategy",
            profile_type="strategy",
            config_data={"param1": "value1", "param2": 100},
            user="test",
            description="Test strategy profile"
        )
        
        assert profile.name == "test-strategy"
        assert profile.profile_type == "strategy"
        assert profile.config_data["param1"] == "value1"
    
    def test_activate_profile(self):
        """Test profile activation"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        profile = service.create_profile(
            name="test-strategy",
            profile_type="strategy",
            config_data={"profile.active": True},
            user="test"
        )
        
        service.activate_profile(profile.profile_id, user="test")
        
        activated = service.get_profile(profile.profile_id)
        assert activated.is_active


class TestSecrets:
    """Tests for encrypted secrets"""
    
    def test_set_and_get_secret(self):
        """Test storing and retrieving secrets"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        service.set_secret("api_key", "secret123", user="test", description="API key")
        
        # Get secret
        value = service.get_secret("api_key")
        assert value == "secret123"
    
    def test_list_secrets(self):
        """Test listing secrets (without values)"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        service.set_secret("secret1", "value1", user="test")
        service.set_secret("secret2", "value2", user="test")
        
        secrets = service.list_secrets()
        assert len(secrets) >= 2


class TestFeatureFlags:
    """Tests for feature flags"""
    
    def test_create_flag(self):
        """Test creating a feature flag"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        flag = service.create_feature_flag(
            name="new_feature",
            description="A new feature",
            enabled=False,
            user="test"
        )
        
        assert flag.name == "new_feature"
        assert flag.enabled is False
    
    def test_enable_disable_flag(self):
        """Test enabling and disabling flags"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        service.create_feature_flag(
            name="toggle_feature",
            enabled=False,
            user="test"
        )
        
        # Enable
        service.set_flag("toggle_feature", True, user="test")
        assert service.is_flag_enabled("toggle_feature")
        
        # Disable
        service.set_flag("toggle_feature", False, user="test")
        assert not service.is_flag_enabled("toggle_feature")


class TestSnapshots:
    """Tests for configuration snapshots"""
    
    def test_create_snapshot(self):
        """Test snapshot creation"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        service.set("snapshot.test", "value", user="test")
        
        snapshot = service.create_snapshot("Test snapshot", user="test")
        
        assert snapshot is not None
        assert snapshot.description == "Test snapshot"


class TestImportExport:
    """Tests for import/export"""
    
    def test_export_config(self):
        """Test configuration export"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        service.set("export.test", "value", user="test")
        
        exported = service.export_config()
        
        assert "config" in exported
        assert "export.test" in exported["config"]
    
    def test_import_config(self):
        """Test configuration import"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        data = {
            "config": {
                "import.test1": "value1",
                "import.test2": 100
            },
            "feature_flags": {}
        }
        
        errors = service.import_config(data, user="test")
        
        assert len(errors) == 0
        assert service.get("import.test1") == "value1"


class TestApprovals:
    """Tests for approval workflow"""
    
    def test_submit_for_approval(self):
        """Test submitting changes for approval"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        request = service.submit_for_approval(
            changes={"approval.test": "new_value"},
            user="testuser",
            approvers=["admin"],
            reason="Testing approval workflow"
        )
        
        assert request.status == "pending"
        assert request.submitted_by == "testuser"
    
    def test_approve_request(self):
        """Test approving a request"""
        from config.core import ConfigService
        
        service = ConfigService()
        
        request = service.submit_for_approval(
            changes={"approval.test": "approved"},
            user="testuser",
            approvers=["admin"]
        )
        
        success = service.approve_request(request.request_id, "admin", "Approved!")
        
        assert success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
