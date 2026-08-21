"""Small deterministic contract-validation result shared by semantic submissions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    status: str
    repair_targets: list[str] = field(default_factory=list)
    generated_artifacts: list[dict[str, Any]] = field(default_factory=list)
    route: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status,
            "repair_targets": list(self.repair_targets),
            "generated_artifacts": list(self.generated_artifacts),
        }
        if self.route is not None:
            result["route"] = self.route
        return result
