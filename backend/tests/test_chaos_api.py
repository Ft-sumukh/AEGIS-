"""Tests for Chaos Engineering Lab and controlled fault injection."""

from starlette.testclient import TestClient

from app.chaos.engine import ChaosEngine


def test_list_chaos_scenarios(client: TestClient):
    res = client.get("/api/v1/chaos/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) >= 4
    ids = [s["id"] for s in scenarios]
    assert "LATENCY_SPIKE" in ids
    assert "ERROR_BURST" in ids
    assert "CPU_SATURATION" in ids
    assert "CANARY_MEMORY_LEAK" in ids


def test_inject_and_recover_chaos_fault(client: TestClient):
    # Operator injects fault
    headers = {"X-User-Role": "operator", "X-User-Id": "chaos-engineer"}
    res_inject = client.post(
        "/api/v1/chaos/inject",
        json={"scenario_id": "LATENCY_SPIKE"},
        headers=headers,
    )
    assert res_inject.status_code == 200
    data = res_inject.json()
    run_id = data["run_id"]
    assert run_id.startswith("CHAOS-")
    assert data["status"] == "ACTIVE_FAULT"
    assert data["scenario"]["metric_name"] == "payment_p99_latency"

    # Active simulations endpoint lists it
    res_active = client.get("/api/v1/chaos/active", headers=headers)
    assert res_active.status_code == 200
    active_runs = res_active.json()
    assert any(r["run_id"] == run_id for r in active_runs)

    # Recover fault
    res_recover = client.post(
        "/api/v1/chaos/recover",
        json={"run_id": run_id},
        headers=headers,
    )
    assert res_recover.status_code == 200
    rec_data = res_recover.json()
    assert rec_data["status"] == "RECOVERED"
    assert "recovered_at" in rec_data


def test_chaos_rbac_restriction(client: TestClient):
    # Viewer cannot inject chaos faults
    viewer_headers = {"X-User-Role": "viewer"}
    res = client.post(
        "/api/v1/chaos/inject",
        json={"scenario_id": "ERROR_BURST"},
        headers=viewer_headers,
    )
    assert res.status_code == 403
