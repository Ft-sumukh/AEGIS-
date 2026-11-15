"""Tests for SRE Runbooks and Operational Playbooks API."""

from starlette.testclient import TestClient

from app.runbooks.service import RunbookService


def test_list_runbooks(client: TestClient):
    res = client.get("/api/v1/runbooks")
    assert res.status_code == 200
    rbs = res.json()
    assert len(rbs) >= 4
    ids = [rb["id"] for rb in rbs]
    assert "RB-PAYMENT-01" in ids
    assert "RB-DATABASE-02" in ids


def test_get_runbook_detail(client: TestClient):
    res = client.get("/api/v1/runbooks/RB-PAYMENT-01")
    assert res.status_code == 200
    rb = res.json()
    assert rb["id"] == "RB-PAYMENT-01"
    assert "diagnostic_steps" in rb
    assert "recommended_actions" in rb
    assert len(rb["recommended_actions"]) >= 1


def test_get_nonexistent_runbook(client: TestClient):
    res = client.get("/api/v1/runbooks/RB-UNKNOWN-99")
    assert res.status_code == 404
