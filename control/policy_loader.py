import os
import yaml
from pathlib import Path


POLICY_PATH = Path(__file__).resolve().parent / "policy.yaml"

_cache = None
_cache_mtime = None


def _load_raw() -> dict:
    global _cache, _cache_mtime
    mtime = os.path.getmtime(POLICY_PATH)
    if _cache is not None and _cache_mtime == mtime:
        return _cache
    with open(POLICY_PATH, "r") as f:
        _cache = yaml.safe_load(f) or {}
    _cache_mtime = mtime
    return _cache


def reload() -> dict:
    global _cache, _cache_mtime
    _cache = None
    _cache_mtime = None
    return _load_raw()


def is_auto_run_enabled() -> bool:
    return bool(_load_raw().get("auto_run", {}).get("enabled", False))


def get_max_iterations() -> int:
    return int(_load_raw().get("limits", {}).get("max_iterations", 10))


def get_max_consecutive_failures() -> int:
    return int(_load_raw().get("limits", {}).get("max_consecutive_failures", 3))


def get_max_tasks_per_session() -> int:
    return int(_load_raw().get("limits", {}).get("max_tasks_per_session", 20))


def get_emergency_keywords() -> list:
    return list(_load_raw().get("emergency_stop", {}).get("keywords", []))


def get_api_budget_usd() -> float:
    return float(_load_raw().get("budget", {}).get("api_budget_usd", 0))


def get_importyeti_min_credits() -> int:
    return int(_load_raw().get("budget", {}).get("importyeti_min_credits", 25))


def get_blocked_operations() -> list:
    return list(_load_raw().get("dangerous_operations", {}).get("blocked", []))


def get_min_quality_score() -> int:
    return int(_load_raw().get("reviewer", {}).get("min_quality_score", 50))


def get_manual_review_triggers() -> list:
    return list(_load_raw().get("reviewer", {}).get("manual_review_triggers", []))


def is_operation_allowed(objective: str) -> bool:
    blocked = get_blocked_operations()
    objective_lower = objective.lower()
    for pattern in blocked:
        if pattern.lower() in objective_lower:
            return False
    return True


def check_emergency_stop(text: str) -> bool:
    keywords = get_emergency_keywords()
    text_lower = text.lower()
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True
    return False


def requires_manual_review(review_result: dict) -> bool:
    triggers = get_manual_review_triggers()
    if "quality_below_threshold" in triggers and review_result.get("quality_score", 100) < get_min_quality_score():
        return True
    if "repeated_failure" in triggers and review_result.get("failure_count", 0) >= 1:
        return True
    if "out_of_scope_changes" in triggers and review_result.get("out_of_scope", False):
        return True
    if "api_credit_consumed" in triggers and review_result.get("api_credits_used", 0) > 0:
        return True
    return False
