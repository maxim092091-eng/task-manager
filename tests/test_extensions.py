import sqlite3
from pathlib import Path

from task_manager.extensions import (
    is_login_blocked,
    record_failed_login_attempt,
    reset_failed_login_attempts,
)

EMAIL = "alice@gmail.com"


def test_limiter_blocks_11st_request(
    client, app, add_user, frezing_current_time
) -> None:
    app.config["THROTTLING_ENABLED"] = True

    for _ in range(10):
        response = client.post(
            "/login",
            data={"email": EMAIL, "password": "alice123"},
        )
        assert response.status_code == 200

    response = client.post(
        "/login",
        data={"email": EMAIL, "password": "alice123"},
    )

    assert response.status_code == 429
    assert response.get_json() == {
        "error": "rate_limit_exceeded",
        "message": "Too many requests. Try again in 300 seconds.",
    }


def test_rate_limiter_returns_throttling_error(
    client, app, add_user, frezing_current_time
) -> None:
    app.config["TESTING"] = False
    app.config["THROTTLING_ENABLED"] = True

    assert (
        client.post(
            "/login",
            data={"email": EMAIL, "password": "alice123"},
        ).status_code
        == 200
    )

    assert client.post(
        "/login",
        data={"email": EMAIL, "password": "alice123"},
    ).get_json() == {
        "error": "throttling_exceed",
        "message": "Too many requests. Try again in 2 seconds.",
    }


def test_reset_failed_login_attempts_clears_blocked_login(app) -> None:
    with app.app_context():
        record_failed_login_attempt(EMAIL)
        reset_failed_login_attempts(EMAIL)
        assert is_login_blocked(EMAIL) is None

    database_path = Path(app.config["DATABASE"])
    try:
        with sqlite3.connect(database_path) as db:
            attempt_count, blocked_until = db.execute(
                """SELECT attempts, blocked_until 
                    FROM login_attempts
                    WHERE email = ?;
                    """,
                (EMAIL,),
            ).fetchone()
    finally:
        db.close()

    assert attempt_count == 0
    assert blocked_until == 0


def test_failed_login_attempts_block_login_after_threshold(
    app, frezing_current_time
) -> None:
    with app.app_context():
        for _ in range(4):
            record_failed_login_attempt(EMAIL)
            assert is_login_blocked(EMAIL) is None

        record_failed_login_attempt(EMAIL)

        assert is_login_blocked(EMAIL) == (
            {
                "error": "login_blocked",
                "message": "Too many attempts. Try again in 60 seconds.",
            },
            429,
        )

    database_path = Path(app.config["DATABASE"])

    try:
        with sqlite3.connect(database_path) as db:
            attempt_count, blocked_until = db.execute(
                """SELECT attempts, blocked_until 
                    FROM login_attempts
                    WHERE email = ?;
                    """,
                (EMAIL,),
            ).fetchone()
    finally:
        db.close()

    assert attempt_count == 5
    assert blocked_until == 1_000 + 60


def test_reset_failed_login_attempts_clears_database_record(app) -> None:
    with app.app_context():
        for _ in range(5):
            record_failed_login_attempt(EMAIL)

        reset_failed_login_attempts(EMAIL)

    with sqlite3.connect(app.config["DATABASE"]) as db:
        attempt_count, blocked_until = db.execute(
            "SELECT attempts, blocked_until FROM login_attempts WHERE email = ?",
            (EMAIL,),
        ).fetchone()

    assert attempt_count == 0
    assert blocked_until == 0
