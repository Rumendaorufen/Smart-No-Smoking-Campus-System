"""Shared configuration for authenticated Flask-to-Java internal calls."""

from config import Config


def internal_headers() -> dict[str, str]:
    if not Config.INTERNAL_API_TOKEN:
        raise RuntimeError("INTERNAL_API_TOKEN is required for Java internal APIs")
    return {"X-Internal-Token": Config.INTERNAL_API_TOKEN}
