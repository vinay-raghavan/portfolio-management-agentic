from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class ModelProvider(StrEnum):
    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"


@dataclass(frozen=True)
class ModelProviderConfig:
    provider: ModelProvider
    model: str
    base_url: str | None
    api_key_env: str | None
    local: bool

    @property
    def requires_api_key(self) -> bool:
        return self.api_key_env is not None


DEFAULT_MODELS = {
    ModelProvider.GEMINI: "gemini-flash-latest",
    ModelProvider.CLAUDE: "claude-sonnet-4",
    ModelProvider.OPENAI_COMPATIBLE: "gpt-4.1-mini",
    ModelProvider.OLLAMA: "llama3.1:8b",
}


def load_model_provider_config(env: Mapping[str, str]) -> ModelProviderConfig:
    provider = ModelProvider(env.get("LLM_PROVIDER", ModelProvider.GEMINI.value))
    model = env.get("LLM_MODEL", DEFAULT_MODELS[provider])

    if provider == ModelProvider.GEMINI:
        return ModelProviderConfig(provider, model, None, "GOOGLE_API_KEY", False)
    if provider == ModelProvider.CLAUDE:
        return ModelProviderConfig(provider, model, None, "ANTHROPIC_API_KEY", False)
    if provider == ModelProvider.OPENAI_COMPATIBLE:
        return ModelProviderConfig(
            provider,
            model,
            env.get("OPENAI_COMPATIBLE_BASE_URL"),
            "OPENAI_API_KEY",
            False,
        )

    return ModelProviderConfig(
        provider,
        model,
        env.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        None,
        True,
    )

