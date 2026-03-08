# Debug status report — 2026-03-07

## Repo and environment
- Repo path: `/home/workspace/projects_master/google_workspace_mcp`
- Remote: `https://github.com/kam-hak/google_workspace_mcp.git`
- Target branch: `codex/fork-policy-phase1`
- Baseline commit when this debugging session started: `f7609b7b9a43e12779c5e8988d0f57d4bd3e56c5`
- Public MCP auth service used for debugging: `https://gwmcp-auth-kamran.zocomputer.io`
- Local service port: `8011`

## Goal
Deploy and smoke-test the fork under the intended safety policy:
- calendar writes only to primary calendar
- empty attendee allowlist by default
- no invites / no guest invite permissions
- Gmail access limited to readonly
- Calendar access allowed for write operations on primary only

## Fork delta understood
Relevant files reviewed:
- `/home/workspace/projects_master/google_workspace_mcp/MAINTAINING.md`
- `/home/workspace/projects_master/google_workspace_mcp/gcalendar/calendar_policy.py`
- `/home/workspace/projects_master/google_workspace_mcp/gcalendar/calendar_tools.py`
- `/home/workspace/projects_master/google_workspace_mcp/tests/test_calendar_policy.py`
- `/home/workspace/projects_master/google_workspace_mcp/tests/test_calendar_tools_policy.py`

What the fork policy does:
- denies calendar writes unless `WORKSPACE_MCP_ALLOWED_CALENDAR_IDS` is set and contains the target calendar
- denies any attendee not in `WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS`
- allows empty attendee list when the allowlist is empty
- rejects `guestsCanInviteOthers=True`
- validates existing event attendees on modify/delete as well

## What was verified successfully
1. Repo was already present under the requested root and was updated.
2. Branch/commit checked out successfully.
3. Dev dependencies installed with `uv sync --group dev`.
4. Targeted tests passed.
   - Command run: `uv run pytest tests/test_calendar_policy.py tests/test_calendar_tools_policy.py tests/test_main_permissions_tier.py tests/test_permissions.py tests/test_scopes.py -q`
   - Result: `79 passed`
5. Policy-reduced service was brought up using granular permissions:
   - `gmail:readonly`
   - `calendar:full`
6. Tool filtering logs confirmed Gmail write tools were disabled.

## Behavior observed
### Initial auth failure mode
The fork had no reusable local credentials in its default credential store, so CLI smoke-test attempts triggered OAuth.

Early failures:
- port 8000 collision from a `hashcards` process
- after that was removed, the OAuth flow still failed because the auth URL was generated from a short-lived CLI process while the callback was handled by a different long-running service process

Observed error:
- `Invalid or expired OAuth state parameter`

Why this mattered:
- the CLI process stored OAuth state only in memory
- the callback hit a different process with a different in-memory state store
- therefore the callback could not validate the returned state

### Later auth failure mode after state persistence patch
After patching state persistence, the flow advanced further.

Observed later error:
- Google returned an authorization code to the callback endpoint
- token exchange then failed with: `(redirect_uri_mismatch) Bad Request`

This is the current blocker.

## What I think is wrong now
Most likely remaining issue:
- the effective redirect URI and/or client configuration used during token exchange does not exactly match what Google expects, even though the browser step and Google Cloud console screenshot appear aligned

Why I think that:
1. The callback route receives a real authorization `code`, so the browser-facing authorization request is not the main blocker anymore.
2. The failure occurs inside `flow.fetch_token(...)`, which points at token exchange, not the initial consent redirect.
3. The screenshot shows the correct authorized redirect URI present on the web OAuth client.
4. The running service was updated to use:
   - `WORKSPACE_EXTERNAL_URL=https://gwmcp-auth-kamran.zocomputer.io`
   - `GOOGLE_OAUTH_REDIRECT_URI=https://gwmcp-auth-kamran.zocomputer.io/oauth2callback`
5. A fresh process confirmed `get_oauth_redirect_uri()` resolves to the external callback URL when those env vars are set.

So the remaining hypotheses are narrow:
- token exchange is still using a different redirect URI than intended
- the running process is loading different client credentials than expected
- there is some interaction in the Google auth library between stored client config and redirect URI selection that still needs instrumentation

## Things tried
### Repo and branch handling
- cloned or reused repo under `/home/workspace/projects_master/google_workspace_mcp`
- fetched updates
- checked out branch `codex/fork-policy-phase1`
- detached to commit `f7609b7b9a43e12779c5e8988d0f57d4bd3e56c5`

### Code and docs inspection
Read these files to understand policy and auth flow:
- `/home/workspace/projects_master/google_workspace_mcp/MAINTAINING.md`
- `/home/workspace/projects_master/google_workspace_mcp/main.py`
- `/home/workspace/projects_master/google_workspace_mcp/README.md`
- `/home/workspace/projects_master/google_workspace_mcp/pyproject.toml`
- `/home/workspace/projects_master/google_workspace_mcp/auth/service_decorator.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/credential_store.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/oauth_config.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/google_auth.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/oauth_callback_server.py`
- `/home/workspace/projects_master/google_workspace_mcp/core/server.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/permissions.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/scopes.py`

### Test and verification steps
- ran dev sync
- ran targeted tests
- listed services and inspected service health
- inspected repo logs and auth logs

