/**
 * Aegis Centralized Typed Frontend API Client
 * Connects Next.js console components to FastAPI backend with role-aware headers.
 */

import {
  ActionDefinition,
  ActionExecutionResult,
  ActionItem,
  Anomaly,
  AnomalySummary,
  AuditEvent,
  GlobalSearchResponse,
  Incident,
  IncidentDetail,
  IncidentEvidence,
  Investigation,
  OperationalMetric,
  OverviewData,
  PaginatedResponse,
  Recommendation,
  SettingsData,
  SystemDetail,
  SystemHealth,
  TimelineEvent,
  UserRole,
  VerificationResult,
  TraceSummaryItem,
  TraceTreeResponse,
  ServiceDependencyGraphResponse,
  ServiceTraceHealthResponse,
  CorrelatedTraceEvidence,
  PostMortem,
  ChaosScenario,
  ChaosRun,
  Runbook,
  ServiceLevelObjective,
  SLOSummary,
  CoPilotResponse,
  WebhookSubscription,
} from "./types";


export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

class ApiClient {
  private baseUrl: string;
  private currentRole: UserRole = "OPERATOR";
  private actorId: string = "operator_ui";

  constructor() {
    this.baseUrl =
      process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";
  }

  public setRole(role: UserRole, actorId: string = "operator_ui") {
    this.currentRole = role;
    this.actorId = actorId;
  }

