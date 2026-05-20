"""Unit tests for structured logging setup."""
import logging
import os
import pytest


def test_setup_logging_runs_without_error():
    """setup_logging() should not raise."""
    from app.core.logging_config import setup_logging
    setup_logging()


def test_root_logger_has_handler_after_setup():
    """Root logger should have exactly one handler after setup."""
    from app.core.logging_config import setup_logging
    setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) == 1


def test_noisy_libs_set_to_warning():
    """httpx, httpcore etc. should be silenced to WARNING."""
    from app.core.logging_config import setup_logging
    setup_logging()
    for name in ("httpx", "httpcore", "sqlalchemy.engine"):
        assert logging.getLogger(name).level == logging.WARNING


def test_production_flag_switches_renderer(monkeypatch):
    """ENVIRONMENT=production should not raise (uses JSONRenderer)."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    from app.core import logging_config
    import importlib
    importlib.reload(logging_config)
    logging_config.setup_logging()
    monkeypatch.delenv("ENVIRONMENT", raising=False)
