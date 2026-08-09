import sys
import yaml

from opencode_client import OpenCodeClient
from project_reader import read_project_context
from git_manager import git_status, get_commit_hash, get_diff_summary
from report_parser import extract_text, parse_report
from session_manager import (
    get_saved_session,
    save_session,
    clear_session,
    check_session_valid,
)
from report_generator import generate_report
from execution_policy import get_execution_policy
from memory_manager import get_memory
from memory_writer import append_changelog
from task_manager import create_task, update_task
from task_status import get_status_summary


def main():
    args = sys.argv[1:]

    # ---- v0.3: --supervise mode ----
    if "--supervise" in args:
        args.remove("--supervise")
        use_gpt = "--gpt" in args
        if use_gpt:
            args.remove("--gpt")
        return _run_supervisor(args, gpt_mode=use_gpt)

    # ---- v0.2: single-task mode ----
    project = "market"

    if "--project" in args:
        index = args.index("--project")
        project = args[index + 1]
        args.pop(index)
        args.pop(index)

    task = " ".join(args)

    task_id = create_task(project, task)

    status = get_status_summary()

    if status["running"] or status["failed"]:
        print("\nFound unfinished tasks")

    config_path = "config.yaml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    project_path = config["projects"][project]["path"]

    print("Project:")
    print(project)

    print("Path:")
    print(project_path)

    client = OpenCodeClient(
        config["opencode"]["url"],
        config["opencode"]["username"],
        config["opencode"]["password"],
    )

    print("\n读取项目上下文...")

    context = read_project_context(project_path)

    git_before = git_status(project_path)

    before_commit = get_commit_hash(project_path)

    session_id = get_saved_session(config, project)

    if session_id:
        print("\n检查已有 Session:")
        print(session_id)

        valid = check_session_valid(
            config["opencode"]["url"],
            session_id,
            (config["opencode"]["username"], config["opencode"]["password"]),
        )

        if valid:
            print("Session 有效，复用")
        else:
            print("Session 失效，清除并重建")
            clear_session(config_path, project)
            session_id = None

    if not session_id:
        print("\n创建 OpenCode Session...")

        session = client.create_session(project_path)
        session_id = session["id"]

        print("Session:")
        print(session_id)

        print("\n保存 Session...")
        save_session(config_path, project, session_id)

    policy = get_execution_policy(project)

    memory = get_memory(project_path)

    prompt = f"""{policy}

路径：
{project_path}


项目上下文：

{context}


Project Memory:

{memory['project_memory']}


Decisions:

{memory['decisions']}


Changelog:

{memory['changelog']}


Git状态：

{git_before}



Task:

{task}


"""

    print("\n发送任务...")

    update_task(task_id, "running", "")

    try:
        result = client.send_message(session_id, prompt)

        print("\n===== DeepSeek 输出 =====")

        ai_output = extract_text(result)
        print(ai_output)

        after_commit = get_commit_hash(project_path)

        diff_summary = get_diff_summary(project_path)

        report = generate_report(
            project,
            task,
            before_commit,
            after_commit,
            diff_summary,
            ai_output,
        )

        try:
            parsed = parse_report(ai_output)

            changelog_lines = [
                f"Task: {task}",
                "",
                "Modified Files:",
            ]

            for f in parsed.get("modified_files", []):
                changelog_lines.append(f"- {f}")

            if parsed.get("tests"):
                changelog_lines.append("")
                changelog_lines.append("Tests:")
                for t in parsed["tests"]:
                    changelog_lines.append(f"- {t}")

            next_step = parsed.get("next_step", "")
            if next_step:
                changelog_lines.append("")
                changelog_lines.append(f"Next Step: {next_step}")

            append_changelog(project_path, "\n".join(changelog_lines))
        except Exception:
            pass

        update_task(task_id, "completed", ai_output)

        print("\n" + report)

    except Exception as e:
        update_task(task_id, "failed", str(e))
        raise


def _run_supervisor(args: list, gpt_mode: bool = False) -> None:
    """v0.3 autonomous supervisor mode."""
    import json
    from core.supervisor import run_supervisor
    from core.memory import full_state

    project = "market"
    if "--project" in args:
        idx = args.index("--project")
        project = args[idx + 1]

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    project_path = None
    for w in config.get("workers", []):
        if w.get("project") == project or w.get("project") == f"{project}-intelligence":
            project_path = w["directory"]
            break
    if not project_path:
        project_path = config.get("projects", {}).get(project, {}).get("path", "")

    if not project_path:
        print(f"ERROR: Unknown project '{project}'")
        sys.exit(1)

    print(f"Yundor Agent Bridge v0.3 — Supervisor Mode {'(GPT-managed)' if gpt_mode else '(Rule-based)'}")
    print(f"Project: {project}")
    print(f"Path: {project_path}")
    print()

    if gpt_mode:
        from core.gpt_supervisor import run_gpt_supervisor
        print("Starting GPT-managed supervisor...")
        result = run_gpt_supervisor(project_path)
    else:
        print("Starting rule-based supervisor...")
        result = run_supervisor(project_path)
    print()
    print(json.dumps({
        "status": result.get("status", "unknown"),
        "iterations": result.get("iterations", 0),
        "tasks_completed": result.get("tasks_completed", 0),
        "failures": result.get("failures", result.get("consecutive_failures", 0)),
        "decisions": result.get("decisions", []),
    }, ensure_ascii=False, indent=2))

    if result.get("status") == "paused":
        print(f"\n⚠️  Supervisor paused. Reason: {result.get('reason', 'unknown')}")
    elif result.get("status") == "blocked":
        print(f"\n⛔ Supervisor blocked. Reason: {result.get('reason', 'unknown')}")


if __name__ == "__main__":
    main()
