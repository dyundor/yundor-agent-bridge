import os


def get_memory(project_path):

    project_name = os.path.basename(project_path)

    memory_dir = os.path.join("memory", project_name)

    files = {
        "project_memory": "PROJECT_MEMORY.md",
        "decisions": "DECISIONS.md",
        "changelog": "CHANGELOG.md",
    }

    result = {}

    for key, filename in files.items():
        filepath = os.path.join(memory_dir, filename)

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                result[key] = f.read()
        else:
            result[key] = ""

    return result
