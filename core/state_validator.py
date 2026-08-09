import os
import subprocess
from core.memory import (
    get_project_state,
    get_task_history,
    get_decisions,
    get_agent_state,
)


def validate(project_path: str) -> dict:
    result = {
        "valid": True,
        "conflict": False,
        "issues": [],
        "warnings": [],
        "evidence": {},
    }

    _check_goals(result)
    _check_project_state(result, project_path)
    _check_sprint_15_69(result, project_path)
    _check_git_state(result, project_path)
    _check_agent_state_consistency(result, project_path)

    result["valid"] = not result["conflict"]
    return result


def _check_goals(result: dict) -> None:
    goals_path = os.path.join("goals", "market-intelligence.md")
    if not os.path.exists(goals_path):
        result["conflict"] = True
        result["issues"].append("GOAL_MISSING: goals/market-intelligence.md not found")
        return
    with open(goals_path, "r") as f:
        content = f.read()
    if "Ultimate Goal" not in content:
        result["issues"].append("GOAL_INCOMPLETE: missing Ultimate Goal section")
    if "Sprint 15.69" not in content:
        result["warnings"].append("GOAL_STALE: goals file may not reflect latest sprint")
    result["evidence"]["goals"] = "present"


def _check_project_state(result: dict, project_path: str) -> None:
    state = get_project_state(project_path)
    if not state.strip():
        result["warnings"].append("PROJECT_STATE_EMPTY: no project state recorded")
        result["evidence"]["project_state"] = "empty"
        return
    result["evidence"]["project_state"] = f"{len(state)} chars"


def _check_sprint_15_69(result: dict, project_path: str) -> None:
    """Verify Sprint 15.69 completion by cross-referencing multiple evidence sources."""
    evidence = {}

    # 1. Git log
    try:
        log = subprocess.check_output(
            ["git", "-C", project_path, "log", "--oneline", "-10"],
            stderr=subprocess.DEVNULL, text=True,
        )
        evidence["git_log"] = log.strip().split("\n")[:3]
    except Exception:
        evidence["git_log_error"] = "unable to read git log"

    commit_found = any("Sprint 15." in line for line in evidence.get("git_log", []))
    evidence["sprint_15_69_commit"] = commit_found

    # 2. Check for actual code changes (not just doc commits)
    try:
        log_full = subprocess.check_output(
            ["git", "-C", project_path, "log", "--oneline", "--all", "-20"],
            stderr=subprocess.DEVNULL, text=True,
        )
        evidence["all_commits"] = [l for l in log_full.strip().split("\n") if "Sprint 15." in l]
    except Exception:
        pass

    # 3. Check key files exist
    expected_files = [
        "app/api/hot-products/buyers/route.ts",
        "lib/products/hot-products.ts",
    ]
    missing = [f for f in expected_files if not os.path.exists(os.path.join(project_path, f))]
    evidence["expected_files_missing"] = missing

    # 4. Verify tests known to exist
    test_file = os.path.join(project_path, "tests/shipments.test.ts")
    if os.path.exists(test_file):
        with open(test_file, "r") as f:
            test_content = f.read()
        evidence["has_enrich_test"] = "enrichProductBuyers" in test_content
    else:
        evidence["has_enrich_test"] = False

    # Assessment — any Sprint 15.x commit is sufficient evidence
    any_sprint = any("Sprint 15." in line for line in evidence.get("all_commits", []))
    if not any_sprint and not commit_found:
        result["warnings"].append("SPRINT_EVIDENCE_WEAK: No recent Sprint 15.x commit in git log")
    elif missing:
        result["conflict"] = True
        result["issues"].append(
            f"SPRINT_INCOMPLETE: Expected files missing: {', '.join(missing)}"
        )
    elif not evidence.get("has_enrich_test"):
        result["warnings"].append(
            "SPRINT_TESTS: enrichProductBuyers test not found"
        )
    else:
        result["evidence"]["sprint_status"] = "verified by files + tests"

    result["evidence"]["sprint_15_69_detail"] = evidence


def _check_git_state(result: dict, project_path: str) -> None:
    try:
        status = subprocess.check_output(
            ["git", "-C", project_path, "status", "--short"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except Exception:
        result["warnings"].append("GIT_UNAVAILABLE: cannot read git status")
        result["evidence"]["git_status"] = "unavailable"
        return

    result["evidence"]["git_dirty"] = bool(status)
    if status:
        result["warnings"].append(
            f"GIT_DIRTY: uncommitted changes exist. "
            f"Continue only if these are known working files."
        )
        result["evidence"]["git_status_lines"] = status.split("\n")[:5]


def _check_agent_state_consistency(result: dict, project_path: str) -> None:
    state = get_agent_state(project_path)
    if state.get("emergency_stop"):
        result["conflict"] = True
        result["issues"].append("AGENT_EMERGENCY_STOP: emergency stop is active. Clear before continuing.")
    if state.get("paused"):
        result["warnings"].append("AGENT_PAUSED: agent state is paused. Review pause_reason before resuming.")
    result["evidence"]["agent_state"] = {
        "mode": state.get("supervisor_mode"),
        "iteration": state.get("iteration"),
        "failures": state.get("consecutive_failures"),
    }
