import sqlite3

from .database import get_db

ALLOWED_STATUSES = ["todo", "in_progress", "done"]


def get_tasks(
    status: list[str], sort_by: str, sort_order: str, page: int, user_id: int
) -> tuple[int, list[sqlite3.Row]]:
    """Return a paginated list of tasks for a user."""
    ALLOWED_SORT_COLUMNS = {"created_at", "title", "status"}
    ALLOWED_SORT_ORDERS = {"asc", "desc"}

    page = max(page, 1)

    if sort_by not in ALLOWED_SORT_COLUMNS:
        sort_by = "created_at"

    if sort_order not in ALLOWED_SORT_ORDERS:
        sort_order = "desc"

    if not status:
        status = ALLOWED_STATUSES

    placeholders = ", ".join("?" for _ in status)
    offset = (page - 1) * 10

    db = get_db()

    total_tasks = db.execute(
        f"""
        SELECT COUNT(*)
        FROM tasks
        WHERE user_id = ? AND status IN ({placeholders}) 
        """,
        (user_id, *status),
    ).fetchone()[0]

    tasks = db.execute(
        f"""
        SELECT title, description, status, created_at
        FROM tasks
        WHERE user_id = ? AND status IN ({placeholders}) 
        ORDER BY {sort_by} {sort_order}, id ASC
        LIMIT 10 OFFSET ?;
        """,
        (user_id, *status, offset),
    ).fetchall()

    return (total_tasks, tasks)


def create_task(
    user_id: int,
    title: str,
    description: str = "",
) -> None:
    """Create a task in the database."""
    validate_task_params(title, description)

    db = get_db()

    db.execute(
        """
        INSERT INTO tasks (user_id, title, description, status) VALUES(?, ?, ?, ?);
        """,
        (
            user_id,
            title,
            description,
            "todo",
        ),
    )
    db.commit()


def update_task_context(
    task_id: int,
    user_id: int,
    title: str,
    description: str,
) -> None:
    """Update an existing task in the database."""
    validate_task_params(title, description)

    db = get_db()

    db.execute(
        """
        UPDATE tasks 
        SET 
            title = ?, 
            description = ?
        WHERE id = ? AND user_id = ?;
        """,
        (
            title,
            description,
            task_id,
            user_id,
        ),
    )
    db.commit()


def update_task_status(
    task_id: int,
    user_id: int,
    status: str,
) -> None:
    """Update an existing task status in the database."""
    if not isinstance(status, str):
        raise TypeError("Status must be a string")

    if status not in ALLOWED_STATUSES:
        raise ValueError("Invalid status")

    db = get_db()

    db.execute(
        """
        UPDATE tasks 
        SET status = ? 
        WHERE id = ? AND user_id = ?;
        """,
        (
            status,
            task_id,
            user_id,
        ),
    )
    db.commit()


def delete_task(task_id: int, user_id: int) -> None:
    """Delete a task from the database."""
    db = get_db()

    db.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?;",
        (
            task_id,
            user_id,
        ),
    )
    db.commit()


def validate_task_params(
    title: str,
    description: str,
) -> None:
    """Validate the task parameters."""
    if not isinstance(title, str):
        raise TypeError("Title must be a string")

    if not title.strip():
        raise ValueError("Title cannot be empty")

    if not isinstance(description, str):
        raise TypeError("Description must be a string")
