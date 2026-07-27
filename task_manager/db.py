"""
CareScheduler - 看護管理者タスク管理アプリ
データベースアクセス層 (SQLite)
"""
import sqlite3
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "tasks.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

URGENCY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
URGENCY_LABELS = {"urgent": "緊急", "high": "高", "medium": "中", "low": "低"}
STATUS_LABELS = {"todo": "未着手", "in_progress": "進行中", "done": "完了"}


def get_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def _now():
    return datetime.now().isoformat(timespec="seconds")


def list_tasks(status=None, urgency=None, order_by="urgency"):
    conn = get_db()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if urgency:
        query += " AND urgency = ?"
        params.append(urgency)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    tasks = [dict(r) for r in rows]

    if order_by == "due_date":
        tasks.sort(key=lambda t: (t["due_date"] or "9999-99-99", t["due_time"] or "99:99"))
    else:
        tasks.sort(
            key=lambda t: (
                URGENCY_ORDER.get(t["urgency"], 9),
                t["due_date"] or "9999-99-99",
                t["due_time"] or "99:99",
            )
        )
    return tasks


def get_task(task_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_task(title, description, category, urgency, due_date, due_time, status="todo"):
    conn = get_db()
    now = _now()
    conn.execute(
        """INSERT INTO tasks
           (title, description, category, urgency, status, due_date, due_time, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, description, category, urgency, status, due_date, due_time, now, now),
    )
    conn.commit()
    conn.close()


def update_task(task_id, title, description, category, urgency, due_date, due_time, status):
    conn = get_db()
    conn.execute(
        """UPDATE tasks SET title=?, description=?, category=?, urgency=?,
           due_date=?, due_time=?, status=?, updated_at=? WHERE id=?""",
        (title, description, category, urgency, due_date, due_time, status, _now(), task_id),
    )
    conn.commit()
    conn.close()


def set_task_status(task_id, status):
    conn = get_db()
    conn.execute(
        "UPDATE tasks SET status=?, updated_at=? WHERE id=?", (status, _now(), task_id)
    )
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


def today_str():
    return date.today().isoformat()
