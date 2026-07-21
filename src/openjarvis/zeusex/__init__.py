"""Camada oficial de personalização do ZeusExAI."""

from openjarvis.zeusex.analysis_360 import (
    Analysis360Report,
    analysis_360_from_mapping,
    build_analysis_360,
)
from openjarvis.zeusex.analysis_queue import AnalysisJob, AnalysisQueue
from openjarvis.zeusex.analysis_worker import AnalysisWorker, WorkerOutcome
from openjarvis.zeusex.android_support import (
    AndroidDiagnostic,
    AndroidPackageManifest,
    AndroidUpdatePlan,
    BackupResult,
    backup_android_databases,
    build_android_update_plan,
    diagnose_android,
)
from openjarvis.zeusex.auth import AuthenticationResult, LocalAPIAuthenticator
from openjarvis.zeusex.campaign_store import (
    CampaignTemplateStore,
    SavedCampaignTemplate,
)
from openjarvis.zeusex.campaigns import (
    ACHADINHOS_JR_TEMPLATE,
    CampaignPackage,
    CampaignTemplate,
    CatalogItem,
    CombinationSuggestion,
    campaign_from_mapping,
    generate_campaign,
    suggest_combinations,
)
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
from openjarvis.zeusex.commercial_analysis import (
    CommercialAnalysisRequest,
    CommercialAnalysisResult,
    CommercialAnalysisService,
    CommercialCosts,
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
from openjarvis.zeusex.mobile_api import APIResponse, MobileAPIService
from openjarvis.zeusex.mobile_server import (
    MobileServerConfig,
    create_mobile_server,
    serve_mobile_api,
)
from openjarvis.zeusex.multichannel import (
    MarketplaceCopy,
    MultichannelPackage,
    SocialCopy,
    VideoScene,
    VideoScript,
    generate_multichannel_content,
)
from openjarvis.zeusex.pwa_assets import (
    PWA_ICON_SVG,
    PWA_MANIFEST,
    PWA_SERVICE_WORKER,
)
from openjarvis.zeusex.report_store import AnalysisReportStore, SavedAnalysis
from openjarvis.zeusex.runtime import AIEngine, CallableEngine, DisabledEngine, RuntimeConfig, ZeusRuntime
from openjarvis.zeusex.schedule_executor import ScheduleExecutor, ScheduleOutcome
from openjarvis.zeusex.scheduler import (
    ALLOWED_JOB_TYPES,
    SafeScheduler,
    ScheduledTask,
)
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
    "ACHADINHOS_JR_TEMPLATE",
    "ALLOWED_JOB_TYPES",
    "APIResponse",
    "AIEngine",
    "Analysis360Report",
    "AnalysisJob",
    "AnalysisQueue",
    "AnalysisReportStore",
    "AnalysisWorker",
    "AndroidDiagnostic",
    "AndroidPackageManifest",
    "AndroidUpdatePlan",
    "AuthenticationResult",
    "AdvertisementDraft",
    "BackupResult",
    "CampaignPackage",
    "CampaignTemplate",
    "CampaignTemplateStore",
    "CommercialAnalysisRequest",
    "CommercialAnalysisResult",
    "CommercialAnalysisService",
    "CommercialCosts",
    "CatalogItem",
    "CallableEngine",
    "CombinationSuggestion",
    "CompetitorComparison",
    "DiagnosticResult",
    "DisabledEngine",
    "ENTRY_POINT_GROUP",
    "EngineSettings",
    "HTTPClientConfig",
    "MarketplaceAdapter",
    "MarketplaceCopy",
    "LocalAPIAuthenticator",
    "MarketplaceHTTPError",
    "MercadoLivreAdapter",
    "MercadoLivreReadClient",
    "MobileAPIService",
    "MobileServerConfig",
    "MultichannelPackage",
    "NormalizedListing",
    "NullSpeechCapture",
    "NullSpeechSynthesizer",
    "OllamaEngine",
    "PotentialAnalysis",
    "PotentialSignals",
    "PWA_ICON_SVG",
    "PWA_MANIFEST",
    "PWA_SERVICE_WORKER",
    "ProductInput",
    "ProfitAnalysis",
    "OpenAICompatibleEngine",
    "ReadOnlyHTTPClient",
    "RuntimeConfig",
    "SafeScheduler",
    "ScheduleExecutor",
    "ScheduleOutcome",
    "SavedCampaignTemplate",
    "SavedAnalysis",
    "Skill",
    "SkillRegistry",
    "ScheduledTask",
    "ShopeeAdapter",
    "ShopeeReadClient",
    "SocialCopy",
    "SpeechCapture",
    "SpeechSynthesizer",
    "VideoScene",
    "VideoScript",
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
    "backup_android_databases",
    "build_analysis_360",
    "build_android_update_plan",
    "build_engine",
    "campaign_from_mapping",
    "compare_listings",
    "create_advertisement_draft",
    "create_mobile_server",
    "default_registry",
    "diagnose_provider",
    "diagnose_android",
    "discover_skills",
    "extract_wake_command",
    "generate_campaign",
    "generate_multichannel_content",
    "open_allowed_application",
    "serve_mobile_api",
    "suggest_combinations",
    "voice_status",
]
