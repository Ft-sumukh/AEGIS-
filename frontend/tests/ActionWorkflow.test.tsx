import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ActionQueuePage from "@/app/actions/page";
import ActionDetailPage from "@/app/actions/[id]/page";
import { api } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  api: {
    getActions: vi.fn(),
    getAction: vi.fn(),
    getActionDefinitions: vi.fn(),
    submitAction: vi.fn(),
    approveAction: vi.fn(),
    rejectAction: vi.fn(),
    executeAction: vi.fn(),
    dryRunAction: vi.fn(),
    verifyAction: vi.fn(),
    getRole: vi.fn(() => "ADMIN"),
  },
}));

describe("Action Workflow and Human Approval Engine UI", () => {
  const mockActionList = [
    {
      id: "act-101",
      action_type: "ROLLBACK_DEPLOYMENT",
      target_service: "checkout-service",
      status: "PENDING_APPROVAL",
      risk_level: "HIGH",
      title: "Rollback checkout-service to v1.2.0",
      description: "Revert broken release v1.2.1 causing 500 error spike",
      parameters: { service_name: "checkout-service", target_version: "v1.2.0" },
      fingerprint: "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
      is_reversible: true,
      requires_approval: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "act-102",
      action_type: "CLEAR_CACHE",
      target_service: "cache-redis",
      status: "VERIFIED",
      risk_level: "LOW",
      title: "Clear Redis inventory cache",
      description: "Purge stale cache keys",
      parameters: { service_name: "cache-redis", key_pattern: "inv:*" },
      fingerprint: "f1e2d3c4b5a67890abcdef1234567890abcdef1234567890abcdef1234567890",
      is_reversible: false,
      requires_approval: false,
      verification_outcome: "VERIFIED_SUCCESS",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  const mockDefinitions = [
    {
      action_type: "ROLLBACK_DEPLOYMENT",
      name: "Rollback Deployment",
      description: "Roll back target service to previous stable release",
      risk_level: "HIGH",
      required_role: "OPERATOR",
      requires_approval: true,
      preconditions: ["Deployment exists", "Target version stable"],
      potential_downside: "Transient dropped keepalives",
      expected_outcome: "500 error rate recovers",
    },
    {
      action_type: "RESTART_SERVICE",
      name: "Restart Service",
      description: "Perform graceful rolling restart of microservice pods",
      risk_level: "MEDIUM",
      required_role: "OPERATOR",
      requires_approval: true,
      preconditions: ["Service responds to health probes"],
      potential_downside: "Brief pod restart delay",
      expected_outcome: "Hung threads cleared",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getActions).mockResolvedValue({
      total: 2,
      page: 1,
      page_size: 100,
      items: mockActionList as any,
    });
    vi.mocked(api.getActionDefinitions).mockResolvedValue(mockDefinitions as any);
  });

  it("renders Action Queue page with KPIs, action records, risk badges, and catalog toggle", async () => {
    render(<ActionQueuePage />);

    // Check header and KPI counters
    await waitFor(() => {
      expect(screen.getByText("Operational Action Queue")).toBeDefined();
      expect(screen.getByText("Pending Human Approval")).toBeDefined();
    });

    // Check actions rendered in table
    expect(screen.getByText("Rollback checkout-service to v1.2.0")).toBeDefined();
    expect(screen.getByText("Clear Redis inventory cache")).toBeDefined();
    expect(screen.getByText("checkout-service")).toBeDefined();

    // Toggle catalog drawer
    const catalogBtn = screen.getByText(/Action Catalog/i);
    fireEvent.click(catalogBtn);

    await waitFor(() => {
      expect(screen.getByText(/Registered Operational Capabilities/i)).toBeDefined();
      expect(screen.getByText("Rollback Deployment")).toBeDefined();
      expect(screen.getByText("Restart Service")).toBeDefined();
    });
  });

  it("renders Action Detail page with 7-step stepper, fingerprint, and parameters", async () => {
    vi.mocked(api.getAction).mockResolvedValue(mockActionList[0] as any);

    render(<ActionDetailPage params={Promise.resolve({ id: "act-101" })} />);

    await waitFor(() => {
      expect(screen.getByText("Rollback checkout-service to v1.2.0")).toBeDefined();
    });

    // Verify 7-step progression indicators
    expect(screen.getByText("Proposed")).toBeDefined();
    expect(screen.getByText("Awaiting Approval")).toBeDefined();
    expect(screen.getByText("Approved")).toBeDefined();
    expect(screen.getByText("Executing")).toBeDefined();
    expect(screen.getByText("Executed")).toBeDefined();
    expect(screen.getByText("Verifying")).toBeDefined();
    expect(screen.getByText("Verified")).toBeDefined();

    // Verify SHA-256 fingerprint displayed
    expect(screen.getByText(/Cryptographic Fingerprint/i)).toBeDefined();
    expect(screen.getByText("a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890")).toBeDefined();

    // Verify parameters inspected
    expect(screen.getByText(/target_version/i)).toBeDefined();
  });

  it("requires typed confirmation phrase for HIGH risk human approval and submits", async () => {
    vi.mocked(api.getAction).mockResolvedValue(mockActionList[0] as any);
    vi.mocked(api.approveAction).mockResolvedValue({
      ...mockActionList[0],
      status: "APPROVED",
    } as any);

    render(<ActionDetailPage params={Promise.resolve({ id: "act-101" })} />);

    await waitFor(() => {
      expect(screen.getByText("Human Authorization Required")).toBeDefined();
    });

    // Verify confirmation phrase required
    const expectedPhrase = "APPROVE ROLLBACK DEPLOYMENT";
    expect(screen.getByText(expectedPhrase)).toBeDefined();

    const approveButton = screen.getByRole("button", { name: /Grant Human Authorization/i });
    expect(approveButton).toHaveProperty("disabled", true);

    // Type the confirmation phrase and reason
    const phraseInput = screen.getByPlaceholderText(`Type '${expectedPhrase}' to authorize...`);
    const reasonInput = screen.getByPlaceholderText(/Authorized following incident triage/i);

    fireEvent.change(phraseInput, { target: { value: expectedPhrase } });
    fireEvent.change(reasonInput, { target: { value: "Approved by On-Call Lead for incident resolution" } });

    expect(approveButton).toHaveProperty("disabled", false);

    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(api.approveAction).toHaveBeenCalledWith("act-101", {
        decision: "APPROVED",
        reason: "Approved by On-Call Lead for incident resolution",
        confirmation_phrase: expectedPhrase,
      });
    });
  });

  it("supports dry-run execution toggle and verified telemetry display", async () => {
    const verifiedAction = {
      ...mockActionList[0],
      status: "VERIFIED",
      verification_status: "VERIFIED_SUCCESS",
      verification_result: {
        outcome: "VERIFIED_SUCCESS",
        summary: "Operational metric recovery verified across all indicators.",
        target_service: "checkout-service",
        action_type: "ROLLBACK_DEPLOYMENT",
        verified_at: new Date().toISOString(),
        metrics_before: {
          error_rate: "18.2%",
          latency_p95: "850ms",
        },
        metrics_after: {
          error_rate: "0.4%",
          latency_p95: "115ms",
        },
        signals_verified: 2,
        signals_failed: 0,
        details: [
          "5xx error rate normalized to baseline threshold (<1%)",
          "p95 latency reduced from 850ms to 115ms",
        ],
      },
    };

    vi.mocked(api.getAction).mockResolvedValue(verifiedAction as any);

    render(<ActionDetailPage params={Promise.resolve({ id: "act-101" })} />);

    await waitFor(() => {
      expect(screen.getByText("Post-Action Metric Verification")).toBeDefined();
    });

    // Check verification summary and recovery metrics
    expect(screen.getByText("Operational metric recovery verified across all indicators.")).toBeDefined();
    expect(screen.getByText("2 Passed / 0 Failed")).toBeDefined();
    expect(screen.getByText("18.2%")).toBeDefined();
    expect(screen.getByText("0.4%")).toBeDefined();
    expect(screen.getByText("5xx error rate normalized to baseline threshold (<1%)")).toBeDefined();
  });
});
