from portfolio_mcp.tools import (
    create_backtest_request,
    draft_paper_strategy,
    get_backtest_request,
    get_backtest_result,
    get_strategy_draft,
    list_backtest_requests,
    list_strategy_drafts,
)


def test_strategy_draft_history_is_readable_without_execution() -> None:
    draft = draft_paper_strategy(
        "SUNPHARMA",
        "Fixture candidate for defensive trend-resumption review.",
    )
    history = list_strategy_drafts()
    retrieved = get_strategy_draft(draft["strategy"]["strategy_id"])

    assert draft["status"] == "success"
    assert draft["policy"]["tier"] == "draft_only"
    assert draft["strategy"]["mode"] == "paper"
    assert draft["strategy"]["status"] == "draft"
    assert draft["strategy"]["source"] == "offline_fixture"
    assert draft["strategy"]["created_at"]

    assert history["status"] == "success"
    assert history["policy"]["tier"] == "read_only"
    assert any(
        item["strategy_id"] == draft["strategy"]["strategy_id"]
        for item in history["strategy_drafts"]
    )
    assert retrieved["status"] == "success"
    assert retrieved["policy"]["tier"] == "read_only"
    assert retrieved["strategy"]["strategy_id"] == draft["strategy"]["strategy_id"]
    assert "live" not in retrieved["strategy"]["status"].lower()


def test_backtest_request_history_links_to_simulated_result() -> None:
    request = create_backtest_request(
        "SBIN",
        "pullback-to-support",
        "2026-03-01",
        "2026-06-22",
    )
    history = list_backtest_requests()
    retrieved = get_backtest_request(request["backtest_request"]["request_id"])
    result = get_backtest_result(request["backtest_request"]["request_id"])

    assert request["status"] == "success"
    assert request["policy"]["tier"] == "draft_only"
    assert request["backtest_request"]["mode"] == "paper"
    assert request["backtest_request"]["status"] == "draft"
    assert request["backtest_request"]["source"] == "offline_fixture"

    assert history["status"] == "success"
    assert history["policy"]["tier"] == "read_only"
    assert any(
        item["request_id"] == request["backtest_request"]["request_id"]
        for item in history["backtest_requests"]
    )
    assert retrieved["status"] == "success"
    assert retrieved["policy"]["tier"] == "read_only"
    assert retrieved["backtest_request"] == request["backtest_request"]

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert (
        result["backtest_result"]["request_id"]
        == request["backtest_request"]["request_id"]
    )
    assert result["backtest_result"]["status"] == "simulated"
