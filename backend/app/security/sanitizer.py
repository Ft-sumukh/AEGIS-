"""Sensitive data detection and redaction engine for Aegis operational data and logs."""

import re
from typing import Any

# ==============================================================================
# Regex Patterns for Common Sensitive Data Categories
# ==============================================================================

# Email addresses
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# International & National Phone Numbers (e.g., +1-555-123-4567, (555) 123-4567, +919876543210)
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)

# IPv4 Addresses (excluding loopback 127.0.0.1 if desired, but redacting generic public/private IPs)
IPV4_REGEX = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)

# JWT Tokens: Three base64url segments separated by dots
JWT_REGEX = re.compile(
    r"\beyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+\b"
)

# Bearer Authorization headers / tokens
BEARER_REGEX = re.compile(
    r"(Bearer\s+)[A-Za-z0-9_\-\.]+",
    re.IGNORECASE,
)

# Standard API Keys
# OpenAI (sk-...), AWS Access Key (AKIA...), GitHub (ghp_...), Slack (xoxb-...)
API_KEY_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
]

# Database Connection URLs with embedded credentials (postgres://user:pass@host/db)
DB_URL_REGEX = re.compile(
    r"(?:postgres(?:ql)?|mysql|sqlite|mongodb(?:\+srv)?):\/\/[^\s@]+:[^\s@]+@[^\s/:]+(?::\d+)?\/[^\s?#]+",
    re.IGNORECASE,
)

# Key-Value Credentials in Text (e.g. password=xyz, api_key: "abc")
KV_CREDENTIAL_REGEX = re.compile(
    r'(["\']?(?:password|passwd|pwd|token|api_key|secret|authorization|auth_token|client_secret)["\']?\s*[:=]\s*["\']?)([^"\'\s,;}{]+)(["\']?)',
    re.IGNORECASE,
)

# Generic Credit / Debit Card-like Numbers (13-16 digits with optional dashes/spaces)
CREDIT_CARD_REGEX = re.compile(
    r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,16}\b"
)

# Private Key Blocks
PRIVATE_KEY_REGEX = re.compile(
    r"-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----",
    re.IGNORECASE,
)

# Sensitive dictionary keys that should always be masked structurally
SENSITIVE_DICT_KEYS = {
    "password",
    "passwd",
    "pwd",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "secret",
    "client_secret",
    "authorization",
    "auth",
    "private_key",
    "card_number",
    "credit_card",
    "cvv",
    "ssn",
}


class SensitiveDataDetector:
    """Detects presence of sensitive information categories in raw text."""

    @classmethod
    def detect_types(cls, text: str) -> list[str]:
        """Returns list of detected sensitive data category names found in text."""
        if not text:
            return []

        detected = []
        if PRIVATE_KEY_REGEX.search(text):
            detected.append("PRIVATE_KEY")
        if JWT_REGEX.search(text):
            detected.append("JWT_TOKEN")
        if BEARER_REGEX.search(text):
            detected.append("BEARER_TOKEN")
        for pat in API_KEY_PATTERNS:
            if pat.search(text):
                detected.append("API_KEY")
                break
        if DB_URL_REGEX.search(text):
            detected.append("DATABASE_URL")
        if KV_CREDENTIAL_REGEX.search(text):
            detected.append("CREDENTIAL_ASSIGNMENT")
        if EMAIL_REGEX.search(text):
            detected.append("EMAIL")
        if PHONE_REGEX.search(text):
            detected.append("PHONE")
        if CREDIT_CARD_REGEX.search(text):
            # Verify potential card is not a simple short integer or timestamp
            matches = CREDIT_CARD_REGEX.findall(text)
            for m in matches:
                clean_m = re.sub(r"[\s-]", "", m)
                if len(clean_m) in (13, 15, 16):
                    detected.append("CREDIT_CARD")
                    break
        return detected

    @classmethod
    def contains_sensitive_data(cls, text: str) -> bool:
        """Boolean check whether text contains any sensitive information."""
        return len(cls.detect_types(text)) > 0


