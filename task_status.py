from task_manager import list_tasks


def get_status_summary():

    tasks = list_tasks()

    summary = {
        "pending": [],
        "running": [],
        "failed": [],
        "completed": [],
    }

    for task in tasks:
        task_id = task.get("id", "")
        status = task.get("status", "")

        if status in summary:
            summary[status].append(task_id)

    return summary
