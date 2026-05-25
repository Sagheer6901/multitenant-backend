from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="Tenants API")

TENANTS = {
    "sandbox_test": {
        "name": "Sandbox Transit",
        "primary_color": "#4CAF50",
        "drivers": [
            {"id": "drv_001", "name": "Alex Rivera", "status": "available"},
            {"id": "drv_002", "name": "Jordan Lee", "status": "on_trip"},
            {"id": "drv_003", "name": "Sam Patel", "status": "offline"},
        ],
    },
    "agency_alpha": {
        "name": "Alpha Rides",
        "primary_color": "#FF5722",
        "drivers": [
            {"id": "drv_101", "name": "Morgan Chen", "status": "available"},
            {"id": "drv_102", "name": "Taylor Brooks", "status": "available"},
            {"id": "drv_103", "name": "Casey Nguyen", "status": "on_trip"},
            {"id": "drv_104", "name": "Riley Adams", "status": "offline"},
        ],
    },
}


@app.get("/")
def root():
    return {"status": "ok", "service": "tenants-api"}


@app.get("/api/config")
def get_config(x_tenant_id: str = Header(..., alias="X-Tenant-ID")):
    tenant = TENANTS.get(x_tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail=f"Tenant '{x_tenant_id}' not found")
    return {
        "tenant_id": x_tenant_id,
        "name": tenant["name"],
        "primary_color": tenant["primary_color"],
        "drivers": tenant["drivers"],
    }
