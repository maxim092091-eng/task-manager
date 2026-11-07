import time
from functools import wraps

from flask import current_app, request

from .auth_utils import get_user_id_from_token
from .database import get_db


def rate_limiter(
    limit: int = 60, window: int = 60, throttling: int = 0, key_type: str = "ip"
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.endpoint == "static":
                return func(*args, **kwargs)

            if not current_app.config.get("THROTTLING_ENABLED", True):
                return func(*args, **kwargs)

            if key_type == "ip":
                rate_limit_key = request.remote_addr

            elif key_type == "user":
                try:
                    rate_limit_key = get_user_id_from_token()
                except ValueError:
                    return {"error": "Invalid or missing token"}, 401

            else:
                raise ValueError("key_type must be 'ip' or 'user'")

            db = get_db()

            try:
                db.execute("BEGIN IMMEDIATE")

                current_time = time.time()

                db.execute(
                    "DELETE FROM rate_limiting WHERE request_time < ?;",
                    (current_time - window,),
                )

                count_user_request, last_request_time, oldest_request_time = db.execute(
                    """
                    SELECT COUNT(*), MAX(request_time), MIN(request_time)  
                    FROM rate_limiting 
                    WHERE rate_limit_key = ?;
                    """,
                    (rate_limit_key,),
                ).fetchone()

                if count_user_request >= limit:
                    db.rollback()

                    retry_after = max(oldest_request_time + window - current_time, 0)
                    retry_after_text = str(round(retry_after))

                    return {
                        "error": "rate_limit_exceeded",
                        "message": (
                            f"Too many requests. Try again in "
                            f"{retry_after_text} seconds."
                        ),
                    }, 429

                if last_request_time is not None:
                    delay = throttling - (current_time - last_request_time)

                    if delay > 0 and not current_app.testing:
                        db.rollback()
                        delay_text = str(round(delay))
                        return {
                            "error": "throttling_exceed",
                            "message": (
                                f"Too many requests. Try again in {delay_text} seconds."
                            ),
                        }, 429

                db.execute(
                    "INSERT INTO rate_limiting (rate_limit_key, request_time) VALUES (?, ?);",
                    (rate_limit_key, current_time),
                )

                db.commit()

            except Exception:
                db.rollback()
                raise

            return func(*args, **kwargs)

        return wrapper

    return decorator


def is_login_blocked(email: str) -> tuple[dict, int] | None:
    """Return a 429 response if the email is temporarily blocked."""
    db = get_db()
    email = email.strip().lower()

    row = db.execute(
        "SELECT blocked_until FROM login_attempts WHERE email = ?;",
        (email,),
    ).fetchone()

    if row is not None:
        remaining = row["blocked_until"] - time.time()
        if remaining > 0:
            remaining_text = str(round(remaining))
            return {
                "error": "login_blocked",
                "message": f"Too many attempts. Try again in {remaining_text} seconds.",
            }, 429


def record_failed_login_attempt(email: str) -> None:
    """Record a failed login attempt."""
    db = get_db()
    email = email.lower().strip()

    try:
        db.execute("BEGIN IMMEDIATE")

        attempt = db.execute(
            """
            SELECT attempts
            FROM login_attempts 
            WHERE email = ?;
            """,
            (email,),
        ).fetchone()

        if attempt is None:
            attempt_count = 1
            db.execute(
                "INSERT INTO login_attempts (email, attempts) VALUES (?, ?);",
                (email, attempt_count),
            )
        else:
            attempt_count = attempt["attempts"] + 1
            db.execute(
                "UPDATE login_attempts SET attempts = ? WHERE email = ?;",
                (attempt_count, email),
            )

        LOGIN_LOCKOUT_LEVELS = (
            (5, 60),
            (10, 300),
            (15, 900),
            (20, 1800),
            (25, 3600),
            (30, 10800),
        )

        current_time = time.time()

        query_update_blocked_until = """
                                    UPDATE login_attempts
                                    SET blocked_until = ?
                                    WHERE email = ?;
                                    """

        for failed_attempts, lockout_duration in LOGIN_LOCKOUT_LEVELS:
            if attempt_count == failed_attempts:
                db.execute(
                    query_update_blocked_until,
                    (current_time + lockout_duration, email),
                )

        if attempt_count >= 30 and (attempt_count - 30) % 5 == 0:
            db.execute(
                query_update_blocked_until,
                (current_time + 10800, email),
            )

        db.commit()

    except Exception:
        db.rollback()
        raise


def reset_failed_login_attempts(email: str) -> None:
    """Reset failed login attempts after a successful login."""
    db = get_db()
    db.execute(
        """
        UPDATE login_attempts
        SET attempts = 0, blocked_until = 0
        WHERE email = ?;
        """,
        (email.strip().lower(),),
    )
    db.commit()
