from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: int
    average_price: float
    last_price: float
    sector: str

    @property
    def market_value(self) -> float:
        return round(self.quantity * self.last_price, 2)

    @property
    def unrealized_pnl(self) -> float:
        return round((self.last_price - self.average_price) * self.quantity, 2)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["market_value"] = self.market_value
        payload["unrealized_pnl"] = self.unrealized_pnl
        return payload


@dataclass(frozen=True)
class PortfolioSummary:
    currency: str
    total_value: float
    day_pnl: float
    holdings: list[Holding]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "total_value": self.total_value,
            "day_pnl": self.day_pnl,
            "holdings": [holding.to_dict() for holding in self.holdings],
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ScreenerCandidate:
    symbol: str
    setup: str
    score: float
    evidence: list[str]
    counterevidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UniverseDefinition:
    universe_id: str
    name: str
    source: str
    as_of: str
    symbols: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UniverseMembers:
    provider_id: str
    universe_id: str
    source: str
    as_of: str
    symbols: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    kind: str
    display_name: str
    status: str
    configured: bool
    capabilities: list[str]
    required_env: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderHealth:
    provider_id: str
    kind: str
    status: str
    configured: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderImportValidation:
    provider_id: str
    kind: str
    display_name: str
    status: str
    configured: bool
    provider_mode: str
    required_env: list[str]
    missing_env: list[str]
    message: str
    payload_count: int | None = None
    sample_identifiers: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderConfigurationProfile:
    profile_id: str
    provider_id: str
    kind: str
    display_name: str
    configured: bool
    provider_mode: str
    required_env: list[str]
    path_env: str
    source_label: str
    last_validation_status: str
    missing_env: list[str]
    payload_count: int | None
    sample_identifiers: list[str]
    updated_at: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderImportJob:
    job_id: str
    profile_id: str
    provider_id: str
    kind: str
    status: str
    trigger: str
    provider_mode: str
    source_label: str
    validation_status: str
    payload_count: int | None
    sample_identifiers: list[str]
    message: str
    started_at: str
    completed_at: str
    progress_state: str
    attempts: int
    imported_count: int
    skipped_count: int
    target_store: str
    audit_event: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OHLCVBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarketDataSnapshot:
    provider_id: str
    source: str
    symbol: str
    as_of: str
    bars: list[OHLCVBar]
    latest_close: float
    metrics: dict[str, float | int | str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "source": self.source,
            "symbol": self.symbol,
            "as_of": self.as_of,
            "bars": [bar.to_dict() for bar in self.bars],
            "latest_close": self.latest_close,
            "metrics": self.metrics,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class FundamentalsSnapshot:
    provider_id: str
    source: str
    symbol: str
    as_of: str
    metrics: dict[str, float | int | str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SentimentSnapshot:
    provider_id: str
    source: str
    symbol: str
    as_of: str
    metrics: dict[str, float | int | str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VolatilitySnapshot:
    provider_id: str
    source: str
    symbol: str
    as_of: str
    metrics: dict[str, float | int | str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MacroSnapshot:
    provider_id: str
    source: str
    symbol: str
    as_of: str
    metrics: dict[str, float | int | str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GateResult:
    name: str
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScoreComponent:
    name: str
    score: float
    weight: float
    evidence: list[str]
    counterevidence: list[str]
    citations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RankedScreenerCandidate:
    rank: int
    symbol: str
    setup: str
    score: float
    passed_screeners: list[str]
    gates: list[GateResult]
    score_components: list[ScoreComponent]
    evidence: list[str]
    counterevidence: list[str]
    missing_data: list[str]
    citations: list[str]
    next_allowed_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "symbol": self.symbol,
            "setup": self.setup,
            "score": self.score,
            "passed_screeners": self.passed_screeners,
            "gates": [gate.to_dict() for gate in self.gates],
            "score_components": [
                component.to_dict() for component in self.score_components
            ],
            "evidence": self.evidence,
            "counterevidence": self.counterevidence,
            "missing_data": self.missing_data,
            "citations": self.citations,
            "next_allowed_actions": self.next_allowed_actions,
        }


@dataclass(frozen=True)
class ScreenerRunResult:
    run_id: str
    mode: str
    source: str
    universe_id: str
    preset: str
    run_summary: dict[str, Any]
    candidates: list[RankedScreenerCandidate]
    rejected_symbols: list[str]
    multi_hit_symbols: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "source": self.source,
            "universe_id": self.universe_id,
            "preset": self.preset,
            "run_summary": self.run_summary,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "rejected_symbols": self.rejected_symbols,
            "multi_hit_symbols": self.multi_hit_symbols,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PatternCitation:
    source_id: str
    title: str
    url: str
    usage_notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PatternCard:
    pattern_id: str
    version: str
    title: str
    setup_type: str
    summary: str
    prerequisites: list[str]
    evidence: list[str]
    counterevidence: list[str]
    risk_notes: list[str]
    citations: list[PatternCitation]
    tags: list[str]
    source_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "version": self.version,
            "title": self.title,
            "setup_type": self.setup_type,
            "summary": self.summary,
            "prerequisites": self.prerequisites,
            "evidence": self.evidence,
            "counterevidence": self.counterevidence,
            "risk_notes": self.risk_notes,
            "citations": [citation.to_dict() for citation in self.citations],
            "tags": self.tags,
            "source_type": self.source_type,
        }


@dataclass(frozen=True)
class StrategyEvidencePack:
    symbol: str
    setup: str
    paper_only_status: str
    matched_patterns: list[PatternCard]
    factor_summary: dict[str, Any]
    citations: list[PatternCitation]
    next_allowed_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "setup": self.setup,
            "paper_only_status": self.paper_only_status,
            "matched_patterns": [
                pattern.to_dict() for pattern in self.matched_patterns
            ],
            "factor_summary": self.factor_summary,
            "citations": [citation.to_dict() for citation in self.citations],
            "next_allowed_actions": self.next_allowed_actions,
        }


@dataclass(frozen=True)
class FactorStackExplanation:
    symbol: str
    setup: str
    paper_only_status: str
    sections: dict[str, dict[str, Any]]
    pattern_matches: list[PatternCard]
    missing_data: list[str]
    citations: list[PatternCitation]
    next_allowed_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "setup": self.setup,
            "paper_only_status": self.paper_only_status,
            "sections": self.sections,
            "pattern_matches": [pattern.to_dict() for pattern in self.pattern_matches],
            "missing_data": self.missing_data,
            "citations": [citation.to_dict() for citation in self.citations],
            "next_allowed_actions": self.next_allowed_actions,
        }


@dataclass(frozen=True)
class RecommendationExplanation:
    symbol: str
    setup: str
    mode: str
    stance: str
    confidence: float
    evidence: list[str]
    counterevidence: list[str]
    risk_gates: list[GateResult]
    missing_data: list[str]
    factor_summary: dict[str, dict[str, Any]]
    history_refs: dict[str, list[str]]
    backtest_summary: dict[str, Any]
    ledger_context: dict[str, Any]
    citations: list[PatternCitation]
    next_allowed_actions: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "setup": self.setup,
            "mode": self.mode,
            "stance": self.stance,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "counterevidence": self.counterevidence,
            "risk_gates": [gate.to_dict() for gate in self.risk_gates],
            "missing_data": self.missing_data,
            "factor_summary": self.factor_summary,
            "history_refs": self.history_refs,
            "backtest_summary": self.backtest_summary,
            "ledger_context": self.ledger_context,
            "citations": [citation.to_dict() for citation in self.citations],
            "next_allowed_actions": self.next_allowed_actions,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PaperAuditExport:
    schema_version: str
    export_id: str
    mode: str
    source: str
    generated_at: str
    row_count: int
    rows: list[dict[str, Any]]
    redaction_status: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperTradingReport:
    report_id: str
    report_type: str
    scope: str
    mode: str
    source: str
    generated_at: str
    summary: dict[str, Any]
    sections: dict[str, Any]
    recommendation: RecommendationExplanation | None
    audit_export: PaperAuditExport
    next_allowed_actions: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "scope": self.scope,
            "mode": self.mode,
            "source": self.source,
            "generated_at": self.generated_at,
            "summary": self.summary,
            "sections": self.sections,
            "recommendation": (
                self.recommendation.to_dict()
                if self.recommendation is not None
                else None
            ),
            "audit_export": self.audit_export.to_dict(),
            "next_allowed_actions": self.next_allowed_actions,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class WatchlistItem:
    symbol: str
    last_price: float
    change_percent: float
    setup: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WatchlistSnapshot:
    session: str
    source: str
    items: list[WatchlistItem]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "source": self.source,
            "items": [item.to_dict() for item in self.items],
            "notes": self.notes,
        }


