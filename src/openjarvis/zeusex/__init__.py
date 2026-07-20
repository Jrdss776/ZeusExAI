"""Camada oficial de personalização do ZeusExAI."""

from openjarvis.zeusex.analysis_360 import (
    Analysis360Report,
    analysis_360_from_mapping,
    build_analysis_360,
)
from openjarvis.zeusex.analysis_queue import AnalysisJob, AnalysisQueue
from openjarvis.zeusex.analysis_worker import AnalysisWorker, WorkerOutcome
from openjarvis.zeusex.competitors import CompetitorComparison, compare_listings
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
from openjarvis.zeusex.marketplace_http import (
    HTTPClientConfig,
    MarketplaceHTTPError,
    MercadoLivreReadClient,
    ReadOnlyHTTPClient,
    ShopeeReadClient,
)
from openjarvis.zeusex.marketplace_listings import (
    MarketplaceAdapter,
    MercadoLivreAdapter,
    NormalizedListing,
    ShopeeAdapter,
)
from openjarvis.zeusex.report_store import AnalysisReportStore, SavedAnalysis
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
    "Analysis360Report",
    "AnalysisJob",
    "AnalysisQueue",
    "AnalysisReportStore",
    "AnalysisWorker",
    "AdvertisementDraft",
    "CallableEngine",
    "CompetitorComparison",
    "DiagnosticResult",
    "DisabledEngine",
    "ENTRY_POINT_GROUP",
    "EngineSettings",
    "HTTPClientConfig",
    "MarketplaceAdapter",
    "MarketplaceHTTPError",
    "MercadoLivreAdapter",
    "MercadoLivreReadClient",
    "NormalizedListing",
    "NullSpeechCapture",
    "NullSpeechSynthesizer",
    "OllamaEngine",
    "PotentialAnalysis",
    "PotentialSignals",
    "ProductInput",
    "ProfitAnalysis",
    "OpenAICompatibleEngine",
    "ReadOnlyHTTPClient",
    "RuntimeConfig",
    "SavedAnalysis",
    "Skill",
    "SkillRegistry",
    "ShopeeAdapter",
    "ShopeeReadClient",
    "SpeechCapture",
    "SpeechSynthesizer",
    "VoiceConfig",
    "VoiceSession",
    "VoiceTurn",
    "WorkerOutcome",
    "ZEUSEX_IDENTITY",
    "ZeusExIdentity",
    "ZeusRuntime",
    "allowed_applications",
    "analysis_360_from_mapping",
    "analyze_batch",
    "analyze_potential",
    "analyze_profit",
    "build_analysis_360",
    "build_engine",
    "compare_listings",
    "create_advertisement_draft",
    "default_registry",
    "diagnose_provider",
    "discover_skills",
    "extract_wake_command",
    "open_allowed_application",
    "voice_status",
]
