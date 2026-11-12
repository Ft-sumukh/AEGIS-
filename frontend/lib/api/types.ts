/**
 * Aegis Operations Intelligence - Frontend Type Definitions
 * Strictly maps to backend Pydantic schemas and database models.
 */

export type SeverityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type IncidentStatus = "OPEN" | "INVESTIGATING" | "MITIGATED" | "RESOLVED" | "CLOSED";

export type AnomalyStatus = "NEW" | "ACKNOWLEDGED" | "CORRELATED" | "DISMISSED";

export type InvestigationStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "INSUFFICIENT_EVIDENCE";

export type HypothesisStatus = "PROPOSED" | "TESTING" | "SUPPORTED" | "REJECTED" | "INCONCLUSIVE";

export type RecommendationStatus = "PROPOSED" | "REVIEWED" | "APPROVED" | "REJECTED" | "EXECUTED";

export type TicketPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

export type UserRole = "VIEWER" | "ANALYST" | "OPERATOR" | "ADMIN";

export interface HealthStatus {
  status: string;
  service: string;
  version?: string;
  environment?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit?: number;
  offset?: number;
  page?: number;
  page_size?: number;
}

export interface Incident {
  id: string;
  company_id: string;
  title: string;
  summary: string;
  severity: SeverityLevel;
  severity_reason?: string | null;
  status: IncidentStatus;
  category: string;
  tags?: string[];
  affected_systems: string[];
  affected_metrics: string[];
  fingerprint?: string | null;
  detected_at: string;
  investigation_started_at?: string | null;
  mitigated_at?: string | null;
  resolved_at?: string | null;
  closed_at?: string | null;
  confidence?: number | null;
  estimated_revenue_impact?: number | null;
  estimated_orders_affected?: number | null;
  estimated_users_affected?: number | null;
  affected_users_count?: number | null;
  estimated_support_impact?: number | null;
  owner_id?: string | null;
  team_name?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface IncidentEvidence {
  id: string;
  incident_id: string;
  source_type: string;
  source_id: string;
  title: string;
  summary: string;
  description?: string;
  observed_at: string;
  relevance_score: number;
  confidence?: number;
  evidence_type?: string;
  evidence_metadata?: Record<string, unknown>;
  created_at: string;
}

export interface TimelineEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  title: string;
  summary: string;
  description?: string;
  source_type?: string;
  source_id?: string;
  metadata?: Record<string, unknown>;
}

export interface IncidentDetail extends Incident {
  anomalies?: Anomaly[];
  evidence?: IncidentEvidence[];
  notes?: IncidentNote[];
}

export interface IncidentNote {
  id: string;
  incident_id: string;
  actor_id: string;
  body: string;
  created_at: string;
}

export interface Anomaly {
  id: string;
  company_id: string;
  metric_id?: string | null;
  metric_name: string;
  detected_at: string;
  observed_value: number;
  expected_value?: number | null;
  deviation?: number | null;
  detector_type: string;
  severity: SeverityLevel;
  confidence: number;
  explanation: string;
  status: AnomalyStatus;
  anomaly_metadata?: Record<string, unknown>;
}

export interface AnomalySummary {
  total_anomalies: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_detector: Record<string, number>;
  top_affected_metrics: { metric_name: string; count: number }[];
}

export interface OperationalMetric {
  id: string;
  company_id: string;
  metric_name: string;
  timestamp: string;
  value: number;
  unit: string;
  source: string;
  dimension_data?: Record<string, unknown>;
  created_at?: string;
}

