from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationFinding:
    code: str
    severity: str
    message: str
    source_id: str | None = None

    @property
    def blocking(self) -> bool:
        return self.severity == "error"

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "source_id": self.source_id,
        }
