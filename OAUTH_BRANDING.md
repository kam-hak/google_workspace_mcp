# OAuth branding pages

Updated 2026-09-27.

The server provides two minimal public pages for a personal Calendar integration:

- `/app` describes the app purpose and links to the privacy notice.
- `/privacy` describes consented Calendar use and links to Google Account connections for revocation.

`BearerTokenGateMiddleware` exempts these exact paths. The `/mcp` endpoint still requires authentication. No OAuth scopes or client settings change through these routes.

Use the deployed URLs as the homepage and privacy notice in Google Auth Platform Branding. Publishing status is a separate setting in Google Auth Platform Audience.

After deploying, verify both pages return 200 and an unauthenticated `/mcp` request returns 401. Run the scoped regression with `uv run pytest tests/core/test_well_known_cache_control_middleware.py -q`.
