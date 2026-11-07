import re
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

from task_manager.database import get_db
from task_manager.tokens import create_access_token


def registration(name: str, email: str, password: str) -> str:
    """Register a new user and return a token containing the user ID."""
    name = name.strip()
    email = email.strip().lower()

    if not name:
        raise ValueError("Name is required")

    if not re.fullmatch(r"[a-z0-9._+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}", email):
        raise ValueError("Invalid email address")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    password_hash = generate_password_hash(password)
    db = get_db()

    try:
        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES(?, ?, ?);",
            (name, email, password_hash),
        )
        db.commit()

    except sqlite3.IntegrityError as error:
        if error.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE":
            raise ValueError("Email is already in use")
        raise

    if cursor.lastrowid is None:
        raise RuntimeError("Could not determine the new user's ID")

    return create_access_token(cursor.lastrowid)


def login(email: str, password: str) -> str:
    """Authenticate a user and return a token containing the user ID."""
    db = get_db()
    user = db.execute(
        "SELECT id, password_hash FROM users WHERE email = ?;",
        (email.strip().lower(),),
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        raise ValueError("Invalid email or password")

    return create_access_token(user["id"])
