import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TracesPage from "@/app/traces/page";
import ServiceDependenciesPage from "@/app/systems/dependencies/page";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { api } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  api: {
    listTraces: vi.fn(),
    getSlowTraces: vi.fn(),
    getErrorTraces: vi.fn(),
    getServiceDependencies: vi.fn(),
    getServiceTraceHealth: vi.fn(),
    getRole: vi.fn(() => "OPERATOR"),
    setRole: vi.fn(),
  },
}));

describe("Distributed Traces UI Pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Trace Explorer with filters and trace rows", async () => {
    vi.mocked(api.listTraces).mockResolvedValue({
      items: [
        {
          trace_id: "4bf92f3577b34da6a3ce929d0e0e4736",
          timestamp_start: new Date().toISOString(),
          duration_ms: 320.5,
          root_service: "api-gateway",
          root_operation: "POST /checkout",
          status: "OK",
          span_count: 4,
          error_count: 0,
          services: ["api-gateway", "checkout-service"],
          environment: "production",
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });

    render(
      <AuthProvider>
        <TracesPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Distributed Tracing")).toBeTruthy();
    });

    expect(screen.getAllByText("api-gateway").length).toBeGreaterThan(0);
    expect(screen.getByText("POST /checkout")).toBeTruthy();
    expect(screen.getByText("321 ms")).toBeTruthy();
  });

  it("renders Service Dependency Map with topology nodes", async () => {
    vi.mocked(api.getServiceDependencies).mockResolvedValue({
      nodes: [
        {
          service: "api-gateway",
          request_count: 500,
          error_count: 2,
          error_rate: 0.004,
          p95_latency_ms: 120.0,
          health_status: "HEALTHY",
        },
        {
          service: "checkout-service",
          request_count: 480,
          error_count: 45,
          error_rate: 0.093,
          p95_latency_ms: 850.0,
          health_status: "DEGRADED",
        },
      ],
      edges: [
        {
          source_service: "api-gateway",
          target_service: "checkout-service",
          environment: "production",
          request_count: 480,
          error_count: 45,
          error_rate: 0.093,
          p50_latency_ms: 150.0,
          p95_latency_ms: 850.0,
          p99_latency_ms: 1200.0,
          first_seen: new Date().toISOString(),
          last_seen: new Date().toISOString(),
        },
      ],
    });

    render(
      <AuthProvider>
        <ServiceDependenciesPage />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Service Dependency Map")).toBeTruthy();
    });

    expect(screen.getAllByText("api-gateway").length).toBeGreaterThan(0);
    expect(screen.getAllByText("checkout-service").length).toBeGreaterThan(0);
    expect(screen.getByText(/Healthy/i)).toBeTruthy();
    expect(screen.getByText(/Degraded/i)).toBeTruthy();
  });
});
