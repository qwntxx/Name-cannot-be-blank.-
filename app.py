from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List

from flask import Flask, render_template, request, redirect, url_for, jsonify


BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "todos.json"


app = Flask(__name__)


@dataclass
class Todo:
    id: int
    text: str
    completed: bool = False
    created_at: str = datetime.utcnow().isoformat()
    deleted_at: str | None = None


def load_todos() -> List[Todo]:
    if not DATA_FILE.exists():
        return []
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return [Todo(**item) for item in data]
    except Exception:
        return []


def save_todos(todos: List[Todo]) -> None:
    DATA_FILE.write_text(json.dumps([asdict(t) for t in todos], ensure_ascii=False, indent=2), encoding="utf-8")


def get_next_id(todos: List[Todo]) -> int:
    return (max((t.id for t in todos), default=0) + 1)


def _format_timestamp(iso_str: str | None) -> str | None:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return iso_str


@app.get("/")
def index():
    todos = load_todos()
    current_filter = request.args.get("filter", "all")

    # Derive lists
    active = [t for t in todos if not t.completed and t.deleted_at is None]
    completed = [t for t in todos if t.completed and t.deleted_at is None]
    deleted = [t for t in todos if t.deleted_at is not None]

    if current_filter == "active":
        filtered = active
    elif current_filter == "completed":
        filtered = completed
    elif current_filter == "deleted":
        filtered = deleted
    else:
        filtered = [t for t in todos if t.deleted_at is None]

    # Pre-format timestamps for display
    def view_model(t: Todo) -> dict:
        return {
            **asdict(t),
            "created_at_fmt": _format_timestamp(t.created_at),
            "deleted_at_fmt": _format_timestamp(t.deleted_at),
        }

    filtered_vm = [view_model(t) for t in filtered]

    counts = {
        "active": len(active),
        "completed": len(completed),
        "deleted": len(deleted),
        "all": len([t for t in todos if t.deleted_at is None]),
    }

    return render_template(
        "index.html",
        filtered=filtered_vm,
        counts=counts,
        current_filter=current_filter,
    )


@app.post("/add")
def add():
    todos = load_todos()
    text = (request.form.get("text") or "").strip()
    if text:
        todos.insert(0, Todo(id=get_next_id(todos), text=text))
        save_todos(todos)
    return redirect(url_for("index"))


@app.post("/toggle/<int:todo_id>")
def toggle(todo_id: int):
    todos = load_todos()
    for t in todos:
        if t.id == todo_id and t.deleted_at is None:
            t.completed = not t.completed
            break
    save_todos(todos)
    return redirect(url_for("index"))



@app.post("/delete/<int:todo_id>")
def delete(todo_id: int):
    todos = load_todos()
    for t in todos:
        if t.id == todo_id and t.deleted_at is None:
            t.deleted_at = datetime.utcnow().isoformat()
            break
    save_todos(todos)
    return redirect(url_for("index"))


@app.post("/restore/<int:todo_id>")
def restore(todo_id: int):
    todos = load_todos()
    for t in todos:
        if t.id == todo_id and t.deleted_at is not None:
            t.deleted_at = None
            break
    save_todos(todos)
    return redirect(url_for("index"))


@app.post("/clear/completed")
def clear_completed():
    todos = load_todos()
    todos = [t for t in todos if not t.completed or t.deleted_at is not None]
    save_todos(todos)
    return redirect(url_for("index"))


@app.post("/clear/deleted")
def clear_deleted():
    todos = [t for t in load_todos() if t.deleted_at is None]
    save_todos(todos)
    return redirect(url_for("index"))


@app.get("/api/todos")
def api_list():
    return jsonify([asdict(t) for t in load_todos()])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)





