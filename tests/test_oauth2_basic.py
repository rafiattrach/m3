"""
Basic OAuth2 authentication tests.
"""

import os
from unittest.mock import patch

import pytest

from m3.auth import (
    OAuth2Config,
    init_oauth2,
    is_oauth2_enabled,
    require_oauth2,
)


class TestOAuth2BasicConfig:
    """Test basic OAuth2 configuration."""

    def test_oauth2_disabled_by_default(self):
        """Test that OAuth2 is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            config = OAuth2Config()
            assert not config.enabled

    def test_oauth2_enabled_configuration(self):
        """Test OAuth2 enabled configuration."""
        env_vars = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
            "M3_OAUTH2_REQUIRED_SCOPES": "read:mimic-data,write:mimic-data",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = OAuth2Config()
            assert config.enabled
            assert config.issuer_url == "https://auth.example.com"
            assert config.audience == "m3-api"
            assert config.required_scopes == {"read:mimic-data", "write:mimic-data"}

    def test_oauth2_invalid_configuration_raises_error(self):
        """Test that invalid OAuth2 configuration raises an error."""
        with patch.dict(os.environ, {"M3_OAUTH2_ENABLED": "true"}, clear=True):
            with pytest.raises(ValueError, match="M3_OAUTH2_ISSUER_URL is required"):
                OAuth2Config()

    def test_jwks_url_auto_discovery(self):
        """Test automatic JWKS URL discovery."""
        env_vars = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = OAuth2Config()
            assert config.jwks_url == "https://auth.example.com/.well-known/jwks.json"

    def test_scope_parsing(self):
        """Test scope parsing from environment variable."""
        config = OAuth2Config()

        # Test comma-separated scopes
        scopes = config._parse_scopes("read:data, write:data, admin")
        assert scopes == {"read:data", "write:data", "admin"}

        # Test empty scopes
        scopes = config._parse_scopes("")
        assert scopes == set()


class TestOAuth2BasicIntegration:
    """Test basic OAuth2 integration functions."""

    def test_init_oauth2_disabled(self):
        """Test OAuth2 initialization when disabled."""
        with patch.dict(os.environ, {}, clear=True):
            init_oauth2()
            assert not is_oauth2_enabled()

    def test_init_oauth2_enabled(self):
        """Test OAuth2 initialization when enabled."""
        env_vars = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            init_oauth2()
            assert is_oauth2_enabled()


class TestOAuth2BasicDecorator:
    """Test basic OAuth2 decorator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state
        import m3.auth

        m3.auth._oauth2_config = None
        m3.auth._oauth2_validator = None

    def test_decorator_with_oauth2_disabled(self):
        """Test decorator behavior when OAuth2 is disabled."""

        @require_oauth2
        def test_function():
            return "success"

        with patch.dict(os.environ, {}, clear=True):
            init_oauth2()

            # Should allow access when OAuth2 is disabled
            result = test_function()
            assert result == "success"

    def test_decorator_with_missing_token(self):
        """Test decorator behavior with missing token."""

        @require_oauth2
        def test_function():
            return "success"

        env_vars = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            init_oauth2()

            # Should return error when token is missing
            result = test_function()
            assert "Missing OAuth2 access token" in result

    def test_decorator_with_invalid_token_format(self):
        """Test decorator behavior with invalid token format."""

        @require_oauth2
        def test_function():
            return "success"

        env_vars = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
            "M3_OAUTH2_TOKEN": "invalid-token",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            init_oauth2()

            # Should return error with invalid token format
            result = test_function()
            assert "Invalid token format" in result

    def test_decorator_with_valid_jwt_format(self):
        """Test decorator behavior with valid JWT format."""

        @require_oauth2
        def test_function():
            return "success"

        # Valid JWT format (header.payload.signature)
        valid_jwt = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWV9.signature"

        env_vars = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
            "M3_OAUTH2_TOKEN": f"Bearer {valid_jwt}",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            init_oauth2()

            # Should work with valid JWT format
            result = test_function()
            assert result == "success"

    def test_decorator_with_bearer_prefix_removal(self):
        """Test that Bearer prefix is correctly removed."""

        @require_oauth2
        def test_function():
            return "success"

        # Valid JWT format (header.payload.signature)
        valid_jwt = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWV9.signature"

        env_vars = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
            "M3_OAUTH2_TOKEN": f"Bearer {valid_jwt}",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            init_oauth2()

            # Should work even with Bearer prefix
            result = test_function()
            assert result == "success"
