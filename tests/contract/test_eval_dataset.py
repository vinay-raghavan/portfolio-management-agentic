import json
from pathlib import Path


DATASET = Path("apps/agent-service/tests/eval/datasets/basic-dataset.json")


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
