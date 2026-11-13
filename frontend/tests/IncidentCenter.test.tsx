import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import IncidentsPage from "@/app/incidents/page";
import { api } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  api: {
    getIncidents: vi.fn(),
    setRole: vi.fn(),
    getRole: vi.fn(() => "OPERATOR"),
  },
}));

describe("IncidentCenter Page", () => {
  const mockIncidents = [
    {
      id: "inc-101",
      company_id: "comp-1",
      title: "Checkout API 500 Error Spike",
      description: "High error rates observed in checkout pipeline",
      severity: "SEV-1",
      status: "INVESTIGATING",
      category: "CHECKOUT",
      detected_at: new Date().toISOString(),
      summary: "Critical checkout degradation",
      estimated_revenue_impact: 12500,
      affected_users_count: 320,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "inc-102",
      company_id: "comp-1",
      title: "Payment Gateway Connection Timeout",
      description: "Stripe webhook timeouts",
      severity: "SEV-2",
      status: "OPEN",
      category: "PAYMENTS",
      detected_at: new Date().toISOString(),
      summary: "Payment retry queue elevated",
      estimated_revenue_impact: 4200,
      affected_users_count: 85,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getIncidents).mockResolvedValue({
      total: 2,
      page: 1,
      page_size: 20,
      items: mockIncidents as any,
    });
  });

  it("renders incident table with incident titles, severity badges, and status badges", async () => {
    const { container } = render(<IncidentsPage />);

    await waitFor(() => {
      expect(api.getIncidents).toHaveBeenCalled();
    });

    expect(container.textContent).toContain("Checkout API 500 Error Spike");
    expect(container.textContent).toContain("Payment Gateway Connection Timeout");
    expect(container.textContent).toContain("SEV-1");
    expect(container.textContent).toContain("SEV-2");
    expect(container.textContent).toContain("INVESTIGATING");
    expect(container.textContent).toContain("OPEN");
    expect(container.textContent).toContain("CHECKOUT");
    expect(container.textContent).toContain("PAYMENTS");
  });

  it("triggers API query when severity filter changes", async () => {
    render(<IncidentsPage />);

    await waitFor(() => {
      expect(api.getIncidents).toHaveBeenCalledTimes(1);
    });

    const severitySelect = screen.getByDisplayValue("All Severities");
    fireEvent.change(severitySelect, { target: { value: "CRITICAL" } });

    await waitFor(() => {
      expect(api.getIncidents).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: "CRITICAL",
        })
      );
    });
  });

  it("triggers API query when text search is submitted", async () => {
    render(<IncidentsPage />);

    await waitFor(() => {
      expect(api.getIncidents).toHaveBeenCalledTimes(1);
    });

    const searchInput = screen.getByPlaceholderText(/Search incident title/i);
    fireEvent.change(searchInput, { target: { value: "Checkout" } });

    fireEvent.submit(searchInput.closest("form")!);

    await waitFor(() => {
      expect(api.getIncidents).toHaveBeenCalledWith(
        expect.objectContaining({
          search: "Checkout",
        })
      );
    });
  });
});
