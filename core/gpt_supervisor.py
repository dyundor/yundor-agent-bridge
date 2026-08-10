import json
import os
import time
import yaml
from pathlib import Path
import subprocess

from core.memory import (
    get_agent_state, save_agent_state, reset_agent_state,
    record_task, record_failure, record_decision, full_state,
)
from core.state_validator import validate as validate_state
from control.policy_loader import (
    is_auto_run_enabled, check_emergency_stop, is_operation_allowed,
    get_max_iterations, get_max_consecutive_failures, reload,
)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}


def _get_api_credentials() -> tuple:
    """Resolve API key and endpoint from env or opencode auth."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key, "https://api.openai.com/v1/chat/completions", "gpt-4o-mini"

    auth_path = os.path.expanduser("~/.local/share/opencode/auth.json")
    if os.path.exists(auth_path):
        try:
            with open(auth_path) as f:
                auth = json.load(f)
            ds = auth.get("deepseek", {})
            if ds.get("key"):
                return ds["key"], "https://api.deepseek.com/v1/chat/completions", "deepseek-chat"
        except Exception:
            pass
    return None, None, None


def _call_gpt(prompt: str, max_tokens: int = 800) -> dict:
    """Call GPT/DeepSeek API and return parsed JSON response."""
    import requests
    key, endpoint, model = _get_api_credentials()
    if not key:
        return {"error": "No API credentials available"}

    resp = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}],
              "max_tokens": max_tokens, "temperature": 0.3},
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "JSON parse failed", "raw": content[:500]}


def _build_planning_prompt(project_path: str) -> str:
    """Build comprehensive state snapshot for GPT to plan next action."""
    state = full_state(project_path)
    agent = get_agent_state(project_path)
    config = _load_config()
    goals_path = Path(__file__).resolve().parent.parent / "goals" / "market-intelligence.md"
    goals = ""
    if goals_path.exists():
        goals = goals_path.read_text()[:3000]

    task_hist = state.get("task_history", "")[-2000:]
    failed = state.get("failed_tasks", "")[-1000:]
    decisions = state.get("decisions", "")[-1500:]
    changelog = state.get("changelog", "")[-1000:]

    return f"""You are the supervisor of the Yundor Market Intelligence development pipeline.


    IMPORTANT - CURRENT STATE VERIFICATION RULES:

    Before making any decision, establish the current reality of the project.

    The priority of truth is:

    1. Current git HEAD and actual repository files
    2. Test results and build results
    3. PROJECT_STATE.md
    4. TASK_HISTORY.md
    5. FAILED_TASKS.md


    FAILED_TASKS.md contains historical failures only.

    A task listed in FAILED_TASKS.md may already be completed successfully later.

    Never restart a task only because it appears in FAILED_TASKS.md.

    Always verify:
    - Does the code/file actually exist?
    - Is there a newer git commit fixing the previous failure?
    - Are tests currently passing?


    
## Project Goals
{goals}

## Current Agent State
- Mode: {agent.get('supervisor_mode', 'idle')}
- Iteration: {agent.get('iteration', 0)}
- Consecutive failures: {agent.get('consecutive_failures', 0)}
- Paused: {agent.get('paused', False)}
- Emergency stop: {agent.get('emergency_stop', False)}

## Recent Task History
{task_hist}

## Recent Failures
{failed}

## Key Decisions
{decisions}

## Recent Changes
{changelog}

## Supervisor Config
{json.dumps(config.get('supervisor', {}), indent=2)}

## Policy Constraints
- max_iterations: {get_max_iterations()}
- max_failures: {get_max_consecutive_failures()}
- auto_run: {is_auto_run_enabled()}

YOU decide the next action. Output ONLY valid JSON:

{{
  "action": "execute" | "pause" | "complete",
  "rationale": "why you chose this action",
  "task": {{
    "sprint": "15.XX",
    "objective": "detailed task description for the AI coder",
    "require_tests": true,
    "priority": "high" | "medium" | "low",
    "focus_areas": ["what to pay attention to"],
    "avoid": ["what NOT to do"]
  }}
}}

