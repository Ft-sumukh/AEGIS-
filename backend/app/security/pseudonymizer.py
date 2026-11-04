"""Deterministic pseudonymization engine for entity continuity without privacy leakage."""

import hashlib
import hmac
import uuid
from typing import Any

from app.config import get_settings


class Pseudonymizer:
    """Provides deterministic HMAC-SHA256 pseudonymization for identifiable operational entities.

    Ensures that an entity (e.g. customer ID, requester email) consistently maps to
    the same anonymous token within the configured privacy salt, allowing an AI investigator
    to correlate events across multiple interactions without learning the real identity.
    """

    def __init__(self, salt: str | None = None) -> None:
        self._salt = (salt or get_settings().PRIVACY_SALT).encode("utf-8")

    def pseudonymize(
        self,
        identifier: str | uuid.UUID | Any,
        prefix: str = "entity",
        length: int = 8,
    ) -> str:
        """Generates a stable, deterministic pseudonym for an identifier."""
        if identifier is None:
            return f"{prefix}_ANONYMOUS"

        raw_str = str(identifier).strip().lower()
        if not raw_str:
            return f"{prefix}_EMPTY"

        # Compute HMAC-SHA256 with server-side privacy salt
        digest = hmac.new(self._salt, raw_str.encode("utf-8"), hashlib.sha256).hexdigest()
        token = digest[:length].upper()
        return f"{prefix}_{token}"

    def pseudonymize_customer(self, customer_id_or_email: str | uuid.UUID) -> str:
        """Specialized helper for customer entities."""
        return self.pseudonymize(customer_id_or_email, prefix="customer", length=8)

    def pseudonymize_user(self, user_id_or_username: str | uuid.UUID) -> str:
        """Specialized helper for internal user/actor identifiers."""
        return self.pseudonymize(user_id_or_username, prefix="user", length=8)

    def pseudonymize_ticket(self, ticket_id: str | uuid.UUID) -> str:
        """Specialized helper for support ticket references."""
        return self.pseudonymize(ticket_id, prefix="ticket", length=8)


# Default singleton instance
_default_pseudonymizer = Pseudonymizer()


def pseudonymize_customer(val: str | uuid.UUID) -> str:
    """Module-level convenience function for customer pseudonymization."""
    return _default_pseudonymizer.pseudonymize_customer(val)


def pseudonymize_user(val: str | uuid.UUID) -> str:
    """Module-level convenience function for user pseudonymization."""
    return _default_pseudonymizer.pseudonymize_user(val)


def pseudonymize_ticket(val: str | uuid.UUID) -> str:
    """Module-level convenience function for ticket pseudonymization."""
    return _default_pseudonymizer.pseudonymize_ticket(val)
