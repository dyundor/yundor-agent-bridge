import os
import json
import uuid
from datetime import datetime


RUNTIME_DIR = "tasks/runtime"


def _ensure_dir():
    os.makedirs(RUNTIME_DIR, exist_ok=True)


def create_task(project, task):
    _ensure_dir()

    task_id = str(uuid.uuid4())[:8]

    now = datetime.now().isoformat()

    record = {
        "id": task_id,
        "project": project,
        "task": task,
        "status": "pending",
        "result": "",
        "created_at": now,
        "updated_at": now,
    }

    filepath = os.path.join(RUNTIME_DIR, f"{task_id}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return task_id


def update_task(task_id, status, result):
    filepath = os.path.join(RUNTIME_DIR, f"{task_id}.json")

    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        record = json.load(f)

    record["status"] = status
    record["result"] = result
    record["updated_at"] = datetime.now().isoformat()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return record


def get_task(task_id):
    filepath = os.path.join(RUNTIME_DIR, f"{task_id}.json")

    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_tasks():
    _ensure_dir()

    tasks = []

    for filename in sorted(os.listdir(RUNTIME_DIR)):
        if filename.endswith(".json"):
            filepath = os.path.join(RUNTIME_DIR, filename)

            with open(filepath, "r", encoding="utf-8") as f:
                tasks.append(json.load(f))

    return tasks


def get_pending_tasks():
    return [t for t in list_tasks() if t.get("status") == "pending"]


def get_running_tasks():
    return [t for t in list_tasks() if t.get("status") == "running"]


def get_failed_tasks():
    return [t for t in list_tasks() if t.get("status") == "failed"]
