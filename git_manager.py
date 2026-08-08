import subprocess


def git_status(path):

    try:

        result = subprocess.check_output(
            [
                "git",
                "-C",
                path,
                "status",
                "--short"
            ],
            stderr=subprocess.DEVNULL,
            text=True
        )

        return result.strip() or "clean"


    except Exception:

        return "not a git repository"