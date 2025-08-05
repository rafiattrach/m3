import asyncio
import logging
import time
from collections.abc import Callable
from functools import wraps
from urllib.parse import urljoin

import httpx
import jwt
from beartype import beartype
from beartype.typing import Any, Dict, List, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from m3.core.config import M3Config
from m3.core.utils.exceptions import M3ValidationError

logger = logging.getLogger(__name__)


@beartype
class Auth:
    def __init__(self, config: M3Config) -> None:
        self.config = config
        self._set_enabled()
        if not self.enabled:
            return
        self._set_issuer_and_audience()
        self._set_required_scopes()
        self._set_jwks_url()
        self._set_cache()
        self._set_http_client()
        self._set_rate_limit()
        self._set_validation_flags()
        logger.info(f"OAuth2 enabled: {self.enabled}, issuer: {self.issuer_url}")

    async def authenticate(self, token: str) -> Dict[str, Any]:
        jwks = await self._get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise M3ValidationError("Token missing key ID (kid)")
        key = self._find_key(jwks, kid)
        if not key:
            raise M3ValidationError(f"No key found for kid: {kid}")
        public_key = self._jwk_to_pem(key)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256", "ES256"],
            audience=self.audience,
            issuer=self.issuer_url,
        )
        self._validate_scopes(payload)
        if self.rate_limit_enabled:
            self._check_rate_limit(payload)
        return payload

    @staticmethod
    def generate_test_token(
        issuer: str = "https://test-issuer.example.com",
        audience: str = "m3-api",
        subject: str = "test-user",
        scopes: Optional[List[str]] = None,
        expires_in: int = 3600,
    ) -> str:
        from datetime import datetime, timedelta, timezone

        scopes = scopes or ["read:mimic-data"]
        now = datetime.now(timezone.utc)
        claims = {
            "iss": issuer,
            "aud": audience,
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
            "scope": " ".join(scopes),
        }
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return jwt.encode(claims, private_pem, algorithm="RS256")

    def decorator(self, func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self.enabled:
                return (
                    await func(*args, **kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(*args, **kwargs)
                )
            token = self.config.get_env_var("M3_OAUTH2_TOKEN", "")
            if token.startswith("Bearer "):
                token = token[7:]
            if not token:
                raise M3ValidationError("Missing OAuth2 access token")
            await self.authenticate(token)
            return (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )

        return wrapper

    async def _get_jwks(self) -> Dict[str, Any]:
        current_time = time.time()
        if (
            self._jwks_cache
            and current_time - self._jwks_cache_time < self.jwks_cache_ttl
        ):
            return self._jwks_cache
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            jwks = response.json()
        self._jwks_cache = jwks
        self._jwks_cache_time = current_time
        return jwks

    def _find_key(self, jwks: Dict[str, Any], kid: str) -> Optional[Dict[str, Any]]:
        keys = jwks.get("keys", [])
        for key in keys:
            if key.get("kid") == kid:
                return key
        return None

    def _jwk_to_pem(self, jwk: Dict[str, Any]) -> bytes:
        from jose.utils import base64url_decode

        if jwk.get("kty") == "RSA":
            n = base64url_decode(jwk["n"])
            e = base64url_decode(jwk["e"])
            public_numbers = rsa.RSAPublicNumbers(
                int.from_bytes(e, byteorder="big"),
                int.from_bytes(n, byteorder="big"),
            )
            public_key = public_numbers.public_key()
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            return pem
        raise M3ValidationError(f"Unsupported key type: {jwk.get('kty')}")

    def _validate_scopes(self, payload: Dict[str, Any]) -> None:
        token_scopes = set()
        scope_claim = payload.get("scope", "")
        if isinstance(scope_claim, str):
            token_scopes = set(scope_claim.split())
        elif isinstance(scope_claim, list):
            token_scopes = set(scope_claim)
        scp_claim = payload.get("scp", [])
        if isinstance(scp_claim, list):
            token_scopes.update(scp_claim)
        missing_scopes = self.required_scopes - token_scopes
        if missing_scopes:
            raise M3ValidationError(f"Missing required scopes: {missing_scopes}")

    def _check_rate_limit(self, payload: Dict[str, Any]) -> None:
        user_id = payload.get("sub", "unknown")
        current_time = time.time()
        window_start = current_time - self.rate_limit_window
        user_requests = self._rate_limit_cache.get(user_id, [])
        user_requests = [t for t in user_requests if t > window_start]
        if len(user_requests) >= self.rate_limit_requests:
            raise M3ValidationError("Rate limit exceeded")
        user_requests.append(current_time)
        self._rate_limit_cache[user_id] = user_requests

    def _set_enabled(self) -> None:
        self.enabled = (
            self.config.get_env_var("M3_OAUTH2_ENABLED", "false").lower() == "true"
        )

    def _set_issuer_and_audience(self) -> None:
        self.issuer_url = self.config.get_env_var(
            "M3_OAUTH2_ISSUER_URL", raise_if_missing=True
        )
        self.audience = self.config.get_env_var(
            "M3_OAUTH2_AUDIENCE", raise_if_missing=True
        )

    def _set_required_scopes(self) -> None:
        self.required_scopes = {
            scope.strip()
            for scope in self.config.get_env_var(
                "M3_OAUTH2_REQUIRED_SCOPES", "read:mimic-data"
            ).split(",")
        }

    def _set_jwks_url(self) -> None:
        self.jwks_url = self.config.get_env_var("M3_OAUTH2_JWKS_URL") or urljoin(
            self.issuer_url.rstrip("/"), "/.well-known/jwks.json"
        )

    def _set_cache(self) -> None:
        self.jwks_cache_ttl = 3600
        self._jwks_cache = {}
        self._jwks_cache_time = 0

    def _set_http_client(self) -> None:
        self.http_client = httpx.Client(timeout=30.0)

    def _set_rate_limit(self) -> None:
        self.rate_limit_enabled = True
        self.rate_limit_requests = 100
        self.rate_limit_window = 3600
        self._rate_limit_cache = {}

    def _set_validation_flags(self) -> None:
        self.validate_exp = (
            self.config.get_env_var("M3_OAUTH2_VALIDATE_EXP", "true").lower() == "true"
        )
        self.validate_aud = (
            self.config.get_env_var("M3_OAUTH2_VALIDATE_AUD", "true").lower() == "true"
        )
        self.validate_iss = (
            self.config.get_env_var("M3_OAUTH2_VALIDATE_ISS", "true").lower() == "true"
        )