@dataclass(frozen=True)
class MarketSignal:
    label: str
    value: str
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SignalSummary:
    regime: str
    confidence: float
    index_moves: dict[str, float]
    breadth: dict[str, float | int | str]
    signals: list[MarketSignal]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime": self.regime,
            "confidence": self.confidence,
            "index_moves": self.index_moves,
            "breadth": self.breadth,
            "signals": [signal.to_dict() for signal in self.signals],
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ResearchDigest:
    theme: str
    source: str
    notes: list[str]
    counterevidence: list[str]
    citations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyDraft:
    strategy_id: str
    symbol: str
    mode: str
    status: str
    source: str
    created_at: str
    rationale: str
    entry_rule: str
    exit_rule: str
    risk_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BacktestRequest:
    request_id: str
    symbol: str
    setup: str
    start_date: str
    end_date: str
    mode: str
    status: str
    source: str
    assumptions: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BacktestTrade:
    trade_id: str
    symbol: str
    side: str
    entry_date: str
    exit_date: str
    quantity: int
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BacktestResult:
    request_id: str
    symbol: str
    setup: str
    mode: str
    status: str
    source: str
    metrics: dict[str, float | int | str]
    trades: list[BacktestTrade]
    warnings: list[str]
    citations: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "symbol": self.symbol,
            "setup": self.setup,
            "mode": self.mode,
            "status": self.status,
            "source": self.source,
            "metrics": self.metrics,
            "trades": [trade.to_dict() for trade in self.trades],
            "warnings": self.warnings,
            "citations": self.citations,
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class PaperOrder:
    order_id: str
    strategy_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    mode: str
    status: str
    requested_price: float | None
    filled_quantity: int
    fill_ids: list[str]
    approval_request_id: str
    created_at: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperFill:
    fill_id: str
    order_id: str
    symbol: str
    side: str
    quantity: int
    fill_price: float
    filled_at: str
    mode: str
    source: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperPosition:
    symbol: str
    quantity: int
    average_price: float
    last_price: float
    mode: str
    source: str
    notes: list[str]

    @property
    def market_value(self) -> float:
        return round(self.quantity * self.last_price, 2)

    @property
    def unrealized_pnl(self) -> float:
        return round((self.last_price - self.average_price) * self.quantity, 2)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["market_value"] = self.market_value
        payload["unrealized_pnl"] = self.unrealized_pnl
        return payload


