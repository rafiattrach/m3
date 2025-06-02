# OAuth2 Authentication for M3 MCP Server

## Overview

The M3 MCP Server now includes robust OAuth2 authentication to secure access to sensitive MIMIC-IV medical data. This implementation follows industry standards for API security and provides flexible configuration options.

## Features

- **JWT Token Validation**: Supports RS256 and ES256 algorithms
- **JWKS Integration**: Automatic key discovery from OAuth2 providers
- **Scope-based Authorization**: Fine-grained access control using OAuth2 scopes
- **Rate Limiting**: Built-in protection against abuse
- **Caching**: Efficient JWKS caching to reduce provider load
- **Multiple Provider Support**: Works with any OAuth2-compliant provider

## Configuration

### Environment Variables

Enable OAuth2 authentication by setting these environment variables:

#### Required Variables
```bash
# Enable OAuth2 authentication
M3_OAUTH2_ENABLED=true

# OAuth2 provider configuration
M3_OAUTH2_ISSUER_URL=https://your-auth-provider.com
M3_OAUTH2_AUDIENCE=m3-api

# Required scopes (comma-separated)
M3_OAUTH2_REQUIRED_SCOPES=read:mimic-data,query:database
```

#### Optional Variables
```bash
# Custom JWKS URL (auto-discovered if not provided)
M3_OAUTH2_JWKS_URL=https://your-auth-provider.com/.well-known/jwks.json

# Client credentials (if needed)
M3_OAUTH2_CLIENT_ID=your-client-id
M3_OAUTH2_CLIENT_SECRET=your-client-secret

# Token validation settings
M3_OAUTH2_VALIDATE_EXP=true          # Validate expiration
M3_OAUTH2_VALIDATE_AUD=true          # Validate audience
M3_OAUTH2_VALIDATE_ISS=true          # Validate issuer

# Rate limiting
M3_OAUTH2_RATE_LIMIT_ENABLED=true
M3_OAUTH2_RATE_LIMIT_REQUESTS=100    # Requests per hour
M3_OAUTH2_RATE_LIMIT_WINDOW=3600     # Time window in seconds

# JWKS caching
M3_OAUTH2_JWKS_CACHE_TTL=3600        # Cache TTL in seconds
```

### Using the Configuration Scripts

#### Automatic Claude Desktop Setup
```bash
# Enable OAuth2 with Claude Desktop setup
m3 config claude --enable-oauth2 \
  --oauth2-issuer https://auth.example.com \
  --oauth2-audience m3-api \
  --oauth2-scopes "read:mimic-data,query:database"
```

#### Dynamic Configuration Generator
```bash
# Interactive OAuth2 setup
m3 config --oauth2-enabled

# Command-line OAuth2 setup
python mcp_client_configs/dynamic_mcp_config.py \
  --oauth2-enabled \
  --oauth2-issuer https://auth.example.com \
  --oauth2-audience m3-api
```

## Usage

### Client Authentication

Clients must provide a valid OAuth2 access token in the `M3_OAUTH2_TOKEN` environment variable:

```bash
# Set the access token (with or without "Bearer " prefix)
export M3_OAUTH2_TOKEN="Bearer your-access-token-here"
# or
export M3_OAUTH2_TOKEN="your-access-token-here"
```

### Token Requirements

Valid tokens must include:

1. **Issuer (`iss`)**: Must match `M3_OAUTH2_ISSUER_URL`
2. **Audience (`aud`)**: Must match `M3_OAUTH2_AUDIENCE`
3. **Scopes**: Must include all required scopes from `M3_OAUTH2_REQUIRED_SCOPES`
4. **Expiration (`exp`)**: Token must not be expired (if validation enabled)
5. **Key ID (`kid`)**: Must be present in token header for JWKS validation

### Example Token Claims
```json
{
  "iss": "https://auth.example.com",
  "aud": "m3-api",
  "sub": "user@example.com",
  "scope": "read:mimic-data query:database",
  "exp": 1234567890,
  "iat": 1234564290,
  "email": "user@example.com"
}
```

## Integration with Popular OAuth2 Providers

### Auth0
```bash
M3_OAUTH2_ISSUER_URL=https://your-domain.auth0.com/
M3_OAUTH2_AUDIENCE=https://api.your-domain.com
M3_OAUTH2_REQUIRED_SCOPES=read:mimic-data
```

### Google Identity Platform
```bash
M3_OAUTH2_ISSUER_URL=https://accounts.google.com
M3_OAUTH2_AUDIENCE=your-client-id.apps.googleusercontent.com
M3_OAUTH2_REQUIRED_SCOPES=openid,email,profile
```

### Microsoft Azure AD
```bash
M3_OAUTH2_ISSUER_URL=https://login.microsoftonline.com/your-tenant-id/v2.0
M3_OAUTH2_AUDIENCE=api://your-api-identifier
M3_OAUTH2_REQUIRED_SCOPES=read:data
```

### Keycloak
```bash
M3_OAUTH2_ISSUER_URL=https://your-keycloak.com/auth/realms/your-realm
M3_OAUTH2_AUDIENCE=m3-api
M3_OAUTH2_REQUIRED_SCOPES=mimic:read
```

