# Maintaining This Fork

- Upstream remote: `https://github.com/taylorwilsdon/google_workspace_mcp.git`
- Baseline upstream commit for this patch series: `6a2633984a85e8d281f6568201c24d787e74ccc8`

## Fork Policy Surface

Keep custom behavior limited to:
- `gcalendar/calendar_policy.py`
- `gcalendar/calendar_tools.py`
- related calendar policy tests
- related documentation updates

Do not broaden the fork delta unless a new requirement explicitly needs it.

## Merge Workflow

1. `git fetch upstream`
2. merge or rebase `upstream/main`
3. rerun `uv sync --group dev`
4. rerun `uv run pytest`
5. inspect `gcalendar/calendar_tools.py`, `main.py`, and related calendar tests first for conflicts or behavior drift

## Maintenance Rules

- Preserve upstream CLI and permission behavior unless the calendar policy layer explicitly needs a change.
- Keep policy behavior env-configured and fail closed.
- Keep secrets, OAuth tokens, and local registration details out of git.
