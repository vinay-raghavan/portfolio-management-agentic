from __future__ import annotations

from typing import Any

from .models import (
    FactorStackExplanation,
    FundamentalsSnapshot,
    GateResult,
    MacroSnapshot,
    MarketDataSnapshot,
    PatternCard,
    PatternCitation,
    RankedScreenerCandidate,
    ScoreComponent,
    ScreenerRunResult,
    SentimentSnapshot,
    StrategyEvidencePack,
    UniverseDefinition,
    VolatilitySnapshot,
)
from .provider_profiles import list_provider_import_reconciliation
from .provider_profiles import list_provider_refresh_readiness
from .providers import DataProviderRegistry, get_data_provider_registry
from .research_store import FileBackedPatternStore

OFFLINE_SOURCE = "offline_fixture"

TA_LIB = PatternCitation(
    source_id="ta-lib-indicators",
    title="TA-Lib Technical Analysis Indicator Catalog",
    url="https://ta-lib.org/",
    usage_notes="Indicator names and families for RSI, MACD, ADX, Bollinger Bands, ATR, and candlestick recognition.",
)
FAMA_FRENCH_MOMENTUM = PatternCitation(
    source_id="fama-french-momentum",
    title="Fama/French Momentum Factor",
    url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/det_mom_factor.html",
    usage_notes="Public reference for prior-return momentum factor construction.",
)
FAMA_FRENCH_FACTORS = PatternCitation(
    source_id="fama-french-five-factor",
    title="Fama/French Five-Factor Data Library",
    url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_5_factors_2x3.html",
    usage_notes="Public reference for value, size, profitability, and investment factor definitions.",
)
SP_QVM = PatternCitation(
    source_id="sp-qvm-multifactor",
    title="S&P Quality, Value & Momentum Multi-Factor Index",
    url="https://www.spglobal.com/spdji/en/indices/dividends-factors/sp-500-quality-value-momentum-multi-factor-index/",
    usage_notes="Public example of selecting securities by combined quality, value, and momentum score.",
)
CBOE_VIX = PatternCitation(
    source_id="cboe-vix-methodology",
    title="Cboe VIX Methodology",
    url="https://cdn.cboe.com/resources/indices/Volatility_Index_Methodology_Cboe_Volatility_Index.pdf",
    usage_notes="Reference for expected 30-day equity-market volatility methodology.",
)
NSE_INDIA_VIX = PatternCitation(
    source_id="nse-india-vix",
    title="NSE India VIX",
    url="https://www.nseindia.com/static/products-services/indices-indiavix-index",
    usage_notes="Reference for India VIX as NIFTY options-derived expected volatility.",
)
AAII_SENTIMENT = PatternCitation(
    source_id="aaii-sentiment-survey",
    title="AAII Investor Sentiment Survey",
    url="https://www.aaii.com/sentimentsurvey",
    usage_notes="Public reference for bullish, neutral, and bearish investor sentiment survey framing.",
)
FRED_API = PatternCitation(
    source_id="fred-api",
    title="Federal Reserve Economic Data API",
    url="https://fred.stlouisfed.org/docs/api/fred/",
    usage_notes="Reference for economic series, release calendars, and historical observations used in macro context.",
)

PROVIDER_READINESS_CITATION = "provider-refresh-readiness"
PROVIDER_IMPORT_RECONCILIATION_CITATION = "provider-import-reconciliation"
_READINESS_NEEDS_ATTENTION = {
    "backoff",
    "needs_attention",
    "pending_refresh",
    "retry_due",
    "stale",
}
_RECONCILIATION_NEEDS_ATTENTION = {
    "needs_attention",
    "pending_refresh",
    "source_changed",
    "store_mismatch",
}

UNIVERSES = [
    UniverseDefinition(
        universe_id="fixture_nifty50",
        name="Offline Fixture NIFTY 50 Slice",
        source=OFFLINE_SOURCE,
        as_of="2026-06-22",
        symbols=["TATAMOTORS", "SBIN", "SUNPHARMA", "LOWLIQ"],
        notes=[
            "Deterministic fixture for tests and capstone evidence.",
            "No live market feed, broker account, or provider credential is required.",
        ],
    )
]