  public getRole(): UserRole {
    return this.currentRole;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

    const headers = new Headers(options.headers || {});
    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }
    if (!headers.has("Content-Type") && options.body) {
      headers.set("Content-Type", "application/json");
    }
    // Forward RBAC simulation headers
    headers.set("X-User-Role", this.currentRole);
    headers.set("X-Actor-Id", this.actorId);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        cache: "no-store",
      });

      if (!response.ok) {
        let errorData: unknown;
        try {
          errorData = await response.json();
        } catch {
          errorData = await response.text();
        }
        throw new ApiError(
          response.status,
          response.statusText,
          `API request failed: ${response.status} ${response.statusText}`,
          errorData
        );
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        throw err;
      }
      throw new ApiError(
        0,
        "NetworkError",
        err instanceof Error ? err.message : "Network error communicating with backend"
      );
    }
  }

  // 1. Health & Status
  async getHealth() {
    return this.request<{ status: string; service: string }>("/api/v1/health");
  }

  async getReadiness() {
    return this.request<{ status: string; database: string }>("/api/v1/health/ready");
  }

  // 2. Overview
  async getOverview(companyId?: string): Promise<OverviewData> {
    const query = companyId ? `?company_id=${companyId}` : "";
    return this.request<OverviewData>(`/api/v1/overview${query}`);
  }

  // 3. Incidents
  async getIncidents(params?: {
    severity?: string;
    status?: string;
    category?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<Incident>> {
    const sp = new URLSearchParams();
    if (params?.severity) sp.set("severity", params.severity);
    if (params?.status) sp.set("status", params.status);
    if (params?.category) sp.set("category", params.category);
    if (params?.search) sp.set("search", params.search);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));

    const qs = sp.toString();
    return this.request<PaginatedResponse<Incident>>(`/api/v1/incidents${qs ? `?${qs}` : ""}`);
  }

  async getIncident(id: string): Promise<IncidentDetail> {
    return this.request<IncidentDetail>(`/api/v1/incidents/${id}`);
  }

  async acknowledgeIncident(id: string, transitionToInvestigating: boolean = true): Promise<IncidentDetail> {
    return this.request<IncidentDetail>(`/api/v1/incidents/${id}/acknowledge`, {
      method: "POST",
      body: JSON.stringify({ transition_to_investigating: transitionToInvestigating }),
    });
  }

  async getIncidentTimeline(id: string, ascending: boolean = true): Promise<TimelineEvent[]> {
    return this.request<TimelineEvent[]>(
      `/api/v1/incidents/${id}/timeline?ascending=${ascending}&include_adjacent=true`
    );
  }

  async getIncidentEvidence(id: string): Promise<IncidentEvidence[]> {
    return this.request<IncidentEvidence[]>(`/api/v1/incidents/${id}/evidence`);
  }

  // 4. Investigations
  async triggerInvestigation(incidentId: string): Promise<Investigation> {
    return this.request<Investigation>(`/api/v1/incidents/${incidentId}/investigate`, {
      method: "POST",
    });
  }

  async getInvestigations(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<Investigation>> {
    const sp = new URLSearchParams();
    if (params?.status) sp.set("status", params.status);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));

    const qs = sp.toString();
    return this.request<PaginatedResponse<Investigation>>(
      `/api/v1/investigations${qs ? `?${qs}` : ""}`
    );
  }

  async getIncidentInvestigations(incidentId: string): Promise<Investigation[]> {
    return this.request<Investigation[]>(`/api/v1/incidents/${incidentId}/investigations`);
  }

  async getInvestigation(id: string): Promise<Investigation> {
    return this.request<Investigation>(`/api/v1/investigations/${id}`);
  }

  // 5. Recommendations
  async getRecommendations(params?: {
    incident_id?: string;
    status?: string;
    priority?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<Recommendation>> {
    const sp = new URLSearchParams();
    if (params?.incident_id) sp.set("incident_id", params.incident_id);
    if (params?.status) sp.set("status", params.status);
    if (params?.priority) sp.set("priority", params.priority);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));

    const qs = sp.toString();
    return this.request<PaginatedResponse<Recommendation>>(
      `/api/v1/recommendations${qs ? `?${qs}` : ""}`
    );
  }

  // 6. Systems
  async getSystems(): Promise<SystemHealth[]> {
    return this.request<SystemHealth[]>("/api/v1/systems");
  }

  async getSystem(name: string): Promise<SystemDetail> {
    return this.request<SystemDetail>(`/api/v1/systems/${name}`);
  }

  // 7. Telemetry & Analytics
  async getMetrics(params?: {
    metric_name?: string;
    start_time?: string;
    end_time?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<OperationalMetric>> {
    const sp = new URLSearchParams();
    if (params?.metric_name) sp.set("metric_name", params.metric_name);
    if (params?.start_time) sp.set("start_time", params.start_time);
    if (params?.end_time) sp.set("end_time", params.end_time);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));

    const qs = sp.toString();
    return this.request<PaginatedResponse<OperationalMetric>>(`/api/v1/metrics${qs ? `?${qs}` : ""}`);
  }

  async getAnomalies(params?: {
    severity?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<Anomaly>> {
    const sp = new URLSearchParams();
    if (params?.severity) sp.set("severity", params.severity);
    if (params?.status) sp.set("status", params.status);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));

    const qs = sp.toString();
    return this.request<PaginatedResponse<Anomaly>>(`/api/v1/anomalies${qs ? `?${qs}` : ""}`);
  }

  async getAnomalySummary(companyId?: string): Promise<AnomalySummary> {
    const query = companyId ? `?company_id=${companyId}` : "";
    return this.request<AnomalySummary>(`/api/v1/anomalies/summary${query}`);
  }

  async getIncidentCandidates(companyId?: string): Promise<unknown[]> {
    const query = companyId ? `?company_id=${companyId}` : "";
    return this.request<unknown[]>(`/api/v1/incident-candidates${query}`);
  }

  async triggerAnalyticsRun(payload: {
    company_id?: string;
    metric_filter?: string[];
  }): Promise<unknown> {
    return this.request<unknown>("/api/v1/analytics/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  // 8. Audit
  async getAuditLogs(params?: {
    action?: string;
    actor_id?: string;
    resource_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<AuditEvent>> {
    const sp = new URLSearchParams();
    if (params?.action) sp.set("action", params.action);
    if (params?.actor_id) sp.set("actor_id", params.actor_id);
    if (params?.resource_type) sp.set("resource_type", params.resource_type);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));

    const qs = sp.toString();
    return this.request<PaginatedResponse<AuditEvent>>(`/api/v1/audit${qs ? `?${qs}` : ""}`);
  }

  // 9. Settings
  async getSettings(): Promise<SettingsData> {
    return this.request<SettingsData>("/api/v1/settings");
  }

  // 10. Search
  async search(query: string): Promise<GlobalSearchResponse> {
    return this.request<GlobalSearchResponse>(`/api/v1/search?q=${encodeURIComponent(query)}`);
  }

  // 11. Operational Actions & Human Approval Engine (Group 9)
  async getActionDefinitions(): Promise<ActionDefinition[]> {
    return this.request<ActionDefinition[]>("/api/v1/actions/registry/definitions");
  }

  async getActions(params?: {
    incident_id?: string;
    status?: string;
    risk_level?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<ActionItem>> {
    const sp = new URLSearchParams();
    if (params?.incident_id) sp.set("incident_id", params.incident_id);
    if (params?.status) sp.set("status", params.status);
    if (params?.risk_level) sp.set("risk_level", params.risk_level);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));

    const qs = sp.toString();
    return this.request<PaginatedResponse<ActionItem>>(`/api/v1/actions${qs ? `?${qs}` : ""}`);
  }

  async getAction(actionId: string): Promise<ActionItem> {
    return this.request<ActionItem>(`/api/v1/actions/${actionId}`);
  }

  async proposeAction(
    incidentId: string,
    payload: {
      recommendation_id: string;
      title?: string;
      action_type: string;
      description?: string;
      risk_level?: string;
      target_service?: string;
      parameters: Record<string, unknown>;
      idempotency_key?: string;
    }
  ): Promise<ActionItem> {
    return this.request<ActionItem>(`/api/v1/actions/incidents/${incidentId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async submitAction(actionId: string, notes?: string): Promise<ActionItem> {
    return this.request<ActionItem>(`/api/v1/actions/${actionId}/submit`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    });
  }

  async approveAction(
    actionId: string,
    payload: {
      decision?: "APPROVED";
      reason?: string;
      confirmation_phrase?: string;
    }
  ): Promise<ActionItem> {
    return this.request<ActionItem>(`/api/v1/actions/${actionId}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async rejectAction(
    actionId: string,
    payload: { reason: string }
  ): Promise<ActionItem> {
    return this.request<ActionItem>(`/api/v1/actions/${actionId}/reject`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async dryRunAction(actionId: string): Promise<ActionExecutionResult> {
    return this.request<ActionExecutionResult>(`/api/v1/actions/${actionId}/dry-run`);
  }

  async executeAction(
    actionId: string,
    payload?: { dry_run?: boolean; idempotency_key?: string }
  ): Promise<ActionExecutionResult> {
    return this.request<ActionExecutionResult>(`/api/v1/actions/${actionId}/execute`, {
      method: "POST",
      body: JSON.stringify(payload || { dry_run: false }),
    });
  }

  async verifyAction(actionId: string): Promise<VerificationResult> {
    return this.request<VerificationResult>(`/api/v1/actions/${actionId}/verify`, {
      method: "POST",
    });
  }

  // ===========================================================================
  // Distributed Tracing & Service Topology Endpoints
  // ===========================================================================

  async listTraces(params?: {
    service?: string;
    environment?: string;
    status?: string;
    min_duration_ms?: number;
    start_time?: string;
    end_time?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<TraceSummaryItem>> {
    const sp = new URLSearchParams();
    if (params?.service) sp.set("service", params.service);
    if (params?.environment) sp.set("environment", params.environment);
    if (params?.status) sp.set("status", params.status);
    if (params?.min_duration_ms) sp.set("min_duration_ms", String(params.min_duration_ms));
    if (params?.start_time) sp.set("start_time", params.start_time);
    if (params?.end_time) sp.set("end_time", params.end_time);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));

    const qs = sp.toString();
    return this.request<PaginatedResponse<TraceSummaryItem>>(`/api/v1/traces${qs ? `?${qs}` : ""}`);
  }

  async getTrace(traceId: string): Promise<TraceTreeResponse> {
    return this.request<TraceTreeResponse>(`/api/v1/traces/${traceId}`);
  }

  async getTraceSpans(traceId: string): Promise<Record<string, unknown>[]> {
    return this.request<Record<string, unknown>[]>(`/api/v1/traces/${traceId}/spans`);
  }

  async getSlowTraces(params?: {
    min_duration_ms?: number;
    service?: string;
    limit?: number;
  }): Promise<TraceSummaryItem[]> {
    const sp = new URLSearchParams();
    if (params?.min_duration_ms) sp.set("min_duration_ms", String(params.min_duration_ms));
    if (params?.service) sp.set("service", params.service);
    if (params?.limit) sp.set("limit", String(params.limit));

    const qs = sp.toString();
    return this.request<TraceSummaryItem[]>(`/api/v1/traces/slow${qs ? `?${qs}` : ""}`);
  }

  async getErrorTraces(params?: {
    service?: string;
    limit?: number;
  }): Promise<TraceSummaryItem[]> {
    const sp = new URLSearchParams();
    if (params?.service) sp.set("service", params.service);
    if (params?.limit) sp.set("limit", String(params.limit));

    const qs = sp.toString();
    return this.request<TraceSummaryItem[]>(`/api/v1/traces/errors${qs ? `?${qs}` : ""}`);
  }

  async getServiceDependencies(params?: {
    environment?: string;
    time_window_hours?: number;
    service?: string;
  }): Promise<ServiceDependencyGraphResponse> {
    const sp = new URLSearchParams();
    if (params?.environment) sp.set("environment", params.environment);
    if (params?.time_window_hours) sp.set("time_window_hours", String(params.time_window_hours));
    if (params?.service) sp.set("service", params.service);

    const qs = sp.toString();
    return this.request<ServiceDependencyGraphResponse>(`/api/v1/services/dependencies${qs ? `?${qs}` : ""}`);
  }

  async getServiceTraceHealth(
    service: string,
    params?: { environment?: string; time_window_hours?: number }
  ): Promise<ServiceTraceHealthResponse> {
    const sp = new URLSearchParams();
    if (params?.environment) sp.set("environment", params.environment);
    if (params?.time_window_hours) sp.set("time_window_hours", String(params.time_window_hours));

    const qs = sp.toString();
    return this.request<ServiceTraceHealthResponse>(
      `/api/v1/services/${service}/trace-health${qs ? `?${qs}` : ""}`
    );
  }

  async getIncidentTraces(incidentId: string): Promise<CorrelatedTraceEvidence> {
    return this.request<CorrelatedTraceEvidence>(`/api/v1/incidents/${incidentId}/traces`);
  }

  async attachIncidentTraceEvidence(incidentId: string): Promise<Record<string, unknown>[]> {
    return this.request<Record<string, unknown>[]>(
      `/api/v1/incidents/${incidentId}/correlate-traces`,
      { method: "POST" }
    );
  }

  // ===========================================================================
  // AI Post-Mortem & Incident Retrospective (PIR) Endpoints
  // ===========================================================================

  async generatePostMortem(incidentId: string): Promise<PostMortem> {
    return this.request<PostMortem>(`/api/v1/incidents/${incidentId}/postmortem`, {
      method: "POST",
    });
  }

  async getPostMortem(incidentId: string): Promise<PostMortem> {
    return this.request<PostMortem>(`/api/v1/incidents/${incidentId}/postmortem`);
  }

  async getPostMortemMarkdown(incidentId: string): Promise<string> {
    const res = await fetch(`${this.baseUrl}/api/v1/incidents/${incidentId}/postmortem/markdown`, {
      headers: {
        "X-User-Role": this.currentRole,
        "X-Actor-Id": this.actorId,
      },
      cache: "no-store",
    });
    if (!res.ok) {
      throw new ApiError(res.status, res.statusText, "Failed to fetch postmortem markdown");
    }
    return res.text();
  }

  // ===========================================================================
  // Chaos Engineering Lab & Fault Injection Endpoints
  // ===========================================================================

  async listChaosScenarios(): Promise<ChaosScenario[]> {
    return this.request<ChaosScenario[]>("/api/v1/chaos/scenarios");
  }

  async listActiveChaosRuns(): Promise<ChaosRun[]> {
    return this.request<ChaosRun[]>("/api/v1/chaos/active");
  }

  async injectChaosFault(scenarioId: string): Promise<ChaosRun> {
    return this.request<ChaosRun>("/api/v1/chaos/inject", {
      method: "POST",
      body: JSON.stringify({ scenario_id: scenarioId }),
    });
  }

  async recoverChaosFault(runId: string): Promise<ChaosRun> {
    return this.request<ChaosRun>("/api/v1/chaos/recover", {
      method: "POST",
      body: JSON.stringify({ run_id: runId }),
    });
  }

  // ===========================================================================
  // SRE Runbooks & Playbooks Endpoints
  // ===========================================================================

  async listRunbooks(): Promise<Runbook[]> {
    return this.request<Runbook[]>("/api/v1/runbooks");
  }

  async getRunbook(runbookId: string): Promise<Runbook> {
    return this.request<Runbook>(`/api/v1/runbooks/${runbookId}`);
  }

  async matchRunbooksForIncident(incidentId: string): Promise<Runbook[]> {
    return this.request<Runbook[]>(`/api/v1/runbooks/for-incident/${incidentId}`);
  }

  // ===========================================================================
  // Service Level Objectives (SLO) & Error Budget Endpoints
  // ===========================================================================

  async getSLOs(): Promise<ServiceLevelObjective[]> {
    return this.request<ServiceLevelObjective[]>("/api/v1/slos");
  }

  async getSLOSummary(): Promise<SLOSummary> {
    return this.request<SLOSummary>("/api/v1/slos/summary");
  }

  async evaluateSLO(sloId: string, overrideRecentErrorRate?: number): Promise<ServiceLevelObjective> {
    return this.request<ServiceLevelObjective>(`/api/v1/slos/${sloId}/evaluate`, {
      method: "POST",
      body: JSON.stringify(overrideRecentErrorRate !== undefined ? { override_recent_error_rate: overrideRecentErrorRate } : {}),
    });
  }

  async createSLO(data: {
    name: string;
    service_name: string;
    description?: string;
    target_percentage: number;
    sli_metric_name: string;
    sli_type: string;
    time_window_days?: number;
  }): Promise<ServiceLevelObjective> {
    return this.request<ServiceLevelObjective>("/api/v1/slos", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // ===========================================================================
  // Incident Commander AI Co-Pilot Endpoints
  // ===========================================================================

  async queryCoPilot(message: string, incidentId?: string, contextHint?: string): Promise<CoPilotResponse> {
    return this.request<CoPilotResponse>("/api/v1/copilot/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        incident_id: incidentId || null,
        context_hint: contextHint || null,
      }),
    });
  }

  // ===========================================================================
  // External Webhook Subscriptions Endpoints
  // ===========================================================================

  async listWebhooks(): Promise<WebhookSubscription[]> {
    return this.request<WebhookSubscription[]>("/api/v1/webhooks");
  }

  async createWebhook(data: {
    name: string;
    url: string;
    secret_token?: string;
    target_type: string;
    subscribed_events?: string[];
  }): Promise<WebhookSubscription> {
    return this.request<WebhookSubscription>("/api/v1/webhooks", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async testWebhook(webhookId: string): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>(`/api/v1/webhooks/${webhookId}/test`, {
      method: "POST",
    });
  }

  async deleteWebhook(webhookId: string): Promise<{ message: string; deleted_id: string }> {
    return this.request<{ message: string; deleted_id: string }>(`/api/v1/webhooks/${webhookId}`, {
      method: "DELETE",
    });
  }
}

export const api = new ApiClient();

