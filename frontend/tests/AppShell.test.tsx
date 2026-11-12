import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api/client";

// Mock API
vi.mock("@/lib/api/client", () => ({
  api: {
    getOverview: vi.fn(),
    search: vi.fn(),
    setRole: vi.fn(),
    getRole: vi.fn(() => "OPERATOR"),
  },
}));

describe("AppShell Layout Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getOverview).mockResolvedValue({
      status: "OPERATIONAL",
      environment: "production",
      company_name: "Apex Global",
      last_updated: new Date().toISOString(),
      kpis: {
        active_incidents: 2,
        critical_incidents: 1,
        active_anomalies: 3,
        affected_systems_count: 2,
        estimated_revenue_impact: 42000,
        failed_orders_count: 14,
        api_error_rate_current: 4.8,
        checkout_failure_rate_current: 9.2,
      },
      recent_incidents: [],
      latest_investigation: null,
      key_metrics: [],
      systems_summary: [],
    });
  });

  it("renders navigation items with correct links", async () => {
    const { container } = render(
      <AppShell>
        <div>Test Child Content</div>
      </AppShell>
    );

    expect(container.textContent).toContain("Overview");
    expect(container.textContent).toContain("Incidents");
    expect(container.textContent).toContain("Investigations");
    expect(container.textContent).toContain("Analytics");
    expect(container.textContent).toContain("Systems");
    expect(container.textContent).toContain("Recommendations");
    expect(container.textContent).toContain("Audit Trail");
    expect(container.textContent).toContain("Settings");
    expect(container.textContent).toContain("Test Child Content");
  });

  it("renders active incidents indicator in TopBar", async () => {
    const { container } = render(
      <AppShell>
        <div>Content</div>
      </AppShell>
    );

    await waitFor(() => {
      expect(api.getOverview).toHaveBeenCalled();
    });

    expect(container.textContent).toContain("Aegis Operational");
    expect(container.textContent).toContain("Active Incident");
  });

  it("allows switching simulated operator roles", async () => {
    const { container } = render(
      <AppShell>
        <div>Role Gating Test</div>
      </AppShell>
    );

    // Default role is OPERATOR
    expect(container.textContent).toContain("OPERATOR");

    // Click role switcher dropdown
    const roleButton = screen.getByTitle(/Switch User Role/i);
    fireEvent.click(roleButton);

    // Select VIEWER role
    const viewerOption = screen.getByText("VIEWER");
    fireEvent.click(viewerOption);

    // Expect VIEWER to now be displayed
    expect(container.textContent).toContain("VIEWER");
  });
});
