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


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'raktdoot.db'}"))
    public_base_url: str = field(default_factory=lambda: _env("PUBLIC_BASE_URL", "http://localhost:3000"))
    cors_origins: list[str] = field(default_factory=lambda: [o.strip() for o in _env("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()])
    admin_token: str = field(default_factory=lambda: _env("ADMIN_TOKEN", "change-me"))
    timezone: str = field(default_factory=lambda: _env("APP_TIMEZONE", "Asia/Kolkata"))

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

    @property
    def tinyfish_live(self) -> bool:
        if self.tinyfish_mode == "demo":
            return False
        return bool(self.tinyfish_api_key)


settings = Settings()
