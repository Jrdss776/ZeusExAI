"""Camada oficial de personalização do ZeusExAI.

O pacote mantém identidade, runtime, memória, provedores, diagnóstico e Skills
isolados do núcleo OpenJarvis para facilitar atualizações futuras do projeto-base.
"""

from openjarvis.zeusex.desktop_automation import allowed_applications, open_allowed_application
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
from openjarvis.zeusex.skills import (
    ENTRY_POINT_GROUP,
    Skill,
    SkillRegistry,
    default_registry,
    discover_skills,
)
from openjarvis.zeusex.voice import VoiceConfig, extract_wake_command, voice_status

__all__ = [
    "AIEngine",
    "CallableEngine",
    "DiagnosticResult",
    "DisabledEngine",
    "ENTRY_POINT_GROUP",
    "EngineSettings",
    "OllamaEngine",
    "OpenAICompatibleEngine",
    "RuntimeConfig",
    "Skill",
    "SkillRegistry",
    "VoiceConfig",
    "ZEUSEX_IDENTITY",
    "ZeusExIdentity",
    "ZeusRuntime",
    "allowed_applications",
    "build_engine",
    "default_registry",
    "diagnose_provider",
    "discover_skills",
    "extract_wake_command",
    "open_allowed_application",
    "voice_status",
]