PATTERN_CARDS = [
    PatternCard(
        pattern_id="breakout-continuation-v1",
        version="1.0",
        title="Breakout Continuation",
        setup_type="breakout-continuation",
        summary="A trend-following setup where price extends above a prior range with volume and trend confirmation.",
        prerequisites=[
            "Tradable liquidity and sufficient daily history.",
            "Price above relevant moving averages.",
            "Volume expansion or breadth confirmation.",
        ],
        evidence=[
            "Prior-return momentum remains positive.",
            "Breakout or close above a recent range is present.",
            "Volume confirms demand rather than a thin move.",
        ],
        counterevidence=[
            "Elevated volatility can widen stops and reduce sizing.",
            "Failed breakout close should invalidate the setup.",
        ],
        risk_notes=[
            "Use ATR-aware stop width and position caps.",
            "Analysis can support only a draft paper strategy.",
        ],
        citations=[TA_LIB, FAMA_FRENCH_MOMENTUM],
        tags=["technical", "momentum", "breakout", "volume"],
        source_type="public_reference",
    ),
    PatternCard(
        pattern_id="pullback-to-support-v1",
        version="1.0",
        title="Pullback To Support",
        setup_type="pullback-to-support",
        summary="An uptrend continuation setup where price cools toward support without breaking the broader trend.",
        prerequisites=[
            "Uptrend remains intact.",
            "Pullback is controlled, not a trend break.",
            "Liquidity and volatility gates pass.",
        ],
        evidence=[
            "RSI or short-term momentum cools from an extended zone.",
            "Price remains above medium-term trend support.",
            "Risk reward improves if volatility is controlled.",
        ],
        counterevidence=[
            "Weak breadth or sector exposure can reduce confidence.",
            "A close below support invalidates the setup.",
        ],
        risk_notes=[
            "Do not average down failed support.",
            "Keep paper proposals pending until risk review passes.",
        ],
        citations=[TA_LIB, FAMA_FRENCH_MOMENTUM],
        tags=["technical", "pullback", "support", "momentum"],
        source_type="public_reference",
    ),
    PatternCard(
        pattern_id="quality-momentum-confirmation-v1",
        version="1.0",
        title="Quality And Momentum Confirmation",
        setup_type="quality-momentum",
        summary="A cross-factor confirmation pattern where technical momentum is supported by quality or profitability evidence.",
        prerequisites=[
            "Technical signal is valid after hard gates.",
            "Fundamental data is fresh enough for comparison.",
        ],
        evidence=[
            "Momentum and quality factors agree.",
            "Profitability or leverage data does not contradict the setup.",
        ],
        counterevidence=[
            "Missing fundamentals should lower confidence.",
            "One strong factor should not hide weakness in another.",
        ],
        risk_notes=[
            "Treat factors as evidence, not trade authorization.",
            "Use portfolio concentration checks before drafting paper exposure.",
        ],
        citations=[FAMA_FRENCH_FACTORS, SP_QVM],
        tags=["fundamental", "quality", "momentum", "multi_factor"],
        source_type="public_reference",
    ),
    PatternCard(
        pattern_id="volatility-regime-sizing-v1",
        version="1.0",
        title="Volatility Regime Sizing",
        setup_type="volatility-regime",
        summary="A risk-control pattern that uses expected volatility context to downgrade sizing, confidence, or candidate count.",
        prerequisites=[
            "A volatility proxy is available.",
            "Candidate technical evidence is separated from risk sizing.",
        ],
        evidence=[
            "Expected volatility affects stop width and position caps.",
            "Elevated volatility can turn a valid setup into a watch-only candidate.",
        ],
        counterevidence=[
            "Low volatility does not make a weak setup valid.",
            "Volatility context must not mechanically create orders.",
        ],
        risk_notes=[
            "Use volatility for sizing and gating, not standalone entry signals.",
            "Keep live trading forbidden regardless of volatility regime.",
        ],
        citations=[CBOE_VIX, NSE_INDIA_VIX],
        tags=["risk", "volatility", "vix", "sizing"],
        source_type="public_reference",
    ),
]

PATTERN_STORE = FileBackedPatternStore(PATTERN_CARDS)

_COMPONENTS: dict[str, list[ScoreComponent]] = {
    "TATAMOTORS": [
        ScoreComponent(
            "technical",
            0.92,
            0.35,
            [
                "Price is above short and medium moving-average support.",
                "Breakout and momentum screen families both pass.",
            ],
            [],
            [TA_LIB.source_id, FAMA_FRENCH_MOMENTUM.source_id],
        ),
        ScoreComponent(
            "fundamental",
            0.66,
            0.15,
            ["Quality proxy is acceptable in fixture data."],
            ["Full earnings-revision history is unavailable in fixtures."],
            [FAMA_FRENCH_FACTORS.source_id, SP_QVM.source_id],
        ),
        ScoreComponent(
            "sentiment",
            0.58,
            0.10,
            ["Fixture sentiment is mildly constructive."],
            ["No live news sentiment adapter is configured."],
            [AAII_SENTIMENT.source_id],
        ),
        ScoreComponent(
            "volatility",
            0.52,
            0.15,
            ["Volatility is tradable but elevated."],
            ["ATR is high enough to require smaller paper sizing."],
            [NSE_INDIA_VIX.source_id, CBOE_VIX.source_id],
        ),
        ScoreComponent(
            "portfolio_fit",
            0.74,
            0.15,
            ["Adds auto exposure without increasing current technology concentration."],
            [],
            ["portfolio-policy-paper-only"],
        ),
        ScoreComponent(
            "pattern",
            0.88,
            0.10,
            ["Matches breakout-continuation pattern prerequisites."],
            ["Failed breakout close would invalidate the setup."],
            ["breakout-continuation-v1"],
        ),
    ],
    "SBIN": [
        ScoreComponent(
            "technical",
            0.76,
            0.35,
            ["Pullback remains above medium-term support."],
            ["Breakout evidence is weaker than the top candidate."],
            [TA_LIB.source_id],
        ),
        ScoreComponent(
            "fundamental",
            0.68,
            0.15,
            ["Profitability proxy is acceptable in fixture data."],
            [],
            [FAMA_FRENCH_FACTORS.source_id],
        ),
        ScoreComponent(
            "sentiment",
            0.61,
            0.10,
            ["Investor sentiment context is neutral to constructive."],
            ["No live news adapter is configured."],
            [AAII_SENTIMENT.source_id],
        ),
        ScoreComponent(
            "volatility",
            0.64,
            0.15,
            ["Volatility is inside fixture risk bounds."],
            [],
            [NSE_INDIA_VIX.source_id],
        ),
        ScoreComponent(
            "portfolio_fit",
            0.44,
            0.15,
            [],
            ["Financial exposure already exists in the fixture portfolio."],
            ["portfolio-policy-paper-only"],
        ),
        ScoreComponent(
            "pattern",
            0.80,
            0.10,
            ["Matches pullback-to-support pattern prerequisites."],
            [],
            ["pullback-to-support-v1"],
        ),
    ],
    "SUNPHARMA": [
        ScoreComponent(
            "technical",
            0.63,
            0.35,
            ["Trend has resumed above short-term support."],
            ["Momentum confirmation is moderate."],
            [TA_LIB.source_id],
        ),
        ScoreComponent(
            "fundamental",
            0.72,
            0.15,
            ["Quality proxy supports defensive review."],
            [],
            [FAMA_FRENCH_FACTORS.source_id, SP_QVM.source_id],
        ),
        ScoreComponent(
            "sentiment",
            0.54,
            0.10,
            ["Sentiment is neutral in fixture data."],
            [],
            [AAII_SENTIMENT.source_id],
        ),
        ScoreComponent(
            "volatility",
            0.70,
            0.15,
            ["Volatility is calmer than other candidates."],
            [],
            [NSE_INDIA_VIX.source_id],
        ),
        ScoreComponent(
            "portfolio_fit",
            0.78,
            0.15,
            ["Defensive sector diversifies fixture exposure."],
            [],
            ["portfolio-policy-paper-only"],
        ),
        ScoreComponent(
            "pattern",
            0.58,
            0.10,
            ["Partial match to quality-momentum confirmation."],
            ["Momentum evidence is not as strong as top candidates."],
            ["quality-momentum-confirmation-v1"],
        ),
    ],
}

