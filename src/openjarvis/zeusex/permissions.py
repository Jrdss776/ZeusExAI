"""Política declarativa de permissões para Skills do ZeusExAI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    allowed: bool
    reason: str


@dataclass(slots=True)
class PermissionPolicy:
    """Valida permissões conhecidas e exige confirmação para ações elevadas."""

    allowed_permissions: set[str] = field(
        default_factory=lambda: {
            "system.read_basic",
            "filesystem.read_directory",
            "system.sensitive_action",
        }
    )
    confirmation_required: set[str] = field(
        default_factory=lambda: {
            "filesystem.read_directory",
            "system.sensitive_action",
        }
    )

    def evaluate(self, permissions: tuple[str, ...], *, confirmed: bool) -> PermissionDecision:
        unknown = sorted(set(permissions) - self.allowed_permissions)
        if unknown:
            return PermissionDecision(False, f"Permissão não autorizada: {', '.join(unknown)}.")
        elevated = sorted(set(permissions) & self.confirmation_required)
        if elevated and not confirmed:
            return PermissionDecision(
                False,
                f"Confirmação necessária para as permissões: {', '.join(elevated)}.",
            )
        return PermissionDecision(True, "Permissões autorizadas.")


__all__ = ["PermissionDecision", "PermissionPolicy"]
