"""Configuration — loads config.yaml + environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class CandidateConfig(BaseModel):
    resume_path: str = "./resume.pdf"
    name: str = "Candidate"
    yoe_target: list[int] = Field(default=[2, 4])
    locations: list[str] = Field(default=["remote", "hyderabad", "bangalore"])
    must_not_match: list[str] = Field(
        default=["senior", "staff", "principal", "lead", "director", "5+ years", "7+ years"]
    )


class SourceConfig(BaseModel):
    enabled: bool = True


class ScoringConfig(BaseModel):
    use_llm: bool = False
    min_score: int = 40
    top_n: int = 10


class EmailOutputConfig(BaseModel):
    enabled: bool = True
    to: str = ""
    from_addr: str = Field(default="", alias="from")
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587

    model_config = {"populate_by_name": True}


class MarkdownOutputConfig(BaseModel):
    enabled: bool = True
    commit_to_repo: bool = True


class OutputConfig(BaseModel):
    email: EmailOutputConfig = Field(default_factory=EmailOutputConfig)
    markdown: MarkdownOutputConfig = Field(default_factory=MarkdownOutputConfig)


class Settings(BaseModel):
    candidate: CandidateConfig = Field(default_factory=CandidateConfig)
    skill_weights: dict[str, int] = Field(
        default={
            "java": 10,
            "spring": 10,
            "spring_boot": 10,
            "kafka": 7,
            "rabbitmq": 5,
            "postgres": 5,
            "redis": 5,
            "microservices": 8,
            "aws": 5,
            "system_design": 5,
        }
    )
    sources: dict[str, SourceConfig] = Field(default_factory=dict)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    # env-injected secrets (never in config.yaml)
    smtp_password: str = ""
    anthropic_api_key: str = ""
    instahyre_token: str = ""
    instahyre_cookies: str = ""  # full Cookie header string (sessionid, cf_clearance, csrftoken)
    findwork_api_key: str = ""

    @property
    def llm_enabled(self) -> bool:
        use_llm = self.scoring.use_llm or bool(self.anthropic_api_key)
        return use_llm and bool(self.anthropic_api_key)

    def source_enabled(self, name: str) -> bool:
        cfg = self.sources.get(name)
        return cfg.enabled if cfg else True


def load_settings(config_path: str = "./config.yaml") -> Settings:
    """Load settings from YAML file, then overlay env vars for secrets."""
    from dotenv import load_dotenv
    load_dotenv()  # no-op if .env absent
    path = Path(config_path)
    data: dict[str, Any] = {}
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}

    settings = Settings.model_validate(data)

    # Overlay secrets from environment
    settings.smtp_password = os.environ.get("SMTP_PASSWORD", "")
    settings.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    settings.instahyre_token = os.environ.get("INSTAHYRE_TOKEN", "")
    settings.instahyre_cookies = os.environ.get("INSTAHYRE_COOKIES", "")
    settings.findwork_api_key = os.environ.get("FINDWORK_API_KEY", "")

    return settings
