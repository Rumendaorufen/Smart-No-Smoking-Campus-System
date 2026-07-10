import pytest

from app.core.java_client import internal_headers
from config import Config


def test_internal_headers_contains_configured_token(monkeypatch):
    monkeypatch.setattr(Config, "INTERNAL_API_TOKEN", "x" * 32)

    assert internal_headers() == {"X-Internal-Token": "x" * 32}


def test_internal_headers_rejects_missing_token(monkeypatch):
    monkeypatch.setattr(Config, "INTERNAL_API_TOKEN", "")

    with pytest.raises(RuntimeError, match="INTERNAL_API_TOKEN"):
        internal_headers()
