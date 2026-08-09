import os
import json
from datetime import date, datetime

from memory_manager import get_memory as _v02_get_memory
from memory_writer import append_changelog as _v02_append_changelog


MEMORY_FILES = {
    "project_state": "PROJECT_STATE.md",
    "task_history": "TASK_HISTORY.md",
    "failed_tasks": "FAILED_TASKS.md",
    "decisions": "DECISIONS.md",
}


def _memory_dir(project_path: str) -> str:
    project_name = os.path.basename(project_path)
    return os.path.join("memory", project_name)


def _ensure_dir(dir_path: str) -> None:
    os.makedirs(dir_path, exist_ok=True)


def _read_file(filepath: str) -> str:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _write_file(filepath: str, content: str) -> None:
    _ensure_dir(os.path.dirname(filepath))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _append_file(filepath: str, content: str) -> None:
    _ensure_dir(os.path.dirname(filepath))
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(content)


# ---- v0.2 compatibility wrappers ----

def load_context(project_path: str) -> dict:
    """Load all memory context using v0.2 manager."""
    return _v02_get_memory(project_path)


def append_to_changelog(project_path: str, content: str) -> str:
    """Append entry to CHANGELOG.md using v0.2 writer."""
    return _v02_append_changelog(project_path, content)


# ---- Project State ----

def get_project_state(project_path: str) -> str:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["project_state"])
    return _read_file(filepath)


def save_project_state(project_path: str, content: str) -> None:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["project_state"])
    _write_file(filepath, content)


def update_project_state(project_path: str, section: str, value: str) -> None:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["project_state"])
    current = _read_file(filepath)
    marker = f"## {section}"
    new_block = f"{marker}\n\n{value}\n"
    if marker in current:
        lines = current.split("\n")
        start = next((i for i, line in enumerate(lines) if line.strip() == marker), -1)
        if start >= 0:
            end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
            lines[start:end] = [l for l in new_block.split("\n") if l or (lines[start:end] and any(ll.strip() for ll in lines[start:end]))]
            _write_file(filepath, "\n".join(lines))
    else:
        if current and not current.endswith("\n"):
            current += "\n"
        _write_file(filepath, current + "\n" + new_block)


# ---- Task History ----

def get_task_history(project_path: str) -> str:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["task_history"])
    return _read_file(filepath)


def record_task(project_path: str, task_id: str, objective: str, status: str,
                commit_hash: str = "", tests_result: str = "", notes: str = "") -> None:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["task_history"])
    now = datetime.now().isoformat()
    entry = f"\n## {now}\n\n"
    entry += f"- **Task ID**: {task_id}\n"
    entry += f"- **Objective**: {objective}\n"
    entry += f"- **Status**: {status}\n"
    if commit_hash:
        entry += f"- **Commit**: {commit_hash}\n"
    if tests_result:
        entry += f"- **Tests**: {tests_result}\n"
    if notes:
        entry += f"- **Notes**: {notes}\n"
    _append_file(filepath, entry)


# ---- Failed Tasks ----

def get_failed_tasks(project_path: str) -> str:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["failed_tasks"])
    return _read_file(filepath)


def record_failure(project_path: str, task_id: str, objective: str, error: str,
                   attempt: int = 1) -> None:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["failed_tasks"])
    now = datetime.now().isoformat()
    entry = f"\n## {now} (Attempt {attempt})\n\n"
    entry += f"- **Task ID**: {task_id}\n"
    entry += f"- **Objective**: {objective}\n"
    entry += f"- **Error**: {error}\n"
    _append_file(filepath, entry)


def count_consecutive_failures(project_path: str) -> int:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["failed_tasks"])
    content = _read_file(filepath)
    if not content:
        return 0
    entries = content.split("## ")
    count = 0
    for entry in reversed(entries):
        if not entry.strip():
            continue
        header_line = entry.split("\n")[0].strip()
        if "(" in header_line:
            attempt_part = header_line.rsplit("(", 1)[-1].rstrip(")")
            count += 1
    return count


def clear_failures(project_path: str) -> None:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["failed_tasks"])
    _write_file(filepath, "")


# ---- Decisions ----

def get_decisions(project_path: str) -> str:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["decisions"])
    return _read_file(filepath)


def record_decision(project_path: str, title: str, description: str, rationale: str = "") -> None:
    filepath = os.path.join(_memory_dir(project_path), MEMORY_FILES["decisions"])
    now = date.today().isoformat()
    entry = f"\n## {now}: {title}\n\n"
    entry += f"{description}\n"
    if rationale:
        entry += f"\n**Rationale**: {rationale}\n"
    _append_file(filepath, entry)


# ---- Full State Snapshot (for supervisor) ----

def full_state(project_path: str) -> dict:
    v02_context = load_context(project_path)
    return {
        "project_memory": v02_context.get("project_memory", ""),
        "decisions": get_decisions(project_path) or v02_context.get("decisions", ""),
        "changelog": v02_context.get("changelog", ""),
        "project_state": get_project_state(project_path),
        "task_history": get_task_history(project_path),
        "failed_tasks": get_failed_tasks(project_path),
        "consecutive_failures": count_consecutive_failures(project_path),
    }


# ---- Agent State (runtime) ----

AGENT_STATE_FILE = "AGENT_STATE.json"

_agent_state_default = {
    "supervisor_mode": "idle",
    "current_task_id": None,
    "current_task_objective": None,
    "iteration": 0,
    "consecutive_failures": 0,
    "total_tasks_completed": 0,
    "last_review": {
        "approved": None,
        "quality_score": None,
        "timestamp": None,
    },
    "paused": False,
    "pause_reason": None,
    "emergency_stop": False,
}


def get_agent_state(project_path: str) -> dict:
    filepath = os.path.join(_memory_dir(project_path), AGENT_STATE_FILE)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return dict(_agent_state_default)
    return dict(_agent_state_default)


def save_agent_state(project_path: str, state: dict) -> None:
    filepath = os.path.join(_memory_dir(project_path), AGENT_STATE_FILE)
    _ensure_dir(os.path.dirname(filepath))
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def reset_agent_state(project_path: str) -> dict:
    state = dict(_agent_state_default)
    save_agent_state(project_path, state)
    return state