_PASSED_SCREENERS = {
    "TATAMOTORS": ["momentum", "breakout"],
    "SBIN": ["momentum", "pullback"],
    "SUNPHARMA": ["momentum"],
}

_SETUPS = {
    "TATAMOTORS": "breakout-continuation",
    "SBIN": "pullback-to-support",
    "SUNPHARMA": "quality-momentum",
}

_GATES = {
    "TATAMOTORS": [
        GateResult("data_quality", "pass", "252 daily bars available in fixture."),
        GateResult("tradability", "pass", "Liquidity and ATR sanity checks pass."),
        GateResult("paper_only", "pass", "Only read-only or draft paper actions are allowed."),
    ],
    "SBIN": [
        GateResult("data_quality", "pass", "252 daily bars available in fixture."),
        GateResult("tradability", "pass", "Liquidity and ATR sanity checks pass."),
        GateResult("paper_only", "pass", "Only read-only or draft paper actions are allowed."),
    ],
    "SUNPHARMA": [
        GateResult("data_quality", "pass", "252 daily bars available in fixture."),
        GateResult("tradability", "pass", "Liquidity and ATR sanity checks pass."),
        GateResult("paper_only", "pass", "Only read-only or draft paper actions are allowed."),
    ],
    "LOWLIQ": [
        GateResult("data_quality", "pass", "Daily history is present in fixture."),
        GateResult("tradability", "fail", "Fixture median turnover is below the liquidity floor."),
        GateResult("paper_only", "pass", "Only read-only or draft paper actions are allowed."),
    ],
}


def list_fixture_universes() -> list[UniverseDefinition]:
    return get_data_provider_registry().universe.list_universes()


def _universe_by_id(universe_id: str) -> UniverseDefinition:
    for universe in list_fixture_universes():
        if universe.universe_id == universe_id:
            return universe
    raise ValueError(f"Unknown universe_id: {universe_id}")


def _weighted_score(components: list[ScoreComponent]) -> float:
    total_weight = sum(component.weight for component in components)
    if total_weight == 0:
        return 0.0
    raw = sum(component.score * component.weight for component in components) / total_weight
    return round(raw, 3)


def _citations_for_components(components: list[ScoreComponent]) -> list[str]:
    citations: list[str] = []
    for component in components:
        for citation in component.citations:
            if citation not in citations:
                citations.append(citation)
    return citations


def _active_provider_refresh_readiness() -> list[dict[str, Any]]:
    readiness = list_provider_refresh_readiness()
    return [
        item
        for item in readiness
        if item.get("configured") or item.get("latest_status") != "none"
    ]


def _active_provider_import_reconciliation() -> list[dict[str, Any]]:
    reconciliation = list_provider_import_reconciliation()
    return [
        item
        for item in reconciliation
        if item.get("configured") or item.get("latest_job", {}).get("status") != "none"
    ]


def _provider_refresh_readiness_summary(
    readiness: list[dict[str, Any]],
) -> dict[str, Any]:
    statuses = {
        str(item["provider_id"]): str(item["readiness_status"])
        for item in readiness
    }
    needs_attention = [
        provider_id
        for provider_id, status in statuses.items()
        if status in _READINESS_NEEDS_ATTENTION
    ]
    return {
        "configured_count": len(readiness),
        "ready": sum(1 for status in statuses.values() if status == "ready"),
        "stale": sum(1 for status in statuses.values() if status == "stale"),
        "needs_attention": len(needs_attention),
        "provider_statuses": statuses,
        "needs_attention_provider_ids": needs_attention,
    }


