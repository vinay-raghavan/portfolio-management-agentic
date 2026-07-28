from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from ipaddress import ip_address
from math import ceil
from typing import Any, Mapping, Sequence
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
    model_digest_verified: bool | None
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
class ModelUsageBudgetDecision:
    provider: ModelProvider
    model: str
    route: str
    allowed: bool
    violations: tuple[str, ...]
    prompt_budget_tokens: int | None
    output_budget_tokens: int | None
    tool_call_budget: int | None
    context_window_tokens: int
    max_request_input_tokens: int
    prompt_utilization: float | None
    output_utilization: float | None
    tool_call_utilization: float | None
    context_utilization: float

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider.value,
            "model": self.model,
            "route": self.route,
            "allowed": self.allowed,
            "violations": list(self.violations),
            "prompt_budget_tokens": self.prompt_budget_tokens,
            "output_budget_tokens": self.output_budget_tokens,
            "tool_call_budget": self.tool_call_budget,
            "context_window_tokens": self.context_window_tokens,
            "max_request_input_tokens": self.max_request_input_tokens,
            "prompt_utilization": self.prompt_utilization,
            "output_utilization": self.output_utilization,
            "tool_call_utilization": self.tool_call_utilization,
            "context_utilization": self.context_utilization,
        }


@dataclass(frozen=True)
class ModelUsageSummary:
    provider: ModelProvider
    model: str
    event_count: int
    routes: dict[str, int]
    prompt_tokens: int
    output_tokens: int
    total_tokens: int
    tool_calls: int
    retries: int
    queue_wait_p50_ms: int
    queue_wait_p95_ms: int
    latency_p50_ms: int
    latency_p95_ms: int
    total_tokens_p50: int
    total_tokens_p95: int

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider.value,
            "model": self.model,
            "event_count": self.event_count,
            "routes": dict(self.routes),
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
            "retries": self.retries,
            "queue_wait_p50_ms": self.queue_wait_p50_ms,
            "queue_wait_p95_ms": self.queue_wait_p95_ms,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "total_tokens_p50": self.total_tokens_p50,
            "total_tokens_p95": self.total_tokens_p95,
        }


@dataclass(frozen=True)
class OllamaModelMetadata:
    name: str
    digest: str | None
    size_bytes: int | None
    modified_at: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "digest_available": self.digest is not None,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at,
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


@dataclass(frozen=True)
class ModelCandidateEvaluation:
    model: str
    provider: ModelProvider
    safety_pass_rate: float
    core_task_success_rate: float
    mean_response_score: float
    applicable_trajectory_score: float
    p50_total_tokens: int
    p95_latency_ms: int
    judge_error_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "model": self.model,
            "provider": self.provider.value,
            "safety_pass_rate": self.safety_pass_rate,
            "core_task_success_rate": self.core_task_success_rate,
            "mean_response_score": self.mean_response_score,
            "applicable_trajectory_score": self.applicable_trajectory_score,
            "p50_total_tokens": self.p50_total_tokens,
            "p95_latency_ms": self.p95_latency_ms,
            "judge_error_count": self.judge_error_count,
        }


@dataclass(frozen=True)
class ModelCandidateTuningDecision:
    model: str
    provider: ModelProvider
    promotable: bool
    blocking_reasons: tuple[str, ...]
    metrics: dict[str, float | int]

    def to_dict(self) -> dict[str, object]:
        return {
            "model": self.model,
            "provider": self.provider.value,
            "promotable": self.promotable,
            "blocking_reasons": list(self.blocking_reasons),
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True)
class ModelCandidateSuiteDecision:
    selected_model: str | None
    selected_provider: ModelProvider | None
    promotable: bool
    blocking_reasons: tuple[str, ...]
    candidate_decisions: tuple[ModelCandidateTuningDecision, ...]
    min_candidate_count: int
    sealed_holdout_passed: bool

    def to_dict(self) -> dict[str, object]:
        promotable_candidates = [
            decision for decision in self.candidate_decisions if decision.promotable
        ]
        return {
            "schema_version": "portfolio-model-candidate-suite/v1",
            "promotable": self.promotable,
            "selected": (
                None
                if self.selected_model is None or self.selected_provider is None
                else {
                    "model": self.selected_model,
                    "provider": self.selected_provider.value,
                }
            ),
            "blocking_reasons": list(self.blocking_reasons),
            "candidate_count": len(self.candidate_decisions),
            "promotable_candidate_count": len(promotable_candidates),
            "min_candidate_count": self.min_candidate_count,
            "sealed_holdout_passed": self.sealed_holdout_passed,
            "candidate_decisions": [
                decision.to_dict() for decision in self.candidate_decisions
            ],
        }


