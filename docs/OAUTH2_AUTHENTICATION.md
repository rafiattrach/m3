# OAuth2 Authentication for M3

This guide covers the technical details of OAuth2 authentication in M3. For basic setup, see the OAuth2 section in the main README.

## Configuration Reference

### Required Environment Variables

```bash
# Core Configuration
M3_OAUTH2_ENABLED=true
M3_OAUTH2_ISSUER_URL=https://your-auth-provider.com
M3_OAUTH2_AUDIENCE=m3-api
M3_OAUTH2_REQUIRED_SCOPES=read:mimic-data
```

### Optional Environment Variables

```bash
# Advanced Configuration (all optional)
M3_OAUTH2_JWKS_URL=https://your-auth-provider.com/.well-known/jwks.json  # Auto-discovered if not set
M3_OAUTH2_RATE_LIMIT_REQUESTS=100    # Default: 100 requests per hour
M3_OAUTH2_JWKS_CACHE_TTL=3600        # Default: 1 hour
```

## Token Requirements

Your JWT token must include:

1. **Header**:
   - `alg`: RS256 or ES256
   - `kid`: Key ID matching a key in the JWKS

2. **Claims**:
   ```json
   {
     "iss": "https://your-auth-provider.com",    // Must match M3_OAUTH2_ISSUER_URL
     "aud": "m3-api",                           // Must match M3_OAUTH2_AUDIENCE
     "scope": "read:mimic-data",                // Must include all required scopes
     "exp": 1234567890                         // Must not be expired
   }
   ```

## Provider-Specific Setup

### Auth0
```bash
M3_OAUTH2_ISSUER_URL=https://your-domain.auth0.com/
M3_OAUTH2_AUDIENCE=https://api.your-domain.com
```

### Other Providers
Any OAuth2 provider supporting JWT tokens with RS256/ES256 signing will work. Key requirements:
- Must expose JWKS endpoint
- Must support JWT tokens with required claims
- Must allow scope configuration

## Troubleshooting

### Common Error Messages

1. `Missing OAuth2 access token`
   - Set `M3_OAUTH2_TOKEN` environment variable
   - Include "Bearer " prefix (optional)

2. `Invalid token signature`
   - Verify token is signed by configured issuer
   - Check JWKS URL is accessible
   - Ensure token's `kid` matches a key in JWKS

3. `Missing required scopes`
   - Request new token with all required scopes
   - Check scope format matches provider's format (space vs comma-separated)

### Debug Mode

```bash
export M3_OAUTH2_DEBUG=true  # Enables detailed logging
```

## Security Best Practices

1. **Token Management**
   - Use short-lived tokens (< 1 hour)
   - Never store tokens in code or version control
   - Use environment variables or secure secret storage

2. **Rate Limiting**
   - Start conservative (100/hour default)
   - Monitor usage patterns before increasing
   - Consider per-endpoint limits for production

3. **Scope Design**
   - Use granular scopes for different access levels
   - Follow principle of least privilege
   - Document scope requirements clearly
