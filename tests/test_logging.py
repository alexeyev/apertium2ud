"""
    Tests for the package's logging behaviour.

    The library must use a module-level logger (not the root logger), must not
    emit anything unless the application opts in, and must honour the
    `disable_undocumented_tags_warnings` switch. These tests use pytest's
    `caplog` fixture rather than the global `logging.disable`, so they actually
    exercise the logging path.
"""

import logging


def test_unknown_tag_warns_via_named_logger(caplog):
    """ An undocumented tag should log a warning through the package's own
        logger (apertium2ud.convert), not the root logger. """
    from apertium2ud.convert import a2ud

    with caplog.at_level(logging.WARNING, logger="apertium2ud.convert"):
        a2ud(["definitely_not_a_real_tag"])

    assert any(
        rec.name == "apertium2ud.convert" and rec.levelno == logging.WARNING
        for rec in caplog.records
    ), "expected a WARNING from the apertium2ud.convert logger"
    # and it must NOT have gone through the root logger
    assert all(rec.name != "root" for rec in caplog.records)


def test_warning_suppressed_when_disabled(caplog):
    """ disable_undocumented_tags_warnings=True must silence the warning. """
    from apertium2ud.convert import a2ud

    with caplog.at_level(logging.WARNING, logger="apertium2ud.convert"):
        a2ud(["definitely_not_a_real_tag"], disable_undocumented_tags_warnings=True)

    assert not caplog.records, "no warning should be emitted when disabled"


def test_known_tags_do_not_warn(caplog):
    """ A fully-documented reading must not emit any warning. """
    from apertium2ud.convert import a2ud

    with caplog.at_level(logging.WARNING, logger="apertium2ud.convert"):
        a2ud(["n", "pl", "acc"])

    assert not caplog.records


def test_library_does_not_configure_root_logger():
    """ Importing and using the library must not attach handlers to the root
        logger (that is the application's responsibility). """
    from apertium2ud.convert import a2ud

    root_handlers_before = list(logging.getLogger().handlers)
    a2ud(["unknown_tag_xyz"], disable_undocumented_tags_warnings=True)
    root_handlers_after = list(logging.getLogger().handlers)

    assert root_handlers_before == root_handlers_after


def test_convert_module_has_named_logger():
    """ convert.py must expose a module-level logger named after the module. """
    import apertium2ud.convert as conv

    assert hasattr(conv, "logger")
    assert conv.logger.name == "apertium2ud.convert"
