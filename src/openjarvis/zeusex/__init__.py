"""Camada oficial de personalização do ZeusExAI."""

from openjarvis.zeusex.desktop_automation import allowed_applications, open_allowed_application
from openjarvis.zeusex.diagnostics import DiagnosticResult, diagnose_provider
from openjarvis.zeusex.engines import EngineSettings, OllamaEngine, OpenAICompatibleEngine, build_engine
from openjarvis.zeusex.identity import ZEUSEX_IDENTITY, ZeusExIdentity
from openjarvis.zeusex.marketplace import (
    AdvertisementDraft,
    PotentialAnalysis,
    PotentialSignals,
    ProductInput,
    ProfitAnalysis,
    analyze_batch,
    analyze_potential,
    analyze_profit,
    create_advertisement_draft,
)
from openjarvis.zeusex.runtime import AIEngine, CallableEngine, DisabledEngine, RuntimeConfig, ZeusRuntime
from openjarvis.zeusex.skills import ENTRY_POINT_GROUP, Skill, SkillRegistry, default_registry, discover_skills
from openjarvis.zeusex.voice import VoiceConfig, extract_wake_command, voice_status
from openjarvis.zeusex.voice_runtime import (
    NullSpeechCapture,
    NullSpeechSynthesizer,
    SpeechCapture,
    SpeechSynthesizer,
    VoiceSession,
    VoiceTurn,
)

__all__ = [
    "AIEngine",
    "AdvertisementDraft",
    "CallableEngine",
    "DiagnosticResult",
    "DisabledEngine",
    "ENTRY_POINT_GROUP",
    "EngineSettings",
    "NullSpeechCapture",
    "NullSpeechSynthesizer",
    "OllamaEngine",
    "PotentialAnalysis",
    "PotentialSignals",
    "ProductInput",
    "ProfitAnalysis",
    "OpenAICompatibleEngine",
    "RuntimeConfig",
    "Skill",
    "SkillRegistry",
    "SpeechCapture",
    "SpeechSynthesizer",
    "VoiceConfig",
    "VoiceSession",
    "VoiceTurn",
    "ZEUSEX_IDENTITY",
    "ZeusExIdentity",
    "ZeusRuntime",
    "allowed_applications",
    "analyze_batch",
    "analyze_potential",
    "analyze_profit",
    "build_engine",
    "create_advertisement_draft",
    "default_registry",
    "diagnose_provider",
    "discover_skills",
    "extract_wake_command",
    "open_allowed_application",
    "voice_status",
]