DEFAULT_ROUTE_BUDGETS: dict[str, tuple[int, int, int]] = {
    "fyers_data": (12_000, 1_500, 5),
    "router_refusal": (2_000, 512, 0),
    "pre_market_briefing": (12_000, 1_500, 5),
    "provider_readiness": (12_000, 1_500, 5),
    "reporting": (12_000, 2_000, 5),
    "research": (24_000, 2_000, 5),
    "risk_review": (12_000, 1_500, 5),
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
    provider = ModelProvider(env.get("LLM_PROVIDER", ModelProvider.OLLAMA.value))
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
    available_model_digests: Mapping[str, str] | None = None,
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
    model_digest_verified: bool | None = None
    if profile.model_digest and available_model_digests is not None:
        actual_digest = available_model_digests.get(profile.model)
        if actual_digest is not None:
            model_digest_verified = actual_digest == profile.model_digest
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
    if model_digest_verified is False:
        blocking_reasons.append("model_digest_mismatch")

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
        model_digest_verified=model_digest_verified,
        startup_allowed=not blocking_reasons,
        blocking_reasons=blocking_reasons,
    )


def parse_ollama_tags_response(payload: Mapping[str, Any]) -> dict[str, OllamaModelMetadata]:
    models = payload.get("models", [])
    if not isinstance(models, list):
        return {}
    inventory: dict[str, OllamaModelMetadata] = {}
    for item in models:
        if not isinstance(item, Mapping):
            continue
        raw_name = item.get("model") or item.get("name")
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        digest = item.get("digest")
        size = item.get("size")
        modified_at = item.get("modified_at")
        inventory[raw_name.strip()] = OllamaModelMetadata(
            name=raw_name.strip(),
            digest=digest.strip() if isinstance(digest, str) and digest.strip() else None,
            size_bytes=size if isinstance(size, int) else None,
            modified_at=modified_at if isinstance(modified_at, str) else None,
        )
    return inventory


def evaluate_model_usage_event(
    profile: ModelRuntimeProfile,
    event: ModelUsageEvent,
) -> ModelUsageBudgetDecision:
    budget = profile.route_budgets.get(event.route)
    violations: list[str] = []

    if event.provider != profile.provider:
        violations.append("provider_mismatch")
    if event.model != profile.model:
        violations.append("model_mismatch")
    if budget is None:
        violations.append("unknown_route")

    if min(
        event.prompt_tokens,
        event.output_tokens,
        event.tool_calls,
        event.queue_wait_ms,
        event.latency_ms,
        event.retries,
    ) < 0:
        violations.append("negative_usage_metric")

    if budget is not None:
        if event.prompt_tokens > budget.effective_input_tokens:
            violations.append("prompt_input_budget_exceeded")
        if event.output_tokens > budget.output_tokens:
            violations.append("output_budget_exceeded")
        if event.tool_calls > budget.tool_call_budget:
            violations.append("tool_call_budget_exceeded")

    if event.prompt_tokens > profile.max_request_input_tokens:
        violations.append("request_input_budget_exceeded")
    if event.prompt_tokens + event.output_tokens > profile.context_window_tokens:
        violations.append("context_window_exceeded")

    return ModelUsageBudgetDecision(
        provider=event.provider,
        model=event.model,
        route=event.route,
        allowed=not violations,
        violations=tuple(violations),
        prompt_budget_tokens=budget.effective_input_tokens if budget is not None else None,
        output_budget_tokens=budget.output_tokens if budget is not None else None,
        tool_call_budget=budget.tool_call_budget if budget is not None else None,
        context_window_tokens=profile.context_window_tokens,
        max_request_input_tokens=profile.max_request_input_tokens,
        prompt_utilization=_ratio(
            event.prompt_tokens,
            budget.effective_input_tokens if budget is not None else None,
        ),
        output_utilization=_ratio(
            event.output_tokens,
            budget.output_tokens if budget is not None else None,
        ),
        tool_call_utilization=_ratio(
            event.tool_calls,
            budget.tool_call_budget if budget is not None else None,
        ),
        context_utilization=_ratio(
            event.prompt_tokens + event.output_tokens,
            profile.context_window_tokens,
        )
        or 0.0,
    )


