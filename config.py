from pathlib import Path

from dotenv import set_key, unset_key
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROMPT = Path(__file__).resolve().parent / "prompts" / "master_prompt.txt"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    foundry_project_endpoint: str = ""
    foundry_agent_name: str = "cobuilder-agent"
    foundry_model: str = "gpt-4o-mini"
    azure_credential_mode: str = "default"
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    cobuilder_master_prompt: str = ""

    def master_prompt(self) -> str:
        if self.cobuilder_master_prompt.strip():
            return self.cobuilder_master_prompt.strip()
        return DEFAULT_PROMPT.read_text(encoding="utf-8")


def save_connection_settings(values: dict[str, str]) -> None:
    env_path = ROOT / ".env"
    for field, value in values.items():
        env_name = field.upper()
        if value:
            set_key(env_path, env_name, value)
        else:
            unset_key(env_path, env_name)
        setattr(settings, field, value)


settings = Settings()
