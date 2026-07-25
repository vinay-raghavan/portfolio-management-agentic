from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from portfolio_capabilities import CapabilityManifest, load_capability_manifests


class RouteDecisionType(StrEnum):
    CAPABILITY = "capability"
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


class DeterministicRouter:
    def __init__(
        self,
        manifests: dict[str, CapabilityManifest] | None = None,
    ) -> None:
        self.manifests = manifests or load_capability_manifests()

    def route(self, user_text: str) -> RouteDecision:
        text = _normalize(user_text)
        if _contains_any(text, FORBIDDEN_TERMS):
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


FORBIDDEN_TERMS = (
    "live order",
    "place a live",
    "place live",
    "real order",
    "broker token",
    "trading token",
    "enable live strategy",
    "enable auto trade",
    "print all credentials",
    "show credentials",
    "approval bypass",
    "bypass approval",
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

PAPER_PROPOSAL_TERMS = (
    "paper order proposal",
    "paper trade proposal",
    "create a paper order",
    "draft paper strategy",
    "backtest and risk",
)


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _contains_all(value: str, terms: tuple[str, ...]) -> bool:
    return all(term in value for term in terms)
