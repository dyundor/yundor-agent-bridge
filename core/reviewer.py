import os
import json
import yaml
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}


def _get_gpt_config() -> dict:
    return _load_config().get("gpt", {})


def review(task: dict, execution_result: dict, project_path: str = "") -> dict:
    result = {
        "approved": False,
        "quality_score": 0,
        "technical_score": 0,
        "business_score": 0,
        "issues": [],
        "risks": [],
        "next_task": "",
        "requires_human": False,
        "human_reason": "",
        "level": 1,
        "details": {},
    }

    l1 = _level1_automatic(task, execution_result)
    result["issues"].extend(l1["issues"])
    result["details"]["auto_check"] = l1

    if not l1["passed"]:
        result["quality_score"] = max(0, 100 - len(l1["issues"]) * 25)
        return result

    l2 = _level2_review(task, execution_result, project_path)
    result["level"] = 2
    result["quality_score"] = l2.get("quality_score", 60)
    result["technical_score"] = l2.get("technical_score", 0)
    result["business_score"] = l2.get("business_score", 0)
    result["issues"].extend(l2.get("issues", []))
    result["risks"] = l2.get("risks", [])
    result["next_task"] = l2.get("next_task", "")
    result["details"]["gpt_review"] = l2

    result["approved"] = result["quality_score"] >= 50 and len(l2.get("issues", [])) == 0

    if l2.get("requires_human"):
        result["requires_human"] = True
        result["human_reason"] = l2.get("note", "GPT review requires manual verification")

    l3 = _level3_human_pause(task, execution_result, result)
    if l3["requires_human"]:
        result["requires_human"] = True
        result["human_reason"] = l3["reason"]
        result["approved"] = False

    return result


def _level1_automatic(task: dict, exec_result: dict) -> dict:
    issues = []
    details = {}

    build_passed = exec_result.get("build_passed", None)
    if build_passed is False:
        issues.append("BUILD_FAILED: production build did not pass")

    tests = exec_result.get("tests", {})
    details["tests"] = tests
    require_tests = task.get("require_tests", True)
    if require_tests:
        if tests.get("failed", 0) > 0:
            issues.append(f"TESTS_FAILED: {tests['failed']} tests failed")
        elif tests.get("passed", 0) == 0 and tests.get("total", 0) == 0:
            issues.append("NO_TESTS: no test results reported")
    else:
        details["tests_skipped"] = True

    files_changed = exec_result.get("files_changed", [])
    has_commit = bool(exec_result.get("commit", ""))
    is_analysis = task.get("require_tests") is False and not task.get("objective", "").lower().startswith("mi-test")
    details["files_changed_count"] = len(files_changed)
    if not files_changed and not has_commit and not is_analysis:
        issues.append("NO_CHANGES: no files were modified")
    elif has_commit and not files_changed:
        details["commit_evidence"] = exec_result["commit"][:12]
        details["diff_evidence"] = exec_result.get("diff_summary", "")

    api_credits = exec_result.get("api_credits_used", 0)
    details["api_credits_used"] = api_credits
    if api_credits > 0:
        details["api_warning"] = f"{api_credits} credits consumed"

    out_of_scope = exec_result.get("out_of_scope_files", [])
    if out_of_scope:
        issues.append(f"OUT_OF_SCOPE: {', '.join(out_of_scope[:3])}")

    details["issues_count"] = len(issues)
    return {"passed": len(issues) == 0, "issues": issues, "details": details}


def _resolve_api_key() -> tuple:
    """Try OPENAI_API_KEY first, then DeepSeek key from opencode auth."""
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        return openai_key, "openai", "https://api.openai.com/v1/chat/completions"

    auth_path = os.path.expanduser("~/.local/share/opencode/auth.json")
    if os.path.exists(auth_path):
        try:
            with open(auth_path, "r") as f:
                auth = json.load(f)
            ds = auth.get("deepseek", {})
            if ds.get("key"):
                return ds["key"], "deepseek", "https://api.deepseek.com/v1/chat/completions"
        except Exception:
            pass

    return None, None, None


