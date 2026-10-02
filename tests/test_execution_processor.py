"""Tests for DataProcessor and sensitive data redaction."""

from cz.execution.processor import NoopProcessor, RedactionProcessor


def test_noop_processor():
    proc = NoopProcessor()
    data = {"api_key": "sk-12345", "nested": [1, 2, 3]}
    assert proc.process(data) == data
    assert proc.process("hello") == "hello"
    assert proc.process(None) is None


def test_redaction_processor_sensitive_keys():
    proc = RedactionProcessor()
    payload = {
        "user": "alice",
        "api_key": "secret_key_value",
        "nested": {
            "token": "bearer 12345",
            "password": "supersecretpassword",
            "safe_data": 42,
        },
    }
    redacted = proc.process(payload)
    assert redacted["user"] == "alice"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["safe_data"] == 42


def test_redaction_processor_regex_patterns():
    proc = RedactionProcessor()
    text = "Connecting with sk-abcdef1234567890abcdef12345678 to OpenAI and Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    processed = proc.process(text)
    assert "sk-" not in processed
    assert "[REDACTED]" in processed


def test_redaction_processor_collections():
    proc = RedactionProcessor()
    items = [{"password": "p1"}, {"password": "p2"}, "plain string"]
    result = proc.process(items)
    assert result[0]["password"] == "[REDACTED]"
    assert result[1]["password"] == "[REDACTED]"
    assert result[2] == "plain string"
