import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import DashboardPage from "@/app/dashboard/page";
import IncidentDetailPage from "@/app/incidents/[id]/page";
import InvestigationDetailPage from "@/app/investigations/[id]/page";
import RecommendationsPage from "@/app/recommendations/page";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { api } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  api: {
    getOverview: vi.fn(),
    getIncident: vi.fn(),
    getIncidentTimeline: vi.fn(),
    getIncidentEvidence: vi.fn(),
    getIncidentInvestigations: vi.fn(),
    getInvestigation: vi.fn(),
    getRecommendations: vi.fn(),
    setRole: vi.fn(),
    getRole: vi.fn(() => "OPERATOR"),
  },
}));

describe("End-to-End Operator Workflow Story", () => {
  const mockOverviewData = {
    status: "CRITICAL",
    environment: "production",
    company_name: "Apex Global Commerce",
    last_updated: new Date().toISOString(),
    kpis: {
      active_incidents: 1,
      critical_incidents: 1,
      active_anomalies: 4,
      affected_systems_count: 3,
      estimated_revenue_impact: 38400,
      failed_orders_count: 154,
      api_error_rate_current: 18.5,
      checkout_failure_rate_current: 42.8,
    },
    recent_incidents: [
      {
        id: "inc-101",
        company_id: "comp-1",
        title: "Checkout API 500 Outage Following v4.8.2 Deployment",
        description: "Surge in HTTP 500 errors across checkout and payment gateways",
        severity: "CRITICAL",
        status: "INVESTIGATING",
        category: "CHECKOUT",
        summary: "Checkout failure rate spiked to 42.8% immediately following deployment of v4.8.2",
        affected_systems: ["checkout-service", "payment-service"],
        estimated_revenue_impact: 38400,
        estimated_orders_affected: 154,
        detected_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
    latest_investigation: {
      id: "inv-999",
      incident_id: "inc-101",
      status: "COMPLETED",
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      summary: "Database connection pool exhaustion caused by unindexed query",
      root_cause: "v4.8.2 migration omitted index on active_sessions table",
      confidence: 0.94,
      uncertainty: 0.06,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      hypotheses: [
        {
          id: "h-1",
          investigation_id: "inv-999",
          title: "Connection Pool Exhaustion via Unindexed Query",
          description: "Database locks accumulated leading to 100/100 connections acquired",
          status: "SUPPORTED",
          confidence: 0.94,
          supporting_evidence_summary: "Confirmed by database connection pool metrics",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      recommendations: [],
    },
    key_metrics: [],
    systems_summary: [
      {
        name: "checkout-service",
        category: "API",
        status: "CRITICAL",
        latency_ms: 820,
        error_rate: 18.5,
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("Step 1: Operator opens Overview and sees critical incident alert, revenue impact, and telemetry", async () => {
    vi.mocked(api.getOverview).mockResolvedValue(mockOverviewData as any);

    const { container } = render(<DashboardPage />);

    await waitFor(() => {
      expect(api.getOverview).toHaveBeenCalled();
    });

    // Verify KPIs
    expect(container.textContent).toContain("Apex Global Commerce");
    expect(container.textContent).toContain("38,400");
    expect(container.textContent).toContain("42.8%");

    // Verify Critical Active Incident Alert Banner
    expect(container.textContent).toContain("Checkout API 500 Outage Following v4.8.2 Deployment");
    expect(container.textContent).toContain("checkout-service");
  });

  it("Step 2: Operator inspects Incident Detail, blast radius, timeline, and correlated evidence", async () => {
    vi.mocked(api.getIncident).mockResolvedValue(mockOverviewData.recent_incidents[0] as any);
    vi.mocked(api.getIncidentTimeline).mockResolvedValue([
      {
        id: "tl-1",
        event_type: "DEPLOYMENT",
        source: "github-actions",
        title: "checkout-service v4.8.2 Deployed",
        description: "Release triggered by CI pipeline",
        timestamp: new Date().toISOString(),
      },
    ] as any);
    vi.mocked(api.getIncidentEvidence).mockResolvedValue([
      {
        id: "ev-1",
        evidence_type: "ANOMALY",
        title: "HTTP 500 Spike on /checkout",
        description: "Z-score 4.8 above normal baseline",
        confidence: 0.98,
        source_id: "anom-1",
      },
    ] as any);
    vi.mocked(api.getIncidentInvestigations).mockResolvedValue([
      mockOverviewData.latest_investigation as any,
    ]);

    const { container } = render(
      <AuthProvider>
        <IncidentDetailPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(api.getIncident).toHaveBeenCalled();
    });

    expect(container.textContent).toContain("checkout-service v4.8.2 Deployed");
    expect(container.textContent).toContain("HTTP 500 Spike on /checkout");
    expect(container.textContent).toContain("Connection Pool Exhaustion via Unindexed Query");
  });

  it("Step 3: Operator reviews AI Investigation with calibrated causality and hypotheses", async () => {
    vi.mocked(api.getInvestigation).mockResolvedValue(mockOverviewData.latest_investigation as any);

    const { container } = render(<InvestigationDetailPage />);

    await waitFor(() => {
      expect(api.getInvestigation).toHaveBeenCalled();
    });

    // Calibrated probabilistic language
    expect(container.textContent).toContain("Calibrated Causality Boundary");
    expect(container.textContent).toContain("Causality has not been independently proven");

    // Hypotheses
    expect(container.textContent).toContain("Connection Pool Exhaustion via Unindexed Query");
    expect(container.textContent).toContain("SUPPORTED");
    expect(container.textContent).toContain("94%");
  });

  it("Step 4: Operator views Recommendations queue and confirms advisory-only disclaimer", async () => {
    vi.mocked(api.getRecommendations).mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 15,
      items: [
        {
          id: "rec-1",
          incident_id: "inc-101",
          action_type: "ROLLBACK_DEPLOYMENT",
          title: "Rollback checkout-service to v4.8.1",
          description: "Immediately restores previous stable image and relieves database queue",
          priority: "CRITICAL",
          risk_level: "SEV-1",
          expected_impact: "Restores checkout throughput within 2 minutes",
          status: "PROPOSED",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ] as any,
    });

    const { container } = render(<RecommendationsPage />);

    await waitFor(() => {
      expect(api.getRecommendations).toHaveBeenCalled();
    });

    // Scope boundary check
    expect(container.textContent).toContain("ADVISORY MODE ONLY — ACTION EXECUTION ENGINE (GROUP 9)");
    expect(container.textContent).toContain("Rollback checkout-service to v4.8.1");
    expect(container.textContent).toContain("CRITICAL");
    expect(container.textContent).toContain("PROPOSED");
  });
});
