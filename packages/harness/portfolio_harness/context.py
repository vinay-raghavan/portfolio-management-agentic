from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from portfolio_policy import redact_sensitive

from .findings import EvaluationFinding


PROMPT_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal the system prompt",
    "developer message",
    "system prompt",
    "disable safety",
    "bypass policy",
)

SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|secret|password|broker[_-]?token|fyers[_-]?token)\b\s*[:=]"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
)
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|secret|password|broker[_-]?token|fyers[_-]?token)\b\s*[:=]\s*[^,\s]+"
)


@dataclass(frozen=True)
class ContextItem:
    source_id: str
    source_type: str
    content: str
    tenant_id: str
    as_of: datetime
    fetched_at: datetime
    expires_at: datetime
    token_count: int
    relevance_score: float
    checksum: str
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "content": _redact_context_content(self.content),
            "tenant_id": self.tenant_id,
            "as_of": self.as_of.isoformat(),
            "fetched_at": self.fetched_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "token_count": self.token_count,
            "relevance_score": self.relevance_score,
            "checksum": self.checksum,
            "provenance": redact_sensitive(self.provenance),
        }


@dataclass(frozen=True)
class ContextPack:
    tenant_id: str
    user_id: str
    route: str
    request_id: str
    max_input_tokens: int
    items: tuple[ContextItem, ...]

    @property
    def total_tokens(self) -> int:
        return sum(item.token_count for item in self.items)

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(item.source_id for item in self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "route": self.route,
            "request_id": self.request_id,
            "max_input_tokens": self.max_input_tokens,
            "total_tokens": self.total_tokens,
            "source_ids": self.source_ids,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True)
class ContextEvaluation:
    valid: bool
    findings: tuple[EvaluationFinding, ...]

    @property
    def blocking_findings(self) -> tuple[EvaluationFinding, ...]:
        return tuple(finding for finding in self.findings if finding.blocking)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "findings": [finding.to_dict() for finding in self.findings],
        }


class ContextEvaluator:
    def __init__(
        self,
        *,
        now: datetime | None = None,
        min_relevance_score: float = 0.2,
    ) -> None:
        self.now = now or datetime.now(timezone.utc)
        self.min_relevance_score = min_relevance_score

    def evaluate(self, pack: ContextPack) -> ContextEvaluation:
        findings: list[EvaluationFinding] = []
        if pack.total_tokens > pack.max_input_tokens:
            findings.append(
                EvaluationFinding(
                    code="context_token_budget_exceeded",
                    severity="error",
                    message=(
                        f"Context token count {pack.total_tokens} exceeds "
                        f"budget {pack.max_input_tokens}."
                    ),
                )
            )

        seen_checksums: dict[str, str] = {}
        for item in pack.items:
            findings.extend(self._evaluate_item(pack, item))
            previous_source = seen_checksums.get(item.checksum)
            if previous_source is not None:
                findings.append(
                    EvaluationFinding(
                        code="context_duplicate",
                        severity="error",
                        message=(
                            f"Context source duplicates checksum already used by "
                            f"{previous_source}."
                        ),
                        source_id=item.source_id,
                    )
                )
            else:
                seen_checksums[item.checksum] = item.source_id

        return ContextEvaluation(
            valid=not any(finding.blocking for finding in findings),
            findings=tuple(findings),
        )

    def _evaluate_item(
        self,
        pack: ContextPack,
        item: ContextItem,
    ) -> list[EvaluationFinding]:
        findings: list[EvaluationFinding] = []
        if item.tenant_id != pack.tenant_id:
            findings.append(
                EvaluationFinding(
                    code="context_tenant_mismatch",
                    severity="error",
                    message="Context item tenant does not match request tenant.",
                    source_id=item.source_id,
                )
            )
        if item.expires_at <= self.now:
            findings.append(
                EvaluationFinding(
                    code="context_stale",
                    severity="error",
                    message="Context item is stale or expired.",
                    source_id=item.source_id,
                )
            )
        if item.relevance_score < self.min_relevance_score:
            findings.append(
                EvaluationFinding(
                    code="context_low_relevance",
                    severity="error",
                    message="Context item relevance score is below route threshold.",
                    source_id=item.source_id,
                )
            )
        lowered = item.content.lower()
        if any(pattern in lowered for pattern in PROMPT_INJECTION_PATTERNS):
            findings.append(
                EvaluationFinding(
                    code="context_prompt_injection",
                    severity="error",
                    message="Context item contains prompt-injection language.",
                    source_id=item.source_id,
                )
            )
        if any(pattern.search(item.content) for pattern in SECRET_PATTERNS):
            findings.append(
                EvaluationFinding(
                    code="context_secret_leakage",
                    severity="error",
                    message="Context item appears to contain a redacted secret marker.",
                    source_id=item.source_id,
                )
            )
        return findings


def _redact_context_content(content: str) -> str:
    return SECRET_VALUE_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", content)
