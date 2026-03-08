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

## Hosted Contract

This fork's canonical deployment target is a Zo-hosted remote MCP server that uses streamable HTTP plus bearer-token access control.

High-level hosted behavior:
- Gmail access is intended to remain read-oriented.
- Calendar reads are allowed.
- Calendar writes and edits are allowed only when server-side policy permits them.
- Policy must stay fail-closed: unallowlisted calendars, disallowed attendees, and unsafe guest-invite settings should be rejected by the server.

Current policy shape is env-configured. At minimum, review these together when changing behavior:
- `GWORKSPACE_REMOTE_MCP_TOKEN`
- `WORKSPACE_MCP_ALLOWED_CALENDAR_IDS`
- `WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS`
- `WORKSPACE_GOOGLE_OAUTH_CLIENT_ID`
- `WORKSPACE_GOOGLE_OAUTH_CLIENT_SECRET`

When hosted policy changes, update these together:
- `gcalendar/calendar_policy.py`
- `gcalendar/calendar_tools.py`
- related calendar policy tests
- `README.md`
- this file

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
