"""
Tests for OAuth2 authentication functionality.
"""

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from m3.auth import (
    OAuth2Config,
    OAuth2Validator,
    TokenValidationError,
    generate_test_token,
    init_oauth2,
    is_oauth2_enabled,
)


class TestOAuth2Config:
    """Test OAuth2 configuration."""

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


class TestOAuth2Validator:
    """Test OAuth2 token validator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = OAuth2Config()
        self.config.enabled = True
        self.config.issuer_url = "https://auth.example.com"
        self.config.audience = "m3-api"
        self.config.required_scopes = {"read:mimic-data"}
        self.config.jwks_url = "https://auth.example.com/.well-known/jwks.json"
        
        self.validator = OAuth2Validator(self.config)
        
        # Generate test RSA key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def _create_test_jwks(self):
        """Create a test JWKS response."""
        # Get public key components
        public_numbers = self.public_key.public_numbers()
        n = public_numbers.n
        e = public_numbers.e
        
        # Convert to base64url format
        import base64
        
        def int_to_base64url(value):
            """Convert integer to base64url encoding."""
            byte_length = (value.bit_length() + 7) // 8
            value_bytes = value.to_bytes(byte_length, byteorder='big')
            return base64.urlsafe_b64encode(value_bytes).decode('utf-8').rstrip('=')
        
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "kid": "test-key-id",
                    "n": int_to_base64url(n),
                    "e": int_to_base64url(e),
                    "alg": "RS256"
                }
            ]
        }

    def _create_test_token(self, **claims):
        """Create a test JWT token."""
        import jwt
        
        default_claims = {
            "iss": self.config.issuer_url,
            "aud": self.config.audience,
            "sub": "test-user",
            "scope": "read:mimic-data",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }
        default_claims.update(claims)
        
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return jwt.encode(
            default_claims,
            private_pem,
            algorithm="RS256",
            headers={"kid": "test-key-id"}
        )

    @pytest.mark.asyncio
    async def test_valid_token_validation(self):
        """Test validation of a valid token."""
        jwks = self._create_test_jwks()
        token = self._create_test_token()
        
        with patch.object(self.validator, '_get_jwks', return_value=jwks):
            claims = await self.validator.validate_token(token)
            assert claims["sub"] == "test-user"
            assert claims["aud"] == self.config.audience
            assert claims["iss"] == self.config.issuer_url

    @pytest.mark.asyncio
    async def test_expired_token_validation(self):
        """Test validation of an expired token."""
        jwks = self._create_test_jwks()
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        token = self._create_test_token(exp=int(expired_time.timestamp()))
        
        with patch.object(self.validator, '_get_jwks', return_value=jwks):
            with pytest.raises(TokenValidationError, match="Token has expired"):
                await self.validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_invalid_audience_validation(self):
        """Test validation with invalid audience."""
        jwks = self._create_test_jwks()
        token = self._create_test_token(aud="wrong-audience")
        
        with patch.object(self.validator, '_get_jwks', return_value=jwks):
            with pytest.raises(TokenValidationError, match="Invalid token audience"):
                await self.validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_invalid_issuer_validation(self):
        """Test validation with invalid issuer."""
        jwks = self._create_test_jwks()
        token = self._create_test_token(iss="https://wrong-issuer.com")
        
        with patch.object(self.validator, '_get_jwks', return_value=jwks):
            with pytest.raises(TokenValidationError, match="Invalid token issuer"):
                await self.validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_missing_required_scopes(self):
        """Test validation with missing required scopes."""
        jwks = self._create_test_jwks()
        token = self._create_test_token(scope="wrong:scope")
        
        with patch.object(self.validator, '_get_jwks', return_value=jwks):
            with pytest.raises(TokenValidationError, match="Missing required scopes"):
                await self.validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_token_without_kid(self):
        """Test validation of token without key ID."""
        import jwt
        
        claims = {
            "iss": self.config.issuer_url,
            "aud": self.config.audience,
            "sub": "test-user",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Create token without kid header
        token = jwt.encode(claims, private_pem, algorithm="RS256")
        
        with pytest.raises(TokenValidationError, match="Token missing key ID"):
            await self.validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_jwks_fetch_failure(self):
        """Test handling of JWKS fetch failure."""
        token = self._create_test_token()
        
        with patch.object(self.validator.http_client, 'get', side_effect=Exception("Network error")):
            with pytest.raises(TokenValidationError, match="Failed to fetch JWKS"):
                await self.validator.validate_token(token)

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        self.config.rate_limit_enabled = True
        self.config.rate_limit_requests = 2
        self.config.rate_limit_window = 60
        
        jwks = self._create_test_jwks()
        token = self._create_test_token()
        
        with patch.object(self.validator, '_get_jwks', return_value=jwks):
            # First two requests should succeed
            await self.validator.validate_token(token)
            await self.validator.validate_token(token)
            
            # Third request should be rate limited
            with pytest.raises(TokenValidationError, match="Rate limit exceeded"):
                await self.validator.validate_token(token)

    def test_jwks_caching(self):
        """Test JWKS caching functionality."""
        jwks = self._create_test_jwks()
        
        # Mock HTTP client
        mock_response = Mock()
        mock_response.json.return_value = jwks
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.validator.http_client, 'get', return_value=mock_response) as mock_get:
            # First call should fetch JWKS
            result1 = self.validator._get_jwks()
            assert mock_get.call_count == 1
            
            # Second call should use cache
            result2 = self.validator._get_jwks()
            assert mock_get.call_count == 1  # Still only called once
            
            assert result1 == result2 == jwks


class TestOAuth2Integration:
    """Test OAuth2 integration functions."""

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

    def test_generate_test_token(self):
        """Test test token generation."""
        token = generate_test_token(
            issuer="https://test.example.com",
            audience="test-api",
            subject="test-user",
            scopes=["read:test", "write:test"],
            expires_in=3600
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded (without verification)
        import jwt
        unverified_claims = jwt.decode(token, options={"verify_signature": False})
        assert unverified_claims["iss"] == "https://test.example.com"
        assert unverified_claims["aud"] == "test-api"
        assert unverified_claims["sub"] == "test-user"
        assert unverified_claims["scope"] == "read:test write:test"


class TestOAuth2Decorator:
    """Test OAuth2 decorator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global state
        import m3.auth
        m3.auth._oauth2_config = None
        m3.auth._oauth2_validator = None

    def test_decorator_with_oauth2_disabled(self):
        """Test decorator behavior when OAuth2 is disabled."""
        from m3.auth import require_oauth2
        
        @require_oauth2
        async def test_function():
            return "success"
        
        with patch.dict(os.environ, {}, clear=True):
            init_oauth2()
            
            # Should allow access when OAuth2 is disabled
            result = test_function()
            assert result == "success"

    def test_decorator_with_missing_token(self):
        """Test decorator behavior with missing token."""
        from m3.auth import require_oauth2
        
        @require_oauth2
        async def test_function():
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

    def test_decorator_with_bearer_token(self):
        """Test decorator behavior with Bearer token."""
        from m3.auth import require_oauth2
        
        @require_oauth2
        async def test_function():
            return "success"
        
        env_vars = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
            "M3_OAUTH2_TOKEN": "Bearer test-token",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            init_oauth2()
            
            # Mock the validator to return success
            from m3.auth import _oauth2_validator
            
            async def mock_validate_token(token):
                assert token == "test-token"  # Bearer prefix should be removed
                return {"sub": "test-user", "scope": "read:mimic-data"}
            
            with patch.object(_oauth2_validator, 'validate_token', side_effect=mock_validate_token):
                result = test_function()
                assert result == "success"