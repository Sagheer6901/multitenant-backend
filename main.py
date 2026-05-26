import json
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from github_ci import GitHubCIError, run_deploy_pipeline
from registry import load_manifest, tenants_for_api, upsert_tenant

app = FastAPI(title="Tenants API")

STATIC_DIR = Path(__file__).parent / "static"


def reload_tenants() -> dict:
    manifest = load_manifest()
    tenants = tenants_for_api(manifest)
    app.state.tenants = tenants
    return tenants


@app.on_event("startup")
def on_startup() -> None:
    reload_tenants()
    if not STATIC_DIR.joinpath("portal.html").is_file():
        raise RuntimeError(f"Missing portal UI at {STATIC_DIR / 'portal.html'}")


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "tenants-api",
        "portal": "/portal",
        "message": "Agency owners: open /portal to register and auto-deploy to Play Store.",
    }


@app.get("/portal", response_class=HTMLResponse)
def agency_portal():
    portal_path = STATIC_DIR / "portal.html"
    return HTMLResponse(portal_path.read_text(encoding="utf-8"))


@app.get("/api/config")
def get_config(x_tenant_id: str = Header(..., alias="X-Tenant-ID")):
    tenants = getattr(app.state, "tenants", {})
    tenant = tenants.get(x_tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail=f"Tenant '{x_tenant_id}' not found")
    return {
        "tenant_id": x_tenant_id,
        "name": tenant["name"],
        "primary_color": tenant["primary_color"],
        "drivers": tenant["drivers"],
    }


@app.get("/api/agencies")
def list_agencies():
    return load_manifest()


@app.post("/api/agencies/register")
async def register_agency(
    tenant_id: str = Form(...),
    brand_name: str = Form(...),
    primary_color: str = Form(...),
    application_id: str = Form(...),
    play_json: str | None = Form(default=None),
    play_json_file: UploadFile | None = File(default=None),
):
    try:
        entry = upsert_tenant(
            tenant_id=tenant_id,
            brand_name=brand_name,
            primary_color=primary_color,
            application_id=application_id,
        )
        reload_tenants()

        play_payload: str | None = None
        if play_json_file and play_json_file.filename:
            raw = await play_json_file.read()
            play_payload = raw.decode("utf-8")
        elif play_json and play_json.strip():
            play_payload = play_json.strip()

        if not play_payload:
            raise HTTPException(
                status_code=400,
                detail="Play Store JSON key is required for automatic deployment.",
            )
        json.loads(play_payload)

        manifest = load_manifest()
        note = None
        pipeline: dict[str, str] = {}

        try:
            pipeline = run_deploy_pipeline(
                tenant_id=entry["id"],
                manifest=manifest,
                play_json=play_payload,
            )
        except GitHubCIError as exc:
            note = (
                f"Agency saved on API server, but cloud deploy was not triggered: {exc} "
                "Add GITHUB_TOKEN to Render and re-submit, or run GitHub Actions manually."
            )

        return {
            "status": "deploying",
            "message": "Automated build and Play Store upload started.",
            "tenant_id": entry["id"],
            "name": entry["name"],
            "primary_color": entry["primary_color"],
            "application_id": entry["application_id"],
            "upload_to_play": pipeline.get("upload_to_play", "true"),
            "commit_url": pipeline.get("commit_url"),
            "actions_url": pipeline.get("actions_url"),
            "note": note,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Play JSON key is not valid JSON.") from exc
