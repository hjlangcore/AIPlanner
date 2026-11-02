"""Keep smoke tests from writing a SQLite file into the repository.

backend.db.db_handler creates todo_agent.db in the process working directory
as soon as it is imported. Switch to a temp directory before that import.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def isolated_workdir():
    tmp = tempfile.mkdtemp(prefix="aiplanner-pytest-")
    os.chdir(tmp)
    os.environ.setdefault("JWT_SECRET_KEY", "pytest-only-secret-not-for-production")
    os.environ.setdefault("LLM_API_KEY", "pytest-only-not-a-real-key")
    os.environ.setdefault("LLM_BASE_URL", "http://127.0.0.1:9/v1")
    yield tmp
