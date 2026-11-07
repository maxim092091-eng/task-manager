import sqlite3

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """Return the database connection, creating it if necessary."""
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        g.db = db

    return g.db


def close_db(_error: BaseException | None = None) -> None:
    """Close the database connection and remove it from the current context."""
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db() -> None:
    """Create the database tables if they do not already exist."""
    db = get_db()

    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'todo'
                CHECK (status IN ('todo', 'in_progress', 'done')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS rate_limiting (
            id INTEGER PRIMARY KEY,
            rate_limit_key TEXT NOT NULL,
            request_time REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            blocked_until REAL NOT NULL DEFAULT 0
        );
        
        """
    )
    db.commit()
