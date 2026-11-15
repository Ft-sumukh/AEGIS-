import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ChaosLabPage from "@/app/chaos/page";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { api } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  api: {
    listChaosScenarios: vi.fn(),
    listActiveChaosRuns: vi.fn(),
    injectChaosFault: vi.fn(),
    recoverChaosFault: vi.fn(),
    getOverview: vi.fn().mockResolvedValue({
      kpis: { active_incidents: 2, critical_sev1: 1 },
      services_health: [],
    }),
    setRole: vi.fn(),
    getRole: vi.fn(() => "OPERATOR"),
  },
}));

// Mock EventSource
class MockEventSource {
  onopen: any = null;
  onmessage: any = null;
  onerror: any = null;
  close = vi.fn();
  addEventListener = vi.fn();
}
(global as any).EventSource = MockEventSource;

describe("Chaos Engineering Lab UI", () => {
  const mockScenarios = [
    {
      id: "LATENCY_SPIKE",
      name: "Payment Gateway Upstream Throttling",
      description: "Simulates downstream processor timeout cascading into P99 latency spikes.",
      target_service: "payment-service",
      metric_name: "payment_p99_latency",
      baseline_value: 115.0,
      fault_value: 3450.0,
      unit: "ms",
      risk_level: "HIGH",
      recommended_action: "ENABLE_FEATURE_FLAG",
      action_params: {},
    },
    {
      id: "ERROR_BURST",
      name: "Order Processing Connection Pool Starvation",
      description: "Simulates database connection pool exhaustion resulting in HTTP 500 errors.",
      target_service: "order-service",
      metric_name: "order_error_rate",
      baseline_value: 0.12,
      fault_value: 44.8,
      unit: "%",
      risk_level: "CRITICAL",
      recommended_action: "RESTART_SERVICE",
      action_params: {},
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (api.listChaosScenarios as any).mockResolvedValue(mockScenarios);
    (api.listActiveChaosRuns as any).mockResolvedValue([]);
  });

  it("renders Chaos Lab header and scenario catalog cards", async () => {
    const { container } = render(
      <AuthProvider>
        <ChaosLabPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(container.textContent).toContain("Chaos Engineering Lab");
      expect(container.textContent).toContain("Payment Gateway Upstream Throttling");
      expect(container.textContent).toContain("Order Processing Connection Pool Starvation");
    });

    expect(container.textContent).toContain("SIMULATED SAFEHOUSE");
  });

  it("allows operator to trigger fault injection", async () => {
    (api.injectChaosFault as any).mockResolvedValue({
      run_id: "CHAOS-TEST1",
      scenario: mockScenarios[0],
      injected_at: new Date().toISOString(),
      injected_by: "operator",
      status: "ACTIVE_FAULT",
      metric_id: "m-123",
    });

    const { container } = render(
      <AuthProvider>
        <ChaosLabPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(container.textContent).toContain("Payment Gateway Upstream Throttling");
    });

    const injectBtns = screen.getAllByRole("button", { name: /Inject Fault/i });
    fireEvent.click(injectBtns[0]);

    await waitFor(() => {
      expect(api.injectChaosFault).toHaveBeenCalledWith("LATENCY_SPIKE");
    });
  });
});
