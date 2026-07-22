"""Configuração central do ZeusExAI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True, slots=True)
class ZeusConfig:
    """Configurações imutáveis carregadas de variáveis de ambiente."""

    name: str = "ZeusExAI"
    wake_word: str = "zeus"
    language: str = "pt-BR"
    data_dir: Path = Path(".zeusex")
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "ZeusConfig":
        data_dir = Path(os.getenv("ZEUSEX_DATA_DIR", ".zeusex")).expanduser()
        return cls(
            name=os.getenv("ZEUSEX_NAME", "ZeusExAI"),
            wake_word=os.getenv("ZEUSEX_WAKE_WORD", "zeus").strip().lower(),
            language=os.getenv("ZEUSEX_LANGUAGE", "pt-BR"),
            data_dir=data_dir,
            log_level=os.getenv("ZEUSEX_LOG_LEVEL", "INFO").upper(),
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(parents=True, exist_ok=True)
