import os
from datetime import timedelta
from pathlib import Path

from flask import Flask

from task_manager.database import close_db, init_db


def create_app() -> Flask:
    """Create the Flask application, register routes, and initialize the SQLite database."""
    project_root = Path(__file__).resolve().parents[2]
    default_data_path = project_root / "data"

    data_path = Path(os.environ.get("TASK_MANAGER_DATA_PATH", default_data_path))
    data_path.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)

    secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("FLASK_SECRET_KEY environment variable is required")

    app.config["SECRET_KEY"] = secret_key

    jwt_secret_key = os.environ.get("JWT_SECRET_KEY")
    if not jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY environment variable is required")
    if len(jwt_secret_key.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 bytes long")

    app.config["JWT_SECRET_KEY"] = jwt_secret_key

    token_ttl_minutes = int(os.environ.get("JWT_ACCESS_TOKEN_MINUTES", "15"))
    if token_ttl_minutes <= 0:
        raise RuntimeError("JWT_ACCESS_TOKEN_MINUTES must be positive")

    app.config["JWT_ACCESS_TOKEN_TTL"] = timedelta(minutes=token_ttl_minutes)

    app.config["DATABASE"] = str(data_path / "task_manager.sqlite3")

    app.teardown_appcontext(close_db)

    from task_manager.routes import main

    app.register_blueprint(main)

    with app.app_context():
        init_db()

    return app
