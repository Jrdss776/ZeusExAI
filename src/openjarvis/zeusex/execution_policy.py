"""Políticas declarativas para execução local controlada."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ActionExecutionPolicy:
    action: str
    max_attempts_per_plan: int = 3
    max_executions_per_hour: int = 20
    timeout_seconds: float = 5.0
    max_argument_length: int = 2048

    def __post_init__(self) -> None:
        if not self.action.strip() or self.action != self.action.strip().lower():
            raise ValueError("action precisa estar normalizada em minúsculas.")
        if not 1 <= self.max_attempts_per_plan <= 100:
            raise ValueError("max_attempts_per_plan precisa estar entre 1 e 100.")
        if not 1 <= self.max_executions_per_hour <= 10_000:
            raise ValueError("max_executions_per_hour precisa estar entre 1 e 10000.")
        if not 0.01 <= self.timeout_seconds <= 300:
            raise ValueError("timeout_seconds precisa estar entre 0.01 e 300.")
        if not 0 <= self.max_argument_length <= 100_000:
            raise ValueError("max_argument_length precisa estar entre 0 e 100000.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_execution_policies() -> dict[str, ActionExecutionPolicy]:
    return {
        "system.information": ActionExecutionPolicy(
            "system.information", 3, 30, 2.0, 0
        ),
        "filesystem.list_directory": ActionExecutionPolicy(
            "filesystem.list_directory", 5, 20, 5.0, 2048
        ),
    }


__all__ = ["ActionExecutionPolicy", "default_execution_policies"]
