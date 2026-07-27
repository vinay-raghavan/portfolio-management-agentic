from portfolio_agent_platform import AgentPlatform, get_platform_profile
from portfolio_model_provider import (
    DEFAULT_ROUTE_BUDGETS,
    ModelCandidateEvaluation,
    ModelCandidateTuningDecision,
    ModelUsageBudgetDecision,
    ModelProvider,
    ModelUsageEvent,
    ModelUsageSummary,
    build_model_capability_report,
    evaluate_model_candidate_for_tuning,
    build_model_tuning_plan,
    evaluate_model_usage_event,
    load_model_provider_config,
    load_model_runtime_profile,
    parse_ollama_tags_response,
    summarize_model_usage_events,
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


def test_ollama_tags_parser_keeps_inventory_without_prompt_or_secret_payloads() -> None:
    inventory = parse_ollama_tags_response(
        {
            "models": [
                {
                    "name": "llama3.1:8b",
                    "model": "llama3.1:8b",
                    "digest": "sha256:local-test",
                    "size": 4_900_000_000,
                    "modified_at": "2026-07-27T03:00:00Z",
                },
                {"name": "", "digest": "ignored"},
            ]
        }
    )

    metadata = inventory["llama3.1:8b"]
    payload = metadata.to_dict()

    assert set(inventory) == {"llama3.1:8b"}
    assert metadata.digest == "sha256:local-test"
    assert payload["digest_available"] is True
    assert "digest" not in payload
    assert "prompt" not in payload
    assert "response" not in payload


def test_model_capability_report_blocks_ollama_digest_mismatch() -> None:
    profile = load_model_runtime_profile(
        {
            "LLM_PROVIDER": "ollama",
            "LLM_MODEL": "llama3.1:8b",
            "OLLAMA_BASE_URL": "http://host.containers.internal:11434",
            "OLLAMA_MODEL_DIGEST": "sha256:expected",
            "MODEL_SUPPORTS_TOOL_USE": "true",
            "MODEL_SUPPORTS_STRUCTURED_OUTPUTS": "true",
        }
    )

    report = build_model_capability_report(
        profile,
        available_model_ids={"llama3.1:8b"},
        available_model_digests={"llama3.1:8b": "sha256:actual"},
    )

    assert report.startup_allowed is False
    assert report.model_digest_verified is False
    assert "model_digest_mismatch" in report.blocking_reasons


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


def test_model_candidate_tuning_gate_promotes_provider_neutral_candidate() -> None:
    baseline = ModelCandidateEvaluation(
        model="incumbent",
        provider=ModelProvider.GEMINI,
        safety_pass_rate=1.0,
        core_task_success_rate=0.96,
        mean_response_score=4.5,
        applicable_trajectory_score=1.0,
        p50_total_tokens=10_000,
        p95_latency_ms=4_000,
        judge_error_count=0,
    )
    candidate = ModelCandidateEvaluation(
        model="llama3.1:8b",
        provider=ModelProvider.OLLAMA,
        safety_pass_rate=1.0,
        core_task_success_rate=0.97,
        mean_response_score=4.6,
        applicable_trajectory_score=1.0,
        p50_total_tokens=10_900,
        p95_latency_ms=4_700,
        judge_error_count=0,
    )

    decision = evaluate_model_candidate_for_tuning(candidate, baseline=baseline)

    assert isinstance(decision, ModelCandidateTuningDecision)
    assert decision.model == "llama3.1:8b"
    assert decision.provider == ModelProvider.OLLAMA
    assert decision.promotable is True
    assert decision.blocking_reasons == ()
    assert decision.metrics["token_ratio_to_baseline"] == 1.09
    assert decision.metrics["latency_ratio_to_baseline"] == 1.175
    assert "prompt" not in decision.to_dict()
    assert "response" not in decision.to_dict()


def test_model_candidate_tuning_gate_fails_closed_on_safety_quality_and_efficiency() -> None:
    baseline = ModelCandidateEvaluation(
        model="incumbent",
        provider=ModelProvider.GEMINI,
        safety_pass_rate=1.0,
        core_task_success_rate=0.96,
        mean_response_score=4.5,
        applicable_trajectory_score=1.0,
        p50_total_tokens=10_000,
        p95_latency_ms=4_000,
        judge_error_count=0,
    )
    candidate = ModelCandidateEvaluation(
        model="gemma:7b",
        provider=ModelProvider.OLLAMA,
        safety_pass_rate=0.99,
        core_task_success_rate=0.94,
        mean_response_score=3.9,
        applicable_trajectory_score=0.98,
        p50_total_tokens=11_500,
        p95_latency_ms=4_900,
        judge_error_count=1,
    )

    decision = evaluate_model_candidate_for_tuning(candidate, baseline=baseline)

    assert decision.promotable is False
    assert decision.blocking_reasons == (
        "safety_pass_rate_below_100_percent",
        "core_task_success_below_95_percent",
        "mean_response_score_below_4",
        "applicable_trajectory_below_1",
        "judge_errors_present",
        "p50_tokens_exceed_110_percent_baseline",
        "p95_latency_exceed_120_percent_baseline",
    )
    assert decision.metrics["token_ratio_to_baseline"] == 1.15
    assert decision.metrics["latency_ratio_to_baseline"] == 1.225


def test_model_candidate_tuning_gate_requires_baseline_without_judge_errors() -> None:
    baseline = ModelCandidateEvaluation(
        model="incumbent",
        provider=ModelProvider.GEMINI,
        safety_pass_rate=1.0,
        core_task_success_rate=0.96,
        mean_response_score=4.5,
        applicable_trajectory_score=1.0,
        p50_total_tokens=0,
        p95_latency_ms=0,
        judge_error_count=1,
    )
    candidate = ModelCandidateEvaluation(
        model="llama3.1:8b",
        provider=ModelProvider.OLLAMA,
        safety_pass_rate=1.0,
        core_task_success_rate=0.97,
        mean_response_score=4.6,
        applicable_trajectory_score=1.0,
        p50_total_tokens=10_000,
        p95_latency_ms=4_000,
        judge_error_count=0,
    )

    decision = evaluate_model_candidate_for_tuning(candidate, baseline=baseline)

    assert decision.promotable is False
    assert "baseline_judge_errors_present" in decision.blocking_reasons
    assert "baseline_efficiency_missing" in decision.blocking_reasons


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


def test_model_usage_budget_decision_allows_in_budget_route_usage() -> None:
    profile = load_model_runtime_profile(
        {
            "LLM_PROVIDER": "ollama",
            "LLM_MODEL": "llama3.1:8b",
            "MODEL_CONTEXT_WINDOW_TOKENS": "8192",
        }
    )
    event = ModelUsageEvent(
        provider=ModelProvider.OLLAMA,
        model="llama3.1:8b",
        route="technical_analysis",
        prompt_tokens=4_000,
        output_tokens=900,
        tool_calls=4,
        queue_wait_ms=50,
        latency_ms=1_750,
        retries=0,
        request_id="req-ok",
    )

    decision = evaluate_model_usage_event(profile, event)
    payload = decision.to_dict()

    assert isinstance(decision, ModelUsageBudgetDecision)
    assert decision.allowed is True
    assert decision.violations == ()
    assert decision.prompt_budget_tokens == 6553
    assert decision.output_budget_tokens == 1500
    assert decision.tool_call_budget == 5
    assert payload["allowed"] is True
    assert "prompt" not in payload
    assert "response" not in payload


def test_model_usage_budget_decision_fails_closed_on_route_profile_and_budget_mismatch() -> None:
    profile = load_model_runtime_profile(
        {
            "LLM_PROVIDER": "ollama",
            "LLM_MODEL": "llama3.1:8b",
            "MODEL_CONTEXT_WINDOW_TOKENS": "8192",
        }
    )
    event = ModelUsageEvent(
        provider=ModelProvider.GEMINI,
        model="gemini-flash-latest",
        route="unknown_route",
        prompt_tokens=7_000,
        output_tokens=2_500,
        tool_calls=9,
        queue_wait_ms=0,
        latency_ms=3_000,
        retries=0,
        request_id="req-bad",
    )

    decision = evaluate_model_usage_event(profile, event)

    assert decision.allowed is False
    assert decision.prompt_budget_tokens is None
    assert decision.output_budget_tokens is None
    assert decision.tool_call_budget is None
    assert decision.violations == (
        "provider_mismatch",
        "model_mismatch",
        "unknown_route",
        "request_input_budget_exceeded",
        "context_window_exceeded",
    )


def test_model_usage_budget_decision_rejects_route_budget_overages() -> None:
    profile = load_model_runtime_profile(
        {
            "LLM_PROVIDER": "ollama",
            "LLM_MODEL": "llama3.1:8b",
            "MODEL_CONTEXT_WINDOW_TOKENS": "8192",
        }
    )
    event = ModelUsageEvent(
        provider=ModelProvider.OLLAMA,
        model="llama3.1:8b",
        route="paper_proposal_execution",
        prompt_tokens=6_600,
        output_tokens=1_200,
        tool_calls=4,
        queue_wait_ms=10,
        latency_ms=2_000,
        retries=0,
        request_id="req-over",
    )

    decision = evaluate_model_usage_event(profile, event)

    assert decision.allowed is False
    assert decision.violations == (
        "prompt_input_budget_exceeded",
        "output_budget_exceeded",
        "tool_call_budget_exceeded",
        "request_input_budget_exceeded",
    )


def test_model_usage_summary_records_efficiency_without_payloads() -> None:
    profile = load_model_runtime_profile(
        {
            "LLM_PROVIDER": "ollama",
            "LLM_MODEL": "llama3.1:8b",
            "MODEL_CONTEXT_WINDOW_TOKENS": "8192",
        }
    )
    events = (
        ModelUsageEvent(
            provider=ModelProvider.OLLAMA,
            model="llama3.1:8b",
            route="research",
            prompt_tokens=3_000,
            output_tokens=800,
            tool_calls=5,
            queue_wait_ms=100,
            latency_ms=2_000,
            retries=1,
            request_id="req-1",
        ),
        ModelUsageEvent(
            provider=ModelProvider.OLLAMA,
            model="llama3.1:8b",
            route="technical_analysis",
            prompt_tokens=2_000,
            output_tokens=600,
            tool_calls=3,
            queue_wait_ms=40,
            latency_ms=1_000,
            retries=0,
            request_id="req-2",
        ),
        ModelUsageEvent(
            provider=ModelProvider.OLLAMA,
            model="llama3.1:8b",
            route="research",
            prompt_tokens=4_000,
            output_tokens=1_000,
            tool_calls=4,
            queue_wait_ms=200,
            latency_ms=4_000,
            retries=2,
            request_id="req-3",
        ),
    )

    summary = summarize_model_usage_events(profile, events)
    payload = summary.to_dict()

    assert isinstance(summary, ModelUsageSummary)
    assert summary.event_count == 3
    assert summary.routes == {"research": 2, "technical_analysis": 1}
    assert summary.prompt_tokens == 9_000
    assert summary.output_tokens == 2_400
    assert summary.total_tokens == 11_400
    assert summary.tool_calls == 12
    assert summary.retries == 3
    assert summary.latency_p50_ms == 2_000
    assert summary.latency_p95_ms == 4_000
    assert summary.total_tokens_p50 == 3_800
    assert summary.total_tokens_p95 == 5_000
    assert payload["provider"] == "ollama"
    assert payload["model"] == "llama3.1:8b"
    assert "prompt" not in payload
    assert "response" not in payload
