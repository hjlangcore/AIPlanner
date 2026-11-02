"""Smoke tests for task storage, passwords, and the manual task API.

These tests do not call a language model.
"""
import jwt
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client


def test_task_round_trip_and_default_categories():
    from backend.db.db_handler import TodoDatabase

    database = TodoDatabase("smoke_tasks.db")
    try:
        task_id = database.save_task(
            raw_task="Write the weekly report",
            sub_tasks=["Outline", "Draft"],
            priority="高",
            deadline="2026-12-01",
            schedule="",
            category="工作",
            tags=["portfolio"],
        )
        row = database.get_task_by_id(task_id)
        assert row is not None
        assert row[1] == "Write the weekly report"
        assert row[3] == "高"
        assert row[6] == "待执行"

        high_priority = database.get_all_tasks(priority="高")
        assert any(item[0] == task_id for item in high_priority)

        assert database.update_task_status(task_id, "已完成") is True
        database.cursor.execute(
            "SELECT status, progress FROM tasks WHERE id = ?",
            (task_id,),
        )
        status, progress = database.cursor.fetchone()
        assert status == "已完成"
        assert progress == 100

        assert database.delete_task(task_id) is True
        assert database.get_task_by_id(task_id) is None

        names = {category[1] for category in database.get_categories()}
        assert {"工作", "学习", "生活", "健康", "默认"} <= names
    finally:
        database.conn.close()


def test_password_hash_and_access_token_round_trip():
    from backend.service.auth_service import (
        ALGORITHM,
        SECRET_KEY,
        create_access_token,
        get_password_hash,
        verify_password,
    )

    hashed = get_password_hash("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrongpass", hashed) is False

    token = create_access_token({"sub": "smokeuser", "user_id": 1})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "smokeuser"
    assert payload["user_id"] == 1


def test_health_register_login_and_manual_task(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    registered = client.post(
        "/api/auth/register",
        json={
            "username": "smokeuser",
            "password": "secret123",
            "full_name": "Smoke User",
        },
    )
    assert registered.status_code == 200
    assert registered.json()["success"] is True

    duplicate = client.post(
        "/api/auth/register",
        json={"username": "smokeuser", "password": "secret123"},
    )
    assert duplicate.status_code == 400

    rejected = client.post(
        "/api/auth/login",
        json={"username": "smokeuser", "password": "nope"},
    )
    assert rejected.status_code == 401

    logged_in = client.post(
        "/api/auth/login",
        json={"username": "smokeuser", "password": "secret123"},
    )
    assert logged_in.status_code == 200
    body = logged_in.json()
    assert body["user"]["username"] == "smokeuser"

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "smokeuser"

    created = client.post(
        "/api/tasks/manual",
        json={
            "raw_task": "Ship the portfolio README",
            "priority": "中",
            "deadline": "2026-12-15",
            "category": "工作",
            "sub_tasks": ["Draft", "Review"],
        },
    )
    assert created.status_code == 200
    created_body = created.json()
    assert created_body["success"] is True

    listing = client.get("/api/tasks")
    assert listing.status_code == 200
    assert created_body["task_id"] in [item["id"] for item in listing.json()]
