from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "InterviewMate AI"
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/interviewmate"
    # If the configured database cannot be reached (for example PostgreSQL is not running), fall back to a local
    # SQLite file so the app still works in development. Set to false in production.
    SQLITE_FALLBACK: bool = True
    SQLITE_FALLBACK_URL: str = "sqlite:///./interviewmate_dev.db"
    SECRET_KEY: str = "dev-only-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    # Comma separated. Any http://localhost:<port> / http://127.0.0.1:<port> origin is also accepted in development.
    CORS_ORIGINS: str = "http://localhost:3000"
    COOKIE_SECURE: bool = False

    # ---- Gemini (text + live voice). The key stays on the server and is never sent to the browser.
    GEMINI_API_KEY: str = ""
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com"
    GEMINI_MODELS: str = "gemini-2.5-flash,gemini-2.0-flash,gemini-flash-latest"
    GEMINI_LIVE_MODELS: str = ("gemini-2.5-flash-native-audio-preview-12-2025,gemini-2.5-flash-native-audio-preview-09-2025,"
                               "gemini-live-2.5-flash-preview,gemini-2.0-flash-live-001")
    GEMINI_LIVE_URL: str = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
    GEMINI_VOICE: str = "Puck"
    GEMINI_TIMEOUT_SECONDS: float = 60.0

    # ---- uploads and code runner
    MAX_UPLOAD_MB: int = 5
    CODE_RUN_ENABLED: bool = True
    CODE_RUN_TIMEOUT_SECONDS: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return _split(self.CORS_ORIGINS)

    @property
    def gemini_models(self) -> list[str]:
        return _split(self.GEMINI_MODELS)

    @property
    def gemini_live_models(self) -> list[str]:
        return _split(self.GEMINI_LIVE_MODELS)

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DATABASE_URL.startswith(("mysql://", "mysql+mysqldb://")):
            raw = self.DATABASE_URL.replace("mysql+mysqldb://", "mysql+pymysql://", 1).replace("mysql://", "mysql+pymysql://", 1)
            parts = urlsplit(raw)
            query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "ssl"]
            return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        return self.DATABASE_URL

    @property
    def database_connect_args(self) -> dict:
        return {"ssl": {"check_hostname": False}} if self.DATABASE_URL.startswith("mysql") else {}


settings = Settings()