## Security Features

### Token Validation
- **Signature Verification**: Uses JWKS to verify token signatures
- **Claims Validation**: Validates issuer, audience, and expiration
- **Scope Authorization**: Ensures tokens have required permissions

### Rate Limiting
- **Per-User Limits**: Based on token subject (`sub` claim)
- **Configurable Windows**: Supports different time windows
- **Automatic Cleanup**: Removes expired rate limit entries

### Error Handling
- **Secure Error Messages**: Doesn't leak sensitive information
- **Audit Logging**: Logs authentication attempts and failures
- **Graceful Degradation**: Falls back to disabled state on configuration errors

## Testing

### Running Tests
```bash
# Run OAuth2-specific tests
pytest tests/test_oauth2_auth.py -v

# Run all tests with OAuth2 integration
pytest tests/test_mcp_server.py -v
```

### Generating Test Tokens
For development and testing, you can generate test tokens:

```python
from m3.auth import generate_test_token

# Generate a test token
token = generate_test_token(
    issuer="https://test.example.com",
    audience="m3-api",
    subject="test-user",
    scopes=["read:mimic-data"],
    expires_in=3600
)
print(f"Test token: {token}")
```

⚠️ **Warning**: Test tokens should only be used in development environments!

## Troubleshooting

### Common Issues

#### 1. Missing Access Token
```
Error: Missing OAuth2 access token
```
**Solution**: Set the `M3_OAUTH2_TOKEN` environment variable with a valid token.

#### 2. Invalid Token Signature
```
Error: OAuth2 authentication failed: Invalid token: Signature verification failed
```
**Solution**: Ensure the token was signed by the configured issuer and the JWKS URL is correct.

#### 3. Missing Required Scopes
```
Error: OAuth2 authentication failed: Missing required scopes: {'read:mimic-data'}
```
**Solution**: Ensure your token includes all required scopes in the `scope` claim.

#### 4. Rate Limit Exceeded
```
Error: OAuth2 authentication failed: Rate limit exceeded
```
**Solution**: Wait for the rate limit window to reset or contact your administrator.

#### 5. JWKS Fetch Failure
```
Error: OAuth2 authentication failed: Failed to fetch JWKS: Connection timeout
```
**Solution**: Check network connectivity to the OAuth2 provider and verify the JWKS URL.

### Debug Mode

Enable debug logging to troubleshoot authentication issues:

```bash
export M3_OAUTH2_DEBUG=true
```

This will log detailed information about token validation, JWKS fetching, and rate limiting.

## Production Deployment

### Security Checklist

- [ ] Use HTTPS for all OAuth2 endpoints
- [ ] Set strong rate limits appropriate for your use case
- [ ] Enable all token validation options in production
- [ ] Use short-lived access tokens (recommend < 1 hour)
- [ ] Implement token refresh mechanisms for long-running clients
- [ ] Monitor authentication logs for suspicious activity
- [ ] Regularly rotate OAuth2 client secrets
- [ ] Use appropriate scopes following principle of least privilege

### Performance Considerations

- **JWKS Caching**: Set appropriate cache TTL (default: 1 hour)
- **Rate Limiting**: Configure limits based on expected usage patterns
- **Token Validation**: Consider disabling expensive validations if not needed
- **Network Timeouts**: Adjust HTTP timeouts for your network conditions

### Monitoring

Monitor these metrics in production:

- Authentication success/failure rates
- Token validation latency
- JWKS fetch frequency and latency
- Rate limit violations per user
- Error distribution by type

## Migration from API Key Authentication

If migrating from a previous API key-based system:

1. **Parallel Running**: Run both systems temporarily
2. **Gradual Migration**: Migrate clients one by one
3. **Monitoring**: Monitor authentication patterns
4. **Rollback Plan**: Keep API key system as backup
5. **Client Updates**: Ensure all clients support OAuth2

## Advanced Configuration

### Custom Token Claims

You can access additional token claims in your MCP tools:

```python
@mcp.tool()
@require_oauth2
def my_tool(param: str, **kwargs) -> str:
    # Access OAuth2 user context
    oauth2_user = kwargs.get('_oauth2_user', {})
    user_email = oauth2_user.get('email')
    user_scopes = oauth2_user.get('scopes', [])

    # Use user context in your logic
    if 'admin:access' in user_scopes:
        # Admin-only functionality
        pass

    return f"Hello {user_email}"
```

### Custom Scope Validation

Implement custom scope validation logic:

```python
def custom_scope_validator(required_scopes, token_scopes):
    # Custom logic for scope validation
    # Return True if access should be granted
    pass
```

## Support

For issues or questions regarding OAuth2 authentication:

1. Check the troubleshooting section above
2. Review the test cases in `tests/test_oauth2_auth.py`
3. Enable debug logging for detailed error information
4. Consult your OAuth2 provider's documentation
5. Open an issue in the project repository

## Security Disclosure

If you discover a security vulnerability in the OAuth2 implementation, please report it responsibly by emailing the maintainers directly rather than opening a public issue.
