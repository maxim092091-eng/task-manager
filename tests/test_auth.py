import pytest
from task_manager.auth import login, registration
from task_manager.database import get_db
from task_manager.tokens import decode_access_token


def test_registration_saves_user_and_returns_token(app) -> None:
    with app.app_context():
        token = registration("Alice", "alice@gmail.com", "alice123")
        row = get_db().execute("SELECT id, name, email FROM users;").fetchone()

        assert isinstance(token, str)
        assert token
        assert row is not None
        assert decode_access_token(token) == row["id"]

    assert row["name"] == "Alice"
    assert row["email"] == "alice@gmail.com"


@pytest.mark.parametrize(
    "name, email, password",
    [
        ("", "alice@gmail.com", "alice123"),  # Missing name
        ("Alice", "", "alice123"),  # Missing email
        ("Alice", "alice@gmail.com", ""),  # Missing password
        ("Alice", "alice@gmail.com", "123"),  # Short password
        ("Alice", "invalid-email", "alice123"),  # Invalid email
    ],
)
def test_registration_rejects_invalid_data(name, email, password):
    with pytest.raises(ValueError):
        registration(name, email, password)


def test_unique_email(app) -> None:
    with app.app_context():
        registration("Alice", "alice@gmail.com", "alice123")

        with pytest.raises(ValueError, match="Email is already in use"):
            registration("Alice", "alice@gmail.com", "alice123")


def test_login(app, add_user):
    with app.app_context():
        token = login("alice@gmail.com", "alice123")
        assert decode_access_token(token) == 1


@pytest.mark.parametrize(
    "email, password",
    [
        ("alice@gmail.com", "invalid-password"),
        ("invalid-gmail", "alice123"),
    ],
)
def test_invalid_login(app, email, password, add_user):
    with (
        app.app_context(),
        pytest.raises(ValueError, match="Invalid email or password"),
    ):
        login(email, password)
