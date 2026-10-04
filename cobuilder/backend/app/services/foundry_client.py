from __future__ import annotations

import base64
import json
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import ClientSecretCredential, DefaultAzureCredential

from app.config import settings

FLOORPLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "unit": {"type": "string", "enum": ["ft", "m"]},
        "wall_height": {"type": "number"},
        "total_sqft": {"type": ["number", "null"]},
        "rooms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "polygon": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                            "required": ["x", "y"],
                        },
                    },
                    "floor_material": {"type": ["string", "null"]},
                    "estimated": {"type": "boolean"},
                },
                "required": ["id", "name", "polygon"],
            },
        },
        "walls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "start": {
                        "type": "object",
                        "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                        "required": ["x", "y"],
                    },
                    "end": {
                        "type": "object",
                        "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                        "required": ["x", "y"],
                    },
                    "thickness_ft": {"type": "number"},
                    "load_bearing": {"type": ["boolean", "null"]},
                },
                "required": ["id", "start", "end"],
            },
        },
        "openings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": ["door", "window"]},
                    "wall_id": {"type": "string"},
                    "position_along_wall": {"type": "number"},
                    "width_ft": {"type": "number"},
                    "height_ft": {"type": "number"},
                },
                "required": ["id", "type", "wall_id", "width_ft", "height_ft"],
            },
        },
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["unit", "wall_height", "rooms", "walls"],
}


class FoundryService:
    def __init__(self) -> None:
        if not settings.foundry_project_endpoint:
            raise ValueError(
                "FOUNDRY_PROJECT_ENDPOINT is not set. Copy .env.example to .env and fill in your Azure values."
            )
        self._project = AIProjectClient(
            endpoint=settings.foundry_project_endpoint,
            credential=self._credential(),
        )
        self._agent_ready = False

    @staticmethod
    def _credential():
        if settings.azure_credential_mode == "service_principal":
            if not all((settings.azure_tenant_id, settings.azure_client_id, settings.azure_client_secret)):
                raise ValueError("Service principal mode requires tenant ID, client ID, and client secret.")
            return ClientSecretCredential(
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret,
            )
        return DefaultAzureCredential()

    def ensure_agent(self) -> None:
        if self._agent_ready:
            return
        self._project.agents.create_version(
            agent_name=settings.foundry_agent_name,
            definition=PromptAgentDefinition(
                model=settings.foundry_model,
                instructions=settings.master_prompt(),
            ),
        )
        self._agent_ready = True

    def _openai(self):
        self.ensure_agent()
        return self._project.get_openai_client(agent_name=settings.foundry_agent_name)

    @staticmethod
    def _image_content(image_bytes: bytes, mime: str) -> dict:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return {
            "type": "input_image",
            "image_url": f"data:{mime};base64,{encoded}",
        }

    def analyze_floorplan(self, image_bytes: bytes, mime: str, hints: str = "") -> dict:
        openai = self._openai()
        user_text = (
            "Analyze this floorplan image and return JSON for a basic 3D recreation. "
            "Include all rooms with polygon coordinates, walls, doors, and windows. "
            "Use feet as the unit unless the plan shows meters."
        )
        if hints.strip():
            user_text += f"\n\nUser hints: {hints.strip()}"

        response = openai.responses.create(
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": user_text},
                        self._image_content(image_bytes, mime),
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "floorplan_scene",
                    "schema": FLOORPLAN_SCHEMA,
                    "strict": True,
                }
            },
        )
        return json.loads(response.output_text)

    def plan_renovation(self, scene: dict, request: str) -> str:
        openai = self._openai()
        prompt = (
            f"Current floorplan JSON:\n{json.dumps(scene, indent=2)}\n\n"
            f"Renovation request: {request}\n\n"
            "Provide a detailed renovation plan with Scope, Phases, Materials (with qty and $), "
            "Tools, Cost Estimate (low/high USD), Permits, and Risks."
        )
        response = openai.responses.create(input=prompt)
        return response.output_text

    def chat(self, message: str, conversation_id: str | None = None) -> tuple[str, str]:
        openai = self._openai()
        conversation = (
            openai.conversations.retrieve(conversation_id)
            if conversation_id
            else openai.conversations.create()
        )
        response = openai.responses.create(
            conversation=conversation.id,
            input=message,
        )
        return response.output_text, conversation.id


def load_image(path: Path) -> tuple[bytes, str]:
    suffix = path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    if suffix not in mime_map:
        raise ValueError(f"Unsupported image type: {suffix}")
    return path.read_bytes(), mime_map[suffix]
