from portfolio_agent_platform import AgentPlatform, get_platform_profile
from portfolio_model_provider import (
    DEFAULT_ROUTE_BUDGETS,
    ModelProvider,
    ModelUsageEvent,
    build_model_capability_report,
    build_model_tuning_plan,
    load_model_provider_config,
    load_model_runtime_profile,
)


def test_gemini_is_default_provider() -> None:
    config = load_model_provider_config({})

    assert config.provider == ModelProvider.GEMINI
    assert config.requires_api_key is True
    assert config.local is False


def test_ollama_provider_is_local_and_does_not_require_api_key() -> None:
    config = load_model_provider_config({"LLM_PROVIDER": "ollama"})

    assert config.provider == ModelProvider.OLLAMA
    assert config.base_url == "http://localhost:11434"
    assert config.model == "llama3.1:8b"
    assert config.requires_api_key is False
    assert config.local is True


def test_claude_and_openai_compatible_providers_are_declared() -> None:
    claude = load_model_provider_config({"LLM_PROVIDER": "claude"})
    openai_compatible = load_model_provider_config(
        {
            "LLM_PROVIDER": "openai_compatible",
            "OPENAI_COMPATIBLE_BASE_URL": "http://localhost:4000/v1",
        }
    )

    assert claude.api_key_env == "ANTHROPIC_API_KEY"
    assert openai_compatible.base_url == "http://localhost:4000/v1"


def test_agent_platforms_all_use_mcp_policy_boundary() -> None:
    for platform in AgentPlatform:
        profile = get_platform_profile(platform)

        assert profile.uses_mcp is True


def test_ollama_runtime_profile_is_model_independent_and_context_capped() -> None:
    profile = load_model_runtime_profile(
        {
            "LLM_PROVIDER": "ollama",
            "LLM_MODEL": "llama3.1:8b",
            "OLLAMA_BASE_URL": "http://host.containers.internal:11434",
            "MODEL_CONTEXT_WINDOW_TOKENS": "8192",
            "OLLAMA_MODEL_DIGEST": "sha256:local-test",
        }
    )

    assert profile.provider == ModelProvider.OLLAMA
    assert profile.model == "llama3.1:8b"
    assert profile.base_url == "http://host.containers.internal:11434"
    assert profile.model_digest == "sha256:local-test"
    assert profile.context_window_tokens == 8192
    assert profile.max_request_input_tokens == 6553
    assert profile.route_budgets["research"].effective_input_tokens == 6553
    assert profile.route_budgets["technical_analysis"].effective_input_tokens == 6553
    assert profile.route_budgets["paper_proposal_execution"].effective_input_tokens == 6553
    assert profile.route_budgets["router_refusal"].effective_input_tokens == 2000
    assert profile.route_budgets["research"].tool_call_budget == 5


def test_model_capability_report_fails_closed_for_public_or_unknown_local_models() -> None:
    public_profile = load_model_runtime_profile(
        {
            "LLM_PROVIDER": "ollama",
            "LLM_MODEL": "unknown:8b",
            "OLLAMA_BASE_URL": "http://8.8.8.8:11434",
            "MODEL_CONTEXT_WINDOW_TOKENS": "8192",
        }
    )

    public_report = build_model_capability_report(public_profile)

    assert public_report.startup_allowed is False
    assert "ollama_base_url_not_private" in public_report.blocking_reasons
    assert "tool_use_capability_unverified" in public_report.blocking_reasons
    assert "structured_output_capability_unverified" in public_report.blocking_reasons


def test_model_capability_report_allows_configured_llama_local_profile() -> None:
    profile = load_model_runtime_profile(
        {
            "LLM_PROVIDER": "ollama",
            "LLM_MODEL": "llama3.1:8b",
            "OLLAMA_BASE_URL": "http://host.containers.internal:11434",
            "MODEL_CONTEXT_WINDOW_TOKENS": "8192",
            "OLLAMA_MODEL_DIGEST": "sha256:local-test",
            "MODEL_SUPPORTS_TOOL_USE": "true",
            "MODEL_SUPPORTS_STRUCTURED_OUTPUTS": "true",
        }
    )

    report = build_model_capability_report(profile, available_model_ids={"llama3.1:8b"})

    assert report.startup_allowed is True
    assert report.required_capabilities == {
        "tool_use": True,
        "structured_outputs": True,
    }
    assert report.blocking_reasons == []


def test_model_capability_report_does_not_block_default_remote_provider() -> None:
    profile = load_model_runtime_profile({})

    report = build_model_capability_report(profile)

    assert profile.provider == ModelProvider.GEMINI
    assert report.startup_allowed is True
    assert report.blocking_reasons == []


def test_model_tuning_plan_prefers_prompt_and_routing_before_fine_tuning() -> None:
    plan = build_model_tuning_plan(
        {
            "MODEL_TUNING_CANDIDATES": "llama3.1:8b,gemma:7b",
            "MODEL_TUNING_DEV_SET": "agent-service-basic",
            "MODEL_TUNING_HOLDOUT_SET": "agent-service-sealed",
        }
    )

    assert plan.primary_candidate_model == "llama3.1:8b"
    assert plan.candidate_models == ("llama3.1:8b", "gemma:7b")
    assert plan.initial_tuning_mode == "prompt_routing_retrieval"
    assert plan.fine_tuning_enabled is False
    assert plan.fine_tuning_min_labeled_examples == 200
    assert plan.fine_tuning_candidate_allowed(
        labeled_examples=199,
        completed_prompt_routing_retrieval_iterations=3,
        repeatable_residual_failure_class=True,
    ) is False
    assert plan.fine_tuning_candidate_allowed(
        labeled_examples=200,
        completed_prompt_routing_retrieval_iterations=3,
        repeatable_residual_failure_class=True,
    ) is True
    assert set(DEFAULT_ROUTE_BUDGETS) == {
        "router_refusal",
        "research",
        "technical_analysis",
        "paper_proposal_execution",
    }


def test_model_usage_event_records_token_latency_and_tool_counts_only() -> None:
    event = ModelUsageEvent(
        provider=ModelProvider.OLLAMA,
        model="llama3.1:8b",
        route="technical_analysis",
        prompt_tokens=3_200,
        output_tokens=700,
        tool_calls=4,
        queue_wait_ms=120,
        latency_ms=2_400,
        retries=1,
        request_id="req-123",
    )

    payload = event.to_dict()

    assert payload == {
        "provider": "ollama",
        "model": "llama3.1:8b",
        "route": "technical_analysis",
        "prompt_tokens": 3_200,
        "output_tokens": 700,
        "tool_calls": 4,
        "queue_wait_ms": 120,
        "latency_ms": 2_400,
        "retries": 1,
        "request_id": "req-123",
    }
    assert "prompt" not in payload
    assert "response" not in payload
