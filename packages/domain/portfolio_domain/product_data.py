from __future__ import annotations

from .models import (
    FactorStackExplanation,
    FundamentalsSnapshot,
    GateResult,
    MarketDataSnapshot,
    PatternCard,
    PatternCitation,
    RankedScreenerCandidate,
    ScoreComponent,
    ScreenerRunResult,
    StrategyEvidencePack,
    UniverseDefinition,
)
from .providers import DataProviderRegistry, get_data_provider_registry

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
) -> list[ScoreComponent]:
    roc20 = _metric(snapshot, "roc20_pct")
    rsi14 = _metric(snapshot, "rsi14")
    atr_pct = _metric(snapshot, "atr_pct")
    turnover = _metric(snapshot, "median_turnover_cr")
    technical_score = _bounded(0.48 + (roc20 / 20.0) + ((rsi14 - 50.0) / 120.0))
    volatility_score = _bounded(1.0 - abs(atr_pct - 2.5) / 8.0)
    liquidity_score = _bounded(turnover / 10.0)
    pattern_score = 0.82 if "breakout" in passed_screeners else 0.68
    pattern_counterevidence = ["Configured sentiment adapter is not available for this symbol."]
    if fundamentals is None:
        pattern_counterevidence.insert(
            0,
            "Configured fundamentals are unavailable for this symbol.",
        )
    components = [
        ScoreComponent(
            "technical",
            round(technical_score, 3),
            0.35,
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
    components.extend(
        [
            ScoreComponent(
                "volatility",
                round(volatility_score, 3),
                0.15,
                [f"Configured ATR proxy is {atr_pct:.2f}%."],
                [
                    "Volatility controls can still downgrade sizing or candidate count.",
                ],
                [NSE_INDIA_VIX.source_id, CBOE_VIX.source_id],
            ),
            ScoreComponent(
                "liquidity",
                round(liquidity_score, 3),
                0.15,
                [f"Configured median turnover proxy is {turnover:.2f} crore."],
                [],
                ["portfolio-policy-paper-only"],
            ),
            ScoreComponent(
                "pattern",
                pattern_score,
                0.15,
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
) -> RankedScreenerCandidate:
    passed_screeners = _configured_passed_screeners(snapshot)
    components = _configured_components(snapshot, passed_screeners, fundamentals)
    gates = _configured_gates(snapshot)
    missing_data = [
        "configured_sentiment",
        "intraday_spread",
    ]
    if fundamentals is None:
        missing_data.insert(0, "configured_fundamentals")
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
    providers_used = registry.providers_used()
    run_source = (
        "configured_json_file"
        if any(
            "configured_" in providers_used[name]
            for name in ("market_data", "universe", "fundamentals")
        )
        else OFFLINE_SOURCE
    )

    for symbol in universe.symbols:
        snapshot = registry.market_data.get_snapshot(symbol)
        fundamentals = _fundamentals_for_symbol(registry, symbol)
        candidate = (
            _candidate(symbol, 0)
            if symbol in _COMPONENTS
            else _configured_candidate(snapshot, 0, fundamentals)
        )
        gates = candidate.gates
        if any(gate.status != "pass" for gate in gates):
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
    terms = [term for term in query.lower().split() if term]
    tag_filter = {tag.strip().lower() for tag in tags or [] if tag.strip()}

    def score(card: PatternCard) -> int:
        haystack = " ".join(
            [
                card.pattern_id,
                card.title,
                card.setup_type,
                card.summary,
                " ".join(card.tags),
                " ".join(card.evidence),
            ]
        ).lower()
        term_score = sum(1 for term in terms if term in haystack)
        tag_score = 2 if tag_filter and tag_filter.intersection(card.tags) else 0
        return term_score + tag_score

    cards = [
        card
        for card in PATTERN_CARDS
        if not tag_filter or tag_filter.intersection(set(card.tags))
    ]
    cards.sort(key=lambda card: (score(card), card.pattern_id), reverse=True)
    if terms or tag_filter:
        cards = [card for card in cards if score(card) > 0]
    return cards[: max(0, limit)]


def get_pattern_card(pattern_id: str) -> PatternCard:
    for card in PATTERN_CARDS:
        if card.pattern_id == pattern_id:
            return card
    raise ValueError(f"Unknown pattern_id: {pattern_id}")


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
    if normalized in _COMPONENTS:
        return _candidate(normalized, 1)
    registry = get_data_provider_registry()
    try:
        snapshot = registry.market_data.get_snapshot(normalized)
    except ValueError as exc:
        if "Unknown fixture symbol" in str(exc):
            raise ValueError(str(exc)) from exc
        raise ValueError(f"Unknown symbol: {symbol}") from exc
    return _configured_candidate(snapshot, 1, _fundamentals_for_symbol(registry, normalized))


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
    sections["market_regime"] = {
        "evidence": ["Fixture regime is constructive but not broad enough to ignore risk."],
        "counterevidence": ["Live breadth and macro adapters are not configured."],
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
