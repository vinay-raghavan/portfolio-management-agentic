import json
from pathlib import Path
from typing import Any, Callable


DATASET = Path("apps/agent-service/tests/eval/datasets/basic-dataset.json")
EVAL_CONFIG = Path("apps/agent-service/tests/eval/eval_config.yaml")


def _extract_metric_function(metric_name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    lines = EVAL_CONFIG.read_text().splitlines()
    metric_start = next(
        index for index, line in enumerate(lines) if line == f"  - name: {metric_name}"
    )
    function_start = next(
        index
        for index in range(metric_start + 1, len(lines))
        if lines[index] == "    custom_function: |"
    )
    function_lines = []
    for line in lines[function_start + 1 :]:
        if line.startswith("  - name: "):
            break
        if line.startswith("      "):
            function_lines.append(line[6:])
        elif line:
            break
    namespace: dict[str, Any] = {}
    exec("\n".join(function_lines), namespace)
    return namespace["evaluate"]


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
        "workflow_tool_trajectory_policy",
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


def test_workflow_tool_trajectory_metric_passes_safe_composite_route() -> None:
    evaluate = _extract_metric_function("workflow_tool_trajectory_policy")

    result = evaluate(
        {
            "eval_case_id": "pre_market_briefing",
            "agent_data": {
                "turns": [
                    {
                        "events": [
                            {
                                "content": {
                                    "parts": [
                                        {
                                            "function_call": {
                                                "name": "create_pre_market_briefing"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            },
        }
    )

    assert result["score"] == 1


def test_workflow_tool_trajectory_metric_fails_missing_required_tool() -> None:
    evaluate = _extract_metric_function("workflow_tool_trajectory_policy")

    result = evaluate(
        {
            "eval_case_id": "provider_health_before_real_data",
            "agent_data": {
                "turns": [
                    {
                        "events": [
                            {
                                "content": {
                                    "parts": [
                                        {
                                            "function_call": {
                                                "name": "list_data_providers"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            },
        }
    )

    assert result["score"] == 0
    assert "get_data_provider_health" in result["explanation"]


def test_workflow_tool_trajectory_metric_fails_tools_on_forbidden_request() -> None:
    evaluate = _extract_metric_function("workflow_tool_trajectory_policy")

    result = evaluate(
        {
            "eval_case_id": "refuse_live_market_order",
            "agent_data": {
                "turns": [
                    {
                        "events": [
                            {
                                "content": {
                                    "parts": [
                                        {
                                            "function_call": {
                                                "name": "get_portfolio_summary"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            },
        }
    )

    assert result["score"] == 0
    assert "without tool calls" in result["explanation"]
