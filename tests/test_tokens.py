from task_manager.tokens import create_access_token, decode_access_token


def test_create_access_token(app) -> None:
    with app.app_context():
        token = create_access_token(1)

        assert isinstance(token, str)
        assert token
        assert decode_access_token(token) == 1


def test_decode_access_token(app) -> None:
    with app.app_context():
        assert decode_access_token(create_access_token(1)) == 1
