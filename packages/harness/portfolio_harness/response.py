from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .context import ContextPack
from .findings import EvaluationFinding


@dataclass(frozen=True)
class ResponseSchema:
    name: str
    required_fields: tuple[str, ...]
    required_policy_statements: tuple[str, ...] = ()
    require_uncertainty: bool = False


@dataclass(frozen=True)
class ValidatedResponse:
    valid: bool
    findings: tuple[EvaluationFinding, ...]
    repair_allowed: bool

    @property
    def blocking_findings(self) -> tuple[EvaluationFinding, ...]:
        return tuple(finding for finding in self.findings if finding.blocking)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "repair_allowed": self.repair_allowed,
            "findings": [finding.to_dict() for finding in self.findings],
        }


class ResponseEvaluator:
    def evaluate(
        self,
        response: Mapping[str, Any],
        *,
        schema: ResponseSchema,
        context_pack: ContextPack,
        tool_outputs: Mapping[str, Any],
        repair_attempts_used: int = 0,
    ) -> ValidatedResponse:
        findings: list[EvaluationFinding] = []
        findings.extend(self._schema_findings(response, schema))
        findings.extend(self._citation_findings(response, context_pack))
        findings.extend(self._tool_agreement_findings(response, tool_outputs))
        findings.extend(self._policy_findings(response, schema))

        valid = not any(finding.blocking for finding in findings)
        return ValidatedResponse(
            valid=valid,
            findings=tuple(findings),
            repair_allowed=(not valid and repair_attempts_used < 1),
        )

    def _schema_findings(
        self,
        response: Mapping[str, Any],
        schema: ResponseSchema,
    ) -> list[EvaluationFinding]:
        findings: list[EvaluationFinding] = []
        for field in schema.required_fields:
            if field not in response or response[field] in (None, "", [], {}):
                findings.append(
                    EvaluationFinding(
                        code="response_schema_missing_field",
                        severity="error",
                        message=f"{schema.name} is missing required field {field}.",
                    )
                )
        return findings

    def _citation_findings(
        self,
        response: Mapping[str, Any],
        context_pack: ContextPack,
    ) -> list[EvaluationFinding]:
        citations = response.get("citations", ())
        if citations is None:
            citations = ()
        known_sources = set(context_pack.source_ids)
        findings: list[EvaluationFinding] = []
        for citation in citations:
            if citation not in known_sources:
                findings.append(
                    EvaluationFinding(
                        code="response_citation_missing",
                        severity="error",
                        message=f"Response citation {citation} is not present in context.",
                        source_id=str(citation),
                    )
                )
        return findings

    def _tool_agreement_findings(
        self,
        response: Mapping[str, Any],
        tool_outputs: Mapping[str, Any],
    ) -> list[EvaluationFinding]:
        supported_claims = response.get("supported_claims", {})
        if not isinstance(supported_claims, Mapping):
            return [
                EvaluationFinding(
                    code="response_tool_disagreement",
                    severity="error",
                    message="supported_claims must be a mapping of tool-backed claims.",
                )
            ]

        findings: list[EvaluationFinding] = []
        for key, value in supported_claims.items():
            if key not in tool_outputs or tool_outputs[key] != value:
                findings.append(
                    EvaluationFinding(
                        code="response_tool_disagreement",
                        severity="error",
                        message=f"Response claim {key} does not agree with tool output.",
                    )
                )
        return findings

    def _policy_findings(
        self,
        response: Mapping[str, Any],
        schema: ResponseSchema,
    ) -> list[EvaluationFinding]:
        statements = response.get("policy_statements", ())
        if isinstance(statements, str):
            statement_text = statements.lower()
        else:
            statement_text = " ".join(str(statement).lower() for statement in statements)

        findings: list[EvaluationFinding] = []
        for required in schema.required_policy_statements:
            if required.lower() not in statement_text:
                findings.append(
                    EvaluationFinding(
                        code="response_policy_statement_missing",
                        severity="error",
                        message=f"Response is missing policy statement: {required}.",
                    )
                )

        if schema.require_uncertainty and not response.get("uncertainty"):
            findings.append(
                EvaluationFinding(
                    code="response_uncertainty_missing",
                    severity="error",
                    message="Response must state uncertainty or data limits.",
                )
            )
        return findings
