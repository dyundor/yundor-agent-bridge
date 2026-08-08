import os


FILES = [
    "AGENTS.md",
    "PROJECT_STATE.md",
    "PROJECT_DECISIONS.md"
]


def read_project_context(path):

    result = ""


    for file in FILES:

        full = os.path.join(
            path,
            file
        )


        if os.path.exists(full):

            result += f"\n\n===== {file} =====\n"

            with open(
                full,
                "r",
                encoding="utf-8"
            ) as f:

                result += f.read()


    return result