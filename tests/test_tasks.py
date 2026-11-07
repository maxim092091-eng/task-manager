import sqlite3
from pathlib import Path

import pytest
from task_manager.tasks import (
    create_task,
    delete_task,
    get_tasks,
    update_task_context,
    update_task_status,
    validate_task_params,
)


def test_get_tasks(app) -> None:
    database_path = Path(app.config["DATABASE"])

    try:
        with sqlite3.connect(database_path) as db:
            db.executemany(
                "INSERT INTO tasks (user_id, title, description, status) VALUES (?, ?, ?, ?);",
                [
                    (1, "Eat", "Buy milk", "in_progress"),
                    (1, "Eat", "Buy oat", "done"),
                    (2, "Hunger", "Buy meat", "in_progress"),
                    (2, "Hunger", "Buy chesse", "todo"),
                ],
            )
    finally:
        db.close()

    with app.app_context():
        tasks = get_tasks(("done", "in_progress"), "created_at", "desc", 1, 1)

    assert tasks[0] == 2

    task_in_progress = tasks[1][0]
    assert task_in_progress["title"] == "Eat"
    assert task_in_progress["status"] == "in_progress"
    assert task_in_progress["description"] == "Buy milk"
    assert task_in_progress["created_at"] is not None

    tasl_done = tasks[1][1]
    assert tasl_done["title"] == "Eat"
    assert tasl_done["status"] == "done"
    assert tasl_done["description"] == "Buy oat"
    assert tasl_done["created_at"] is not None


PARAM_FOR_CREATING_TASK = (
    1,
    "Alisa's Birthday",
    "I need to buy a gift",
)


def test_create_task(app, add_user) -> None:
    with app.app_context():
        create_task(*PARAM_FOR_CREATING_TASK)

    database_path = Path(app.config["DATABASE"])
    try:
        with sqlite3.connect(database_path) as db:
            user_id, title, description, status, created_at = db.execute(
                """SELECT user_id, title, description, status, created_at
                    FROM tasks
                    WHERE id = ?;
                    """,
                (1,),
            ).fetchone()
    finally:
        db.close()

    assert user_id == 1
    assert title == "Alisa's Birthday"
    assert description == "I need to buy a gift"
    assert status == "todo"
    assert created_at is not None


def test_update_task(app, add_user) -> None:
    with app.app_context():
        create_task(*PARAM_FOR_CREATING_TASK)
        update_task_context(1, 1, "Something", "I need to buy a gift and some cookies")
        update_task_status(1, 1, "done")

    database_path = Path(app.config["DATABASE"])
    try:
        with sqlite3.connect(database_path) as db:
            title, description, status = db.execute(
                """SELECT title, description, status
                    FROM tasks
                    WHERE id = ?;
                    """,
                (1,),
            ).fetchone()
    finally:
        db.close()

    assert title == "Something"
    assert description == "I need to buy a gift and some cookies"
    assert status == "done"


def test_delete_task(app, add_user) -> None:
    with app.app_context():
        create_task(*PARAM_FOR_CREATING_TASK)
        delete_task(1, 1)

    database_path = Path(app.config["DATABASE"])
    try:
        with sqlite3.connect(database_path) as db:
            task = db.execute(
                """SELECT *
                    FROM tasks
                    WHERE id = ?;
                    """,
                (1,),
            ).fetchone()
    finally:
        db.close()

    assert task is None


@pytest.mark.parametrize(
    "title, description",
    [
        (
            1234,
            "I need to buy a gift",
        ),
        (
            "",
            "I need to buy a gift",
        ),
        (
            "Alisa's Birthday",
            1234,
        ),
    ],
)
def test_validate_task_params(title, description) -> None:
    with pytest.raises((ValueError, TypeError)):
        validate_task_params(title, description)