Rules:
- action "execute": there is meaningful next work. Provide a specific task.
- action "pause": state is unclear, needs human input, or consecutive failures > 1.
- action "complete": all goals achieved or no more meaningful tasks.
- Never suggest tasks that delete data, modify credentials, or call paid APIs without approval.
- Keep tasks small and incremental (one Sprint scope).
- If consecutive_failures >= 2, prefer "pause".
- If the current sprint from git log is the last planned sprint, prefer "complete".
"""


def _build_review_prompt(task: dict, result: dict, project_path: str) -> str:
    """Build review context for GPT to evaluate task completion."""
    return f"""You are reviewing a completed development task for the Yundor Market Intelligence project.

## Task
{json.dumps(task, indent=2, ensure_ascii=False)}

## Execution Result
- Status: {result.get('status')}
- Commit: {result.get('commit', 'N/A')[:12]}
- Files: {result.get('files_changed', [])}
- Diff: {result.get('diff_summary', '')}
- Tests: {json.dumps(result.get('tests', {}))}
- AI Output: {result.get('ai_output', '')[:600]}
- API Credits: {result.get('api_credits_used', 0)}

Output ONLY valid JSON:

{{
  "decision": "approve" | "retry" | "skip" | "escalate",
  "rationale": "brief explanation",
  "quality_score": 0-100,
  "technical_score": 0-100,
  "business_score": 0-100,
  "data_quality_score": 0-100,
  "issues": ["specific issues found"],
  "risks": ["architectural or data risks"],
  "next_suggestion": "what to do next"
}}

Scoring guide:
- quality_score: overall code and process quality
- technical_score: code quality, architecture, test coverage
- business_score: does this help find real buyers? (0-100)
- data_quality_score: data integrity, no fabricated data, proper sources (0-100)

