#!/usr/bin/env python3
"""Configure Render service env vars and trigger deploy via Render API."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.render.com/v1"
SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "multitenant-backend")


def request(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def find_service_id(token: str) -> str:
    cursor = None
    while True:
        path = "/services?limit=50"
        if cursor:
            path += f"&cursor={cursor}"
        payload = request("GET", path, token)
        for item in payload:
            service = item.get("service") or item
            name = service.get("name") or service.get("serviceDetails", {}).get("name")
            if name == SERVICE_NAME:
                return service["id"]
        cursor = payload[-1].get("cursor") if payload else None
        if not cursor:
            break
    raise RuntimeError(f"Render service '{SERVICE_NAME}' not found")


def main() -> int:
    token = os.getenv("RENDER_API_KEY", "").strip()
    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        print("RENDER_API_KEY is required", file=sys.stderr)
        return 1
    if not github_token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 1

    service_id = find_service_id(token)
    print(f"Found service: {service_id}")

    env_vars = [
        {"key": "GITHUB_TOKEN", "value": github_token},
        {"key": "GITHUB_OWNER", "value": os.getenv("GITHUB_OWNER", "Sagheer6901")},
        {
            "key": "GITHUB_MOBILE_REPO",
            "value": os.getenv("GITHUB_MOBILE_REPO", "multitenant-mobile"),
        },
    ]
    request("PUT", f"/services/{service_id}/env-vars", token, env_vars)
    print("Environment variables updated")

    deploy = request("POST", f"/services/{service_id}/deploys", token, {})
    deploy_id = deploy.get("id") or deploy.get("deploy", {}).get("id")
    print(f"Deploy triggered: {deploy_id or deploy}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
