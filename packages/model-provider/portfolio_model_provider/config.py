from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from ipaddress import ip_address
from typing import Mapping
from urllib.parse import urlparse


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


@dataclass(frozen=True)
class RouteBudget:
    route: str
    configured_input_tokens: int
    output_tokens: int
    tool_call_budget: int
    effective_input_tokens: int


@dataclass(frozen=True)
class ModelRuntimeProfile:
    provider: ModelProvider
    model: str
    base_url: str | None
    model_digest: str | None
    local: bool
    context_window_tokens: int
    max_request_input_tokens: int
    route_budgets: dict[str, RouteBudget]
    queue_max_active_requests: int
    queue_max_depth: int


@dataclass(frozen=True)
class ModelCapabilityReport:
    provider: ModelProvider
    model: str
    base_url: str | None
    model_digest: str | None
    required_capabilities: dict[str, bool]
    context_window_tokens: int
    max_request_input_tokens: int
    base_url_private: bool
    model_available: bool | None
    startup_allowed: bool
    blocking_reasons: list[str]


@dataclass(frozen=True)
class ModelUsageEvent:
    provider: ModelProvider
    model: str
    route: str
    prompt_tokens: int
    output_tokens: int
    tool_calls: int
    queue_wait_ms: int
    latency_ms: int
    retries: int
    request_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider.value,
            "model": self.model,
            "route": self.route,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "tool_calls": self.tool_calls,
            "queue_wait_ms": self.queue_wait_ms,
            "latency_ms": self.latency_ms,
            "retries": self.retries,
            "request_id": self.request_id,
        }


@dataclass(frozen=True)
class ModelTuningPlan:
    primary_candidate_model: str
    candidate_models: tuple[str, ...]
    dev_set: str
    holdout_set: str
    initial_tuning_mode: str
    fine_tuning_enabled: bool
    fine_tuning_min_labeled_examples: int
    required_prompt_routing_retrieval_iterations: int

    def fine_tuning_candidate_allowed(
        self,
        *,
        labeled_examples: int,
        completed_prompt_routing_retrieval_iterations: int,
        repeatable_residual_failure_class: bool,
    ) -> bool:
        return (
            labeled_examples >= self.fine_tuning_min_labeled_examples
            and completed_prompt_routing_retrieval_iterations
            >= self.required_prompt_routing_retrieval_iterations
            and repeatable_residual_failure_class
        )


DEFAULT_ROUTE_BUDGETS: dict[str, tuple[int, int, int]] = {
    "router_refusal": (2_000, 512, 0),
    "research": (24_000, 2_000, 5),
    "technical_analysis": (12_000, 1_500, 5),
    "paper_proposal_execution": (8_000, 1_000, 3),
}

DEFAULT_CONTEXT_WINDOWS = {
    ModelProvider.GEMINI: 1_000_000,
    ModelProvider.CLAUDE: 200_000,
    ModelProvider.OPENAI_COMPATIBLE: 128_000,
    ModelProvider.OLLAMA: 8_192,
}

