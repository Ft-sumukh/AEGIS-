"""Unit tests for deterministic entity pseudonymization."""

import uuid
import pytest
from app.security.pseudonymizer import Pseudonymizer, pseudonymize_customer, pseudonymize_ticket, pseudonymize_user


def test_pseudonym_deterministic_consistency():
    p = Pseudonymizer(salt="test-salt-abc-123")
    email = "alice@example.com"
    token1 = p.pseudonymize_customer(email)
    token2 = p.pseudonymize_customer(email)
    token3 = p.pseudonymize_customer("  ALICE@EXAMPLE.COM  ")

    assert token1 == token2 == token3
    assert token1.startswith("customer_")
    assert "alice" not in token1.lower()


def test_pseudonym_distinctness():
    p = Pseudonymizer(salt="test-salt-abc-123")
    cust_a = p.pseudonymize_customer("customer_alpha@domain.com")
    cust_b = p.pseudonymize_customer("customer_beta@domain.com")

    assert cust_a != cust_b


def test_pseudonym_salt_isolation():
    p1 = Pseudonymizer(salt="salt-one")
    p2 = Pseudonymizer(salt="salt-two")
    target = "user-12345"

    assert p1.pseudonymize_user(target) != p2.pseudonymize_user(target)


def test_pseudonymize_uuid_and_edge_cases():
    test_uuid = uuid.uuid4()
    p_uuid1 = pseudonymize_customer(test_uuid)
    p_uuid2 = pseudonymize_customer(test_uuid)
    assert p_uuid1 == p_uuid2

    # None and empty handling
    p = Pseudonymizer()
    assert p.pseudonymize(None) == "entity_ANONYMOUS"
    assert p.pseudonymize("") == "entity_EMPTY"


def test_convenience_functions():
    assert pseudonymize_customer("cust1").startswith("customer_")
    assert pseudonymize_user("usr1").startswith("user_")
    assert pseudonymize_ticket("TICK-100").startswith("ticket_")
