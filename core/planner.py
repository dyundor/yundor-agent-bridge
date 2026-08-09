import json
import os
import re
import subprocess
from pathlib import Path

from core.memory import (
    get_project_state,
    get_task_history,
    get_decisions,
    get_failed_tasks,
    full_state,
)

QUEUE_PATH = Path(__file__).resolve().parent.parent / "queue" / "task_queue.json"


def create_task(project_path: str, reviewer_feedback: dict = None) -> dict | None:
    state = full_state(project_path)
    current = _detect_current_sprint(project_path, state)

    if reviewer_feedback and reviewer_feedback.get("next_task"):
        return _build_task(current["sprint"], reviewer_feedback["next_task"], current)

    task = _generate_from_roadmap(project_path, current, state)
    if task:
        return task

    return _generate_from_sequence(current, state)


def _detect_current_sprint(project_path: str, state: dict) -> dict:
    result = {"sprint": "15.69", "next_sprint": "15.70", "source": "default"}
    try:
        log = subprocess.check_output(
            ["git", "-C", project_path, "log", "--oneline", "-20"],
            stderr=subprocess.DEVNULL, text=True,
        )
        for line in log.split("\n"):
            if "Sprint 15." in line:
                match = re.search(r"Sprint (15\.\d+)", line)
                if match:
                    version = match.group(1)
                    minor = int(version.split(".")[1])
                    result["sprint"] = version
                    result["next_sprint"] = f"15.{minor + 1}"
                    result["source"] = "git_log"
                    break
    except Exception:
        pass

    ps = state.get("project_state", "")
    sprint_match = re.search(r"Sprint (15\.\d+)", ps)
    if sprint_match:
        ps_version = sprint_match.group(1)
        ps_minor = int(ps_version.split(".")[1])
        git_minor = int(result["sprint"].split(".")[1])
        if ps_minor > git_minor:
            result["sprint"] = ps_version
            result["next_sprint"] = f"15.{ps_minor + 1}"
            result["source"] = "project_state"

    return result


def _parse_roadmap(project_path: str) -> list:
    """
    Parse the handoff document for recommended Sprint sequence.
    Extracts Sprint sections from OPENCODE_DEEPSEEK_HANDOFF.md.
    Returns list of {sprint, objective, constraints, success_criteria}.
    """
    roadmap = []
    handoff_path = os.path.join(project_path, "OPENCODE_DEEPSEEK_HANDOFF.md")
    if not os.path.exists(handoff_path):
        return roadmap

    with open(handoff_path, "r", encoding="utf-8") as f:
        content = f.read()

    sections = re.split(r"\n### (Sprint \d+\.\d+[：:].*)\n", content)
    for i in range(1, len(sections), 2):
        header = sections[i].strip()
        body = sections[i + 1] if i + 1 < len(sections) else ""

        match = re.match(r"Sprint (\d+\.\d+)[：:]\s*(.+)", header)
        if not match:
            continue
        sprint_id = match.group(1)
        objective = match.group(2).strip()

        constraints = []
        if "paid api" in body.lower() and "not" not in body.lower():
            constraints.append("paid_api_approval_required")
        else:
            constraints.append("no_paid_api")
        constraints.append("preserve_existing_data")
        constraints.append("incremental_change")

        success = []
        ac_section = re.search(r"验收标准[：:]\s*\n(.*?)(?=\n##|\n###|\Z)", body, re.DOTALL)
        if ac_section:
            for line in ac_section.group(1).strip().split("\n"):
                line = line.strip().lstrip("- ").strip()
                if line and not line.startswith("#"):
                    success.append(line)

        roadmap.append({
            "sprint": sprint_id,
            "objective": f"Sprint {sprint_id}: {objective}",
            "constraints": constraints,
            "success_criteria": success or ["npm test passes", "npm run build passes", "no paid API consumed"],
        })

    return roadmap


def _generate_from_roadmap(project_path: str, current: dict, state: dict) -> dict | None:
    roadmap = _parse_roadmap(project_path)
    if not roadmap:
        return None

    next_sprint = current.get("next_sprint", "")
    for entry in roadmap:
        if entry["sprint"] == next_sprint:
            return _build_task(
                next_sprint,
                entry["objective"],
                {"priority": "high", "sprint": next_sprint},
                entry.get("constraints", []),
                entry.get("success_criteria", []),
            )

    return None


def _generate_from_sequence(current: dict, state: dict) -> dict | None:
    sprint = current["next_sprint"]
    fallback = {
        "15.70": {
            "objective": "Sprint 15.70: Expand representative product resources to all 9 categories.",
            "constraints": ["no_paid_api", "preserve_existing_data", "incremental_change"],
            "success_criteria": ["npm test passes", "npm run build passes", "All 9 categories have product entries"],
        },
    }
    if sprint not in fallback:
        return None
    f = fallback[sprint]
    return _build_task(sprint, f["objective"], {"priority": "high", "sprint": sprint},
                       f.get("constraints", []), f.get("success_criteria", []))


def _build_task(sprint: str, objective: str, meta: dict,
                constraints: list = None, success_criteria: list = None) -> dict:
    import uuid
    from datetime import datetime

    require_tests = True
    test_skip_keywords = ["no test", "do not test", "don't test", "skip test", "analysis only",
                          "report only", "只生成报告", "不修改"]
    for kw in test_skip_keywords:
        if kw in objective.lower():
            require_tests = False
            break

    return {
        "id": f"MI-{sprint}-{uuid.uuid4().hex[:6]}",
        "project": "market-intelligence",
        "sprint": sprint,
        "objective": objective,
        "priority": meta.get("priority", "medium"),
        "constraints": constraints or [],
        "success_criteria": success_criteria or [],
        "require_tests": require_tests,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }


def enqueue_task(task: dict) -> None:
    """Append task to the persistent task queue."""
    tasks = _read_queue()
    existing = [t for t in tasks if t.get("id") != task["id"]]
    existing.append(task)
    _write_queue(existing)


def dequeue_next() -> dict | None:
    """Get the next pending task from the queue."""
    tasks = _read_queue()
    pending = [t for t in tasks if t.get("status") == "pending"]
    if not pending:
        return None
    return pending[0]


def mark_completed(task_id: str) -> None:
    from datetime import datetime
    tasks = _read_queue()
    for t in tasks:
        if t.get("id") == task_id:
            t["status"] = "completed"
            t["completed_at"] = datetime.now().isoformat()
    _write_queue(tasks)


def mark_failed(task_id: str, error: str) -> None:
    tasks = _read_queue()
    for t in tasks:
        if t.get("id") == task_id:
            t["status"] = "failed"
            t["error"] = error[:500]
    _write_queue(tasks)


def queue_size() -> int:
    return len(_read_queue())


def pending_count() -> int:
    return len([t for t in _read_queue() if t.get("status") == "pending"])


def _read_queue() -> list:
    if QUEUE_PATH.exists():
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def _write_queue(tasks: list) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
