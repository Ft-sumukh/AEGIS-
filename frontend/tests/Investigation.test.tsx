import React from "react";
import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InvestigationDetailPage from "@/app/investigations/[id]/page";
import { api } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  api: {
    getInvestigation: vi.fn(),
  },
}));

describe("InvestigationDetailPage Diagnostic Findings", () => {
  const mockInvestigation = {
    id: "inv-456",
    incident_id: "inc-101",
    status: "COMPLETED",
    started_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
    summary:
      "Investigation reveals high correlation between deployment of checkout v4.8.2 and connection pool exhaustion.",
    root_cause: "checkout v4.8.2 unindexed query caused connection queue starvation",
    confidence: 0.92,
    uncertainty: 0.08,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    hypotheses: [
      {
        id: "hypo-1",
        investigation_id: "inv-456",
        title: "Connection Pool Exhaustion via Database Query Regression",
        description:
          "v4.8.2 introduced an unindexed query on the orders table causing 100% pool saturation",
        status: "SUPPORTED",
        confidence: 0.92,
        supporting_evidence_summary: "Confirmed by 100/100 active connections in pool telemetry",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: "hypo-2",
        investigation_id: "inv-456",
        title: "Third-Party Payment Gateway Outage",
        description: "Payment provider endpoint failure or upstream latency spike",
        status: "REJECTED",
        confidence: 0.12,
        supporting_evidence_summary: "Payment provider health status API returned 200 OK across period",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
    recommendations: [
      {
        id: "rec-1",
        incident_id: "inc-101",
        action_type: "ROLLBACK",
        title: "Rollback checkout-service to v4.8.1",
        description: "Reverts the unindexed query and restores database connection pool capacity",
        priority: "CRITICAL",
        risk_level: "SEV-1",
        expected_impact: "Immediate restoration of database pool capacity",
        status: "PROPOSED",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getInvestigation).mockResolvedValue(mockInvestigation as any);
  });

  it("renders diagnostic confidence and residual uncertainty meters", async () => {
    const { container } = render(<InvestigationDetailPage />);

    await waitFor(() => {
      expect(api.getInvestigation).toHaveBeenCalledWith("inc-101");
    });

    expect(container.textContent).toContain("92%");
    expect(container.textContent).toContain("8%");
    expect(container.textContent).toContain("Diagnostic Confidence");
    expect(container.textContent).toContain("Residual Uncertainty");
  });

  it("renders calibrated causality disclaimer preserving scientific rigor", async () => {
    const { container } = render(<InvestigationDetailPage />);

    await waitFor(() => {
      expect(api.getInvestigation).toHaveBeenCalled();
    });

    expect(container.textContent).toContain("Calibrated Causality Boundary");
    expect(container.textContent).toContain(
      "The deployment is temporally correlated with the service degradation"
    );
    expect(container.textContent).toContain("Causality has not been independently proven");
  });

  it("renders supported and rejected candidate hypotheses with evidence summaries", async () => {
    const { container } = render(<InvestigationDetailPage />);

    await waitFor(() => {
      expect(api.getInvestigation).toHaveBeenCalled();
    });

    expect(container.textContent).toContain(
      "Connection Pool Exhaustion via Database Query Regression"
    );
    expect(container.textContent).toContain("SUPPORTED");
    expect(container.textContent).toContain("Third-Party Payment Gateway Outage");
    expect(container.textContent).toContain("REJECTED");
    expect(container.textContent).toContain("Payment provider health status API returned 200 OK");
  });

  it("renders observed facts distinctly from AI interpretations", async () => {
    const { container } = render(<InvestigationDetailPage />);

    await waitFor(() => {
      expect(container.textContent).toContain("OBSERVED FACT");
      expect(container.textContent).toContain("AI ASSESSMENT");
      expect(container.textContent).toContain("Observed Facts");
      expect(container.textContent).toContain("Deployment of checkout-service v4.8.2 completed");
      expect(container.textContent).toContain("Identified Uncertainties & Blindspots");
    });
  });
});