Review rules:
- "approve": task achieved objective, tests pass, no data violations.
- "retry": fixable issues found. Describe what to fix.
- "skip": task is redundant or already done. Move on.
- "escalate": requires human intervention (API budget, data deletion, architecture risk).
"""


def run_gpt_supervisor(project_path: str, executor=None) -> dict:
    """GPT-managed autonomous supervisor loop."""
    config = _load_config()
    max_iter = config.get("supervisor", {}).get("max_iterations", 10)
    max_fail = config.get("supervisor", {}).get("max_consecutive_failures", 3)

    if not is_auto_run_enabled():
        return {"status": "stopped", "reason": "auto_run disabled",
                "iterations": 0, "failures": 0, "decisions": [], "log": []}

    validation = validate_state(project_path)
    if validation["conflict"]:
        return {"status": "blocked", "reason": str(validation["issues"]),
                "iterations": 0, "failures": 0, "decisions": [], "log": []}

    # Select executor
    if executor is None:
        from core.supervisor import _select_worker
        worker = _select_worker(project_path)
        if not worker:
            return {"status": "blocked", "reason": "no worker for project",
                    "iterations": 0, "failures": 0, "decisions": [], "log": []}
        from opencode.executor import OpenCodeExecutor
        opencode_cfg = config.get("opencode", {})
        executor = OpenCodeExecutor(
            opencode_url=worker["opencode_url"],
            username=opencode_cfg.get("username", "opencode"),
            password=opencode_cfg.get("password", ""),
            project_path=project_path,
        )

    state = get_agent_state(project_path)
    if state.get("emergency_stop"):
        return {"status": "stopped", "reason": "emergency stop active",
                "iterations": 0, "failures": 0, "decisions": [], "log": []}

    state["supervisor_mode"] = "gpt_running"
    save_agent_state(project_path, state)

    log = []
    iteration = 0
    failures = 0
    gpt_decisions = []

    try:
        while iteration < max_iter and failures < max_fail:
            iteration += 1

            # ---- GPT plans next action ----
            planning_prompt = _build_planning_prompt(project_path)
            decision = _call_gpt(planning_prompt, 600)

            if "error" in decision:
                log.append({"iteration": iteration, "event": "gpt_error", "error": decision["error"]})
                failures += 1
                continue

            action = decision.get("action", "pause")
            rationale = decision.get("rationale", "")
            gpt_decisions.append({"iteration": iteration, "action": action, "rationale": rationale[:200]})
            log.append({"iteration": iteration, "event": "gpt_decision", "action": action})

            if action == "complete":
                log.append({"iteration": iteration, "event": "complete", "rationale": rationale})
                break

            if action == "pause":
                state["paused"] = True
                state["pause_reason"] = rationale
                save_agent_state(project_path, state)
                log.append({"iteration": iteration, "event": "paused", "reason": rationale[:100]})
                break

            # ---- Execute task from GPT ----
            task = decision.get("task", {})
            objective = task.get("objective", "")
            if not objective:
                log.append({"iteration": iteration, "event": "no_objective"})
                continue

            # Safety checks (non-negotiable, rule-based)
            if check_emergency_stop(objective):
                state["emergency_stop"] = True
                save_agent_state(project_path, state)
                log.append({"iteration": iteration, "event": "emergency_stop"})
                break

            if not is_operation_allowed(objective):
                log.append({"iteration": iteration, "event": "blocked", "reason": "policy"})
                continue

            task["id"] = f"GPT-{iteration}-{int(time.time())}"
            state["current_task_id"] = task["id"]
            state["current_task_objective"] = objective
            save_agent_state(project_path, state)

            # ---- Execute ----
            result = executor.run(task)
            log.append({"iteration": iteration, "event": "executed"})

            # ---- GPT reviews result ----
            review_prompt = _build_review_prompt(task, result, project_path)
            review = _call_gpt(review_prompt, 500)

            if "error" in review:
                log.append({"iteration": iteration, "event": "review_error"})
                review = {"decision": "retry", "rationale": "review API error",
                         "quality_score": 0, "technical_score": 0,
                         "business_score": 0, "data_quality_score": 0,
                         "issues": ["review API unavailable"], "risks": []}

            decision_result = review.get("decision", "retry")
            log.append({
                "iteration": iteration, "event": "reviewed",
                "decision": decision_result,
                "quality": review.get("quality_score"),
            })

            record_decision(project_path, f"GPT-{iteration}",
                f"Action={action} Decision={decision_result} Q={review.get('quality_score')} "
                f"T={review.get('technical_score')} B={review.get('business_score')} "
                f"D={review.get('data_quality_score')}",
                f"GPT manager rationale: {rationale[:200]}")

            if decision_result == "approve":
                record_task(project_path, task["id"], objective, "completed",
                           result.get("commit", ""),
                           f"GPT-managed, Q={review.get('quality_score')}")
                failures = 0
            elif decision_result == "skip":
                failures = 0  # intentional skip, not failure
            elif decision_result == "escalate":
                state["paused"] = True
                state["pause_reason"] = f"GPT escalated: {review.get('rationale', '')[:200]}"
                save_agent_state(project_path, state)
                log.append({"iteration": iteration, "event": "escalated"})
                break
            else:  # retry
                record_failure(project_path, task["id"], objective,
                             "; ".join(review.get("issues", [])), failures + 1)
                failures += 1

            state["iteration"] = iteration
            state["consecutive_failures"] = failures
            save_agent_state(project_path, state)

    finally:
        state["supervisor_mode"] = "idle"
        state["iteration"] = iteration
        state["consecutive_failures"] = failures
        state["total_tasks_completed"] = len([l for l in log if l.get("decision") == "approve"])
        save_agent_state(project_path, state)

    return {
        "status": state["supervisor_mode"],
        "iterations": iteration,
        "failures": failures,
        "decisions": gpt_decisions,
        "log": log,
    }