@dataclass(frozen=True)
class PaperPortfolioAccounting:
    currency: str
    source: str
    total_market_value: float
    total_unrealized_pnl: float
    open_positions: int
    pending_orders: int
    approved_orders: int
    filled_orders: int
    simulated_fills: int
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApprovalRequest:
    approval_id: str
    action_type: str
    status: str
    summary: str
    related_id: str
    required_approval: str
    requested_at: str
    risk_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: str
    entity_type: str
    entity_id: str
    message: str
    created_at: str
    actor: str
    redacted_payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskReview:
    status: str
    concentration_notes: list[str]
    safety_switches: dict[str, str]
    recommended_pauses: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PreMarketBriefing:
    session: str
    mode: str
    source: str
    portfolio: PortfolioSummary
    watchlist: WatchlistSnapshot
    signal_summary: SignalSummary
    research_digest: ResearchDigest
    risk_review: RiskReview
    suggested_review_actions: list[str]
    non_goals: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "mode": self.mode,
            "source": self.source,
            "portfolio": self.portfolio.to_dict(),
            "watchlist": self.watchlist.to_dict(),
            "signal_summary": self.signal_summary.to_dict(),
            "research_digest": self.research_digest.to_dict(),
            "risk_review": self.risk_review.to_dict(),
            "suggested_review_actions": self.suggested_review_actions,
            "non_goals": self.non_goals,
        }
