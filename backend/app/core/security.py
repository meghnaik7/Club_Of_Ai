import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from typing import Any, Union

from app.core.config import settings

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)
except ImportError:
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        if ":" in hashed_password:
            salt, h = hashed_password.split(":", 1)
            return hmac.compare_digest(hashlib.sha256((salt + plain_password).encode()).hexdigest(), h)
        return plain_password == hashed_password

    def get_password_hash(password: str) -> str:
        salt = os.urandom(8).hex()
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}:{h}"

ALGORITHM = "HS256"

try:
    from jose import jwt, JWTError
except ImportError:
    class JWTError(Exception):
        pass

    class JWTFallback:
        @staticmethod
        def _b64_encode(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

        @staticmethod
        def _b64_decode(data: str) -> bytes:
            pad = 4 - (len(data) % 4)
            if pad != 4:
                data += '=' * pad
            return base64.urlsafe_b64decode(data)

        @classmethod
        def encode(cls, claims: dict, key: str, algorithm: str = "HS256") -> str:
            header = {"alg": algorithm, "typ": "JWT"}
            h_b64 = cls._b64_encode(json.dumps(header).encode('utf-8'))
            clean_claims = {}
            for k, v in claims.items():
                if isinstance(v, datetime):
                    clean_claims[k] = int(v.timestamp())
                else:
                    clean_claims[k] = v
            p_b64 = cls._b64_encode(json.dumps(clean_claims, default=str).encode('utf-8'))
            msg = f"{h_b64}.{p_b64}".encode('utf-8')
            sig = cls._b64_encode(hmac.new(key.encode('utf-8'), msg, hashlib.sha256).digest())
            return f"{h_b64}.{p_b64}.{sig}"

        @classmethod
        def decode(cls, token: str, key: str, algorithms: list = None) -> dict:
            parts = token.split('.')
            if len(parts) != 3:
                raise JWTError("Invalid token format")
            msg = f"{parts[0]}.{parts[1]}".encode('utf-8')
            expected_sig = cls._b64_encode(hmac.new(key.encode('utf-8'), msg, hashlib.sha256).digest())
            if not hmac.compare_digest(parts[2], expected_sig):
                raise JWTError("Signature verification failed")
            try:
                return json.loads(cls._b64_decode(parts[1]).decode('utf-8'))
            except Exception as e:
                raise JWTError(str(e))

    jwt = JWTFallback()


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