KNOWN_LOCAL_MODEL_CAPABILITIES: dict[str, dict[str, object]] = {
    "llama3.1:8b": {
        "context_window_tokens": 8_192,
        "tool_use": True,
        "structured_outputs": True,
    },
    "gemma:7b": {
        "context_window_tokens": 8_192,
        "tool_use": False,
        "structured_outputs": False,
    },
    "gemma4:12b": {
        "context_window_tokens": 32_768,
        "tool_use": True,
        "structured_outputs": True,
    },
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


def load_model_runtime_profile(env: Mapping[str, str]) -> ModelRuntimeProfile:
    config = load_model_provider_config(env)
    default_context = _known_context_window(config.provider, config.model)
    context_window = _positive_int(
        env.get("MODEL_CONTEXT_WINDOW_TOKENS"),
        default_context,
    )
    max_request_input_tokens = int(context_window * 0.8)
    return ModelRuntimeProfile(
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
        model_digest=_blank_to_none(env.get("OLLAMA_MODEL_DIGEST")),
        local=config.local,
        context_window_tokens=context_window,
        max_request_input_tokens=max_request_input_tokens,
        route_budgets=_route_budgets(max_request_input_tokens),
        queue_max_active_requests=_positive_int(
            env.get("MODEL_QUEUE_MAX_ACTIVE_REQUESTS"),
            3 if config.local else 20,
        ),
        queue_max_depth=_positive_int(env.get("MODEL_QUEUE_MAX_DEPTH"), 24),
    )


def build_model_capability_report(
    profile: ModelRuntimeProfile,
    available_model_ids: set[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> ModelCapabilityReport:
    env = {} if env is None else env
    known = KNOWN_LOCAL_MODEL_CAPABILITIES.get(profile.model, {})
    supports_tool_use = _optional_bool(
        env.get("MODEL_SUPPORTS_TOOL_USE"),
        _optional_known_bool(known.get("tool_use")),
    )
    supports_structured_outputs = _optional_bool(
        env.get("MODEL_SUPPORTS_STRUCTURED_OUTPUTS"),
        _optional_known_bool(known.get("structured_outputs")),
    )
    required_capabilities = {
        "tool_use": bool(supports_tool_use),
        "structured_outputs": bool(supports_structured_outputs),
    }
    base_url_private = (
        _is_private_base_url(profile.base_url) if profile.provider == ModelProvider.OLLAMA else True
    )
    model_available = (
        None if available_model_ids is None else profile.model in available_model_ids
    )
    blocking_reasons: list[str] = []
    if not base_url_private:
        blocking_reasons.append("ollama_base_url_not_private")
    ollama_profile = profile.provider == ModelProvider.OLLAMA
    if supports_tool_use is not True and ollama_profile:
        blocking_reasons.append("tool_use_capability_unverified")
    if supports_structured_outputs is not True and ollama_profile:
        blocking_reasons.append("structured_output_capability_unverified")
    if model_available is False:
        blocking_reasons.append("model_not_available")
    if ollama_profile and profile.model_digest is None:
        blocking_reasons.append("model_digest_not_pinned")

    return ModelCapabilityReport(
        provider=profile.provider,
        model=profile.model,
        base_url=profile.base_url,
        model_digest=profile.model_digest,
        required_capabilities=required_capabilities,
        context_window_tokens=profile.context_window_tokens,
        max_request_input_tokens=profile.max_request_input_tokens,
        base_url_private=base_url_private,
        model_available=model_available,
        startup_allowed=not blocking_reasons,
        blocking_reasons=blocking_reasons,
    )


def build_model_tuning_plan(env: Mapping[str, str]) -> ModelTuningPlan:
    candidates = tuple(
        candidate.strip()
        for candidate in env.get(
            "MODEL_TUNING_CANDIDATES",
            "llama3.1:8b,gemma:7b,gemma4:12b",
        ).split(",")
        if candidate.strip()
    )
    candidate_models = candidates or ("llama3.1:8b",)
    return ModelTuningPlan(
        primary_candidate_model=candidate_models[0],
        candidate_models=candidate_models,
        dev_set=env.get("MODEL_TUNING_DEV_SET", "agent-service-dev"),
        holdout_set=env.get("MODEL_TUNING_HOLDOUT_SET", "agent-service-sealed"),
        initial_tuning_mode="prompt_routing_retrieval",
        fine_tuning_enabled=False,
        fine_tuning_min_labeled_examples=200,
        required_prompt_routing_retrieval_iterations=3,
    )


def _known_context_window(provider: ModelProvider, model: str) -> int:
    if provider == ModelProvider.OLLAMA:
        known = KNOWN_LOCAL_MODEL_CAPABILITIES.get(model, {})
        value = known.get("context_window_tokens")
        if isinstance(value, int):
            return value
    return DEFAULT_CONTEXT_WINDOWS[provider]


def _route_budgets(max_request_input_tokens: int) -> dict[str, RouteBudget]:
    return {
        route: RouteBudget(
            route=route,
            configured_input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_call_budget=tool_calls,
            effective_input_tokens=min(input_tokens, max_request_input_tokens),
        )
        for route, (input_tokens, output_tokens, tool_calls) in DEFAULT_ROUTE_BUDGETS.items()
    }


def _positive_int(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _optional_known_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_bool(value: str | None, default: bool | None) -> bool | None:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _is_private_base_url(base_url: str | None) -> bool:
    if not base_url:
        return False
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname in {"localhost", "host.containers.internal", "ollama"}:
        return True
    if hostname.endswith((".internal", ".local")):
        return True
    try:
        address = ip_address(hostname)
    except ValueError:
        return False
    return address.is_private or address.is_loopback
