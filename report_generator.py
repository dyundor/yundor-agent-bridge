from report_parser import parse_report


def generate_report(project, task, before_commit, after_commit, diff_summary, ai_output):
    parsed = parse_report(ai_output)
    next_step = parsed.get("next_step", "")

    return f"""# Sprint Bridge Report

## Project

{project}

## Task

{task}

## Git Changes

Before Commit:
{before_commit}

After Commit:
{after_commit}

Changed Files:
{diff_summary}

## AI Summary

{ai_output}

## Next Step

{next_step}
"""
