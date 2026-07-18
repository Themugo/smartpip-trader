"""
Test configuration for pytest
"""

import os
import sys

# Set environment variables before importing modules
os.environ.setdefault("SANITIZATION_SECRET_KEY", "test-secret-key-for-development")
os.environ.setdefault("TESTING", "true")

# Don't set real API credentials - these tests require real connections
# os.environ.setdefault("DERIV_APP_ID", "test_app_id")
# os.environ.setdefault("DERIV_API_TOKEN", "test_token")
# os.environ.setdefault("DERIV_API_URL", "wss://test.deriv.com")
