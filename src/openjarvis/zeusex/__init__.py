"""Camada oficial de personalização do ZeusExAI.

O pacote mantém identidade, runtime, memória e provedores isolados do núcleo
OpenJarvis para facilitar atualizações futuras do projeto-base.
"""

from openjarvis.zeusex.engines import (
    EngineSettings,
    OllamaEngine,
    OpenAICompatibleEngine,
    build_engine,
)
from openjarvis.zeusex.identity import ZEUSEX_IDENTITY, ZeusExIdentity
from openjarvis.zeusex.runtime import (
    AIEngine,
    CallableEngine,
    DisabledEngine,
    RuntimeConfig,
    ZeusRuntime,
)

__all__ = [
    "AIEngine",
    "CallableEngine",
    "DisabledEngine",
    "EngineSettings",
    "OllamaEngine",
    "OpenAICompatibleEngine",
    "RuntimeConfig",
    "ZEUSEX_IDENTITY",
    "ZeusExIdentity",
    "ZeusRuntime",
    "build_engine",
]
