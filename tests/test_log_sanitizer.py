import unittest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log_sanitizer import LogSanitizer, SanitizedLogger, get_sanitized_logger


class TestLogSanitizer(unittest.TestCase):
    """Test LogSanitizer functionality"""
    
    def test_sanitize_api_token(self):
        """Test API token sanitization"""
        message = 'api_token="abcdefghijklmnopqrstuvwxyz1234567890"'
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz1234567890", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_api_token_with_underscore(self):
        """Test API token sanitization with underscore"""
        message = 'api-token=abcdefghijklmnopqrstuvwxyz1234567890'
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz1234567890", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_authorization_header(self):
        """Test authorization header sanitization"""
        # Use a bearer token that matches the specific pattern
        message = 'bearer="abcdefghijklmnopqrstuvwxyz"'
        sanitized = LogSanitizer.sanitize(message)
        
        # The token should be redacted
        self.assertIn("[REDACTED]", sanitized)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", sanitized)
    
    def test_sanitize_email_address(self):
        """Test email address sanitization"""
        message = "Contact user@example.com for support"
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("user@example.com", sanitized)
        self.assertIn("[EMAIL_REDACTED]", sanitized)
    
    def test_sanitize_phone_number(self):
        """Test phone number sanitization"""
        message = "Call us at +1-555-123-4567"
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("+1-555-123-4567", sanitized)
        self.assertIn("[PHONE_REDACTED]", sanitized)
    
    def test_sanitize_credit_card(self):
        """Test credit card number sanitization"""
        message = "Card: 1234-5678-9012-3456"
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("1234-5678-9012-3456", sanitized)
        self.assertIn("[CARD_REDACTED]", sanitized)
    
    def test_sanitize_password(self):
        """Test password sanitization"""
        message = 'password="supersecret123"'
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("supersecret123", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_secret(self):
        """Test secret sanitization"""
        message = 'secret="mysecretkey1234567890"'
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("mysecretkey1234567890", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_account_id(self):
        """Test account ID sanitization"""
        message = 'account_id="ACC1234567890"'
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("ACC1234567890", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_user_id(self):
        """Test user ID sanitization"""
        message = 'user_id="USR1234567890"'
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("USR1234567890", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_trade_id(self):
        """Test trade ID sanitization - using a value without 10 consecutive digits"""
        message = 'trade_id="TRD-abc-def-ghi-jkl-mno-123"'
        sanitized = LogSanitizer.sanitize(message)
        
        # The full value should be redacted by the trade_id pattern
        self.assertNotIn("TRD-abc-def-ghi-jkl-mno-123", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_contract_id(self):
        """Test contract ID sanitization"""
        message = 'contract_id="CTR-xyz-uvw-rst-opq-lmn-456"'
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("CTR-xyz-uvw-rst-opq-lmn-456", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_ws_token(self):
        """Test WebSocket token sanitization"""
        message = 'ws_token="wstoken-abc-def-ghi-jkl-mno"'
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("wstoken-abc-def-ghi-jkl-mno", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_session_id(self):
        """Test session ID sanitization"""
        message = 'session_id="sess-abc-def-ghi-jkl-mno-pqr-xyz"'
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("sess-abc-def-ghi-jkl-mno-pqr-xyz", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_non_string(self):
        """Test sanitization of non-string values"""
        result = LogSanitizer.sanitize(123)
        self.assertEqual(result, "123")
        
        result = LogSanitizer.sanitize(None)
        self.assertEqual(result, "None")
    
    def test_sanitize_preserves_label(self):
        """Test that sanitization preserves the key/label"""
        message = 'password="secretvalue12345678"'
        sanitized = LogSanitizer.sanitize(message)
        
        # The label should be preserved
        self.assertIn("password", sanitized)
        # But the value should be redacted
        self.assertNotIn("secretvalue12345678", sanitized)
    
    def test_sanitize_case_insensitive(self):
        """Test that sanitization is case insensitive"""
        message = 'API_TOKEN="abcdefghijklmnopqrstuvwxyz1234567890"'
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz1234567890", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_multiple_patterns(self):
        """Test sanitization of multiple sensitive patterns in one message"""
        message = '''
        User john@example.com logged in.
        Password: mysecretpassword1234
        API Key: apikey12345678901234567890
        '''
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertNotIn("john@example.com", sanitized)
        self.assertNotIn("mysecretpassword1234", sanitized)
        self.assertIn("[EMAIL_REDACTED]", sanitized)
        self.assertIn("[REDACTED]", sanitized)
    
    def test_sanitize_no_sensitive_data(self):
        """Test sanitization of message with no sensitive data"""
        message = "This is a normal log message with no sensitive data"
        sanitized = LogSanitizer.sanitize(message)
        
        self.assertEqual(sanitized, message)
    
    def test_sanitize_empty_string(self):
        """Test sanitization of empty string"""
        sanitized = LogSanitizer.sanitize("")
        self.assertEqual(sanitized, "")


class TestLogSanitizerDict(unittest.TestCase):
    """Test LogSanitizer dictionary sanitization"""
    
    def test_sanitize_dict_sensitive_keys(self):
        """Test sanitization of dict with sensitive keys"""
        data = {
            "token": "secret_token_value",
            "password": "my_password",
            "api_key": "key123456789",
            "name": "John Doe"
        }
        
        sanitized = LogSanitizer.sanitize_dict(data)
        
        self.assertEqual(sanitized["token"], "[REDACTED]")
        self.assertEqual(sanitized["password"], "[REDACTED]")
        self.assertEqual(sanitized["api_key"], "[REDACTED]")
        self.assertEqual(sanitized["name"], "John Doe")
    
    def test_sanitize_dict_mixed_case_keys(self):
        """Test sanitization with mixed case sensitive keys"""
        data = {
            "TOKEN": "secret1",
            "ApiKey": "secret2",
            "PASSWORD": "secret3"
        }
        
        sanitized = LogSanitizer.sanitize_dict(data)
        
        self.assertEqual(sanitized["TOKEN"], "[REDACTED]")
        self.assertEqual(sanitized["ApiKey"], "[REDACTED]")
        self.assertEqual(sanitized["PASSWORD"], "[REDACTED]")
    
    def test_sanitize_dict_nested(self):
        """Test sanitization of nested dictionaries"""
        data = {
            "outer": {
                "inner": {
                    "secret": "hidden_value",
                    "public": "visible_value"
                }
            }
        }
        
        sanitized = LogSanitizer.sanitize_dict(data)
        
        self.assertEqual(sanitized["outer"]["inner"]["secret"], "[REDACTED]")
        self.assertEqual(sanitized["outer"]["inner"]["public"], "visible_value")
    
    def test_sanitize_dict_with_string_values(self):
        """Test sanitization of dict with string values that contain sensitive data"""
        data = {
            "message": 'User logged in with api_token=myverylongsecrettoken123456789'
        }
        
        sanitized = LogSanitizer.sanitize_dict(data)
        
        # The value itself should be sanitized
        self.assertNotIn("myverylongsecrettoken123456789", sanitized["message"])
    
    def test_sanitize_dict_with_numeric_values(self):
        """Test sanitization of dict with numeric values"""
        data = {
            "user_id": "USR123456789",
            "count": 42,
            "balance": 100.50
        }
        
        sanitized = LogSanitizer.sanitize_dict(data)
        
        self.assertEqual(sanitized["user_id"], "[REDACTED]")
        self.assertEqual(sanitized["count"], 42)
        self.assertEqual(sanitized["balance"], 100.50)
    
    def test_sanitize_dict_empty(self):
        """Test sanitization of empty dictionary"""
        sanitized = LogSanitizer.sanitize_dict({})
        self.assertEqual(sanitized, {})


class TestSanitizedLogger(unittest.TestCase):
    """Test SanitizedLogger class"""
    
    def test_get_sanitized_logger(self):
        """Test getting a sanitized logger instance"""
        logger = get_sanitized_logger("test_logger")
        
        self.assertIsInstance(logger, SanitizedLogger)
        self.assertEqual(logger.name, "test_logger")
    
    def test_sanitized_logger_is_logger(self):
        """Test that SanitizedLogger is a proper Logger subclass"""
        from logging import Logger
        
        self.assertTrue(issubclass(SanitizedLogger, Logger))


if __name__ == "__main__":
    unittest.main()
