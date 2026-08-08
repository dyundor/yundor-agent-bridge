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


def get_commit_hash(path):

    try:

        result = subprocess.check_output(
            [
                "git",
                "-C",
                path,
                "rev-parse",
                "HEAD"
            ],
            stderr=subprocess.DEVNULL,
            text=True
        )

        return result.strip()


    except Exception:

        return "N/A"


def get_diff_summary(path):

    try:

        result = subprocess.check_output(
            [
                "git",
                "-C",
                path,
                "diff",
                "--stat"
            ],
            stderr=subprocess.DEVNULL,
            text=True
        )

        return result.strip() or "clean"


    except Exception:

        return "N/A"


def get_diff_between(path, before, after):

    try:

        result = subprocess.check_output(
            [
                "git",
                "-C",
                path,
                "diff",
                "--stat",
                f"{before}..{after}"
            ],
            stderr=subprocess.DEVNULL,
            text=True
        )

        return result.strip() or "no diff"


    except Exception:

        return "N/A"