def _level2_review(task: dict, exec_result: dict, project_path: str) -> dict:
    api_key, provider, endpoint = _resolve_api_key()

    if not api_key:
        return {
            "quality_score": 0, "technical_score": 0, "business_score": 0,
            "issues": ["REVIEW_UNAVAILABLE: No API key (OPENAI_API_KEY or DeepSeek)"],
            "next_task": "", "risks": [], "mode": "fallback",
            "requires_human": True,
            "note": "No review API available — requires manual review",
        }

    gpt_config = _get_gpt_config()
    model = gpt_config.get("model", "gpt-4o-mini")
    if provider == "deepseek":
        model = "deepseek-chat"

    try:
        return _call_review_api(api_key, endpoint, model, gpt_config, task, exec_result, provider)
    except Exception as e:
        return {
            "quality_score": 0, "technical_score": 0, "business_score": 0,
            "issues": [f"REVIEW_ERROR: {str(e)[:200]}"],
            "next_task": "", "risks": [], "mode": "error",
            "requires_human": True,
            "note": f"Review API call failed — requires manual review",
        }


def _call_review_api(api_key: str, endpoint: str, model: str, gpt_config: dict,
                     task: dict, exec_result: dict, provider: str) -> dict:
    import requests

    max_tokens = int(gpt_config.get("max_tokens", 1000))

    objective = task.get("objective", task.get("task", "Unknown"))
    commit = exec_result.get("commit", "N/A")
    files_changed = exec_result.get("files_changed", [])
    tests = exec_result.get("tests", {})
    diff_summary = exec_result.get("diff_summary", "")
    ai_output = exec_result.get("ai_output", "")

    prompt = f"""Review the following completed development task for the Yundor Market Intelligence project.

## Task Objective
{objective}

## Git Commit
{commit}

## Files Changed
{', '.join(files_changed[:10])}

## Test Results
Passed: {tests.get('passed', 'N/A')}, Failed: {tests.get('failed', 'N/A')}, Total: {tests.get('total', 'N/A')}

## Diff Summary
{diff_summary[:500]}

## AI Output Summary
{ai_output[:800]}

Answer in JSON only:
{{
  "did_task_achieve_objective": true/false,
  "quality_score": 0-100,
  "technical_score": 0-100,
  "business_score": 0-100,
  "issues": ["code quality issues or regressions"],
  "risks": ["architectural or data risks"],
  "next_task": "suggested next sprint or fix task"
}}

Scoring guide:
- technical_score: code quality, test coverage, architecture impact (0-100)
- business_score: does this help find real buyers faster? (0-100)
- quality_score: overall (weighted: technical 50% + business 50%)

Only return valid JSON, no other text."""

    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        },
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    content = body["choices"][0]["message"]["content"].strip()

    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    parsed = json.loads(content)

    return {
        "quality_score": int(parsed.get("quality_score", 60)),
        "technical_score": int(parsed.get("technical_score", 50)),
        "business_score": int(parsed.get("business_score", 50)),
        "issues": parsed.get("issues", []),
        "risks": parsed.get("risks", []),
        "next_task": parsed.get("next_task", ""),
        "mode": provider,
        "model": model,
        "did_achieve": parsed.get("did_task_achieve_objective", True),
        "raw_response": content[:500],
    }


def _level3_human_pause(task: dict, exec_result: dict, review_result: dict) -> dict:
    from control.policy_loader import requires_manual_review, get_manual_review_triggers

    triggers = get_manual_review_triggers()
    failure_count = exec_result.get("attempt", 1)
    check_data = {
        "quality_score": review_result.get("quality_score", 0),
        "failure_count": failure_count - 1,
        "out_of_scope": bool(exec_result.get("out_of_scope_files")),
        "api_credits_used": exec_result.get("api_credits_used", 0),
    }

    if requires_manual_review(check_data):
        reasons = []
        if "quality_below_threshold" in triggers and check_data["quality_score"] < 50:
            reasons.append(f"quality score {check_data['quality_score']} below threshold")
        if "repeated_failure" in triggers and check_data["failure_count"] >= 1:
            reasons.append(f"task failed {check_data['failure_count']} time(s) previously")
        if "out_of_scope_changes" in triggers and check_data["out_of_scope"]:
            reasons.append("out-of-scope file changes detected")
        if "api_credit_consumed" in triggers and check_data["api_credits_used"] > 0:
            reasons.append(f"API credits consumed: {check_data['api_credits_used']}")
        return {"requires_human": True, "reason": "; ".join(reasons)}

    return {"requires_human": False, "reason": ""}