### Service and auth attempts
1. Tried CLI smoke test directly.
   - blocked by missing local credentials and then by OAuth callback server issues
2. Removed the conflicting `hashcards` process on port 8000.
3. Created a public service for the fork so auth could use an external callback URL.
4. Initially exposed the service with broad tool loading; later tightened to granular permissions.
5. Regenerated auth URLs multiple times.
6. Confirmed the old failure mode was `Invalid or expired OAuth state parameter`.
7. Patched OAuth state persistence to disk so state could survive across processes.
8. Restarted the hosted service after the patch.
9. Confirmed the new failure mode moved downstream to `(redirect_uri_mismatch) Bad Request`.
10. Updated hosted service env to explicitly include external callback config.

### Scope reduction work
The auth request was originally too broad because startup used service-level loading that included many scopes.

I changed the hosted service entrypoint to use granular permissions:
- `--permissions gmail:readonly calendar:full`

That reduced access to the intended surfaces.

## Code change made in this session
### OAuth state persistence patch
File changed:
- `/home/workspace/projects_master/google_workspace_mcp/auth/oauth21_session_store.py`

Purpose:
- persist OAuth state entries to a shared JSON file so state created by one process can be consumed by another process handling the callback

Effect:
- fixed the earlier cross-process state loss problem
- moved the auth failure from `Invalid or expired OAuth state parameter` to the later token-exchange-stage `redirect_uri_mismatch`

### OAuth env precedence patch
Files changed:
- `/home/workspace/projects_master/google_workspace_mcp/auth/google_auth.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/oauth_config.py`

Purpose:
- prefer app-specific `WORKSPACE_GOOGLE_OAUTH_*` variables over generic `GOOGLE_OAUTH_*`
- avoid accidentally inheriting Zo-level Google OAuth credentials inside the hosted service runtime

Expected effect:
- the fork should load Kamran's intended Google OAuth client ID and secret first
- this should remove the most likely client-config mismatch behind the remaining `redirect_uri_mismatch` failure

## Hosted service configuration used near the end
Service label:
- `gwmcp-auth`

Service URL:
- `https://gwmcp-auth-kamran.zocomputer.io`

Effective startup mode:
- `uv run python main.py --transport streamable-http --single-user --permissions gmail:readonly calendar:full`

Key env vars set on the service:
- `WORKSPACE_MCP_ALLOWED_CALENDAR_IDS=primary`
- `WORKSPACE_MCP_ALLOWED_ATTENDEE_EMAILS=`
- `WORKSPACE_EXTERNAL_URL=https://gwmcp-auth-kamran.zocomputer.io`
- `GOOGLE_OAUTH_REDIRECT_URI=https://gwmcp-auth-kamran.zocomputer.io/oauth2callback`

## Smoke test status
Not completed.

Blocked operations:
- send test email with subject beginning `TEST-ZO-MCP`
- create calendar event named `TEST-TODELETE`
- delete that event

Reason blocked:
- OAuth/token exchange is not completing successfully for the fork

## Highest-value artifacts on disk
### Repo and code
- `/home/workspace/projects_master/google_workspace_mcp`
- `/home/workspace/projects_master/google_workspace_mcp/auth/oauth21_session_store.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/google_auth.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/oauth_config.py`
- `/home/workspace/projects_master/google_workspace_mcp/core/server.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/permissions.py`
- `/home/workspace/projects_master/google_workspace_mcp/auth/scopes.py`
- `/home/workspace/projects_master/google_workspace_mcp/DEBUG_STATUS_REPORT_2026-03-07.md`

### Logs and generated artifacts
- `/home/workspace/projects_master/google_workspace_mcp/mcp_server_debug.log`
- `/root/.google_workspace_mcp/credentials/oauth_states.json`
- `/home/workspace/projects_master/google_workspace_mcp/google-auth-url.md`

### Supporting evidence files outside the repo
- `/home/.z/chat-images/Screenshot 2026-03-07 at 18.02.45.png`
- `/home/.z/workspaces/con_IwYi3HS8yD0XItcA/read_webpage/gwmcp-auth-kamran.zocomputer.io.md`
- `/home/.z/workspaces/con_IwYi3HS8yD0XItcA/read_webpage/gwmcp-auth-kamran.zocomputer.io.html`

## What a debugging engineer should do next
1. Add temporary logging around auth URL creation and token exchange in `/home/workspace/projects_master/google_workspace_mcp/auth/google_auth.py`:
   - client ID actually loaded
   - redirect URI passed into flow creation
   - redirect URI on the flow object immediately before `fetch_token(...)`
2. Confirm the running hosted service process is definitely using the same client ID and redirect URI the screenshot shows.
3. Verify no stale file-based client secret config is taking precedence over env-based config.
4. Re-run a single fresh auth attempt and compare:
   - authorization URL redirect URI
   - callback URL received
   - token exchange redirect URI used by the library

## Short conclusion
The calendar policy fork itself looks correct and tests pass.
The current blocker is not policy logic; it is the Google OAuth completion path.
A cross-process OAuth state bug was found and patched. After that fix, the auth flow now fails later during token exchange with `redirect_uri_mismatch`, despite the redirect appearing correctly configured in Google Cloud. The most likely remaining issue is an end-to-end redirect URI or client-config mismatch inside the app runtime during token exchange.
