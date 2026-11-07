from flask import request

from .tokens import decode_access_token


def get_user_id_from_token() -> int:
    """Return the user ID from the access token."""
    authorization = request.authorization

    if (
        authorization is None
        or authorization.type.lower() != "bearer"
        or not authorization.token
    ):
        raise ValueError("Bearer token required")

    return decode_access_token(authorization.token)
