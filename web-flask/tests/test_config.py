import pytest

from config import _required_base_url


def test_required_base_url_normalizes_trailing_slash(monkeypatch):
    monkeypatch.setenv("TEST_JAVA_URL", "http://java-back:8080/")

    assert _required_base_url("TEST_JAVA_URL") == "http://java-back:8080"


def test_required_base_url_rejects_missing_value(monkeypatch):
    monkeypatch.delenv("TEST_JAVA_URL", raising=False)

    with pytest.raises(RuntimeError, match="TEST_JAVA_URL is required"):
        _required_base_url("TEST_JAVA_URL")


def test_required_base_url_rejects_non_http_scheme(monkeypatch):
    monkeypatch.setenv("TEST_JAVA_URL", "java-back:8080")

    with pytest.raises(RuntimeError, match="must start with"):
        _required_base_url("TEST_JAVA_URL")
