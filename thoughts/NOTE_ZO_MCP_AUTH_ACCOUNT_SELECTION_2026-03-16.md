# Zo MCP Auth Account Selection Note

Date: 2026-03-16

Summary:
- The live Zo MCP was working at the transport layer and accepted the remote bearer token.
- The persistent auth confusion was not primarily OAuth 2.0 vs OAuth 2.1.
- In single-user mode, the server was selecting the first credential file it found, which caused it to try `kah411@pitt.edu` before `klhakiman@gmail.com`.

Why this mattered:
- `kah411@pitt.edu` is only meant to be an allowed invitee, not the authenticated Gmail account for the MCP.
- Zo logs showed refresh attempts against `kah411@pitt.edu`, including `invalid_grant`, before later fallback to `klhakiman@gmail.com`.
- This made auth behavior look intermittent and confusing even when the public MCP and bearer token were functioning.

Actions taken:
- Patched `auth/google_auth.py` so single-user mode prefers the requested `user_google_email` when selecting stored credentials.
- Added regression tests covering preferred-user selection behavior.
- On Zo, moved `/root/.google_workspace_mcp/credentials/kah411@pitt.edu.json` into a quarantine subdirectory so it is no longer considered an active credential.

Observed result:
- Fresh Zo logs after the credential cleanup showed:
  - `[single-user] Found credentials for klhakiman@gmail.com via credential store`
- This is the desired path and avoids the previous cross-account credential pick.

Remaining note:
- The Zo deployment is still running legacy single-user OAuth 2.0 mode with the outer MCP bearer-token gate.
- That broader auth architecture was not changed here; this note only captures the account-selection fix and credential cleanup.
