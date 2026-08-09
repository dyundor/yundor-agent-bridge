def get_execution_policy(project):

    if project == "market":
        return """# Yundor Market Intelligence Execution Policy

## Allowed

- Modify files inside target project
- Create new files
- Run tests, lint, build
- Run existing npm scripts
- Read database files for research
- Execute git add, git commit (with proper Sprint message format)
- Create new API routes, components, lib modules per Sprint goals

## Forbidden

- Modify files outside target project
- Access unrelated projects
- Delete files without approval
- Modify credentials or secrets (.env files)
- Execute git push
- Call paid APIs (ImportYeti) without explicit approval
- Call paid APIs during tests
- Use git reset --hard or destructive git operations
- Overwrite user's uncommitted changes (AGENTS.md, PROJECT_STATE.md, PROJECT_DECISIONS.md)
- NULL out existing database values
- Fake or fabricate contact info, product images, sales data
- Claim aggregate trade statistics as shipment-level data

## Data Preservation

- NULL never overwrites existing values (use COALESCE)
- Missing website must not delete existing website
- Missing address must not delete existing address
- Lower quality data must not replace richer enrichment data
- Never NULL-out to "correct"; mark as unverified instead
- Preserve raw external data for rebuildable rankings

## Git Rules

- Commit message format: Sprint XX.XX: Short description
- Only stage files relevant to the Sprint
- Report commit hash after each commit
- Never force push or reset

## Reporting

After execution report:

- Sprint completed
- Files changed with commit hash
- Technical changes
- Validation (tests, build)
- Credit usage (always 0 unless paid API was used)
- Risks and next step
"""

    return """# Execution Policy

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
