from portfolio_mcp.tools import (
    cite_strategy_evidence,
    explain_factor_stack,
    get_pattern_playbook,
    list_universes,
    run_screener,
    search_pattern_library,
)


def test_list_universes_returns_fixture_metadata() -> None:
    result = list_universes()

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert result["universes"][0]["universe_id"] == "fixture_nifty50"
    assert result["universes"][0]["source"] == "offline_fixture"
    assert "TATAMOTORS" in result["universes"][0]["symbols"]


def test_fixture_screener_returns_gated_ranked_candidates_with_citations() -> None:
    result = run_screener("fixture_nifty50", "momentum", 5)

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    run = result["screener_run"]

    assert run["mode"] == "read_only"
    assert run["source"] == "offline_fixture"
    assert run["run_summary"]["total_screened"] >= 4
    assert run["run_summary"]["rejected_count"] >= 1
    assert run["multi_hit_symbols"]

    top = run["candidates"][0]
    assert top["rank"] == 1
    assert top["symbol"] == "TATAMOTORS"
    assert set(top["passed_screeners"]) >= {"momentum", "breakout"}
    assert all(gate["status"] == "pass" for gate in top["gates"])
    assert {component["name"] for component in top["score_components"]} >= {
        "technical",
        "fundamental",
        "sentiment",
        "volatility",
        "portfolio_fit",
    }
    assert top["citations"]
    assert top["next_allowed_actions"] == [
        "explain_evidence",
        "draft_paper_strategy",
    ]


def test_pattern_library_search_and_playbook_are_citation_backed() -> None:
    search = search_pattern_library("breakout volume", "", 3)
    assert search["status"] == "success"
    assert search["patterns"]

    first = search["patterns"][0]
    playbook = get_pattern_playbook(first["pattern_id"])

    assert playbook["status"] == "success"
    assert playbook["pattern"]["pattern_id"] == first["pattern_id"]
    assert playbook["pattern"]["citations"]
    assert playbook["pattern"]["source_type"] == "public_reference"


def test_strategy_evidence_and_factor_stack_are_read_only() -> None:
    evidence = cite_strategy_evidence("TATAMOTORS", "breakout-continuation")
    explanation = explain_factor_stack("TATAMOTORS", "breakout-continuation")

    assert evidence["status"] == "success"
    assert evidence["policy"]["tier"] == "read_only"
    assert evidence["evidence_pack"]["paper_only_status"] == "analysis_only"
    assert evidence["evidence_pack"]["citations"]

    assert explanation["status"] == "success"
    assert explanation["factor_stack"]["symbol"] == "TATAMOTORS"
    assert explanation["factor_stack"]["paper_only_status"] == "analysis_only"
    assert explanation["factor_stack"]["sections"]["technical"]["evidence"]
    assert explanation["factor_stack"]["sections"]["volatility"]["counterevidence"]
    assert "intraday_spread" in explanation["factor_stack"]["missing_data"]
