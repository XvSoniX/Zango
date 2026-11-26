import os
from dataclasses import dataclass
from typing import List, Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.infrastructure.logging.logger import logger

security_scheme = HTTPBearer(auto_error=False)

@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    roles: List[str]

    def has_role(self, role: str) -> bool:
        # Match both exact ROLE_ADMIN and ADMIN
        return role in self.roles or f"ROLE_{role}" in self.roles

class TokenVerifier:
    def __init__(self):
        self._public_key: Optional[str] = None

    def _load_public_key(self) -> Optional[str]:
        if self._public_key:
            return self._public_key
        
        key_path = settings.JWT_PUBLIC_KEY_PATH
        if os.path.exists(key_path):
            try:
                with open(key_path, "r", encoding="utf-8") as f:
                    self._public_key = f.read()
                logger.info(f"Loaded JWT RSA Public Key from {key_path}")
            except Exception as e:
                logger.error(f"Failed to read public key from {key_path}: {e}")
        else:
            logger.warning(f"JWT public key not found at path: {key_path}. Token verification will fail unless in dev mock.")
        return self._public_key

    def verify_token(self, token: str) -> AuthenticatedUser:
        key = self._load_public_key()
        if not key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security configuration error: Public key not configured."
            )

        try:
            payload = jwt.decode(
                token,
                key,
                algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
                options={"require": ["sub", "exp", "iss", "aud"]}
            )
            user_id = str(payload.get("sub"))
            roles = payload.get("roles", [])
            return AuthenticatedUser(user_id=user_id, roles=roles)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token has expired."
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT presented: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token."
            )

token_verifier = TokenVerifier()

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> AuthenticatedUser:
    """Dependency for authenticated endpoints."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header."
        )
    return token_verifier.verify_token(credentials.credentials)

def require_role(role_name: str):
    """Dependency factory for RBAC (e.g. ROLE_ADMIN)."""
    def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not user.has_role(role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Missing required authority '{role_name}'."
            )
        return user
    return dependency
