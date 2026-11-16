import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SLOsPage from "@/app/slos/page";
import { CoPilotDrawer } from "@/components/copilot/CoPilotDrawer";
import { api } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  api: {
    getSLOs: vi.fn(),
    getSLOSummary: vi.fn(),
    evaluateSLO: vi.fn(),
    createSLO: vi.fn(),
    queryCoPilot: vi.fn(),
    getOverview: vi.fn().mockResolvedValue({
      kpis: { active_incidents: 1, critical_sev1: 1 },
      services_health: [],
    }),
    setRole: vi.fn(),
    getRole: vi.fn(() => "OPERATOR"),
  },
}));

describe("SLOs & Multi-Window Error Budget UI", () => {
  const mockSLOs = [
    {
      id: "slo-1",
      company_id: "comp-1",
      name: "Checkout Service High Availability",
      service_name: "checkout-service",
      description: "Measures checkout transactions",
      target_percentage: 99.9,
      sli_metric_name: "api_error_rate",
      sli_type: "AVAILABILITY",
      time_window_days: 30,
      current_sli: 99.94,
      error_budget_remaining_percent: 88.5,
      burn_rate_1h: 1.0,
      burn_rate_6h: 1.0,
      burn_rate_24h: 1.0,
      time_to_exhaustion_hours: null,
      status: "HEALTHY",
    },
    {
      id: "slo-2",
      company_id: "comp-1",
      name: "Payment Gateway Processing Reliability",
      service_name: "payment-service",
      description: "Guarantees transaction authorizations",
      target_percentage: 99.95,
      sli_metric_name: "payment_p99_latency",
      sli_type: "LATENCY",
      time_window_days: 30,
      current_sli: 98.2,
      error_budget_remaining_percent: 18.2,
      burn_rate_1h: 16.2,
      burn_rate_6h: 12.0,
      burn_rate_24h: 6.5,
      time_to_exhaustion_hours: 4.5,
      status: "BURNING",
    },
  ];

  const mockSummary = {
    total_slos: 2,
    healthy_count: 1,
    warning_count: 0,
    burning_count: 1,
    exhausted_count: 0,
    average_error_budget_percent: 53.35,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (api.getSLOs as any).mockResolvedValue(mockSLOs);
    (api.getSLOSummary as any).mockResolvedValue(mockSummary);
  });

  it("renders SLO list and error budget indicators", async () => {
    const { container } = render(<SLOsPage />);

    await waitFor(() => {
      expect(container.textContent).toContain("SLOs & Multi-Window Error Budgets");
      expect(container.textContent).toContain("Checkout Service High Availability");
      expect(container.textContent).toContain("Payment Gateway Processing Reliability");
      expect(container.textContent).toContain("88.5%");
      expect(container.textContent).toContain("16.2x");
      expect(container.textContent).toContain("Burning Fast");
    });
  });

  it("triggers simulated error rate evaluation on-demand", async () => {
    const updatedSlo = {
      ...mockSLOs[0],
      burn_rate_1h: 18.5,
      status: "BURNING",
      error_budget_remaining_percent: 65.0,
      time_to_exhaustion_hours: 12.0,
    };
    (api.evaluateSLO as any).mockResolvedValue(updatedSlo);

    const { container } = render(<SLOsPage />);

    await waitFor(() => {
      expect(container.textContent).toContain("Simulate Spike");
    });

    const spikeBtns = screen.getAllByText("Simulate Spike");
    fireEvent.click(spikeBtns[0]);

    await waitFor(() => {
      expect(api.evaluateSLO).toHaveBeenCalledWith("slo-1", 4.8);
    });
  });
});

describe("Incident Commander AI Co-Pilot UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("opens drawer and handles conversational interaction", async () => {
    (api.queryCoPilot as any).mockResolvedValue({
      reply: "Root cause analysis indicates Postgres max connections reached.",
      type: "EXPLANATION",
      citations: ["Incident #db-01"],
      suggested_prompts: ["What runbooks should we run?"],
      timestamp: "12:00",
    });

    const { container } = render(<CoPilotDrawer />);

    // Click toggle button
    const toggleBtn = screen.getByText("SRE Co-Pilot");
    fireEvent.click(toggleBtn);

    await waitFor(() => {
      expect(container.textContent).toContain("Incident Commander AI");
      expect(container.textContent).toContain("Zero autonomous writes");
    });

    // Ask a prompt
    const input = screen.getByPlaceholderText(/Ask Commander/i);
    fireEvent.change(input, { target: { value: "Why did checkout fail?" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => {
      expect(api.queryCoPilot).toHaveBeenCalledWith("Why did checkout fail?");
      expect(container.textContent).toContain("Root cause analysis indicates Postgres max connections reached");
    });
  });
});
