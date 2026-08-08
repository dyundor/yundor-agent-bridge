import yaml
import requests


def get_saved_session(config, project):
    project_config = config.get("projects", {}).get(project, {})
    return project_config.get("session_id")


def save_session(config_path, project, session_id):
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if "projects" not in config:
        config["projects"] = {}
    if project not in config["projects"]:
        config["projects"][project] = {}

    config["projects"][project]["session_id"] = session_id

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def clear_session(config_path, project):
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if "projects" in config and project in config["projects"]:
        config["projects"][project]["session_id"] = None

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def check_session_valid(url, session_id, auth=None):
    try:
        response = requests.get(
            f"{url.rstrip('/')}/session/{session_id}",
            auth=auth,
            timeout=10
        )
        return response.status_code == 200
    except requests.RequestException:
        return False
