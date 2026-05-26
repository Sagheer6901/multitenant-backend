import json
import re
from pathlib import Path
from typing import Any

AGENCIES_PATH = Path(__file__).parent / "agencies.json"

TENANT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
APP_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def load_manifest() -> dict[str, Any]:
    with AGENCIES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_manifest(manifest: dict[str, Any]) -> None:
    with AGENCIES_PATH.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def validate_tenant_id(tenant_id: str) -> str:
    tenant_id = tenant_id.strip().lower()
    if not TENANT_ID_PATTERN.match(tenant_id):
        raise ValueError(
            "Tenant ID must be 3–32 chars, lowercase, start with a letter "
            "(letters, numbers, underscores only)."
        )
    return tenant_id


def validate_application_id(application_id: str) -> str:
    application_id = application_id.strip().lower()
    if not APP_ID_PATTERN.match(application_id):
        raise ValueError("Application ID must look like com.company.appname")
    return application_id


def validate_color(primary_color: str) -> str:
    primary_color = primary_color.strip()
    if not COLOR_PATTERN.match(primary_color):
        raise ValueError("Primary color must be a hex value like #FF5722")
    return primary_color.upper()


def default_drivers(tenant_id: str) -> list[dict[str, str]]:
    return [
        {
            "id": f"drv_{tenant_id}_001",
            "name": "Driver One",
            "status": "available",
        },
        {
            "id": f"drv_{tenant_id}_002",
            "name": "Driver Two",
            "status": "on_trip",
        },
    ]


def tenants_for_api(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tenants: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("tenants", []):
        tenant_id = entry["id"]
        tenants[tenant_id] = {
            "name": entry["name"],
            "primary_color": entry["primary_color"],
            "drivers": entry.get("drivers") or default_drivers(tenant_id),
        }
    return tenants


def upsert_tenant(
    *,
    tenant_id: str,
    brand_name: str,
    primary_color: str,
    application_id: str,
) -> dict[str, Any]:
    tenant_id = validate_tenant_id(tenant_id)
    brand_name = brand_name.strip()
    if len(brand_name) < 2:
        raise ValueError("Brand name is required.")
    primary_color = validate_color(primary_color)
    application_id = validate_application_id(application_id)

    manifest = load_manifest()
    tenants: list[dict[str, Any]] = manifest.setdefault("tenants", [])
    entry = {
        "id": tenant_id,
        "name": brand_name,
        "primary_color": primary_color,
        "application_id": application_id,
    }

    for index, existing in enumerate(tenants):
        if existing.get("id") == tenant_id:
            entry["drivers"] = existing.get("drivers") or default_drivers(tenant_id)
            tenants[index] = entry
            break
    else:
        entry["drivers"] = default_drivers(tenant_id)
        tenants.append(entry)

    save_manifest(manifest)
    return entry
