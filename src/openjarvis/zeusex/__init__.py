"""Camada oficial de personalização do ZeusExAI.

O pacote mantém identidade, runtime, memória, provedores, diagnóstico e Skills
isolados do núcleo OpenJarvis para facilitar atualizações futuras do projeto-base.
"""

from openjarvis.zeusex.diagnostics import DiagnosticResult, diagnose_provider
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
from openjarvis.zeusex.skills import Skill, SkillRegistry, default_registry

__all__ = [
    "AIEngine",
    "CallableEngine",
    "DiagnosticResult",
    "DisabledEngine",
    "EngineSettings",
    "OllamaEngine",
    "OpenAICompatibleEngine",
    "RuntimeConfig",
    "Skill",
    "SkillRegistry",
    "ZEUSEX_IDENTITY",
    "ZeusExIdentity",
    "ZeusRuntime",
    "build_engine",
    "default_registry",
    "diagnose_provider",
]