class DataSanitizer:
    """Sanitizes text and structured payloads by replacing sensitive values with redaction tags."""

    @classmethod
    def sanitize_text(cls, text: str, redact_ip: bool = False) -> str:
        """Scans and redacts sensitive patterns in raw text."""
        if not text or not isinstance(text, str):
            return text

        # 1. Private keys
        text = PRIVATE_KEY_REGEX.sub("[REDACTED_PRIVATE_KEY]", text)

        # 2. Database connection URLs with passwords
        text = DB_URL_REGEX.sub("[REDACTED_DB_URL]", text)

        # 3. Bearer authorization tokens (e.g. Authorization: Bearer abc or Bearer abc)
        auth_bearer_regex = re.compile(
            r"(Authorization\s*:\s*)?Bearer\s+[A-Za-z0-9_\-\.]+",
            re.IGNORECASE,
        )
        def _bearer_replacer(m: re.Match) -> str:
            prefix = m.group(1) or ""
            return f"{prefix}[REDACTED_TOKEN]"
        text = auth_bearer_regex.sub(_bearer_replacer, text)

        # 4. JWT tokens
        text = JWT_REGEX.sub("[REDACTED_JWT]", text)

        # 5. Explicit Key-Value credentials (e.g. password=..., api_key="...")
        def _kv_replacer(match: re.Match) -> str:
            prefix = match.group(1)
            suffix = match.group(3) or ""
            return f"{prefix}[REDACTED]{suffix}"

        text = KV_CREDENTIAL_REGEX.sub(_kv_replacer, text)

        # 6. Explicit API Key formats
        for pat in API_KEY_PATTERNS:
            text = pat.sub("[REDACTED_API_KEY]", text)

        # 7. Credit Cards (Luhn or 13-16 digit patterns)
        for match in CREDIT_CARD_REGEX.finditer(text):
            val = match.group(0)
            clean_digits = re.sub(r"[\s-]", "", val)
            if len(clean_digits) in (13, 15, 16):
                text = text.replace(val, "[REDACTED_CARD]")

        # 8. Emails
        text = EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)

        # 9. Phone numbers
        text = PHONE_REGEX.sub("[REDACTED_PHONE]", text)

        # 10. IP addresses (optional if required by strict policy)
        if redact_ip:
            text = IPV4_REGEX.sub("[REDACTED_IP]", text)

        return text

    @classmethod
    def sanitize_dict(cls, data: dict[str, Any], redact_ip: bool = False) -> dict[str, Any]:
        """Recursively sanitizes dictionary keys and values."""
        if not isinstance(data, dict):
            return data

        sanitized: dict[str, Any] = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if any(sensitive_key in key_lower for sensitive_key in SENSITIVE_DICT_KEYS):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, str):
                sanitized[k] = cls.sanitize_text(v, redact_ip=redact_ip)
            elif isinstance(v, dict):
                sanitized[k] = cls.sanitize_dict(v, redact_ip=redact_ip)
            elif isinstance(v, list):
                sanitized[k] = cls.sanitize_list(v, redact_ip=redact_ip)
            else:
                sanitized[k] = v
        return sanitized

    @classmethod
    def sanitize_list(cls, items: list[Any], redact_ip: bool = False) -> list[Any]:
        """Recursively sanitizes items in a list."""
        if not isinstance(items, list):
            return items

        sanitized: list[Any] = []
        for item in items:
            if isinstance(item, str):
                sanitized.append(cls.sanitize_text(item, redact_ip=redact_ip))
            elif isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item, redact_ip=redact_ip))
            elif isinstance(item, list):
                sanitized.append(cls.sanitize_list(item, redact_ip=redact_ip))
            else:
                sanitized.append(item)
        return sanitized

    @classmethod
    def sanitize_value(cls, value: Any, redact_ip: bool = False) -> Any:
        """Sanitizes any arbitrary value (string, dict, list, primitive)."""
        if isinstance(value, str):
            return cls.sanitize_text(value, redact_ip=redact_ip)
        elif isinstance(value, dict):
            return cls.sanitize_dict(value, redact_ip=redact_ip)
        elif isinstance(value, list):
            return cls.sanitize_list(value, redact_ip=redact_ip)
        return value
