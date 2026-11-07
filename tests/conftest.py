import sqlite3
from pathlib import Path

import pytest
from flask import Flask
from task_manager import create_app
from werkzeug.security import generate_password_hash


@pytest.fixture
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setenv(
        "TASK_MANAGER_DATA_PATH",
        str(tmp_path / "data"),
    )
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-flask-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-" + "x" * 32)

    app = create_app()
    app.config["TESTING"] = True
    app.config["THROTTLING_ENABLED"] = False

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def add_user(app):
    database_path = Path(app.config["DATABASE"])

    try:
        with sqlite3.connect(database_path) as db:
            db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("alice", "alice@gmail.com", generate_password_hash("alice123")),
            )
    finally:
        db.close()


@pytest.fixture
def frezing_current_time(monkeypatch):
    monkeypatch.setattr("task_manager.extensions.time.time", lambda: 1_000.0)
