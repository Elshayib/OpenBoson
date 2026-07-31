"""Tests for rotating file logging setup."""

from __future__ import annotations

import logging

from openboson.logging_setup import log_file_path, setup_logging


def test_setup_logging_creates_file(isolated_home):
    path = setup_logging(force=True)
    assert path == log_file_path()
    assert path.is_file()
    logging.getLogger("openboson.test").info("hello-log")
    for handler in logging.getLogger().handlers:
        handler.flush()
    text = path.read_text(encoding="utf-8")
    assert "hello-log" in text
