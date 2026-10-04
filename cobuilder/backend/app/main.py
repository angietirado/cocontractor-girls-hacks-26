from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, SecretStr

from app.config import save_connection_settings, settings
from app.models import FloorplanScene
from app.services.foundry_client import FoundryService, load_image

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"

app = FastAPI(
    title="CoBuilder",
    description="AI floorplan → 3D visualization & renovation planning powered by Azure AI Foundry",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_foundry: FoundryService | None = None


def get_foundry() -> FoundryService:
    global _foundry
    if _foundry is None:
        try:
            _foundry = FoundryService()
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _foundry


def connection_settings_response() -> dict:
    return {
        "foundry_project_endpoint": settings.foundry_project_endpoint,
        "foundry_agent_name": settings.foundry_agent_name,
        "foundry_model": settings.foundry_model,
        "azure_credential_mode": settings.azure_credential_mode,
        "azure_tenant_id": settings.azure_tenant_id,
        "azure_client_id": settings.azure_client_id,
        "has_client_secret": bool(settings.azure_client_secret),
    }


class ConnectionSettingsUpdate(BaseModel):
    foundry_project_endpoint: str | None = None
    foundry_agent_name: str | None = None
    foundry_model: str | None = None
    azure_credential_mode: str | None = None
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_client_secret: SecretStr | None = None
    clear_client_secret: bool = False


@app.get("/api/settings")
def get_connection_settings():
    return connection_settings_response()


@app.put("/api/settings")
def update_connection_settings(body: ConnectionSettingsUpdate):
    global _foundry
    values = body.model_dump(exclude_unset=True)
    clear_secret = values.pop("clear_client_secret", False)
    secret = values.pop("azure_client_secret", None)
    values = {key: value for key, value in values.items() if value is not None}

    if values.get("azure_credential_mode") not in (None, "default", "service_principal"):
        raise HTTPException(400, "Unsupported Azure credential mode.")
    endpoint = values.get("foundry_project_endpoint")
    if endpoint is not None and (not endpoint.startswith(("https://", "http://")) or not endpoint.strip()):
        raise HTTPException(400, "Foundry project endpoint must be a valid HTTP or HTTPS URL.")
    if values.get("foundry_model") == "":
        raise HTTPException(400, "Model deployment cannot be blank.")

    credentials = {
        "azure_credential_mode": settings.azure_credential_mode,
        "azure_tenant_id": settings.azure_tenant_id,
        "azure_client_id": settings.azure_client_id,
        "azure_client_secret": settings.azure_client_secret,
    }
    credentials.update({key: value for key, value in values.items() if key.startswith("azure_")})
    if secret is not None:
        credentials["azure_client_secret"] = secret.get_secret_value()
    if clear_secret:
        credentials["azure_client_secret"] = ""

    if credentials["azure_credential_mode"] == "service_principal":
        if not all((credentials["azure_tenant_id"], credentials["azure_client_id"], credentials["azure_client_secret"])):
            raise HTTPException(400, "Service principal mode requires tenant ID, client ID, and client secret.")

    if secret is not None:
        values["azure_client_secret"] = secret.get_secret_value()
    if clear_secret:
        values["azure_client_secret"] = ""
    if values:
        save_connection_settings(values)
        _foundry = None
    return connection_settings_response()


ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


@app.get("/api/health")
def health():
    configured = bool(Path(ROOT / ".env").exists())
    return {"status": "ok", "service": "CoBuilder", "env_configured": configured}


@app.post("/api/analyze-floorplan", response_model=FloorplanScene)
async def analyze_floorplan(
    file: UploadFile = File(...),
    hints: str = Form(""),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 20 MB)")

    try:
        scene = get_foundry().analyze_floorplan(data, file.content_type, hints)
        return FloorplanScene.model_validate(scene)
    except Exception as exc:
        raise HTTPException(502, f"Azure AI Foundry error: {exc}") from exc


class RenovationRequest(BaseModel):
    scene: FloorplanScene
    request: str


@app.post("/api/plan-renovation")
async def plan_renovation(body: RenovationRequest):
    try:
        plan_text = get_foundry().plan_renovation(body.scene.model_dump(), body.request)
        return {"plan": plan_text}
    except Exception as exc:
        raise HTTPException(502, f"Azure AI Foundry error: {exc}") from exc


@app.post("/api/chat")
async def chat(message: str = Form(...), conversation_id: str | None = Form(None)):
    try:
        reply, conv_id = get_foundry().chat(message, conversation_id)
        return {"reply": reply, "conversation_id": conv_id}
    except Exception as exc:
        raise HTTPException(502, f"Azure AI Foundry error: {exc}") from exc


if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.get("/")
def index():
    index_path = FRONTEND / "index.html"
    if not index_path.exists():
        raise HTTPException(404, "Frontend not found")
    return FileResponse(index_path)