def _provider_readiness_notes(
    readiness: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    evidence: list[str] = []
    counterevidence: list[str] = []
    missing_data: list[str] = []
    for item in readiness:
        provider_id = str(item["provider_id"])
        status = str(item["readiness_status"])
        source_label = str(item.get("source_label") or "configured provider")
        if status == "ready":
            evidence.append(
                f"{provider_id} refresh readiness is ready from {source_label}."
            )
            continue
        marker = f"{provider_id}_refresh_{status}"
        missing_data.append(marker)
        if status == "stale":
            counterevidence.append(
                f"{provider_id} refresh readiness is stale; refresh before relying on this provider context."
            )
        elif status == "backoff":
            next_attempt = str(item.get("next_attempt_at") or "")
            suffix = f" until {next_attempt}" if next_attempt else ""
            counterevidence.append(
                f"{provider_id} refresh readiness is in backoff{suffix}."
            )
        elif status == "retry_due":
            counterevidence.append(
                f"{provider_id} refresh readiness is retry due and should be refreshed before use."
            )
        elif status == "pending_refresh":
            counterevidence.append(
                f"{provider_id} is configured but has no completed refresh job yet."
            )
        elif status == "needs_attention":
            counterevidence.append(
                f"{provider_id} refresh readiness needs attention before this evidence is trusted."
            )
        elif status == "not_configured":
            counterevidence.append(f"{provider_id} is not configured for refresh.")
    return evidence, counterevidence, missing_data


def _provider_readiness_score(readiness: list[dict[str, Any]]) -> float:
    if not readiness:
        return 1.0
    statuses = {str(item["readiness_status"]) for item in readiness}
    if statuses == {"ready"}:
        return 1.0
    if "backoff" in statuses or "needs_attention" in statuses:
        return 0.25
    if "retry_due" in statuses or "pending_refresh" in statuses:
        return 0.35
    if "stale" in statuses:
        return 0.50
    return 0.60


def _provider_readiness_component(
    readiness: list[dict[str, Any]],
) -> tuple[ScoreComponent | None, list[str]]:
    if not readiness:
        return None, []
    evidence, counterevidence, missing_data = _provider_readiness_notes(readiness)
    return (
        ScoreComponent(
            "provider_readiness",
            _provider_readiness_score(readiness),
            0.05,
            evidence,
            counterevidence,
            [PROVIDER_READINESS_CITATION],
        ),
        missing_data,
    )


def _provider_import_reconciliation_summary(
    reconciliation: list[dict[str, Any]],
) -> dict[str, Any]:
    statuses = {
        str(item["provider_id"]): str(item["reconciliation_status"])
        for item in reconciliation
    }
    needs_attention = [
        provider_id
        for provider_id, status in statuses.items()
        if status in _RECONCILIATION_NEEDS_ATTENTION
    ]
    return {
        "configured_count": len(reconciliation),
        "in_sync": sum(1 for status in statuses.values() if status == "in_sync"),
        "pending_refresh": sum(
            1 for status in statuses.values() if status == "pending_refresh"
        ),
        "source_changed": sum(
            1 for status in statuses.values() if status == "source_changed"
        ),
        "store_mismatch": sum(
            1 for status in statuses.values() if status == "store_mismatch"
        ),
        "needs_attention": sum(
            1 for status in statuses.values() if status == "needs_attention"
        ),
        "provider_statuses": statuses,
        "needs_attention_provider_ids": needs_attention,
    }


def _provider_import_reconciliation_notes(
    reconciliation: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    evidence: list[str] = []
    counterevidence: list[str] = []
    missing_data: list[str] = []
    for item in reconciliation:
        provider_id = str(item["provider_id"])
        status = str(item["reconciliation_status"])
        if status == "in_sync":
            evidence.append(
                f"{provider_id} import reconciliation is in sync with structured storage."
            )
            continue
        if status == "not_configured":
            continue
        marker = f"{provider_id}_import_{status}"
        missing_data.append(marker)
        if status == "pending_refresh":
            counterevidence.append(
                f"{provider_id} configured source has not been refreshed into structured storage."
            )
        elif status == "source_changed":
            counterevidence.append(
                f"{provider_id} configured source changed after the latest refresh; refresh before paper decisions."
            )
        elif status == "store_mismatch":
            counterevidence.append(
                f"{provider_id} latest import count differs from stored rows; rerun refresh before paper decisions."
            )
        elif status == "needs_attention":
            counterevidence.append(
                f"{provider_id} import reconciliation needs attention before configured evidence is trusted."
            )
    return evidence, counterevidence, missing_data


def _provider_import_reconciliation_score(
    reconciliation: list[dict[str, Any]],
) -> float:
    if not reconciliation:
        return 1.0
    statuses = {str(item["reconciliation_status"]) for item in reconciliation}
    if statuses == {"in_sync"}:
        return 1.0
    if "store_mismatch" in statuses or "needs_attention" in statuses:
        return 0.20
    if "source_changed" in statuses:
        return 0.30
    if "pending_refresh" in statuses:
        return 0.35
    return 0.60


def _provider_import_reconciliation_component(
    reconciliation: list[dict[str, Any]],
) -> tuple[ScoreComponent | None, list[str]]:
    if not reconciliation:
        return None, []
    evidence, counterevidence, missing_data = _provider_import_reconciliation_notes(
        reconciliation,
    )
    return (
        ScoreComponent(
            "provider_import_reconciliation",
            _provider_import_reconciliation_score(reconciliation),
            0.05,
            evidence,
            counterevidence,
            [PROVIDER_IMPORT_RECONCILIATION_CITATION],
        ),
        missing_data,
    )


def _provider_import_reconciliation_gate(
    reconciliation: list[dict[str, Any]],
) -> GateResult | None:
    if not reconciliation:
        return None
    statuses = {
        str(item["reconciliation_status"])
        for item in reconciliation
        if str(item["reconciliation_status"]) != "not_configured"
    }
    if not statuses:
        return None
    if statuses == {"in_sync"}:
        return GateResult(
            "provider_import_reconciliation",
            "pass",
            "Configured provider imports are reconciled with structured storage.",
        )
    return GateResult(
        "provider_import_reconciliation",
        "review",
        "Configured provider imports need reconciliation review before paper decisions.",
    )


def _paper_actions_after_reconciliation(
    actions: list[str],
    reconciliation: list[dict[str, Any]],
) -> list[str]:
    statuses = {
        str(item["reconciliation_status"])
        for item in reconciliation
        if str(item["reconciliation_status"]) != "not_configured"
    }
    if not statuses or statuses == {"in_sync"}:
        return actions
    return [
        action
        for action in actions
        if action not in {"draft_paper_strategy", "create_paper_order_proposal"}
    ]


def _candidate_with_provider_readiness(
    candidate: RankedScreenerCandidate,
    readiness: list[dict[str, Any]],
) -> RankedScreenerCandidate:
    component, missing_data = _provider_readiness_component(readiness)
    if component is None:
        return candidate
    components = [*candidate.score_components, component]
    return RankedScreenerCandidate(
        rank=candidate.rank,
        symbol=candidate.symbol,
        setup=candidate.setup,
        score=_weighted_score(components),
        passed_screeners=candidate.passed_screeners,
        gates=candidate.gates,
        score_components=components,
        evidence=[*candidate.evidence, *component.evidence],
        counterevidence=[*candidate.counterevidence, *component.counterevidence],
        missing_data=sorted({*candidate.missing_data, *missing_data}),
        citations=_citations_for_components(components),
        next_allowed_actions=candidate.next_allowed_actions,
    )


def _candidate_with_provider_import_reconciliation(
    candidate: RankedScreenerCandidate,
    reconciliation: list[dict[str, Any]],
) -> RankedScreenerCandidate:
    component, missing_data = _provider_import_reconciliation_component(
        reconciliation,
    )
    if component is None:
        return candidate
    gate = _provider_import_reconciliation_gate(reconciliation)
    components = [*candidate.score_components, component]
    gates = [*candidate.gates]
    if gate is not None:
        gates.append(gate)
    return RankedScreenerCandidate(
        rank=candidate.rank,
        symbol=candidate.symbol,
        setup=candidate.setup,
        score=_weighted_score(components),
        passed_screeners=candidate.passed_screeners,
        gates=gates,
        score_components=components,
        evidence=[*candidate.evidence, *component.evidence],
        counterevidence=[*candidate.counterevidence, *component.counterevidence],
        missing_data=sorted({*candidate.missing_data, *missing_data}),
        citations=_citations_for_components(components),
        next_allowed_actions=_paper_actions_after_reconciliation(
            candidate.next_allowed_actions,
            reconciliation,
        ),
    )


def _candidate(symbol: str, rank: int) -> RankedScreenerCandidate:
    components = _COMPONENTS[symbol]
    return RankedScreenerCandidate(
        rank=rank,
        symbol=symbol,
        setup=_SETUPS[symbol],
        score=_weighted_score(components),
        passed_screeners=_PASSED_SCREENERS[symbol],
        gates=_GATES[symbol],
        score_components=components,
        evidence=[
            evidence
            for component in components
            for evidence in component.evidence
        ],
        counterevidence=[
            item
            for component in components
            for item in component.counterevidence
        ],
        missing_data=["intraday_spread", "live_news_sentiment"],
        citations=_citations_for_components(components),
        next_allowed_actions=["explain_evidence", "draft_paper_strategy"],
    )


def _metric(snapshot: MarketDataSnapshot, name: str, default: float = 0.0) -> float:
    value = snapshot.metrics.get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fundamental_metric(
    fundamentals: FundamentalsSnapshot,
    name: str,
    default: float = 0.0,
) -> float:
    value = fundamentals.metrics.get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sentiment_metric(
    sentiment: SentimentSnapshot,
    name: str,
    default: float = 0.0,
) -> float:
    value = sentiment.metrics.get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _volatility_metric(
    volatility: VolatilitySnapshot,
    name: str,
    default: float = 0.0,
) -> float:
    value = volatility.metrics.get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _macro_metric(
    macro: MacroSnapshot,
    name: str,
    default: float = 0.0,
) -> float:
    value = macro.metrics.get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bounded(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _configured_gates(snapshot: MarketDataSnapshot) -> list[GateResult]:
    bar_count = len(snapshot.bars)
    turnover = _metric(snapshot, "median_turnover_cr")
    atr_pct = _metric(snapshot, "atr_pct")
    data_status = "pass" if bar_count >= 3 else "fail"
    tradability_status = "pass" if turnover >= 1.0 and 0 < atr_pct <= 7.0 else "fail"
    return [
        GateResult(
            "data_quality",
            data_status,
            f"{bar_count} configured OHLCV bars available.",
        ),
        GateResult(
            "tradability",
            tradability_status,
            f"Median turnover proxy is {turnover:.2f} crore and ATR proxy is {atr_pct:.2f}%.",
        ),
        GateResult(
            "paper_only",
            "pass",
            "Only read-only or draft paper actions are allowed.",
        ),
    ]


def _configured_passed_screeners(snapshot: MarketDataSnapshot) -> list[str]:
    roc20 = _metric(snapshot, "roc20_pct")
    rsi14 = _metric(snapshot, "rsi14")
    prior_high = max((bar.high for bar in snapshot.bars[:-1]), default=snapshot.latest_close)
    passed: list[str] = []
    if roc20 >= 3.0 and 45.0 <= rsi14 <= 72.0:
        passed.append("momentum")
    if snapshot.latest_close >= prior_high and roc20 >= 5.0:
        passed.append("breakout")
    if 0.0 < roc20 < 5.0 and 45.0 <= rsi14 <= 58.0:
        passed.append("pullback")
    return passed


def _configured_setup(passed_screeners: list[str]) -> str:
    if "breakout" in passed_screeners:
        return "breakout-continuation"
    if "pullback" in passed_screeners:
        return "pullback-to-support"
    return "quality-momentum"


def _configured_components(
    snapshot: MarketDataSnapshot,
    passed_screeners: list[str],
    fundamentals: FundamentalsSnapshot | None,
    sentiment: SentimentSnapshot | None,
    volatility: VolatilitySnapshot | None,
    macro: MacroSnapshot | None,
) -> list[ScoreComponent]:
    roc20 = _metric(snapshot, "roc20_pct")
    rsi14 = _metric(snapshot, "rsi14")
    atr_pct = _metric(snapshot, "atr_pct")
    turnover = _metric(snapshot, "median_turnover_cr")
    technical_score = _bounded(0.48 + (roc20 / 20.0) + ((rsi14 - 50.0) / 120.0))
    atr_volatility_score = _bounded(1.0 - abs(atr_pct - 2.5) / 8.0)
    liquidity_score = _bounded(turnover / 10.0)
    pattern_score = 0.82 if "breakout" in passed_screeners else 0.68
    pattern_counterevidence: list[str] = []
    if fundamentals is None:
        pattern_counterevidence.append("Configured fundamentals are unavailable for this symbol.")
    if sentiment is None:
        pattern_counterevidence.append("Configured sentiment is unavailable for this symbol.")
    if volatility is None:
        pattern_counterevidence.append(
            "Configured volatility context is unavailable for this symbol."
        )
    if macro is None:
        pattern_counterevidence.append(
            "Configured macro/regime context is unavailable for this symbol."
        )
    components = [
        ScoreComponent(
            "technical",
            round(technical_score, 3),
            0.25,
            [
                f"Configured 20-day momentum proxy is {roc20:.2f}%.",
                f"Configured RSI proxy is {rsi14:.2f}.",
            ],
            [],
            [TA_LIB.source_id, FAMA_FRENCH_MOMENTUM.source_id],
        ),
    ]
    if fundamentals is not None:
        quality = _fundamental_metric(fundamentals, "quality_score")
        value = _fundamental_metric(fundamentals, "value_score")
        growth = _fundamental_metric(fundamentals, "growth_score")
        revision = _fundamental_metric(fundamentals, "earnings_revision_score")
        leverage = _fundamental_metric(fundamentals, "leverage_score")
        fundamental_score = _bounded(
            (quality * 0.30)
            + (growth * 0.25)
            + (value * 0.20)
            + (revision * 0.15)
            + (leverage * 0.10)
        )
        fundamental_counterevidence: list[str] = []
        if quality < 0.55:
            fundamental_counterevidence.append("Quality score is below confirmation range.")
        if revision < 0.50:
            fundamental_counterevidence.append(
                "Earnings revision score does not confirm momentum."
            )
        if leverage < 0.50:
            fundamental_counterevidence.append("Leverage score weakens risk quality.")
        components.append(
            ScoreComponent(
                "fundamental",
                round(fundamental_score, 3),
                0.20,
                [
                    f"Configured fundamentals are as of {fundamentals.as_of}.",
                    f"Quality, value, and growth scores are {quality:.2f}, {value:.2f}, and {growth:.2f}.",
                    f"Earnings revision and leverage scores are {revision:.2f} and {leverage:.2f}.",
                ],
                fundamental_counterevidence,
                [FAMA_FRENCH_FACTORS.source_id, SP_QVM.source_id],
            )
        )
    if sentiment is not None:
        news = _sentiment_metric(sentiment, "news_score")
        investor = _sentiment_metric(sentiment, "investor_score")
        contradiction = _sentiment_metric(sentiment, "contradiction_score")
        sentiment_score = _bounded(
            (news * 0.50)
            + (investor * 0.35)
            + ((1.0 - contradiction) * 0.15)
        )
        sentiment_counterevidence: list[str] = []
        if news < 0.50:
            sentiment_counterevidence.append("News sentiment does not confirm the setup.")
        if contradiction > 0.40:
            sentiment_counterevidence.append(
                "Contradiction score is high enough to reduce confidence."
            )
        components.append(
            ScoreComponent(
                "sentiment",
                round(sentiment_score, 3),
                0.10,
                [
                    f"Configured sentiment is as of {sentiment.as_of}.",
                    f"News and investor sentiment scores are {news:.2f} and {investor:.2f}.",
                    f"Contradiction score is {contradiction:.2f}.",
                ],
                sentiment_counterevidence,
                [AAII_SENTIMENT.source_id],
            )
        )
    volatility_score = atr_volatility_score
    volatility_evidence = [f"Configured ATR proxy is {atr_pct:.2f}%."]
    volatility_counterevidence = [
        "Volatility controls can still downgrade sizing or candidate count.",
    ]
    if volatility is not None:
        india_vix = _volatility_metric(volatility, "india_vix")
        vix_change = _volatility_metric(volatility, "vix_change_pct")
        regime = _volatility_metric(volatility, "regime_score", atr_volatility_score)
        risk_multiplier = _volatility_metric(volatility, "risk_multiplier", 1.0)
        volatility_score = _bounded((atr_volatility_score * 0.45) + (regime * 0.55))
        volatility_evidence.extend(
            [
                f"Configured volatility is as of {volatility.as_of}.",
                f"India VIX is {india_vix:.2f} with {vix_change:.2f}% change.",
                f"Volatility regime score is {regime:.2f}; risk multiplier is {risk_multiplier:.2f}.",
            ]
        )
        if india_vix >= 18.0 or vix_change >= 5.0 or risk_multiplier < 0.65:
            volatility_counterevidence.append(
                "Configured volatility context calls for smaller paper sizing."
            )
    if macro is not None:
        market_regime = _macro_metric(macro, "market_regime_score")
        breadth = _macro_metric(macro, "breadth_score")
        rate_pressure = _macro_metric(macro, "rate_pressure_score")
        event_risk = _macro_metric(macro, "event_risk_score")
        liquidity_condition = _macro_metric(macro, "liquidity_condition_score")
        macro_score = _bounded(
            (market_regime * 0.35)
            + (breadth * 0.25)
            + (rate_pressure * 0.15)
            + (liquidity_condition * 0.15)
            + ((1.0 - event_risk) * 0.10)
        )
        macro_counterevidence: list[str] = []
        if event_risk >= 0.50:
            macro_counterevidence.append(
                "Event risk score is elevated enough to reduce conviction."
            )
        if breadth < 0.50:
            macro_counterevidence.append(
                "Breadth score does not confirm a broad risk-on regime."
            )
        if rate_pressure < 0.45:
            macro_counterevidence.append(
                "Rate-pressure score weakens the macro backdrop."
            )
        components.append(
            ScoreComponent(
                "macro",
                round(macro_score, 3),
                0.10,
                [
                    f"Configured macro context is as of {macro.as_of}.",
                    f"Market regime and breadth scores are {market_regime:.2f} and {breadth:.2f}.",
                    f"Rate-pressure and liquidity-condition scores are {rate_pressure:.2f} and {liquidity_condition:.2f}.",
                    f"Event risk score is {event_risk:.2f}.",
                ],
                macro_counterevidence,
                [FRED_API.source_id],
            )
        )
    components.extend(
        [
            ScoreComponent(
                "volatility",
                round(volatility_score, 3),
                0.15,
                volatility_evidence,
                volatility_counterevidence,
                [NSE_INDIA_VIX.source_id, CBOE_VIX.source_id],
            ),
            ScoreComponent(
                "liquidity",
                round(liquidity_score, 3),
                0.10,
                [f"Configured median turnover proxy is {turnover:.2f} crore."],
                [],
                ["portfolio-policy-paper-only"],
            ),
            ScoreComponent(
                "pattern",
                pattern_score,
                0.10,
                [f"Configured metrics passed: {', '.join(passed_screeners) or 'none'}."],
                pattern_counterevidence,
                [_configured_setup(passed_screeners) + "-v1"],
            ),
        ]
    )
    return components


def _configured_candidate(
    snapshot: MarketDataSnapshot,
    rank: int,
    fundamentals: FundamentalsSnapshot | None = None,
    sentiment: SentimentSnapshot | None = None,
    volatility: VolatilitySnapshot | None = None,
    macro: MacroSnapshot | None = None,
) -> RankedScreenerCandidate:
    passed_screeners = _configured_passed_screeners(snapshot)
    components = _configured_components(
        snapshot,
        passed_screeners,
        fundamentals,
        sentiment,
        volatility,
        macro,
    )
    gates = _configured_gates(snapshot)
    missing_data = ["intraday_spread"]
    if fundamentals is None:
        missing_data.insert(0, "configured_fundamentals")
    if sentiment is None:
        missing_data.insert(0, "configured_sentiment")
    if volatility is None:
        missing_data.insert(0, "configured_volatility")
    if macro is None:
        missing_data.insert(0, "configured_macro")
    return RankedScreenerCandidate(
        rank=rank,
        symbol=snapshot.symbol,
        setup=_configured_setup(passed_screeners),
        score=_weighted_score(components),
        passed_screeners=passed_screeners,
        gates=gates,
        score_components=components,
        evidence=[
            evidence
            for component in components
            for evidence in component.evidence
        ],
        counterevidence=[
            item
            for component in components
            for item in component.counterevidence
        ],
        missing_data=missing_data,
        citations=_citations_for_components(components),
        next_allowed_actions=["explain_evidence", "draft_paper_strategy"],
    )


def _fundamentals_for_symbol(
    registry: DataProviderRegistry,
    symbol: str,
) -> FundamentalsSnapshot | None:
    try:
        return registry.fundamentals.get_metrics(symbol)
    except ValueError:
        return None


def _sentiment_for_symbol(
    registry: DataProviderRegistry,
    symbol: str,
) -> SentimentSnapshot | None:
    try:
        return registry.sentiment.get_context(symbol)
    except ValueError:
        return None


def _volatility_for_symbol(
    registry: DataProviderRegistry,
    symbol: str,
) -> VolatilitySnapshot | None:
    try:
        return registry.volatility.get_context(symbol)
    except ValueError:
        return None


def _macro_for_symbol(
    registry: DataProviderRegistry,
    symbol: str,
) -> MacroSnapshot | None:
    try:
        return registry.macro.get_context(symbol)
    except ValueError:
        return None


def run_fixture_screener(
    universe_id: str = "fixture_nifty50",
    preset: str = "momentum",
    limit: int = 10,
) -> ScreenerRunResult:
    registry = get_data_provider_registry()
    universe = registry.universe.get_members(universe_id)
    normalized_preset = preset.strip().lower() or "momentum"
    rejected_symbols: list[str] = []
    candidates: list[RankedScreenerCandidate] = []
    provider_readiness = _active_provider_refresh_readiness()
    provider_reconciliation = _active_provider_import_reconciliation()
    providers_used = registry.providers_used()
    run_source = (
        "configured_json_file"
        if any(
            "configured_" in providers_used[name]
            for name in (
                "market_data",
                "universe",
                "fundamentals",
                "sentiment",
                "volatility",
                "macro",
            )
        )
        else OFFLINE_SOURCE
    )

    for symbol in universe.symbols:
        snapshot = registry.market_data.get_snapshot(symbol)
        fundamentals = _fundamentals_for_symbol(registry, symbol)
        sentiment = _sentiment_for_symbol(registry, symbol)
        volatility = _volatility_for_symbol(registry, symbol)
        macro = _macro_for_symbol(registry, symbol)
        candidate = (
            _candidate(symbol, 0)
            if symbol in _COMPONENTS
            else _configured_candidate(
                snapshot,
                0,
                fundamentals,
                sentiment,
                volatility,
                macro,
            )
        )
        candidate = _candidate_with_provider_readiness(candidate, provider_readiness)
        candidate = _candidate_with_provider_import_reconciliation(
            candidate,
            provider_reconciliation,
        )
        gates = candidate.gates
        if any(gate.status == "fail" for gate in gates):
            rejected_symbols.append(symbol)
            continue
        if not candidate.passed_screeners:
            rejected_symbols.append(symbol)
            continue
        if normalized_preset != "multi_factor" and normalized_preset not in candidate.passed_screeners:
            continue
        candidates.append(candidate)

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    ranked = [
        RankedScreenerCandidate(
            rank=index,
            symbol=candidate.symbol,
            setup=candidate.setup,
            score=candidate.score,
            passed_screeners=candidate.passed_screeners,
            gates=candidate.gates,
            score_components=candidate.score_components,
            evidence=candidate.evidence,
            counterevidence=candidate.counterevidence,
            missing_data=candidate.missing_data,
            citations=candidate.citations,
            next_allowed_actions=candidate.next_allowed_actions,
        )
        for index, candidate in enumerate(candidates[: max(0, limit)], start=1)
    ]

    multi_hit_symbols = [
        candidate.symbol
        for candidate in ranked
        if len(candidate.passed_screeners) >= 2
    ]
    return ScreenerRunResult(
        run_id=f"{'fixture' if run_source == OFFLINE_SOURCE else 'configured'}-{universe_id}-{normalized_preset}-20260622",
        mode="read_only",
        source=run_source,
        universe_id=universe.universe_id,
        preset=normalized_preset,
        run_summary={
            "total_screened": len(universe.symbols),
            "candidate_count": len(ranked),
            "rejected_count": len(rejected_symbols),
            "hard_gates": ["data_quality", "tradability", "paper_only"],
            "providers_used": providers_used,
            "provider_refresh_readiness": _provider_refresh_readiness_summary(
                provider_readiness,
            ),
            "provider_import_reconciliation": _provider_import_reconciliation_summary(
                provider_reconciliation,
            ),
        },
        candidates=ranked,
        rejected_symbols=rejected_symbols,
        multi_hit_symbols=multi_hit_symbols,
        notes=[
            "Fixture-backed deterministic screener; no live provider or broker access."
            if run_source == OFFLINE_SOURCE
            else "Configured JSON screener; read-only provider inputs, no broker access.",
            "Scores are evidence for paper-trading research, not trade authorization.",
        ],
    )


def search_pattern_cards(
    query: str,
    tags: list[str] | None = None,
    limit: int = 5,
) -> list[PatternCard]:
    return PATTERN_STORE.search(query, tags=tags, limit=limit)


def get_pattern_card(pattern_id: str) -> PatternCard:
    return PATTERN_STORE.get(pattern_id)


def _patterns_for_setup(setup: str) -> list[PatternCard]:
    normalized = setup.strip().lower()
    matches = [
        card
        for card in PATTERN_CARDS
        if card.setup_type == normalized or normalized in card.tags
    ]
    if matches:
        return matches
    return search_pattern_cards(normalized, limit=2)


def _candidate_for_symbol(symbol: str) -> RankedScreenerCandidate:
    normalized = symbol.upper().strip()
    provider_readiness = _active_provider_refresh_readiness()
    provider_reconciliation = _active_provider_import_reconciliation()
    if normalized in _COMPONENTS:
        return _candidate_with_provider_import_reconciliation(
            _candidate_with_provider_readiness(
                _candidate(normalized, 1),
                provider_readiness,
            ),
            provider_reconciliation,
        )
    registry = get_data_provider_registry()
    try:
        snapshot = registry.market_data.get_snapshot(normalized)
    except ValueError as exc:
        if "Unknown fixture symbol" in str(exc):
            raise ValueError(str(exc)) from exc
        raise ValueError(f"Unknown symbol: {symbol}") from exc
    return _candidate_with_provider_import_reconciliation(
        _candidate_with_provider_readiness(
            _configured_candidate(
                snapshot,
                1,
                _fundamentals_for_symbol(registry, normalized),
                _sentiment_for_symbol(registry, normalized),
                _volatility_for_symbol(registry, normalized),
                _macro_for_symbol(registry, normalized),
            ),
            provider_readiness,
        ),
        provider_reconciliation,
    )


def build_strategy_evidence_pack(symbol: str, setup: str) -> StrategyEvidencePack:
    candidate = _candidate_for_symbol(symbol)
    selected_setup = setup.strip().lower() or candidate.setup
    patterns = _patterns_for_setup(selected_setup)
    citations: list[PatternCitation] = []
    for pattern in patterns:
        for citation in pattern.citations:
            if citation not in citations:
                citations.append(citation)

    return StrategyEvidencePack(
        symbol=candidate.symbol,
        setup=selected_setup,
        paper_only_status="analysis_only",
        matched_patterns=patterns,
        factor_summary={
            component.name: {
                "score": component.score,
                "weight": component.weight,
                "evidence": component.evidence,
                "counterevidence": component.counterevidence,
            }
            for component in candidate.score_components
        },
        citations=citations,
        next_allowed_actions=["explain_evidence", "draft_paper_strategy"],
    )


def build_factor_stack_explanation(
    symbol: str,
    setup: str | None = None,
) -> FactorStackExplanation:
    candidate = _candidate_for_symbol(symbol)
    selected_setup = (setup or candidate.setup).strip().lower() or candidate.setup
    evidence_pack = build_strategy_evidence_pack(candidate.symbol, selected_setup)
    sections = {
        component.name: {
            "score": component.score,
            "weight": component.weight,
            "evidence": component.evidence,
            "counterevidence": component.counterevidence,
            "citations": component.citations,
        }
        for component in candidate.score_components
    }
    sections["data_quality"] = {
        "evidence": [gate.reason for gate in candidate.gates if gate.name == "data_quality"],
        "counterevidence": [],
        "citations": [],
    }
    sections["tradability"] = {
        "evidence": [gate.reason for gate in candidate.gates if gate.name == "tradability"],
        "counterevidence": [],
        "citations": [],
    }
    macro_section = sections.get("macro")
    if macro_section:
        sections["market_regime"] = {
            "evidence": macro_section["evidence"],
            "counterevidence": macro_section["counterevidence"],
            "citations": macro_section["citations"],
        }
    else:
        sections["market_regime"] = {
            "evidence": ["Fixture regime is constructive but not broad enough to ignore risk."],
            "counterevidence": ["Configured macro adapter is not available."],
            "citations": [NSE_INDIA_VIX.source_id],
        }
    return FactorStackExplanation(
        symbol=candidate.symbol,
        setup=selected_setup,
        paper_only_status="analysis_only",
        sections=sections,
        pattern_matches=evidence_pack.matched_patterns,
        missing_data=candidate.missing_data,
        citations=evidence_pack.citations,
        next_allowed_actions=["explain_evidence", "draft_paper_strategy"],
    )
