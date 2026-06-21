from portfolio_policy import ActionTier, authorize_tool_call, classify_tool, redact_sensitive


def test_unknown_tools_are_forbidden_by_default() -> None:
    decision = authorize_tool_call("surprise_live_trade_tool")

    assert decision.allowed is False
    assert decision.tier == ActionTier.FORBIDDEN


def test_live_order_and_broker_token_tools_are_forbidden() -> None:
    for tool_name in ("place_live_order", "get_broker_trading_token"):
        decision = authorize_tool_call(tool_name)

        assert decision.allowed is False
        assert decision.requires_approval is False
        assert decision.tier == ActionTier.FORBIDDEN


def test_draft_and_read_only_tools_are_allowed_without_approval() -> None:
    for tool_name in ("get_portfolio_summary", "draft_paper_strategy"):
        decision = authorize_tool_call(tool_name)

        assert decision.allowed is True
        assert decision.requires_approval is False
        assert classify_tool(tool_name) in {ActionTier.READ_ONLY, ActionTier.DRAFT_ONLY}


def test_approval_required_tools_are_marked_for_human_review() -> None:
    decision = authorize_tool_call("request_paper_trade_approval")

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.tier == ActionTier.APPROVAL_REQUIRED


def test_redaction_removes_sensitive_values() -> None:
    payload = {
        "provider": "fyers",
        "token": "abc",
        "nested": {"client_secret": "def", "safe": "value"},
    }

    assert redact_sensitive(payload) == {
        "provider": "fyers",
        "token": "[REDACTED]",
        "nested": {"client_secret": "[REDACTED]", "safe": "value"},
    }

