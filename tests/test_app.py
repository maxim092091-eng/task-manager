import sqlite3
from pathlib import Path

import pytest
from task_manager import create_app
from task_manager.database import get_db


def table_names(database_path: Path) -> set[str]:
    try:
        with sqlite3.connect(database_path) as db:
            rows = db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
            return {row[0] for row in rows}

    finally:
        db.close()


def test_create_app_creates_database_and_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_path = tmp_path / "data"
    monkeypatch.setenv("TASK_MANAGER_DATA_PATH", str(data_path))
    assert not data_path.exists()

    monkeypatch.setenv("FLASK_SECRET_KEY", "test-flask-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-" + "x" * 32)

    app = create_app()

    database_path = Path(app.config["DATABASE"])
    assert database_path.is_file()
    assert {"users", "tasks"} <= table_names(database_path)


def test_create_app_preserves_existing_database_data(app) -> None:
    first_app = create_app()
    database_path = Path(first_app.config["DATABASE"])

    try:
        with sqlite3.connect(database_path) as db:
            db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("alice", "alice@example.com", "test-hash"),
            )

    finally:
        db.close()

    second_app = create_app()

    with second_app.app_context():
        row = (
            get_db()
            .execute(
                "SELECT name FROM users WHERE email = ?",
                ("alice@example.com",),
            )
            .fetchone()
        )

    assert row["name"] == "alice"
    assert {"users", "tasks"} <= table_names(database_path)
