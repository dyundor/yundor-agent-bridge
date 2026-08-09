import time
import subprocess
import yaml
from pathlib import Path
from typing import Optional

from opencode_client import OpenCodeClient as _V02Client


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def _load_executor_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f).get("executor", {})


class OpenCodeExecutor:
    def __init__(self, opencode_url: str, username: str, password: str,
                 project_path: str, poll_interval: float = None, max_wait: float = None):
        self.client = _V02Client(opencode_url, username, password)
        self.project_path = project_path
        cfg = _load_executor_config()
        self.poll_interval = poll_interval or cfg.get("poll_interval", 5.0)
        self.max_wait = max_wait or cfg.get("initial_timeout", 300)
        self.max_wait_adaptive = cfg.get("max_timeout", 1800)
        self.session_id: Optional[str] = None
        self._timeout_escalated = False

    def health_check(self) -> dict:
        import requests
        url = self.client.url.rstrip("/")
        try:
            resp = requests.get(f"{url}/global/health", auth=self.client.auth, timeout=5)
            return {"healthy": resp.status_code == 200, "version": resp.json().get("version", "unknown")}
        except Exception as e:
            return {"healthy": False, "error": str(e)[:100]}

    def run(self, task: dict) -> dict:
        objective = task.get("objective", task.get("task", ""))
        if not objective:
            return _error_result("Empty task objective")

        health = self.health_check()
        if not health["healthy"]:
            return _error_result(f"OpenCode server unhealthy: {health.get('error', 'unknown')}")

        session = self._safe_create_session()
        if not session:
            return _error_result("Failed to create OpenCode session")
        self.session_id = session.get("id", "")
        if not self.session_id:
            return _error_result("Session created but no ID returned")

        resp = self._safe_send_message(objective)
        if not resp:
            return _error_result("Failed to send message to OpenCode")

        poll_result = self._poll_for_completion()
        poll_result["ai_output"] = _extract_text(resp)

        git = self._collect_git_evidence()
        poll_result.update(git)
        poll_result["files_changed"] = self._parse_diff_files()

        # Adaptive timeout: if first run took close to max, escalate for next
        elapsed = time.time() - getattr(self, "_start_time", time.time())
        if elapsed > self.max_wait * 0.8 and not self._timeout_escalated:
            self.max_wait = min(self.max_wait * 2, self.max_wait_adaptive)
            self._timeout_escalated = True

        return poll_result

    def _safe_create_session(self) -> Optional[dict]:
        try:
            return self.client.create_session(self.project_path)
        except Exception:
            return None

    def _safe_send_message(self, message: str) -> Optional[dict]:
        self._start_time = time.time()
        try:
            return self.client.send_message(self.session_id, message)
        except Exception:
            return None

    def _poll_for_completion(self) -> dict:
        import requests

        time.sleep(self.poll_interval)

        url = self.client.url.rstrip("/")
        auth = self.client.auth

        deadline = time.time() + self.max_wait
        last_data = {}
        seen_message = False
        idle_start = None

        while time.time() < deadline:
            try:
                resp = requests.get(
                    f"{url}/session/{self.session_id}",
                    auth=auth, timeout=10,
                )
                if resp.status_code != 200:
                    time.sleep(self.poll_interval)
                    continue

                data = resp.json()
                last_data = data
                summary = data.get("summary", {})
                files_changed = summary.get("files", 0)

                # Detection: has a message been processed?
                tokens = data.get("tokens", {})
                has_processed = tokens.get("output", 0) > 0

                if has_processed and not seen_message:
                    seen_message = True
                    idle_start = None

                if files_changed > 0 and self._session_appears_idle(data):
                    return self._build_result(data, summary)

                # For analysis tasks: wait for idle after message processed
                if seen_message and files_changed == 0:
                    if idle_start is None:
                        idle_start = time.time()
                    elif time.time() - idle_start > 20:
                        return self._build_result(data, summary)

            except requests.RequestException:
                pass

            time.sleep(self.poll_interval)

        if last_data:
            summary = last_data.get("summary", {})
            return self._build_result(last_data, summary)

        return _timeout_result()

    def _session_appears_idle(self, session_data: dict) -> bool:
        time_info = session_data.get("time", {})
        updated = time_info.get("updated", 0)
        now_ms = int(time.time() * 1000)
        idle_ms = now_ms - updated
        return idle_ms > 15000

    def _build_result(self, session_data: dict, summary: dict) -> dict:
        return {
            "build_passed": None,
            "tests": {"passed": 0, "failed": 0, "total": 0, "note": "auto-detected from git"},
            "files_changed": [],
            "commit": "",
            "diff_summary": f"files={summary.get('files', 0)} additions={summary.get('additions', 0)} deletions={summary.get('deletions', 0)}",
            "api_credits_used": 0,
            "out_of_scope_files": [],
            "session_id": self.session_id,
            "session_cost": session_data.get("cost", 0),
            "tokens": session_data.get("tokens", {}),
            "status": "completed",
        }

    def _parse_diff_files(self) -> list:
        try:
            diff = subprocess.check_output(
                ["git", "-C", self.project_path, "diff", "--stat", "HEAD~1..HEAD"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
        except Exception:
            try:
                diff = subprocess.check_output(
                    ["git", "-C", self.project_path, "diff", "--stat"],
                    stderr=subprocess.DEVNULL, text=True,
                ).strip()
            except Exception:
                return []

        files = []
        for line in diff.split("\n"):
            line = line.strip()
            if not line or ("file" in line and "changed" in line):
                continue
            parts = line.split("|")
            if parts:
                fname = parts[0].strip()
                if fname and "/" in fname or "." in fname:
                    files.append(fname)
        return files

    def _collect_git_evidence(self) -> dict:
        try:
            commit = subprocess.check_output(
                ["git", "-C", self.project_path, "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
        except Exception:
            commit = ""

        try:
            diff = subprocess.check_output(
                ["git", "-C", self.project_path, "diff", "--stat", "HEAD~1..HEAD"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
        except Exception:
            try:
                diff = subprocess.check_output(
                    ["git", "-C", self.project_path, "diff", "--stat"],
                    stderr=subprocess.DEVNULL, text=True,
                ).strip()
            except Exception:
                diff = ""

        try:
            log = subprocess.check_output(
                ["git", "-C", self.project_path, "log", "--oneline", "-1"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
        except Exception:
            log = ""

        return {"commit": commit, "diff_summary": diff or "clean", "last_log": log}


def _extract_text(result: dict) -> str:
    parts = result.get("parts", [])
    texts = [p["text"] for p in parts if p.get("type") == "text"]
    return "\n".join(texts)


def _error_result(message: str) -> dict:
    return {
        "build_passed": False,
        "tests": {"passed": 0, "failed": 1, "total": 1},
        "files_changed": [],
        "commit": "",
        "diff_summary": "",
        "api_credits_used": 0,
        "out_of_scope_files": [],
        "status": "error",
        "error": message,
    }


def _timeout_result() -> dict:
    return {
        "build_passed": None,
        "tests": {"passed": 0, "failed": 0, "total": 0},
        "files_changed": [],
        "commit": "",
        "diff_summary": "",
        "api_credits_used": 0,
        "out_of_scope_files": [],
        "status": "timeout",
    }
