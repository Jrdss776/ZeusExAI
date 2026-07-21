"""Teste de fumaça isolado para a Beta do ZeusExAI."""

from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
import sqlite3
import tempfile

from openjarvis.zeusex.runtime import DisabledEngine, RuntimeConfig, ZeusRuntime


@dataclass(frozen=True, slots=True)
class BetaSmokeStep:
    name: str
    ok: bool
    message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BetaSmokeResult:
    ok: bool
    steps: tuple[BetaSmokeStep, ...]
    temporary_data_removed: bool
    external_action_performed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "temporary_data_removed": self.temporary_data_removed,
            "external_action_performed": self.external_action_performed,
            "steps": [step.to_dict() for step in self.steps],
        }


def run_beta_smoke_test(*, base_dir: Path | str | None = None) -> BetaSmokeResult:
    """Executa verificações locais em diretório descartável."""

    steps: list[BetaSmokeStep] = []
    temporary_path: Path | None = None
    with tempfile.TemporaryDirectory(dir=base_dir, prefix="zeusex-beta-") as directory:
        temporary_path = Path(directory)
        try:
            runtime = ZeusRuntime(
                engine=DisabledEngine("Teste Beta offline."),
                config=RuntimeConfig(data_dir=temporary_path),
            )
            database = temporary_path / "zeusex.db"
            steps.append(BetaSmokeStep("runtime", database.is_file(), "Runtime inicializado."))

            with closing(
                sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            ) as connection:
                integrity = connection.execute("PRAGMA quick_check").fetchone()
            database_ok = bool(integrity and integrity[0] == "ok")
            steps.append(BetaSmokeStep("sqlite", database_ok, "Integridade SQLite verificada."))

            marker = "memória temporária do teste Beta"
            runtime.remember(marker)
            memory_ok = marker in runtime.memories()
            steps.append(BetaSmokeStep("memoria", memory_ok, "Memória local validada."))

            status_ok = "online" in runtime.handle("status").lower()
            steps.append(BetaSmokeStep("comando", status_ok, "Comando local validado."))
            del runtime
        except Exception as exc:
            steps.append(
                BetaSmokeStep(
                    "runtime",
                    False,
                    f"Falha controlada: {type(exc).__name__}.",
                )
            )

    removed = temporary_path is not None and not temporary_path.exists()
    return BetaSmokeResult(
        ok=all(step.ok for step in steps) and removed,
        steps=tuple(steps),
        temporary_data_removed=removed,
    )


__all__ = ["BetaSmokeResult", "BetaSmokeStep", "run_beta_smoke_test"]
