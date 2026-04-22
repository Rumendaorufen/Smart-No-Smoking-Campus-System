import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str | None
    openai_model: str
    host: str
    port: int
    debug: bool
    db_uri: str
    include_tables: list[str]
    sql_top_k: int


def get_settings() -> Settings:
    default_tables = ",".join(
        [
            "ai_alarm_detail_view",
            "ai_alarm_daily_stats_view",
            "ai_device_alarm_rank_view",
            "ai_audit_stats_view",
        ]
    )

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        host=os.getenv("AGENT_HOST", "0.0.0.0").strip(),
        port=int(os.getenv("AGENT_PORT", "5050")),
        debug=_as_bool(os.getenv("AGENT_DEBUG"), default=False),
        db_uri=os.getenv("DB_URI", "").strip(),
        include_tables=_split_csv(os.getenv("DB_INCLUDE_TABLES", default_tables)),
        sql_top_k=int(os.getenv("SQL_TOP_K", "10")),
    )
