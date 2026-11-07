from task_manager.routes import get_user_id_from_token
from task_manager.tasks import create_task
from task_manager.tokens import create_access_token, decode_access_token


def test_auth_page(client) -> None:
    response = client.get("/auth")

    assert response.status_code == 200


def test_registration_route(app, client) -> None:
    response = client.post(
        "/register",
        data={"name": "Alice", "email": "alice@gmail.com", "password": "alice123"},
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data is not None
    assert data["token_type"] == "Bearer"

    with app.app_context():
        user_id = decode_access_token(data["access_token"])

    assert user_id > 0


def test_invalid_registration_route(client) -> None:
    response = client.post(
        "/register",
        data={"name": "Alice", "email": "invalid-email", "password": "alice123"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid email address"}


def test_login_route(client, app, add_user) -> None:
    response = client.post(
        "/login",
        data={"email": "alice@gmail.com", "password": "alice123"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data["token_type"] == "Bearer"

    with app.app_context():
        user_id = decode_access_token(data["access_token"])

    assert user_id > 0


def test_invalid_login_route(client, add_user) -> None:
    response = client.post(
        "/login",
        data={"email": "alice@gmail.com", "password": "invalid_password"},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid email or password"}


def test_logout(client) -> None:
    response = client.post("/logout")

    assert response.status_code == 200
    assert response.get_json() == {"message": "Logged out"}


def test_tasks_page(client) -> None:
    response = client.get("/tasks")

    assert response.status_code == 200


def test_get_user_id_from_token_returns_user_id(app) -> None:
    with app.app_context():
        token = create_access_token(123)

    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        assert get_user_id_from_token() == 123


def test_user_tasks_api(app, client) -> None:
    with app.app_context():
        token = create_access_token(1)

    response = client.get(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        query_string={"status": "done", "sort": "title", "order": "desc", "page": 1},
    )

    assert response.status_code == 200
    assert response.get_json() == {"tasks": [], "tasks_count": 0, "tasks_page": 1}


def test_api_tasks_rejects_missing_token(client) -> None:
    response = client.get("/api/tasks")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid or missing token"}


def test_api_create_new_tasks(app, client, add_user) -> None:
    with app.app_context():
        token = create_access_token(1)

    response = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Food", "description": "Milk"},
    )

    assert response.status_code == 201
    assert response.get_json() == {"operation_status": "Task created successfully"}


CREATE_TASK_PARAM = 1, "TITLE", "DESCRIPTION"


def test_api_update_task_context(app, client, add_user) -> None:
    with app.app_context():
        token = create_access_token(1)
        create_task(*CREATE_TASK_PARAM)

    response = client.put(
        "/api/tasks/1/context",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Food", "description": "Oat"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "operation_status": "Task context updated successfully"
    }


def test_api_update_task_status(app, client, add_user) -> None:
    with app.app_context():
        token = create_access_token(1)
        create_task(*CREATE_TASK_PARAM)

    response = client.put(
        "/api/tasks/1/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "done"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "operation_status": "Task status updated successfully"
    }


def test_api_delete_task(app, client, add_user) -> None:
    with app.app_context():
        token = create_access_token(1)
        create_task(*CREATE_TASK_PARAM)

    response = client.delete(
        "/api/tasks/1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
