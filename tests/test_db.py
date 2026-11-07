from task_manager.database import get_db


def test_get_db_reuses_connection_in_app_context(app) -> None:
    with app.app_context():
        first_connection = get_db()
        assert get_db() is first_connection
