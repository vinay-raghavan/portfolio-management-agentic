from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from portfolio_capabilities import CapabilityManifest, load_capability_manifests
from portfolio_policy import ActionTier, classify_tool


class RouteDecisionType(StrEnum):
    CAPABILITY = "capability"
    CLARIFICATION_REQUIRED = "clarification_required"
    FORBIDDEN = "forbidden"
    HUMAN_API_REQUIRED = "human_api_required"
    NEEDS_CLASSIFICATION = "needs_classification"


@dataclass(frozen=True)
class RouteDecision:
    decision_type: RouteDecisionType
    capability_name: str | None
    reason: str
    confidence: float
    allowed_tools: tuple[str, ...]
    response_schema: str | None
    token_budget: dict[str, int] | None
    model_classification_allowed: bool
    human_api: str | None = None
    forbidden_tools: tuple[str, ...] = ()

    @classmethod
    def from_manifest(
        cls,
        *,
        decision_type: RouteDecisionType,
        manifest: CapabilityManifest,
        reason: str,
        confidence: float,
        model_classification_allowed: bool = False,
        human_api: str | None = None,
    ) -> RouteDecision:
        return cls(
            decision_type=decision_type,
            capability_name=manifest.name,
            reason=reason,
            confidence=confidence,
            allowed_tools=manifest.allowed_tools,
            response_schema=manifest.response_schema,
            token_budget={
                "input_tokens": manifest.token_budget.input_tokens,
                "output_tokens": manifest.token_budget.output_tokens,
                "tool_calls": manifest.token_budget.tool_calls,
            },
            model_classification_allowed=model_classification_allowed,
            human_api=human_api,
            forbidden_tools=manifest.forbidden_tools,
        )


@dataclass(frozen=True)
class RouteToolBundle:
    capability_name: str | None
    decision_type: RouteDecisionType
    tool_names: tuple[str, ...]
    model_visible: bool
    response_schema: str | None
    token_budget: dict[str, int] | None
    max_action_tier: str | None
    human_api: str | None = None
    forbidden_tools: tuple[str, ...] = ()
    unavailable_tools: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "capability_name": self.capability_name,
            "decision_type": self.decision_type.value,
            "tool_names": self.tool_names,
            "model_visible": self.model_visible,
            "response_schema": self.response_schema,
            "token_budget": self.token_budget,
            "max_action_tier": self.max_action_tier,
            "human_api": self.human_api,
            "forbidden_tools": self.forbidden_tools,
            "unavailable_tools": self.unavailable_tools,
        }


