import json
from pathlib import Path


DATASET = Path("apps/agent-service/tests/eval/datasets/basic-dataset.json")
EVAL_CONFIG = Path("apps/agent-service/tests/eval/eval_config.yaml")


def test_eval_dataset_contains_positive_and_negative_cases() -> None:
    data = json.loads(DATASET.read_text())
    case_ids = {case["eval_case_id"] for case in data["eval_cases"]}

    assert {
        "pre_market_briefing",
        "momentum_screener_to_paper_strategy",
        "provider_health_before_real_data",
        "factor_grounded_candidate_explanation",
        "backtest_to_paper_order_approval_queue",
        "approval_gated_simulated_fill_accounting",
        "strategy_backtest_history_review",
        "recommendation_explanation_review",
        "paper_trading_report_audit_export",
        "risk_review",
        "feature_navigation",
    }.issubset(case_ids)
    assert {
        "refuse_live_market_order",
        "refuse_fyers_trading_token",
        "refuse_live_strategy_enablement",
        "refuse_print_credentials",
    }.issubset(case_ids)


def test_eval_dataset_has_unique_case_ids() -> None:
    data = json.loads(DATASET.read_text())
    case_ids = [case["eval_case_id"] for case in data["eval_cases"]]

    assert len(case_ids) == len(set(case_ids))


def test_eval_rubric_matches_agent_workflow_routes() -> None:
    rubric = EVAL_CONFIG.read_text()

    for phrase in (
        "create_pre_market_briefing",
        "provider catalog and health tools",
        "import validation, onboarding, import preview, reconciliation",
        "candidate-evidence, pattern-library, citation, or factor-stack tools",
        "recommendation explanation before drafting paper order proposals",
        "approve the paper simulation before simulating a fill",
        "refuse live trading, live strategy enablement, broker trading-token access",
        "without trying to call tools",
    ):
        assert phrase in rubric
