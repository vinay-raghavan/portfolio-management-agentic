from __future__ import annotations

from portfolio_model_provider import (
    ModelCandidateEvaluation,
    ModelProvider,
    evaluate_model_candidate_suite_for_tuning,
)


def _candidate(
    model: str,
    *,
    provider: ModelProvider = ModelProvider.OLLAMA,
    safety_pass_rate: float = 1.0,
    core_task_success_rate: float = 0.96,
    mean_response_score: float = 4.5,
    applicable_trajectory_score: float = 1.0,
    p50_total_tokens: int = 4_100,
    p95_latency_ms: int = 5_200,
    judge_error_count: int = 0,
) -> ModelCandidateEvaluation:
    return ModelCandidateEvaluation(
        model=model,
        provider=provider,
        safety_pass_rate=safety_pass_rate,
        core_task_success_rate=core_task_success_rate,
        mean_response_score=mean_response_score,
        applicable_trajectory_score=applicable_trajectory_score,
        p50_total_tokens=p50_total_tokens,
        p95_latency_ms=p95_latency_ms,
        judge_error_count=judge_error_count,
    )


BASELINE = _candidate(
    "incumbent",
    provider=ModelProvider.GEMINI,
    mean_response_score=4.6,
    p50_total_tokens=4_000,
    p95_latency_ms=5_000,
)


def test_model_candidate_suite_selects_best_promotable_model_without_provider_bias() -> None:
    decision = evaluate_model_candidate_suite_for_tuning(
        [
            _candidate("gemma4:12b", mean_response_score=4.2, p50_total_tokens=4_250),
            _candidate("llama3.1:8b", mean_response_score=4.5, p50_total_tokens=4_100),
            _candidate(
                "hosted-mini",
                provider=ModelProvider.OPENAI_COMPATIBLE,
                mean_response_score=4.9,
                p50_total_tokens=4_600,
            ),
            _candidate("unsafe-local", safety_pass_rate=0.98),
        ],
        baseline=BASELINE,
        sealed_holdout_passed=True,
        min_candidate_count=3,
    )

    payload = decision.to_dict()

    assert decision.promotable is True
    assert decision.selected_model == "llama3.1:8b"
    assert decision.selected_provider == ModelProvider.OLLAMA
    assert decision.blocking_reasons == ()
    assert payload["schema_version"] == "portfolio-model-candidate-suite/v1"
    assert payload["selected"] == {
        "model": "llama3.1:8b",
        "provider": "ollama",
    }
    assert payload["candidate_count"] == 4
    assert payload["promotable_candidate_count"] == 2
    assert payload["candidate_decisions"][0]["model"] == "llama3.1:8b"
    assert payload["candidate_decisions"][-1]["model"] == "unsafe-local"
    assert payload["candidate_decisions"][-1]["blocking_reasons"] == [
        "safety_pass_rate_below_100_percent"
    ]


def test_model_candidate_suite_fails_closed_without_sealed_holdout_or_required_candidate() -> None:
    decision = evaluate_model_candidate_suite_for_tuning(
        [_candidate("llama3.1:8b")],
        baseline=BASELINE,
        sealed_holdout_passed=False,
        min_candidate_count=2,
        required_candidate_models=("llama3.1:8b", "gemma4:12b"),
    )

    assert decision.promotable is False
    assert decision.selected_model is None
    assert decision.selected_provider is None
    assert decision.blocking_reasons == (
        "sealed_holdout_not_passed",
        "candidate_count_below_minimum",
        "required_candidate_model_missing:gemma4:12b",
    )
