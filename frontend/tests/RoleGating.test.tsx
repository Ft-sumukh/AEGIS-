import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import IncidentDetailPage from "@/app/incidents/[id]/page";
import { AuthProvider, useAuth } from "@/lib/auth/AuthContext";
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
  },
}));

// Helper component that allows switching role inside AuthProvider
function TestWrapper({ roleToSet }: { roleToSet: "VIEWER" | "ANALYST" | "OPERATOR" | "ADMIN" }) {
  const { setRole } = useAuth();
  React.useEffect(() => {
    setRole(roleToSet);
  }, [roleToSet, setRole]);

  return <IncidentDetailPage />;
}

describe("Role-Based Access Control (RBAC) Gating", () => {
  const mockOpenIncident = {
    id: "inc-101",
    company_id: "comp-1",
    title: "Checkout Latency Surge",
    description: "Latency above 800ms",
    severity: "SEV-2",
    status: "OPEN",
    category: "CHECKOUT",
    summary: "Elevated latency on checkout API",
    affected_systems: ["checkout-service"],
    detected_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getIncident).mockResolvedValue(mockOpenIncident as any);
    vi.mocked(api.getIncidentTimeline).mockResolvedValue([] as any);
    vi.mocked(api.getIncidentEvidence).mockResolvedValue([] as any);
    vi.mocked(api.getIncidentInvestigations).mockResolvedValue([] as any);
  });

  it("restricts VIEWER role to read-only mode without acknowledge or diagnostic actions", async () => {
    const { container } = render(
      <AuthProvider>
        <TestWrapper roleToSet="VIEWER" />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(api.getIncident).toHaveBeenCalled();
    });

    // Should display read-only indicator
    expect(container.textContent).toContain("Role: VIEWER (Read-Only)");

    // Should NOT have Acknowledge button
    expect(screen.queryByText("Acknowledge Incident")).toBeNull();
    // Should NOT have Trigger AI Diagnostic button
    expect(screen.queryByText("Trigger AI Diagnostic")).toBeNull();
  });

  it("permits ANALYST role to trigger diagnostic but not acknowledge", async () => {
    const { container } = render(
      <AuthProvider>
        <TestWrapper roleToSet="ANALYST" />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(api.getIncident).toHaveBeenCalled();
    });

    // Read-only acknowledgment note
    expect(container.textContent).toContain("Role: ANALYST (Read-Only)");

    // Can investigate
    expect(screen.getByText("Trigger AI Diagnostic")).toBeTruthy();
    // Cannot acknowledge
    expect(screen.queryByText("Acknowledge Incident")).toBeNull();
  });

  it("permits OPERATOR role to acknowledge open incidents and trigger diagnostics", async () => {
    render(
      <AuthProvider>
        <TestWrapper roleToSet="OPERATOR" />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(api.getIncident).toHaveBeenCalled();
    });

    // Operator has acknowledge button
    const ackButton = screen.getByText("Acknowledge Incident");
    expect(ackButton).toBeTruthy();

    // Operator has trigger diagnostic button
    const diagButton = screen.getByText("Trigger AI Diagnostic");
    expect(diagButton).toBeTruthy();

    // Clicking acknowledge calls API
    vi.mocked(api.acknowledgeIncident).mockResolvedValue({
      ...mockOpenIncident,
      status: "INVESTIGATING",
    } as any);

    fireEvent.click(ackButton);

    await waitFor(() => {
      expect(api.acknowledgeIncident).toHaveBeenCalledWith("inc-101", true);
    });
  });
});
