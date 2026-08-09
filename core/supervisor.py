import yaml
from pathlib import Path

from core.memory import (
    get_agent_state,
    save_agent_state,
    reset_agent_state,
    record_task,
    record_failure,
    record_decision,
    update_project_state,
)
from core.planner import create_task, enqueue_task, dequeue_next, mark_completed, mark_failed
from core.reviewer import review as reviewer_review
from core.state_validator import validate as validate_state
from control.policy_loader import (
    is_auto_run_enabled,
    get_max_iterations,
    get_max_consecutive_failures,
    check_emergency_stop,
    is_operation_allowed,
)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}


class MockExecutor:
    def __init__(self, results: list = None):
        self.results = results or []
        self.call_count = 0

    def run(self, task: dict) -> dict:
        if self.call_count < len(self.results):
            result = self.results[self.call_count]
        else:
            result = {
                "build_passed": True,
                "tests": {"passed": 157, "failed": 0, "total": 157},
                "files_changed": ["app/page.tsx"],
                "commit": "mock_abc123",
                "diff_summary": "1 file changed",
                "api_credits_used": 0,
                "ai_output": "Mock: completed.",
                "out_of_scope_files": [],
            }
        self.call_count += 1
        return result


def _select_worker(project_path: str) -> dict | None:
    config = _load_config()
    workers = config.get("workers", [])
    for w in workers:
        if w.get("directory", "") == project_path:
            return w
    return None


def _recovery_loop(project_path: str, state: dict) -> dict:
    validation = validate_state(project_path)
    if validation["conflict"]:
        state["supervisor_mode"] = "blocked"
        state["pause_reason"] = "recovery_failed: state validation conflict"
        save_agent_state(project_path, state)
        return state
    state["supervisor_mode"] = "recovering"
    state["paused"] = False
    state["pause_reason"] = None
    save_agent_state(project_path, state)
    return state


def run_supervisor(project_path: str, executor=None) -> dict:
    config = _load_config()
    supervisor_cfg = config.get("supervisor", {})
    max_iter = supervisor_cfg.get("max_iterations", 10)
    max_fail = supervisor_cfg.get("max_consecutive_failures", 3)

    if not is_auto_run_enabled():
        return {"status": "stopped", "reason": "auto_run disabled in policy"}

    validation = validate_state(project_path)
    if validation["conflict"]:
        return {"status": "blocked", "reason": "state validation failed", "details": validation["issues"]}

    state = get_agent_state(project_path)

    if state.get("paused") and not state.get("emergency_stop"):
        state = _recovery_loop(project_path, state)
        if state.get("supervisor_mode") == "blocked":
            return {"status": "blocked", "reason": state.get("pause_reason", "recovery failed")}

    if executor is None:
        worker = _select_worker(project_path)
        if not worker:
            return {"status": "blocked", "reason": f"no worker found for {project_path}"}
        opencode_cfg = config.get("opencode", {})
        from opencode.executor import OpenCodeExecutor
        executor = OpenCodeExecutor(
            opencode_url=worker["opencode_url"],
            username=opencode_cfg.get("username", "opencode"),
            password=opencode_cfg.get("password", ""),
            project_path=project_path,
        )

    state["supervisor_mode"] = "running"
    save_agent_state(project_path, state)

    log = []
    iteration = state.get("iteration", 0)
    consecutive_failures = state.get("consecutive_failures", 0)

    try:
        while iteration < max_iter and consecutive_failures < max_fail:
            iteration += 1
            state["iteration"] = iteration
            save_agent_state(project_path, state)

            task = create_task(project_path)
            if not task:
                log.append({"iteration": iteration, "event": "no_task"})
                break

            if check_emergency_stop(task.get("objective", "")):
                state["emergency_stop"] = True
                state["supervisor_mode"] = "emergency_stop"
                save_agent_state(project_path, state)
                log.append({"iteration": iteration, "event": "emergency_stop", "task": task["id"]})
                break

            if not is_operation_allowed(task.get("objective", "")):
                log.append({"iteration": iteration, "event": "blocked", "task": task["id"]})
                continue

            enqueue_task(task)
            state["current_task_id"] = task["id"]
            state["current_task_objective"] = task["objective"]
            save_agent_state(project_path, state)

            result = executor.run(task)
            log.append({"iteration": iteration, "event": "executed", "task": task["id"]})

            review = reviewer_review(task, result, project_path)
            state["last_review"] = {
                "approved": review["approved"],
                "quality_score": review["quality_score"],
                "timestamp": task.get("created_at", ""),
            }
            save_agent_state(project_path, state)
            log.append({"iteration": iteration, "event": "reviewed", "approved": review["approved"], "quality": review["quality_score"]})

            if review["requires_human"]:
                state["paused"] = True
                state["pause_reason"] = review["human_reason"]
                state["supervisor_mode"] = "paused"
                save_agent_state(project_path, state)
                log.append({"iteration": iteration, "event": "paused", "reason": review["human_reason"]})
                break

            if review["approved"]:
                mark_completed(task["id"])
                record_task(project_path, task["id"], task["objective"], "completed",
                            result.get("commit", ""),
                            f"{result.get('tests', {}).get('passed', '?')} pass")
                update_project_state(project_path, "Current Sprint", task.get("sprint", ""))
                consecutive_failures = 0
            else:
                mark_failed(task["id"], "; ".join(review["issues"]))
                record_failure(project_path, task["id"], task["objective"],
                               "; ".join(review["issues"]), consecutive_failures + 1)
                consecutive_failures += 1

            state["consecutive_failures"] = consecutive_failures
            save_agent_state(project_path, state)

    finally:
        if state["supervisor_mode"] not in ("paused", "emergency_stop", "blocked"):
            state["supervisor_mode"] = "idle"
        state["total_tasks_completed"] = len([l for l in log if l.get("approved")])
        save_agent_state(project_path, state)

    return {
        "status": state["supervisor_mode"],
        "iterations": iteration,
        "consecutive_failures": consecutive_failures,
        "tasks_completed": state["total_tasks_completed"],
        "log": log,
    }
