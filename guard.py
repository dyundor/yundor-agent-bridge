import os
import yaml


FORBIDDEN_NAMES = {
    ".ssh",
    ".aws",
    ".gnupg",
}

FORBIDDEN_PREFIXES = [
    "/Library/Keychains",
]


def allowed_path(path):

    with open(
        "config.yaml",
        "r"
    ) as f:

        config = yaml.safe_load(f)


    projects = config["projects"]


    real = os.path.realpath(path)


    for name in projects:

        project_path = projects[name]["path"]

        project_real = os.path.realpath(project_path)

        if real == project_real or real.startswith(project_real + os.sep):

            return True


    return False


def check_path_security(path):

    real = os.path.realpath(path)


    parts = [
        p for p in real.split(os.sep) if p
    ]


    for part in parts:

        if part in FORBIDDEN_NAMES:

            return {
                "allowed": False,
                "reason": "restricted directory"
            }


    for prefix in FORBIDDEN_PREFIXES:

        if real == prefix or real.startswith(prefix + os.sep):

            return {
                "allowed": False,
                "reason": "restricted directory"
            }


    return {
        "allowed": True
    }


def validate_project(path):

    real = os.path.realpath(path)


    if not os.path.exists(real):

        raise ValueError(
            f"path does not exist: {path}"
        )


    if not os.path.isdir(real):

        raise ValueError(
            f"path is not a directory: {path}"
        )


    result = check_path_security(real)


    if not result["allowed"]:

        raise ValueError(
            f"restricted directory: {path}"
        )


    return True
