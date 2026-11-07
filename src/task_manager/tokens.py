from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app


def create_access_token(user_id: int) -> str:
    """Create a JWT access token for a user."""
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")

    secret_key = current_app.config.get("JWT_SECRET_KEY")

    lifetime = current_app.config.get(
        "JWT_ACCESS_TOKEN_TTL",
        timedelta(minutes=15),
    )
    issued_at = datetime.now(timezone.utc)

    claims = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": issued_at + lifetime,
    }

    return jwt.encode(claims, secret_key, algorithm="HS256")


def decode_access_token(token: str) -> int:
    secret_key = current_app.config.get("JWT_SECRET_KEY")

    try:
        claims = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )
    except jwt.InvalidTokenError as error:
        raise ValueError("Invalid or expired access token") from error

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.isdecimal():
        raise ValueError("Invalid token subject")

    user_id = int(subject)
    if user_id <= 0:
        raise ValueError("Invalid token subject")

    return user_id