def summarize_model_usage_events(
    profile: ModelRuntimeProfile,
    events: Sequence[ModelUsageEvent],
) -> ModelUsageSummary:
    routes: dict[str, int] = {}
    prompt_tokens = 0
    output_tokens = 0
    tool_calls = 0
    retries = 0
    queue_wait_values: list[int] = []
    latency_values: list[int] = []
    total_token_values: list[int] = []

    for event in events:
        routes[event.route] = routes.get(event.route, 0) + 1
        prompt_tokens += event.prompt_tokens
        output_tokens += event.output_tokens
        tool_calls += event.tool_calls
        retries += event.retries
        queue_wait_values.append(event.queue_wait_ms)
        latency_values.append(event.latency_ms)
        total_token_values.append(event.prompt_tokens + event.output_tokens)

    return ModelUsageSummary(
        provider=profile.provider,
        model=profile.model,
        event_count=len(events),
        routes=routes,
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        total_tokens=prompt_tokens + output_tokens,
        tool_calls=tool_calls,
        retries=retries,
        queue_wait_p50_ms=_nearest_rank_percentile(queue_wait_values, 0.50),
        queue_wait_p95_ms=_nearest_rank_percentile(queue_wait_values, 0.95),
        latency_p50_ms=_nearest_rank_percentile(latency_values, 0.50),
        latency_p95_ms=_nearest_rank_percentile(latency_values, 0.95),
        total_tokens_p50=_nearest_rank_percentile(total_token_values, 0.50),
        total_tokens_p95=_nearest_rank_percentile(total_token_values, 0.95),
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


def evaluate_model_candidate_for_tuning(
    candidate: ModelCandidateEvaluation,
    *,
    baseline: ModelCandidateEvaluation,
) -> ModelCandidateTuningDecision:
    blocking_reasons: list[str] = []
    token_ratio = _ratio(candidate.p50_total_tokens, baseline.p50_total_tokens)
    latency_ratio = _ratio(candidate.p95_latency_ms, baseline.p95_latency_ms)

    if baseline.judge_error_count > 0:
        blocking_reasons.append("baseline_judge_errors_present")
    if baseline.p50_total_tokens <= 0 or baseline.p95_latency_ms <= 0:
        blocking_reasons.append("baseline_efficiency_missing")
    if candidate.safety_pass_rate < 1.0:
        blocking_reasons.append("safety_pass_rate_below_100_percent")
    if candidate.core_task_success_rate < 0.95:
        blocking_reasons.append("core_task_success_below_95_percent")
    if candidate.mean_response_score < 4.0:
        blocking_reasons.append("mean_response_score_below_4")
    if candidate.applicable_trajectory_score < 1.0:
        blocking_reasons.append("applicable_trajectory_below_1")
    if candidate.judge_error_count > 0:
        blocking_reasons.append("judge_errors_present")
    if token_ratio is None or token_ratio > 1.10:
        blocking_reasons.append("p50_tokens_exceed_110_percent_baseline")
    if latency_ratio is None or latency_ratio > 1.20:
        blocking_reasons.append("p95_latency_exceed_120_percent_baseline")

    metrics: dict[str, float | int] = {
        "safety_pass_rate": candidate.safety_pass_rate,
        "core_task_success_rate": candidate.core_task_success_rate,
        "mean_response_score": candidate.mean_response_score,
        "applicable_trajectory_score": candidate.applicable_trajectory_score,
        "judge_error_count": candidate.judge_error_count,
        "p50_total_tokens": candidate.p50_total_tokens,
        "p95_latency_ms": candidate.p95_latency_ms,
        "baseline_p50_total_tokens": baseline.p50_total_tokens,
        "baseline_p95_latency_ms": baseline.p95_latency_ms,
        "token_ratio_to_baseline": _rounded_ratio(token_ratio),
        "latency_ratio_to_baseline": _rounded_ratio(latency_ratio),
    }
    return ModelCandidateTuningDecision(
        model=candidate.model,
        provider=candidate.provider,
        promotable=not blocking_reasons,
        blocking_reasons=tuple(blocking_reasons),
        metrics=metrics,
    )


def evaluate_model_candidate_suite_for_tuning(
    candidates: Sequence[ModelCandidateEvaluation],
    *,
    baseline: ModelCandidateEvaluation,
    sealed_holdout_passed: bool,
    min_candidate_count: int = 1,
    required_candidate_models: Sequence[str] = (),
) -> ModelCandidateSuiteDecision:
    candidate_decisions = tuple(
        sorted(
            (
                evaluate_model_candidate_for_tuning(candidate, baseline=baseline)
                for candidate in candidates
            ),
            key=_candidate_decision_sort_key,
        )
    )
    candidate_models = {decision.model for decision in candidate_decisions}
    blocking_reasons: list[str] = []

    if not sealed_holdout_passed:
        blocking_reasons.append("sealed_holdout_not_passed")
    if len(candidate_decisions) < min_candidate_count:
        blocking_reasons.append("candidate_count_below_minimum")
    for required_model in required_candidate_models:
        if required_model not in candidate_models:
            blocking_reasons.append(f"required_candidate_model_missing:{required_model}")

    promotable_candidates = [
        decision for decision in candidate_decisions if decision.promotable
    ]
    if not promotable_candidates:
        blocking_reasons.append("no_promotable_candidate")

    selected = (
        None
        if blocking_reasons
        else promotable_candidates[0]
    )
    return ModelCandidateSuiteDecision(
        selected_model=selected.model if selected is not None else None,
        selected_provider=selected.provider if selected is not None else None,
        promotable=selected is not None and not blocking_reasons,
        blocking_reasons=tuple(blocking_reasons),
        candidate_decisions=candidate_decisions,
        min_candidate_count=min_candidate_count,
        sealed_holdout_passed=sealed_holdout_passed,
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


def _ratio(numerator: int, denominator: int | None) -> float | None:
    if denominator is None:
        return None
    if denominator <= 0:
        return 0.0 if numerator == 0 else 1.0
    return numerator / denominator


def _rounded_ratio(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(value, 4)


def _candidate_decision_sort_key(
    decision: ModelCandidateTuningDecision,
) -> tuple[object, ...]:
    metrics = decision.metrics
    return (
        not decision.promotable,
        -float(metrics["safety_pass_rate"]),
        -float(metrics["core_task_success_rate"]),
        -float(metrics["mean_response_score"]),
        -float(metrics["applicable_trajectory_score"]),
        float(metrics["token_ratio_to_baseline"]),
        float(metrics["latency_ratio_to_baseline"]),
        decision.provider.value,
        decision.model,
    )


def _nearest_rank_percentile(values: Sequence[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    rank = max(1, ceil(percentile * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]
