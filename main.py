import sys
import yaml

from opencode_client import OpenCodeClient
from project_reader import read_project_context
from git_manager import git_status
from report_parser import extract_text
from session_manager import (
    get_saved_session,
    save_session,
    clear_session,
    check_session_valid,
)


def main():

    args = sys.argv[1:]

    project = "market"

    if "--project" in args:
        index = args.index("--project")
        project = args[index + 1]
        args.pop(index)
        args.pop(index)

    task = " ".join(args)

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

    prompt = f"""

你现在负责项目：

路径：
{project_path}


项目上下文：

{context}



Git状态：

{git_before}



任务：

{task}


规则：

1. 不要修改代码，除非明确要求。
2. 输出清晰总结。
3. 如果发现问题，给实施建议。


"""

    print("\n发送任务...")

    result = client.send_message(session_id, prompt)

    print("\n===== DeepSeek 输出 =====")

    print(extract_text(result))


if __name__ == "__main__":
    main()
