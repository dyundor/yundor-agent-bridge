import os
from datetime import date


def append_changelog(project_path, content):

    try:
        project_name = os.path.basename(project_path)

        memory_dir = os.path.join("memory", project_name)

        os.makedirs(memory_dir, exist_ok=True)

        filepath = os.path.join(memory_dir, "CHANGELOG.md")

        today = date.today().isoformat()

        entry = f"\n## {today}\n\n{content}\n"

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)

        return "success"

    except Exception:
        return "failure"
