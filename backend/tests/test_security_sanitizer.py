"""Unit tests for SensitiveDataDetector and DataSanitizer."""

import pytest
from app.security.sanitizer import DataSanitizer, SensitiveDataDetector


def test_email_detection_and_redaction():
    text = "Contact the SRE lead at alice.ops@enterprise.org or bob@sub.company.co.uk immediately."
    assert SensitiveDataDetector.contains_sensitive_data(text)
    sanitized = DataSanitizer.sanitize_text(text)
    assert "alice.ops@enterprise.org" not in sanitized
    assert "bob@sub.company.co.uk" not in sanitized
    assert "[REDACTED_EMAIL]" in sanitized


def test_phone_number_redaction():
    text = "Emergency escalation line: +1-555-839-2041 or 555-492-1092."
    sanitized = DataSanitizer.sanitize_text(text)
    assert "555-839-2041" not in sanitized
    assert "[REDACTED_PHONE]" in sanitized


def test_ip_address_redaction():
    text = "Traffic originating from proxy 192.168.1.105 and 10.0.4.22."
    sanitized = DataSanitizer.sanitize_text(text, redact_ip=True)
    assert "192.168.1.105" not in sanitized
    assert "[REDACTED_IP]" in sanitized


def test_bearer_token_and_jwt_redaction():
    raw_jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkFsaWNlIn0."
        "dozjgN_p_mX1DXrtk_s1_xK6t1q"
    )
    text = f"Header: Authorization: Bearer secret_session_token_xyz and token {raw_jwt}"
    sanitized = DataSanitizer.sanitize_text(text)
    assert "secret_session_token_xyz" not in sanitized
    assert raw_jwt not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized or "[REDACTED_JWT]" in sanitized


def test_api_key_redaction():
    text = (
        "Integration credentials: OpenAI sk-abcdef1234567890abcdef1234567890, "
        "AWS key AKIAIOSFODNN7EXAMPLE, and GitHub ghp_123456789012345678901234567890123456."
    )
    sanitized = DataSanitizer.sanitize_text(text)
    assert "sk-abcdef1234567890" not in sanitized
    assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
    assert "ghp_1234567890" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_database_url_redaction():
    text = "Failed connecting to postgresql://aegis_admin:super_secret_db_pass@db.internal.net:5432/prod_db"
    sanitized = DataSanitizer.sanitize_text(text)
    assert "super_secret_db_pass" not in sanitized
    assert "[REDACTED_DB_URL]" in sanitized


def test_key_value_credential_assignment():
    text = 'Config payload: {"api_key": "prod-secret-9988", "password": "MySuperPassword123!"}'
    sanitized = DataSanitizer.sanitize_text(text)
    assert "prod-secret-9988" not in sanitized
    assert "MySuperPassword123!" not in sanitized


def test_credit_card_redaction():
    text = "User attempted payment with card 4111-2222-3333-4444 on checkout."
    sanitized = DataSanitizer.sanitize_text(text)
    assert "4111-2222-3333-4444" not in sanitized
    assert "[REDACTED_CARD]" in sanitized


def test_recursive_dict_sanitization():
    payload = {
        "service": "billing",
        "api_key": "sk-super-secret-key",
        "nested": {
            "password": "hidden_db_password",
            "safe_value": 42,
            "user_email": "customer@service.com",
        },
        "log_messages": [
            "User email is test@domain.com",
            "Connecting to postgresql://usr:pass123@localhost/db",
        ],
    }
    sanitized = DataSanitizer.sanitize_dict(payload)
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["safe_value"] == 42
    assert "customer@service.com" not in sanitized["nested"]["user_email"]
    assert "test@domain.com" not in sanitized["log_messages"][0]
    assert "pass123" not in sanitized["log_messages"][1]
