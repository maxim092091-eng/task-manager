import math

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from .auth import login, registration
from .auth_utils import get_user_id_from_token
from .extensions import (
    is_login_blocked,
    rate_limiter,
    record_failed_login_attempt,
    reset_failed_login_attempts,
)
from .tasks import (
    create_task,
    delete_task,
    get_tasks,
    update_task_context,
    update_task_status,
)

main = Blueprint("main", __name__)


@main.get("/")
@rate_limiter()
def index() -> ResponseReturnValue:
    """Display the tasks page or authentication page if the user has no token."""
    try:
        get_user_id_from_token()

    except ValueError:
        return render_template("auth.html")

    return redirect(url_for("main.tasks_page"))


@main.post("/register")
@rate_limiter(limit=10, window=300, throttling=2)
def registration_route() -> ResponseReturnValue:
    """Register a user and redirect based on the result."""
    try:
        token = registration(
            request.form.get("name", ""),
            request.form.get("email", ""),
            request.form.get("password", ""),
        )

    except ValueError as error:
        return jsonify(error=str(error)), 400

    return jsonify(access_token=token, token_type="Bearer"), 201


@main.post("/login")
@rate_limiter(
    limit=10,
    window=300,
    throttling=2,
)
def login_route() -> ResponseReturnValue:
    """Authenticate a user and redirect based on the result."""
    email = request.form.get("email", "").strip().lower()
    blocked_response = is_login_blocked(email)
    if blocked_response is not None:
        return blocked_response

    try:
        token = login(
            email,
            request.form.get("password", ""),
        )

    except ValueError:
        record_failed_login_attempt(email)
        return jsonify(error="Invalid email or password"), 401

    reset_failed_login_attempts(email)

    return jsonify(access_token=token, token_type="Bearer")


@main.post("/logout")
def logout() -> ResponseReturnValue:
    """"""
    return jsonify(message="Logged out"), 200


@main.get("/tasks")
@rate_limiter()
def tasks_page() -> ResponseReturnValue:
    """Display the current user's tasks."""
    return render_template("tasks.html")


@main.get("/api/tasks")
@rate_limiter(key_type="user")
def get_user_tasks() -> ResponseReturnValue:
    """Return the current user's tasks."""
    try:
        user_id = get_user_id_from_token()

    except ValueError:
        return jsonify(error="Invalid or missing token"), 401

    status = request.args.getlist("status", ["todo", "done", "in_progress"])
    sort_by = request.args.get("sort", "created_at")
    sort_order = request.args.get("order", "desc")
    page = request.args.get("page", default=1, type=int)

    tasks_count, rows = get_tasks(status, sort_by, sort_order, page, user_id)

    page_count = max(math.ceil(tasks_count / 10), 1)

    return jsonify(
        tasks=[dict(row) for row in rows],
        tasks_count=tasks_count,
        tasks_page=page_count,
    )


@main.post("/api/tasks")
@rate_limiter(throttling=1, key_type="user")
def create_new_tasks() -> ResponseReturnValue:
    try:
        user_id = get_user_id_from_token()

    except ValueError:
        return jsonify(error="Invalid or missing token"), 401

    data = request.get_json()

    title = data.get("title", "").strip()
    description = data.get("description", "")

    try:
        create_task(user_id, title, description)

    except ValueError as error:
        return jsonify({"error": str(error)}), 422

    return jsonify({"operation_status": "Task created successfully"}), 201


@main.put("/api/tasks/<int:task_id>/context")
@rate_limiter(throttling=1, key_type="user")
def update_task_contexts(task_id: int) -> ResponseReturnValue:
    try:
        user_id = get_user_id_from_token()

    except ValueError:
        return jsonify(error="Invalid or missing token"), 401

    data = request.get_json()

    title = data.get("title").strip()
    description = data.get("description", "")

    try:
        update_task_context(task_id, user_id, title, description)

    except ValueError as error:
        return jsonify({"error": str(error)}), 422

    return jsonify({"operation_status": "Task context updated successfully"}), 200


@main.put("/api/tasks/<int:task_id>/status")
@rate_limiter(throttling=1, key_type="user")
def update_task_statuses(task_id: int) -> ResponseReturnValue:
    try:
        user_id = get_user_id_from_token()

    except ValueError:
        return jsonify(error="Invalid or missing token"), 401

    data = request.get_json()
    status = data.get("status", "todo").strip()

    try:
        update_task_status(task_id, user_id, status)

    except ValueError as error:
        return jsonify({"error": str(error)}), 422

    return jsonify({"operation_status": "Task status updated successfully"}), 200


@main.delete("/api/tasks/<int:task_id>")
@rate_limiter(throttling=1, key_type="user")
def delete_tasks(task_id: int) -> ResponseReturnValue:
    try:
        user_id = get_user_id_from_token()

    except ValueError:
        return jsonify(error="Invalid or missing token"), 401

    delete_task(task_id, user_id)
    return "", 204
