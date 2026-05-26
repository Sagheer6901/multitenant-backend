import base64
import json
import os
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"
WORKFLOW_FILE = "deploy_tenants.yml"


class GitHubCIError(Exception):
    pass


def _settings() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    owner = os.getenv("GITHUB_OWNER", "Sagheer6901").strip()
    mobile_repo = os.getenv("GITHUB_MOBILE_REPO", "multitenant-mobile").strip()
    if not token:
        raise GitHubCIError(
            "GITHUB_TOKEN is not configured on the server. "
            "Set it in Render environment variables."
        )
    return {
        "token": token,
        "owner": owner,
        "mobile_repo": mobile_repo,
    }


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def mobile_manifest_from(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "api_base_url": manifest.get(
            "api_base_url", "https://multitenant-backend-ml5h.onrender.com"
        ),
        "tenants": [
            {
                "id": entry["id"],
                "name": entry["name"],
                "primary_color": entry["primary_color"],
                "application_id": entry["application_id"],
            }
            for entry in manifest.get("tenants", [])
        ],
    }


def sync_mobile_agencies_manifest(manifest: dict[str, Any]) -> str:
    cfg = _settings()
    path = "agencies.json"
    content = json.dumps(mobile_manifest_from(manifest), indent=2) + "\n"
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

    with httpx.Client(timeout=60.0) as client:
        repo = f"{cfg['owner']}/{cfg['mobile_repo']}"
        get_url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
        response = client.get(get_url, headers=_headers(cfg["token"]))
        payload: dict[str, Any] = {
            "message": f"Portal: update agencies.json ({len(manifest.get('tenants', []))} tenants)",
            "content": encoded,
        }
        if response.status_code == 200:
            payload["sha"] = response.json()["sha"]

        put_response = client.put(
            get_url,
            headers=_headers(cfg["token"]),
            json=payload,
        )
        if put_response.status_code not in (200, 201):
            raise GitHubCIError(
                f"Failed to update {path} on {repo}: {put_response.text}"
            )
        return put_response.json()["commit"]["html_url"]


def set_play_service_account_secret(play_json: str) -> None:
    """Store Play Console JSON in PLAY_SERVICE_ACCOUNT_JSON for the next workflow run."""
    from nacl import encoding, public

    cfg = _settings()
    repo = f"{cfg['owner']}/{cfg['mobile_repo']}"

    with httpx.Client(timeout=60.0) as client:
        key_response = client.get(
            f"{GITHUB_API}/repos/{repo}/actions/secrets/public-key",
            headers=_headers(cfg["token"]),
        )
        if key_response.status_code != 200:
            raise GitHubCIError(f"Unable to fetch repo public key: {key_response.text}")

        key_data = key_response.json()
        public_key = public.PublicKey(
            key_data["key"].encode("utf-8"),
            encoding.Base64Encoder(),
        )
        sealed_box = public.SealedBox(public_key)
        encrypted = sealed_box.encrypt(play_json.encode("utf-8"))
        encrypted_value = base64.b64encode(encrypted).decode("utf-8")

        secret_response = client.put(
            f"{GITHUB_API}/repos/{repo}/actions/secrets/PLAY_SERVICE_ACCOUNT_JSON",
            headers=_headers(cfg["token"]),
            json={
                "encrypted_value": encrypted_value,
                "key_id": key_data["key_id"],
            },
        )
        if secret_response.status_code not in (201, 204):
            raise GitHubCIError(
                f"Failed to store Play JSON secret: {secret_response.text}"
            )


def trigger_mobile_deploy(tenant_id: str, *, upload_to_play: bool = True) -> str:
    cfg = _settings()
    repo = f"{cfg['owner']}/{cfg['mobile_repo']}"

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{GITHUB_API}/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/dispatches",
            headers=_headers(cfg["token"]),
            json={
                "ref": "main",
                "inputs": {
                    "tenant_key": tenant_id,
                    "upload_to_play": "true" if upload_to_play else "false",
                },
            },
        )
        if response.status_code != 204:
            raise GitHubCIError(f"Failed to trigger workflow: {response.text}")

        runs_response = client.get(
            f"{GITHUB_API}/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs",
            headers=_headers(cfg["token"]),
            params={"per_page": 1},
        )
        if runs_response.status_code == 200 and runs_response.json().get("workflow_runs"):
            return runs_response.json()["workflow_runs"][0]["html_url"]
        return f"https://github.com/{repo}/actions"


def run_deploy_pipeline(
    *,
    tenant_id: str,
    manifest: dict[str, Any],
    play_json: str | None,
) -> dict[str, str]:
    commit_url = sync_mobile_agencies_manifest(manifest)
    upload_to_play = False
    if play_json:
        set_play_service_account_secret(play_json)
        upload_to_play = True
    actions_url = trigger_mobile_deploy(tenant_id, upload_to_play=upload_to_play)
    return {
        "commit_url": commit_url,
        "actions_url": actions_url,
        "upload_to_play": str(upload_to_play).lower(),
    }
