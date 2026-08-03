import logging

from wasds150.logging_setup import RedactionFilter, configure_logging


def test_configure_logging_returns_named_logger():
    logger = configure_logging()
    assert logger.name == "wasds150"
    assert logger.level == logging.INFO


def test_configure_logging_with_file_creates_it(tmp_path):
    log_file = tmp_path / "logs" / "wasds150.log"
    logger = configure_logging(log_file)
    logger.info("hello")
    for handler in logger.handlers:
        handler.flush()
    assert log_file.exists()
    assert "hello" in log_file.read_text(encoding="utf-8")


def test_configure_logging_is_idempotent_no_duplicate_handlers(tmp_path):
    log_file = tmp_path / "wasds150.log"
    configure_logging(log_file)
    logger = configure_logging(log_file)
    # console + file handler, not accumulating across repeated calls
    assert len(logger.handlers) == 2


def _make_record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1, msg=msg, args=(), exc_info=None
    )


def test_redaction_filter_masks_api_key():
    record = _make_record("using api_key=SUPER-SECRET-VALUE for request")
    RedactionFilter().filter(record)
    assert "SUPER-SECRET-VALUE" not in record.getMessage()
    assert "REDACTED" in record.getMessage()


def test_redaction_filter_masks_token_and_password():
    record = _make_record("token: abc123 password=hunter2")
    RedactionFilter().filter(record)
    rendered = record.getMessage()
    assert "abc123" not in rendered
    assert "hunter2" not in rendered


def test_redaction_filter_leaves_normal_messages_untouched():
    record = _make_record("nothing sensitive here")
    RedactionFilter().filter(record)
    assert record.getMessage() == "nothing sensitive here"
