"""
    Shared pytest fixtures.

    The converter logs a warning for every undocumented Apertium tag. Most tests
    pass `disable_undocumented_tags_warnings=True` where that matters, but to
    keep the test output quiet we raise the package logger's level for the test
    session. This is done by RAISING THE LEVEL (reversible, per-logger) rather
    than `logging.disable()` (a hard global gate), so that tests using pytest's
    `caplog` fixture can still capture log records via `caplog.at_level(...)`.
"""

import logging

import pytest


@pytest.fixture(autouse=True)
def _quiet_apertium2ud_logger():
    logger = logging.getLogger("apertium2ud")
    previous = logger.level
    logger.setLevel(logging.ERROR)
    try:
        yield
    finally:
        logger.setLevel(previous)