export interface Hypothesis {
  id: string;
  investigation_id: string;
  title: string;
  description: string;
  status: HypothesisStatus;
  confidence: number;
  supporting_evidence_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Recommendation {
  id: string;
  investigation_id: string;
  incident_id: string;
  action_type?: string;
  title: string;
  description: string;
  priority: TicketPriority;
  risk_level: SeverityLevel;
  expected_impact: string;
  status: RecommendationStatus;
  created_at: string;
  updated_at: string;
}

export interface Investigation {
  id: string;
  incident_id: string;
  status: InvestigationStatus;
  started_at: string;
  completed_at?: string | null;
  summary?: string | null;
  root_cause?: string | null;
  confidence?: number | null;
  uncertainty?: number | null;
  created_at: string;
  updated_at: string;
  hypotheses: Hypothesis[];
  recommendations: Recommendation[];
}

export interface SystemHealth {
  name: string;
  status: "HEALTHY" | "DEGRADED" | "CRITICAL";
  category: string;
  error_rate: number;
  latency_ms: number;
  active_incidents: number;
  recent_anomalies: number;
  last_deployment?: {
    version: string;
    deployed_at: string;
    status: string;
  } | null;
}

export interface SystemDetail extends SystemHealth {
  dependencies: {
    upstream: string[];
    downstream: string[];
  };
  recent_events: {
    id: string;
    event_type: string;
    severity: string;
    message: string;
    timestamp: string;
  }[];
  recent_deployments: {
    id: string;
    version: string;
    environment: string;
    status: string;
    deployed_at: string;
    deployed_by: string;
  }[];
  metrics_history: OperationalMetric[];
  related_incidents: {
    id: string;
    title: string;
    severity: string;
    status: string;
    detected_at: string;
  }[];
}

export interface AuditEvent {
  id: string;
  company_id?: string | null;
  actor_type: string;
  actor_id: string;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  timestamp: string;
  request_id?: string | null;
  audit_metadata: Record<string, unknown>;
}

export interface OverviewKpis {
  active_incidents: number;
  critical_incidents: number;
  active_anomalies: number;
  affected_systems_count: number;
  estimated_revenue_impact: number;
  failed_orders_count: number;
  api_error_rate_current: number;
  checkout_failure_rate_current: number;
}

export interface OverviewData {
  status: "OPERATIONAL" | "DEGRADED" | "CRITICAL";
  environment: string;
  company_name: string;
  last_updated: string;
  kpis: OverviewKpis;
  recent_incidents: Incident[];
  latest_investigation?: Investigation | null;
  key_metrics: OperationalMetric[];
  systems_summary: {
    name: string;
    category: string;
    status: "HEALTHY" | "DEGRADED" | "CRITICAL";
    latency_ms: number;
    error_rate: number;
  }[];
}

export interface SettingsData {
  app_name: string;
  app_version: string;
  environment: string;
  auth_enabled: boolean;
  default_role: string;
  ai_config: {
    provider: string;
    model: string;
    max_tool_calls_per_investigation: number;
    max_context_records: number;
    max_query_window_hours: number;
    max_investigation_duration_seconds: number;
  };
  data_policy: {
    mode: string;
    privacy_salt_active: boolean;
    redaction_active: boolean;
    pseudonymization_active: boolean;
    allowlisted_tools_count: number;
    arbitrary_sql_access: boolean;
  };
  retention_policy: {
    audit_log_retention_days: number;
    investigation_retention_days: number;
    operational_event_retention_days: number;
    analytics_retention_days: number;
  };
  telemetry_sources: {
    total_telemetry_records: number;
    active_sources: string[];
    dataset_classification: string;
    quality_status: string;
  };
}

export interface SearchResultItem {
  id: string;
  type: "incident" | "investigation" | "system" | "anomaly";
  title: string;
  subtitle?: string | null;
  status?: string | null;
  severity?: string | null;
  url: string;
}

export interface GlobalSearchResponse {
  query: string;
  total: number;
  results: SearchResultItem[];
}

// ---------------------------------------------------------------------------
// Operational Actions & Human Approval Engine Types (Group 9)
// ---------------------------------------------------------------------------

export type ActionStatus =
  | "PROPOSED"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "EXPIRED"
  | "EXECUTING"
  | "EXECUTED"
  | "FAILED"
  | "VERIFYING"
  | "VERIFIED"
  | "VERIFICATION_FAILED";

export type ActionType =
  | "ROLLBACK_DEPLOYMENT"
  | "RESTART_SERVICE"
  | "SCALE_SERVICE"
  | "ENABLE_FEATURE_FLAG"
  | "DISABLE_FEATURE_FLAG"
  | "CLEAR_CACHE"
  | "PAUSE_TRAFFIC"
  | "RESUME_TRAFFIC";

export type ActionApprovalDecision = "APPROVED" | "REJECTED";

export type VerificationOutcome =
  | "VERIFIED_SUCCESS"
  | "VERIFIED_PARTIAL"
  | "VERIFICATION_FAILED"
  | "INCONCLUSIVE";

export interface ActionApproval {
  id: string;
  action_id: string;
  decision: ActionApprovalDecision;
  decision_by: string;
  decision_at: string;
  reason?: string | null;
  fingerprint_verified: string;
  approval_metadata?: Record<string, unknown>;
  created_at: string;
}

export interface ActionItem {
  id: string;
  recommendation_id: string;
  incident_id: string;
  title: string;
  action_type: ActionType;
  description: string;
  risk_level: SeverityLevel;
  status: ActionStatus;
  approval_status: string;
  execution_status: string;
  target_service?: string | null;
  parameters: Record<string, unknown>;
  preconditions: string[];
  expected_outcome?: string | null;
  fingerprint?: string | null;
  idempotency_key?: string | null;
  requested_at: string;
  approved_at?: string | null;
  expires_at?: string | null;
  started_at?: string | null;
  executed_at?: string | null;
  completed_at?: string | null;
  requested_by: string;
  approved_by?: string | null;
  execution_result?: string | null;
  failure_reason?: string | null;
  action_metadata?: Record<string, unknown>;
  verification_strategy?: string | null;
  verification_status?: VerificationOutcome | null;
  verification_result?: Record<string, unknown>;
  verified_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  approvals: ActionApproval[];
}

export interface ActionDefinition {
  action_type: ActionType;
  name: string;
  description: string;
  risk_level: SeverityLevel;
  required_role: UserRole;
  requires_approval: boolean;
  preconditions: string[];
  potential_downside: string;
  expected_outcome: string;
}

export interface ActionExecutionResult {
  success: boolean;
  execution_id: string;
  action_id: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  dry_run: boolean;
  message: string;
  state_before: Record<string, unknown>;
  state_after: Record<string, unknown>;
  emitted_events: Record<string, unknown>[];
  error?: string | null;
}

export interface VerificationResult {
  outcome: VerificationOutcome;
  summary: string;
  target_service: string;
  action_type: string;
  verified_at: string;
  metrics_before: Record<string, unknown>;
  metrics_after: Record<string, unknown>;
  signals_verified: number;
  signals_failed: number;
  details: string[];
}

// =============================================================================
// Phase 2 Distributed Tracing & Service Topology Types
// =============================================================================

export interface TraceSummaryItem {
  trace_id: string;
  timestamp_start: string;
  duration_ms: number;
  root_service: string;
  root_operation: string;
  status: "OK" | "ERROR" | string;
  span_count: number;
  error_count: number;
  services: string[];
  environment: string;
}

export interface TraceSpanNode {
  id: string;
  trace_id: string;
  span_id: string;
  parent_span_id?: string | null;
  service_name: string;
  service_version?: string | null;
  environment: string;
  operation_name: string;
  span_kind: string;
  status: string;
  status_message?: string | null;
  timestamp_start: string;
  timestamp_end: string;
  duration_ms: number;
  self_time_ms: number;
  start_offset_ms: number;
  http_method?: string | null;
  http_route?: string | null;
  http_status_code?: number | null;
  peer_service?: string | null;
  host?: string | null;
  sanitized_attributes: Record<string, unknown>;
  children: TraceSpanNode[];
}

export interface CriticalPathSegment {
  span_id: string;
  service_name: string;
  operation_name: string;
  duration_ms: number;
  self_time_ms: number;
  contribution_percent: number;
  description: string;
}

export interface CriticalPathResponse {
  trace_id: string;
  total_duration_ms: number;
  critical_path_duration_ms: number;
  segments: CriticalPathSegment[];
  non_causal_assessment: string;
}

export interface ErrorPropagationStep {
  span_id: string;
  service_name: string;
  operation_name: string;
  status: string;
  http_status_code?: number | null;
  timestamp: string;
  error_message?: string | null;
  is_deepest_error: boolean;
}

export interface ErrorPropagationResponse {
  trace_id: string;
  has_errors: boolean;
  root_error_service?: string | null;
  root_error_span_id?: string | null;
  root_error_status_code?: number | null;
  root_error_message?: string | null;
  propagation_chain: ErrorPropagationStep[];
  non_causal_assessment: string;
}

export interface TraceTreeResponse {
  trace_id: string;
  root_span: TraceSpanNode | null;
  spans_count: number;
  total_duration_ms: number;
  services: string[];
  status: string;
  error_count: number;
  critical_path?: CriticalPathResponse | null;
  error_propagation?: ErrorPropagationResponse | null;
}

export interface ServiceDependencyItem {
  source_service: string;
  target_service: string;
  environment: string;
  request_count: number;
  error_count: number;
  error_rate: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  first_seen: string;
  last_seen: string;
}

export interface ServiceDependencyNode {
  service: string;
  request_count: number;
  error_count: number;
  error_rate: number;
  p95_latency_ms: number;
  health_status: "HEALTHY" | "DEGRADED" | "FAILED" | string;
}

export interface ServiceDependencyGraphResponse {
  nodes: ServiceDependencyNode[];
  edges: ServiceDependencyItem[];
  time_window_start?: string | null;
  time_window_end?: string | null;
}

export interface ServiceTraceHealthResponse {
  service_name: string;
  environment: string;
  request_count: number;
  error_count: number;
  error_rate: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  slow_request_count: number;
  slow_request_percent: number;
  dependency_failures: number;
  trace_anomaly_count: number;
  health_status: "HEALTHY" | "DEGRADED" | "FAILED" | string;
}

export interface CorrelatedTraceEvidence {
  incident_id: string;
  detected_at: string;
  affected_services: string[];
  lead_deployment?: {
    service: string;
    version: string;
    deployed_at: string;
  } | null;
  timings: Record<string, unknown>;
  trace_metrics: {
    total_spans_in_window: number;
    distinct_traces: number;
    slow_spans_count: number;
    error_spans_count: number;
  };
  error_propagation?: {
    trace_id: string;
    root_error_service?: string;
    assessment: string;
  } | null;
  critical_path?: {
    trace_id: string;
    duration_ms: number;
    assessment: string;
  } | null;
  non_causal_synthesis: string;
}

export interface LiveOperationalEvent {
  id: string;
  type: string;
  timestamp: string;
  company_id?: string | null;
  data: Record<string, any>;
}

export interface PostMortem {
  postmortem_id: string;
  incident_id: string;
  title: string;
  generated_at: string;
  author: string;
  severity: SeverityLevel;
  category: string;
  status: IncidentStatus;
  metrics: {
    mttd_seconds: number;
    mtta_minutes: number | null;
    mttr_minutes: number;
    total_duration_minutes: number;
  };
  blast_radius: {
    estimated_revenue_lost: number;
    orders_affected: number;
    users_affected: number;
    affected_systems: string[];
  };
  executive_summary: string;
  ai_investigation_summary: string;
  root_cause_analysis: string;
  five_whys: Array<{ why: string; statement: string }>;
  timeline: Array<{ timestamp: string; phase: string; summary: string }>;
  actions_taken: Array<{
    action_id: string;
    action_type: string;
    target_service: string;
    status: string;
    approved_by?: string;
    fingerprint: string;
    outcome: string;
  }>;
  preventative_action_items: Array<{
    id: string;
    priority: string;
    title: string;
    owner: string;
    due_date: string;
    status: string;
  }>;
  lessons_learned: string[];
}

export interface ChaosScenario {
  id: string;
  name: string;
  description: string;
  target_service: string;
  metric_name: string;
  baseline_value: number;
  fault_value: number;
  unit: string;
  risk_level: string;
  recommended_action: string;
  action_params: Record<string, any>;
}

export interface ChaosRun {
  run_id: string;
  scenario: ChaosScenario;
  injected_at: string;
  injected_by: string;
  status: "ACTIVE_FAULT" | "RECOVERED";
  metric_id: string;
  recovered_at?: string;
  recovered_by?: string;
}

export interface RunbookDiagnosticStep {
  step: number;
  action: string;
  verified: boolean;
}

export interface RunbookRecommendedAction {
  action_type: string;
  title: string;
  risk_level: string;
  parameters: Record<string, any>;
}

export interface Runbook {
  id: string;
  title: string;
  category: string;
  severity: SeverityLevel;
  target_services: string[];
  summary: string;
  prerequisites: string[];
  diagnostic_steps: RunbookDiagnosticStep[];
  recommended_actions: RunbookRecommendedAction[];
  verification_criteria: string[];
}

export type SLOStatus = "HEALTHY" | "WARNING" | "BURNING" | "EXHAUSTED";

export interface ServiceLevelObjective {
  id: string;
  company_id: string;
  name: string;
  service_name: string;
  description?: string;
  target_percentage: number;
  sli_metric_name: string;
  sli_type: string;
  time_window_days: number;
  current_sli: number;
  error_budget_remaining_percent: number;
  burn_rate_1h: number;
  burn_rate_6h: number;
  burn_rate_24h: number;
  time_to_exhaustion_hours?: number | null;
  status: SLOStatus;
  metadata_info?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface SLOSummary {
  total_slos: number;
  healthy_count: number;
  warning_count: number;
  burning_count: number;
  exhausted_count: number;
  average_error_budget_percent: number;
}

export interface CoPilotResponse {
  reply: string;
  type: string;
  draft_payload?: {
    title?: string;
    status_page_body?: string;
    slack_body?: string;
    [key: string]: any;
  };
  citations: string[];
  suggested_prompts: string[];
  timestamp: string;
}

export interface WebhookSubscription {
  id: string;
  company_id: string;
  name: string;
  url: string;
  target_type: "SLACK" | "PAGERDUTY" | "GENERIC_WEBHOOK" | "STATUSPAGE";
  subscribed_events: string[];
  is_active: boolean;
  last_dispatched_at?: string | null;
  last_status_code?: number | null;
  created_at?: string;
}