class DeterministicRouter:
    min_classification_confidence = 0.7

    def __init__(
        self,
        manifests: dict[str, CapabilityManifest] | None = None,
    ) -> None:
        self.manifests = manifests or load_capability_manifests()

    def route(self, user_text: str) -> RouteDecision:
        text = _normalize(user_text)
        if _contains_non_negated_any(text, FORBIDDEN_TERMS):
            return RouteDecision.from_manifest(
                decision_type=RouteDecisionType.FORBIDDEN,
                manifest=self.manifests["safety"],
                reason="Forbidden live-trading, live-strategy, credential, or approval-bypass intent.",
                confidence=1.0,
            )
        if _contains_any(text, FYERS_REFRESH_TERMS):
            return RouteDecision.from_manifest(
                decision_type=RouteDecisionType.HUMAN_API_REQUIRED,
                manifest=self.manifests["fyers_data"],
                reason="FYERS refresh and OAuth operations must use protected human-facing APIs outside model-visible tools.",
                confidence=1.0,
                human_api="/v1/integrations/fyers/refresh",
            )
        if _contains_any(text, APPROVAL_TERMS):
            return RouteDecision.from_manifest(
                decision_type=RouteDecisionType.HUMAN_API_REQUIRED,
                manifest=self.manifests["paper_proposal_execution"],
                reason="Approval identity must be bound by the authenticated human approval API.",
                confidence=1.0,
                human_api="/v1/paper/batches/{id}/approve",
            )
        if _contains_any(text, PRE_MARKET_BRIEFING_TERMS):
            return RouteDecision.from_manifest(
                decision_type=RouteDecisionType.CAPABILITY,
                manifest=self.manifests["pre_market_briefing"],
                reason="Pre-market briefing request routes to read-only briefing capability.",
                confidence=1.0,
            )
        if _contains_any(text, REPORTING_TERMS):
            return RouteDecision.from_manifest(
                decision_type=RouteDecisionType.CAPABILITY,
                manifest=self.manifests["reporting"],
                reason="Read-only reporting or feature-navigation request routes to reporting capability.",
                confidence=1.0,
            )
        if _contains_all(text, ("paper", "proposal")) or _contains_any(
            text, PAPER_PROPOSAL_TERMS
        ):
            return RouteDecision.from_manifest(
                decision_type=RouteDecisionType.CAPABILITY,
                manifest=self.manifests["paper_proposal_execution"],
                reason="Paper proposal request routes to draft-only proposal capability.",
                confidence=1.0,
            )

        return RouteDecision(
            decision_type=RouteDecisionType.NEEDS_CLASSIFICATION,
            capability_name=None,
            reason="No deterministic high-risk route matched; schema-constrained classification may choose a read-only capability.",
            confidence=0.5,
            allowed_tools=(),
            response_schema=None,
            token_budget=None,
            model_classification_allowed=True,
        )

    def resolve_classified_capability(
        self,
        capability_name: str,
        *,
        confidence: float,
        reason: str,
    ) -> RouteDecision:
        if confidence < self.min_classification_confidence:
            return self._clarification_decision(
                reason=(
                    "Schema-constrained read-only classification confidence "
                    f"{confidence:.2f} is below threshold "
                    f"{self.min_classification_confidence:.2f}."
                ),
                confidence=confidence,
            )
        manifest = self.manifests.get(capability_name)
        if manifest is None:
            return self._clarification_decision(
                reason=f"Unknown classified capability: {capability_name}.",
                confidence=0.0,
            )
        if manifest.max_action_tier != ActionTier.READ_ONLY.value:
            return self._clarification_decision(
                reason=(
                    "Schema-constrained classification may resolve only "
                    f"read-only capabilities; got {capability_name}."
                ),
                confidence=0.0,
            )
        return RouteDecision.from_manifest(
            decision_type=RouteDecisionType.CAPABILITY,
            manifest=manifest,
            reason=reason,
            confidence=confidence,
            model_classification_allowed=True,
        )

    def classify_read_only_request(self, user_text: str) -> RouteDecision:
        """Resolve ambiguous read-only intent into one manifest or clarification.

        This deterministic classifier mirrors the schema-constrained contract a
        small local model will produce later: exactly one read-only capability,
        confidence, and reason. Invalid, tied, unknown, low-confidence, or
        non-read-only outputs fail closed to clarification.
        """
        text = _normalize(user_text)
        scores = {
            capability_name: _term_score(text, terms)
            for capability_name, terms in READ_ONLY_CLASSIFICATION_TERMS.items()
        }
        top_score = max(scores.values(), default=0)
        if top_score <= 0:
            return self._clarification_decision(
                reason="Read-only classifier found no matching capability.",
                confidence=0.0,
            )

        winners = tuple(
            capability_name
            for capability_name, score in scores.items()
            if score == top_score
        )
        if len(winners) != 1:
            return self._clarification_decision(
                reason="Read-only classifier found multiple equally likely capabilities.",
                confidence=0.0,
            )

        capability_name = winners[0]
        confidence = min(0.95, 0.65 + (top_score * 0.08))
        return self.resolve_classified_capability(
            capability_name,
            confidence=confidence,
            reason=(
                "Schema-constrained read-only classifier selected "
                f"{capability_name} from deterministic intent terms."
            ),
        )

    def _clarification_decision(self, *, reason: str, confidence: float) -> RouteDecision:
        return RouteDecision(
            decision_type=RouteDecisionType.CLARIFICATION_REQUIRED,
            capability_name=None,
            reason=reason,
            confidence=confidence,
            allowed_tools=(),
            response_schema=None,
            token_budget=None,
            model_classification_allowed=False,
        )

    def tool_bundle_for(
        self,
        decision: RouteDecision,
        *,
        exposed_tool_names: set[str] | frozenset[str],
    ) -> RouteToolBundle:
        manifest = (
            self.manifests.get(decision.capability_name)
            if decision.capability_name
            else None
        )
        max_action_tier = manifest.max_action_tier if manifest is not None else None
        if decision.decision_type != RouteDecisionType.CAPABILITY:
            return RouteToolBundle(
                capability_name=decision.capability_name,
                decision_type=decision.decision_type,
                tool_names=(),
                model_visible=False,
                response_schema=decision.response_schema,
                token_budget=decision.token_budget,
                max_action_tier=max_action_tier,
                human_api=decision.human_api,
                forbidden_tools=decision.forbidden_tools,
            )

        available = set(exposed_tool_names)
        unavailable = tuple(
            tool_name for tool_name in decision.allowed_tools if tool_name not in available
        )
        allowed_tier = (
            ActionTier(max_action_tier)
            if max_action_tier is not None
            else ActionTier.FORBIDDEN
        )
        safe_tool_names = tuple(
            tool_name
            for tool_name in decision.allowed_tools
            if tool_name in available
            and _tier_within(classify_tool(tool_name), allowed_tier)
        )
        return RouteToolBundle(
            capability_name=decision.capability_name,
            decision_type=decision.decision_type,
            tool_names=safe_tool_names,
            model_visible=bool(safe_tool_names) and not unavailable,
            response_schema=decision.response_schema,
            token_budget=decision.token_budget,
            max_action_tier=max_action_tier,
            human_api=decision.human_api,
            forbidden_tools=decision.forbidden_tools,
            unavailable_tools=unavailable,
        )


