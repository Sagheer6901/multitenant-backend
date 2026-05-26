# Render environment (one-time, platform team only)

Add these env vars on https://dashboard.render.com for **multitenant-backend**:

| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` | PAT with `repo`, `workflow`, `actions:write` — triggers CI & updates `agencies.json` |
| `GITHUB_OWNER` | `Sagheer6901` |
| `GITHUB_MOBILE_REPO` | `multitenant-mobile` |

Agency owners only use **https://multitenant-backend-ml5h.onrender.com/portal** — no GitHub access needed.

GitHub repo **multitenant-mobile** secrets (platform team, once):

- `BASE64_KEYSTORE_DATA`
- `SIGNING_STORE_PASSWORD`
- `SIGNING_KEY_ALIAS`
- `SIGNING_KEY_PASSWORD`

`PLAY_SERVICE_ACCOUNT_JSON` is set automatically per agency when they submit the portal form.
