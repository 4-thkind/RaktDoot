"""Settings, read once from the environment (and a .env file if present)."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / ".env")


def _env(name: str, default: str = "") -> str:
    value = (os.getenv(name) or "").strip()
    return value or default  # an empty line in .env means "use the default"


def _int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    return _env(name, "true" if default else "false").lower() not in ("false", "0", "no", "off")


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'raktdoot.db'}"))
    public_base_url: str = field(default_factory=lambda: _env("PUBLIC_BASE_URL", "http://localhost:3000"))
    cors_origins: list[str] = field(default_factory=lambda: [o.strip() for o in _env("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()])
    admin_token: str = field(default_factory=lambda: _env("ADMIN_TOKEN", "change-me"))
    timezone: str = field(default_factory=lambda: _env("APP_TIMEZONE", "Asia/Kolkata"))

    #Auth
    supabase_url: str = field(default_factory=lambda: _env("SUPABASE_URL").rstrip("/"))
    supabase_anon_key: str = field(default_factory=lambda: _env("SUPABASE_ANON_KEY"))
    
    # TinyFish
    tinyfish_api_key: str = field(default_factory=lambda: _env("TINYFISH_API_KEY"))
    tinyfish_mode: str = field(default_factory=lambda: _env("TINYFISH_MODE", "auto"))  # auto | live | demo
    eraktkosh_stock_url: str = field(default_factory=lambda: _env("ERAKTKOSH_STOCK_URL", "https://eraktkosh.mohfw.gov.in/BLDAHIMS/bloodbank/stockAvailability.cnt"))
    eraktkosh_component: str = field(default_factory=lambda: _env("ERAKTKOSH_COMPONENT", "Packed Red Blood Cells"))
    stock_cache_ttl_min: int = field(default_factory=lambda: _int("STOCK_CACHE_TTL_MIN", 15))
    stock_timeout_s: int = field(default_factory=lambda: _int("STOCK_TIMEOUT_S", 90))

    # WhatsApp
    whatsapp_mode: str = field(default_factory=lambda: _env("WHATSAPP_MODE", "mock"))  # cloud | twilio | mock
    whatsapp_token: str = field(default_factory=lambda: _env("WHATSAPP_TOKEN"))
    whatsapp_phone_number_id: str = field(default_factory=lambda: _env("WHATSAPP_PHONE_NUMBER_ID"))
    whatsapp_verify_token: str = field(default_factory=lambda: _env("WHATSAPP_VERIFY_TOKEN", "raktdoot-verify"))
    whatsapp_app_secret: str = field(default_factory=lambda: _env("WHATSAPP_APP_SECRET"))
    whatsapp_business_number: str = field(default_factory=lambda: _env("WHATSAPP_BUSINESS_NUMBER", "919999999999"))
    whatsapp_template_lang: str = field(default_factory=lambda: _env("WHATSAPP_TEMPLATE_LANG", "en"))
    twilio_account_sid: str = field(default_factory=lambda: _env("TWILIO_ACCOUNT_SID"))
    twilio_auth_token: str = field(default_factory=lambda: _env("TWILIO_AUTH_TOKEN"))
    twilio_webhook_url: str = field(default_factory=lambda: _env("TWILIO_WEBHOOK_URL"))
    twilio_from: str = field(default_factory=lambda: _env("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"))

    # LLM (any OpenAI-compatible chat completions endpoint)
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY"))
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", "https://api.openai.com/v1"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "gpt-4o-mini"))

    # Geocoding
    geocoder: str = field(default_factory=lambda: _env("GEOCODER", "nominatim"))  # nominatim | off

    # Dispatch
    wave_size: int = field(default_factory=lambda: _int("DISPATCH_WAVE_SIZE", 10))
    wave_interval_min: int = field(default_factory=lambda: _int("DISPATCH_WAVE_INTERVAL_MIN", 5))
    wave_radii_km: list[float] = field(default_factory=lambda: [float(x) for x in _env("DISPATCH_RADII_KM", "5,10,25,40").split(",")])
    max_open_requests_per_phone: int = field(default_factory=lambda: _int("MAX_OPEN_REQUESTS_PER_PHONE", 3))
    request_ttl_hours: int = field(default_factory=lambda: _int("REQUEST_TTL_HOURS", 24))
    respect_quiet_hours: bool = field(default_factory=lambda: _env("RESPECT_QUIET_HOURS", "true").lower() != "false")
    ticker_seconds: int = field(default_factory=lambda: _int("TICKER_SECONDS", 15))

    # TinyFish upgrades
    tinyfish_proxy_country: str = field(default_factory=lambda: _env("TINYFISH_PROXY_COUNTRY", "IN"))  # "" or "off" = no proxy
    tinyfish_replay_enabled: bool = field(default_factory=lambda: _bool("TINYFISH_REPLAY_ENABLED", True))
    tinyfish_verify_every: int = field(default_factory=lambda: _int("TINYFISH_VERIFY_EVERY", 20))  # every Nth replay is cross-checked by the Agent
    tinyfish_webhook_url: str = field(default_factory=lambda: _env("TINYFISH_WEBHOOK_URL"))  # public https URL of /webhooks/tinyfish?key=...
    tinyfish_webhook_secret: str = field(default_factory=lambda: _env("TINYFISH_WEBHOOK_SECRET"))  # the ?key= value; empty = webhooks off
    stock_sweep_hours: int = field(default_factory=lambda: _int("STOCK_SWEEP_HOURS", 0))  # 0 = only from /admin
    stock_sweep_districts: list[str] = field(default_factory=lambda: [d.strip() for d in _env(
        "STOCK_SWEEP_DISTRICTS", "Delhi/New Delhi,Delhi/South,Delhi/South West,Delhi/Central,Delhi/East,Delhi/North,Delhi/North West,"
        "Delhi/West,Delhi/Shahdara,Delhi/South East,Delhi/North East,Haryana/Gurugram,Haryana/Faridabad,"
        "Uttar Pradesh/Gautam Buddha Nagar,Uttar Pradesh/Ghaziabad").split(",") if d.strip()])

    # Vision (F3, F9) and speech (F4); any OpenAI-compatible endpoint, defaults to the LLM settings
    vision_model: str = field(default_factory=lambda: _env("VISION_MODEL", "gpt-4o-mini"))
    stt_provider: str = field(default_factory=lambda: _env("STT_PROVIDER", "auto"))  # auto | sarvam | openai | demo
    stt_api_key: str = field(default_factory=lambda: _env("STT_API_KEY"))
    stt_model: str = field(default_factory=lambda: _env("STT_MODEL", ""))
    embedding_model: str = field(default_factory=lambda: _env("EMBEDDING_MODEL", ""))  # empty = BM25 retrieval only
    tts_provider: str = field(default_factory=lambda: _env("TTS_PROVIDER", "auto"))  # auto | sarvam | edge | openai | off
    tts_voice_en: str = field(default_factory=lambda: _env("TTS_VOICE_EN", "en-IN-NeerjaNeural"))  # edge voices
    tts_voice_hi: str = field(default_factory=lambda: _env("TTS_VOICE_HI", "hi-IN-SwaraNeural"))
    public_api_base: str = field(default_factory=lambda: _env("PUBLIC_API_BASE", "http://localhost:8000"))  # media links for Twilio
    camp_portal_url: str = field(default_factory=lambda: _env("CAMP_PORTAL_URL", ""))  # empty = the built-in MOCK portal
    keep_uploads: bool = field(default_factory=lambda: _bool("KEEP_UPLOADS", False))

    # AI features
    forecast_enabled: bool = field(default_factory=lambda: _bool("FORECAST_ENABLED", True))
    shortage_threshold_units: int = field(default_factory=lambda: _int("SHORTAGE_THRESHOLD_UNITS", 5))
    auto_drives: bool = field(default_factory=lambda: _bool("AUTO_DRIVES", False))
    dispatch_agent_enabled: bool = field(default_factory=lambda: _bool("DISPATCH_AGENT_ENABLED", True))
    max_alerts_per_request: int = field(default_factory=lambda: _int("MAX_ALERTS_PER_REQUEST", 60))
    max_alerts_per_hour: int = field(default_factory=lambda: _int("MAX_ALERTS_PER_REQUEST_PER_HOUR", 30))
    bandit_enabled: bool = field(default_factory=lambda: _bool("BANDIT_ENABLED", True))
    use_intel_sklearn: bool = field(default_factory=lambda: _bool("USE_INTEL_SKLEARN", False))
    recurring_reminder_days: int = field(default_factory=lambda: _int("RECURRING_REMINDER_DAYS", 3))

    @property
    def llm_live(self) -> bool:
        return bool(self.llm_api_key)

    @property
    def tinyfish_live(self) -> bool:
        if self.tinyfish_mode == "demo":
            return False
        return bool(self.tinyfish_api_key)


settings = Settings()