FORBIDDEN_TERMS = (
    "live market order",
    "real live market order",
    "live order",
    "place a live",
    "place live",
    "real order",
    "broker token",
    "trading token",
    "enable live strategy",
    "enable auto trade",
    "auto live trading",
    "print all credentials",
    "print broker credentials",
    "reveal credentials",
    "show credentials",
    "provider secrets",
    "approval bypass",
    "bypass approval",
    "skip approval",
)

FYERS_REFRESH_TERMS = (
    "refresh my fyers",
    "refresh fyers",
    "fyers holdings",
    "fyers funds",
    "fyers profile",
    "fyers account",
    "fyers oauth",
    "fyers reconnect",
)

APPROVAL_TERMS = (
    "approve the pending",
    "approve paper",
    "mark it approved",
    "approve order",
    "approve batch",
    "approved by me",
)

PRE_MARKET_BRIEFING_TERMS = (
    "pre-market briefing",
    "premarket briefing",
    "pre market briefing",
    "morning briefing",
    "market briefing",
    "before market open",
)

PAPER_PROPOSAL_TERMS = (
    "paper order proposal",
    "paper trade proposal",
    "create a paper order",
    "draft paper strategy",
    "paper strategy",
    "paper backtest",
    "simulated backtest",
    "recommendation explanation workflow",
    "backtest and risk",
)

REPORTING_TERMS = (
    "paper-trading review report",
    "paper trading review report",
    "paper-trading report",
    "paper trading report",
    "redacted audit export",
    "already approved",
    "externally approved",
    "simulated fills",
    "paper order status",
    "what this portfolio agent can do",
    "features are paper-only",
)

READ_ONLY_CLASSIFICATION_TERMS = {
    "fyers_data": (
        "fyers quote",
        "fyers quotes",
        "fyers depth",
        "fyers option chain",
        "fyers positions",
        "fyers funds",
        "fyers account snapshot",
        "broker snapshot",
    ),
    "provider_readiness": (
        "provider readiness",
        "configured data",
        "data health",
        "provider health",
        "data providers are available",
        "providers are available",
        "before using real market data",
        "fixture provider",
        "import reconciliation",
        "import preview",
        "source onboarding",
        "refresh readiness",
    ),
    "reporting": (
        "paper trading report",
        "paper-trading report",
        "paper-trading review report",
        "audit report",
        "fills report",
        "accounting report",
        "approval status",
        "audit trail",
    ),
    "research": (
        "curated research",
        "research citations",
        "pattern citations",
        "pattern playbook",
        "source grounding",
        "research digest",
    ),
    "risk_review": (
        "risk review",
        "paper-trading risk",
        "paper trading risk",
        "risk state",
        "exposure",
        "concentration",
        "drawdown",
        "safety switch",
        "should be paused",
    ),
    "technical_analysis": (
        "technical analysis",
        "technical setup",
        "screener candidates",
        "factor stack",
        "momentum screener",
        "candidate evidence",
        "chart setup",
    ),
}


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _contains_non_negated_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(_contains_non_negated_term(value, term) for term in terms)


def _contains_non_negated_term(value: str, term: str) -> bool:
    start = value.find(term)
    while start != -1:
        prefix = value[max(0, start - 160) : start]
        if not _is_negated_prefix(prefix):
            return True
        start = value.find(term, start + 1)
    return False


def _is_negated_prefix(prefix: str) -> bool:
    sentence_start = max(prefix.rfind("."), prefix.rfind("?"), prefix.rfind("!"), prefix.rfind(";"))
    scoped_prefix = prefix[sentence_start + 1 :] if sentence_start >= 0 else prefix
    return any(
        marker in scoped_prefix
        for marker in (
            "do not ",
            "don't ",
            "dont ",
            "never ",
            "without ",
            "not ",
            "no ",
        )
    )


def _contains_all(value: str, terms: tuple[str, ...]) -> bool:
    return all(term in value for term in terms)


def _term_score(value: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if term in value)


_TIER_RANK = {
    ActionTier.READ_ONLY: 1,
    ActionTier.DRAFT_ONLY: 2,
    ActionTier.APPROVAL_REQUIRED: 3,
    ActionTier.FORBIDDEN: 4,
}


def _tier_within(actual: ActionTier, maximum: ActionTier) -> bool:
    return (
        actual != ActionTier.FORBIDDEN
        and _TIER_RANK[actual] <= _TIER_RANK[maximum]
    )
