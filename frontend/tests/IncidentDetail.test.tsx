import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import IncidentDetailPage from "@/app/incidents/[id]/page";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { api } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  api: {
    getIncident: vi.fn(),
    getIncidentTimeline: vi.fn(),
    getIncidentEvidence: vi.fn(),
    getIncidentInvestigations: vi.fn(),
    acknowledgeIncident: vi.fn(),
    triggerInvestigation: vi.fn(),
    setRole: vi.fn(),
    getRole: vi.fn(() => "OPERATOR"),
  },
}));

describe("IncidentDetail Page", () => {
  const mockIncident = {
    id: "inc-101",
    company_id: "comp-1",
    title: "Checkout API Error Spike Post-Deployment",
    description: "500 Internal Server Errors surged following release v2.4.1",
    severity: "SEV-1",
    status: "OPEN",
    category: "CHECKOUT",
    summary: "Elevated error rates on checkout and payment processing services.",
    severity_reason: "Directly degrades customer conversion and causes transaction failures.",
    affected_systems: ["checkout-api", "payment-service"],
    team_name: "Core SRE",
    fingerprint: "checkout-500-v241",
    estimated_revenue_impact: 28500,
    affected_users_count: 450,
    detected_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const mockTimeline = [
    {
      id: "tl-1",
      event_type: "DEPLOYMENT",
      source: "github-actions",
      title: "Deployed checkout-api v2.4.1",
      description: "Production release containing updated rate limiter",
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      metadata: { version: "v2.4.1" },
    },
    {
      id: "tl-2",
      event_type: "ANOMALY",
      source: "aegis-detector",
      title: "Error Rate Z-score Spike",
      description: "Error rate jumped from 0.02% to 8.4%",
      timestamp: new Date(Date.now() - 1800000).toISOString(),
      metadata: { z_score: 4.8 },
    },
  ];

  const mockEvidence = [
    {
      id: "ev-1",
      evidence_type: "METRIC_ANOMALY",
      title: "5xx Spike on /checkout",
      description: "Checkout endpoint returning HTTP 500",
      confidence: 0.95,
      raw_data: { endpoint: "/checkout", code: 500 },
      source_id: "metric-anom-1",
    },
  ];

  const mockInvestigations = [
    {
      id: "inv-999",
      incident_id: "inc-101",
      status: "COMPLETED",
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      summary: "Database connection pool exhaustion triggered by unindexed query in v2.4.1",
      root_cause: "checkout-api v2.4.1 unindexed query exhausted DB pool",
      confidence: 0.91,
      uncertainty: 0.09,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      hypotheses: [],
      recommendations: [],
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getIncident).mockResolvedValue(mockIncident as any);
    vi.mocked(api.getIncidentTimeline).mockResolvedValue(mockTimeline as any);
    vi.mocked(api.getIncidentEvidence).mockResolvedValue(mockEvidence as any);
    vi.mocked(api.getIncidentInvestigations).mockResolvedValue(mockInvestigations as any);
  });

  it("renders incident header, business blast radius, and executive summary", async () => {
    const { container } = render(
      <AuthProvider>
        <IncidentDetailPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(api.getIncident).toHaveBeenCalledWith("inc-101");
    });

    expect(container.textContent).toContain("Checkout API Error Spike Post-Deployment");
    expect(container.textContent).toContain("SEV-1");
    expect(container.textContent).toContain("checkout-api");
    expect(container.textContent).toContain("payment-service");
    expect(container.textContent).toContain("$28,500");
    expect(container.textContent).toContain("450");
    expect(container.textContent).toContain(
      "Elevated error rates on checkout and payment processing services."
    );
  });

  it("renders chronological timeline events and evidence items", async () => {
    const { container } = render(
      <AuthProvider>
        <IncidentDetailPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(api.getIncidentTimeline).toHaveBeenCalled();
    });

    // Timeline events
    expect(container.textContent).toContain("Deployed checkout-api v2.4.1");
    expect(container.textContent).toContain("Error Rate Z-score Spike");

    // Correlated evidence
    expect(container.textContent).toContain("5xx Spike on /checkout");
    expect(container.textContent).toContain("Checkout endpoint returning HTTP 500");
  });

  it("links to latest AI investigation diagnostic findings", async () => {
    const { container } = render(
      <AuthProvider>
        <IncidentDetailPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(api.getIncidentInvestigations).toHaveBeenCalled();
    });

    expect(container.textContent).toContain("AI Investigation Active");
    expect(container.textContent).toContain("Review Diagnostic Findings →");
    expect(container.textContent).toContain("checkout-api v2.4.1 unindexed query exhausted DB pool");
    expect(container.textContent).toContain("91%");
  });
});
