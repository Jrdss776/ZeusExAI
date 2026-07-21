"""Camada oficial de personalização do ZeusExAI."""

from openjarvis.zeusex.achadinhos_pipeline import (
    AchadinhosCampaignBatch,
    AchadinhosCampaignItem,
    AchadinhosSelectionPolicy,
    build_achadinhos_campaigns,
)
from openjarvis.zeusex.analysis_360 import (
    Analysis360Report,
    analysis_360_from_mapping,
    build_analysis_360,
)
from openjarvis.zeusex.analysis_queue import AnalysisJob, AnalysisQueue
from openjarvis.zeusex.analysis_worker import AnalysisWorker, WorkerOutcome
from openjarvis.zeusex.android_support import (
    AndroidDiagnostic,
    AndroidHealth,
    AndroidPackageManifest,
    AndroidUpdatePlan,
    BackupResult,
    BackupVerification,
    RestoreResult,
    backup_android_databases,
    build_android_update_plan,
    check_android_health,
    diagnose_android,
    migrate_android_databases,
    restore_android_backup,
    verify_android_backup,
)
from openjarvis.zeusex.auth import AuthenticationResult, LocalAPIAuthenticator
from openjarvis.zeusex.beta_readiness import (
    BetaReadinessCheck,
    BetaReadinessReport,
    assess_beta_readiness,
)
from openjarvis.zeusex.beta_support import (
    BetaSupportSnapshot,
    build_beta_support_snapshot,
    write_beta_support_report,
)
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
from openjarvis.zeusex.commercial_analysis import (
    CommercialAnalysisRequest,
    CommercialAnalysisResult,
    CommercialAnalysisService,
    CommercialCosts,
)
from openjarvis.zeusex.commercial_batch import (
    CommercialBatchRequest,
    CommercialBatchResult,
    CommercialBatchService,
)
from openjarvis.zeusex.commercial_opportunities import (
    OpportunityAssessment,
    PriceRecommendation,
    assess_opportunity,
    rank_opportunities,
    recommend_price,
)
from openjarvis.zeusex.competitors import CompetitorComparison, compare_listings
from openjarvis.zeusex.desktop_automation import allowed_applications, open_allowed_application
from openjarvis.zeusex.diagnostics import DiagnosticResult, diagnose_provider
from openjarvis.zeusex.engines import EngineSettings, OllamaEngine, OpenAICompatibleEngine, build_engine
from openjarvis.zeusex.google_calendar import (
    CalendarAccessMode,
    CalendarConnectorStatus,
    CalendarEvent,
    CalendarEventPreview,
    DisabledGoogleCalendarConnector,
    GoogleCalendarConfig,
    GoogleCalendarConnector,
    GoogleCalendarService,
)
from openjarvis.zeusex.google_calendar_api import (
    CalendarAPIResponse,
    GoogleCalendarAPI,
)
from openjarvis.zeusex.google_drive import (
    DisabledGoogleDriveConnector,
    DriveAccessMode,
    DriveConnectorStatus,
    DriveFile,
    GoogleDriveConfig,
    GoogleDriveConnector,
    GoogleDriveService,
)
from openjarvis.zeusex.google_drive_api import DriveAPIResponse, GoogleDriveAPI
from openjarvis.zeusex.google_integrations import (
    GoogleIntegrationStatus,
    GoogleIntegrationsOverview,
    GoogleIntegrationsService,
)
from openjarvis.zeusex.google_setup import (
    GoogleOAuthSetupPlan,
    READ_ONLY_SCOPES,
    build_google_oauth_setup_plan,
)
from openjarvis.zeusex.google_setup_api import GoogleSetupAPI, GoogleSetupAPIResponse
from openjarvis.zeusex.gmail import (
    DisabledGmailConnector,
    GmailAccessMode,
    GmailConfig,
    GmailConnector,
    GmailConnectorStatus,
    GmailDraftPreview,
    GmailMessage,
    GmailService,
)
from openjarvis.zeusex.gmail_api import GmailAPI, GmailAPIResponse
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
    "AchadinhosCampaignBatch",
    "AchadinhosCampaignItem",
    "AchadinhosSelectionPolicy",
    "Analysis360Report",
    "AnalysisJob",
    "AnalysisQueue",
    "AnalysisReportStore",
    "AnalysisWorker",
    "AndroidDiagnostic",
    "AndroidHealth",
    "AndroidPackageManifest",
    "AndroidUpdatePlan",
    "AuthenticationResult",
    "AdvertisementDraft",
    "BackupResult",
    "BackupVerification",
    "BetaReadinessCheck",
    "BetaReadinessReport",
    "BetaSupportSnapshot",
    "CampaignPackage",
    "CampaignTemplate",
    "CampaignTemplateStore",
    "CalendarAPIResponse",
    "CalendarAccessMode",
    "CalendarConnectorStatus",
    "CalendarEvent",
    "CalendarEventPreview",
    "CommercialAnalysisRequest",
    "CommercialAnalysisResult",
    "CommercialAnalysisService",
    "CommercialBatchRequest",
    "CommercialBatchResult",
    "CommercialBatchService",
    "CommercialCosts",
    "CatalogItem",
    "CallableEngine",
    "CombinationSuggestion",
    "CompetitorComparison",
    "DiagnosticResult",
    "DisabledEngine",
    "DisabledGoogleCalendarConnector",
    "DisabledGoogleDriveConnector",
    "DisabledGmailConnector",
    "ENTRY_POINT_GROUP",
    "EngineSettings",
    "DriveAPIResponse",
    "DriveAccessMode",
    "DriveConnectorStatus",
    "DriveFile",
    "HTTPClientConfig",
    "GoogleCalendarAPI",
    "GoogleCalendarConfig",
    "GoogleCalendarConnector",
    "GoogleCalendarService",
    "GoogleDriveAPI",
    "GoogleDriveConfig",
    "GoogleDriveConnector",
    "GoogleDriveService",
    "GoogleIntegrationStatus",
    "GoogleIntegrationsOverview",
    "GoogleIntegrationsService",
    "GoogleOAuthSetupPlan",
    "GoogleSetupAPI",
    "GoogleSetupAPIResponse",
    "GmailAPI",
    "GmailAPIResponse",
    "GmailAccessMode",
    "GmailConfig",
    "GmailConnector",
    "GmailConnectorStatus",
    "GmailDraftPreview",
    "GmailMessage",
    "GmailService",
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
    "OpportunityAssessment",
    "PotentialAnalysis",
    "PotentialSignals",
    "PriceRecommendation",
    "PWA_ICON_SVG",
    "PWA_MANIFEST",
    "PWA_SERVICE_WORKER",
    "ProductInput",
    "ProfitAnalysis",
    "OpenAICompatibleEngine",
    "ReadOnlyHTTPClient",
    "READ_ONLY_SCOPES",
    "RuntimeConfig",
    "RestoreResult",
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
    "assess_opportunity",
    "assess_beta_readiness",
    "backup_android_databases",
    "build_achadinhos_campaigns",
    "build_analysis_360",
    "build_android_update_plan",
    "check_android_health",
    "build_engine",
    "build_beta_support_snapshot",
    "build_google_oauth_setup_plan",
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
    "migrate_android_databases",
    "open_allowed_application",
    "restore_android_backup",
    "rank_opportunities",
    "recommend_price",
    "serve_mobile_api",
    "suggest_combinations",
    "verify_android_backup",
    "voice_status",
    "write_beta_support_report",
]
