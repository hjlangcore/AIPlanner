"""Tests for TodoDatabase.update_task partial updates.

Imports stay inside fixtures so todo_agent.db is created only after the
session fixture has switched to a temporary working directory.
"""
import json

import pytest


@pytest.fixture
def database():
    from backend.db.db_handler import TodoDatabase

    db = TodoDatabase("update_task_tests.db")
    try:
        yield db
    finally:
        db.conn.close()


def _insert_task(database):
    return database.save_task(
        raw_task="Write the weekly report",
        sub_tasks=["Outline", "Draft"],
        priority="高",
        deadline="2026-12-01",
        schedule="morning",
        category="工作",
        tags=["portfolio"],
    )


def _task_row(database, task_id):
    database.cursor.execute("PRAGMA table_info(tasks)")
    columns = [row[1] for row in database.cursor.fetchall()]
    database.cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = database.cursor.fetchone()
    if row is None:
        return None
    return dict(zip(columns, row))


def test_allowed_task_columns_match_tasks_schema(database):
    from backend.db.db_handler import (
        _TASK_COLUMNS_NOT_UPDATED_BY_UPDATE_TASK,
        _TASK_TABLE_COLUMNS,
        allowed_task_columns,
    )

    database.cursor.execute("PRAGMA table_info(tasks)")
    live_columns = [row[1] for row in database.cursor.fetchall()]
    assert tuple(live_columns) == _TASK_TABLE_COLUMNS
    assert allowed_task_columns == (
        frozenset(live_columns) - _TASK_COLUMNS_NOT_UPDATED_BY_UPDATE_TASK
    )
    assert allowed_task_columns.isdisjoint(_TASK_COLUMNS_NOT_UPDATED_BY_UPDATE_TASK)


def test_update_one_field_leaves_the_rest_unchanged(database):
    task_id = _insert_task(database)
    before = _task_row(database, task_id)

    assert database.update_task(task_id, notes="Bring the figures") is True

    after = _task_row(database, task_id)
    assert after["notes"] == "Bring the figures"
    assert after["update_time"]
    for column in before:
        if column in ("notes", "update_time"):
            continue
        assert after[column] == before[column]


def test_update_several_fields(database):
    task_id = _insert_task(database)
    before = _task_row(database, task_id)
    new_sub_tasks = ["Collect numbers", "Draft", "Send"]
    new_tags = ["portfolio", "q4"]

    assert database.update_task(
        task_id,
        priority="低",
        deadline="2026-12-15",
        category="学习",
        tags=new_tags,
        sub_tasks=new_sub_tasks,
    ) is True

    after = _task_row(database, task_id)
    assert after["priority"] == "低"
    assert after["deadline"] == "2026-12-15"
    assert after["category"] == "学习"
    assert json.loads(after["tags"]) == new_tags
    assert json.loads(after["sub_tasks"]) == new_sub_tasks
    assert after["raw_task"] == before["raw_task"]
    assert after["schedule"] == before["schedule"]
    assert after["status"] == before["status"]
    assert after["progress"] == before["progress"]
    assert after["notes"] == before["notes"]
    assert after["create_time"] == before["create_time"]
    assert after["update_time"]


def test_unknown_field_is_rejected_and_row_is_unchanged(database):
    task_id = _insert_task(database)
    before = _task_row(database, task_id)

    with pytest.raises(ValueError, match="Invalid column name: not_a_column"):
        database.update_task(task_id, notes="should not be saved", not_a_column="x")

    assert _task_row(database, task_id) == before

    with pytest.raises(ValueError, match="Invalid column name: status"):
        database.update_task(task_id, status="已完成")

    with pytest.raises(ValueError, match="Invalid column name"):
        database.update_task(task_id, **{"priority = '高'; DROP TABLE tasks; --": "x"})

    assert _task_row(database, task_id) == before
    database.cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'tasks'"
    )
    assert database.cursor.fetchone() is not None


def test_update_nonexistent_task_returns_false(database):
    missing_id = 999999
    assert database.update_task(missing_id, notes="nobody") is False
    assert _task_row(database, missing_id) is None


def test_api_update_task_applies_partial_fields_and_drops_unknown_json():
    """The PUT route only forwards TaskUpdate fields.

    The edit client also sends status. That key is not on TaskUpdate, so the
    route must keep ignoring it and must not raise while updating notes.
    """
    from fastapi.testclient import TestClient

    from backend.db.db_handler import db
    from backend.main import app

    with TestClient(app) as client:
        created = client.post(
            "/api/tasks/manual",
            json={
                "raw_task": "Route partial update",
                "priority": "中",
                "deadline": "2026-12-20",
                "category": "工作",
                "sub_tasks": ["Draft"],
            },
        )
        assert created.status_code == 200
        task_id = created.json()["task_id"]

        updated = client.put(
            f"/api/tasks/{task_id}",
            json={
                "notes": "from the route",
                "status": "已完成",
                "not_a_column": "ignored by the request model",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["success"] is True

        missing = client.put(
            "/api/tasks/999999",
            json={"notes": "missing"},
        )
        assert missing.status_code == 200
        assert missing.json()["success"] is False

    row = _task_row(db, task_id)
    assert row["notes"] == "from the route"
    assert row["raw_task"] == "Route partial update"
    assert row["status"] == "待执行"
    assert row["priority"] == "中"
