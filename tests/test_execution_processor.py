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


def test_redaction_processor_redacts_common_sensitive_values_and_limits_payloads():
    proc = RedactionProcessor(max_payload_bytes=80)
    payload = {
        "email": "person@example.com",
        "phone": "+1 (415) 555-0123",
        "github": "ghp_abcdefghijklmnopqrstuvwxyz1234567890",
        "openai": "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890",
        "aws": "AKIAIOSFODNN7EXAMPLE",
        "google": "AIzaabcdefghijklmnopqrstuvwxyz1234567890ABCDE",
        "private_key": "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----",
        "text": "Bearer eyJhbGciOiJIUzI1NiJ9.abcdefghijklmnopqrstuvwxyz",
    }

    redacted = proc.process(payload)
    serialized = str(redacted)
    assert "person@example.com" not in serialized
    assert "415) 555" not in serialized
    assert "ghp_" not in serialized
    assert "sk-proj" not in serialized
    assert "AKIA" not in serialized
    assert "AIza" not in serialized
    assert "BEGIN PRIVATE KEY" not in serialized
    assert "Bearer ey" not in serialized
    assert redacted["_cohzen_truncated"] is True

    limited = proc.process({"safe": "x" * 500})
    assert limited["safe"].endswith("bytes]")
