def get_execution_policy(project):

    return f"""# Execution Policy

## Allowed

- Modify files inside target project
- Create new files
- Run tests

## Forbidden

- Modify files outside target project
- Access unrelated projects
- Delete files without approval
- Modify credentials or secrets
- Execute git push

## Reporting

After execution report:

- Modified files
- Tests
- Next steps
"""
