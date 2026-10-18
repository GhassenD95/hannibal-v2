export interface SessionUser {
  id: number;
  email: string;
  full_name?: string | null;
  organization_id?: number | null;
  roles: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  email: string;
  full_name?: string | null;
  organization_id?: number | null;
  roles: string[];
}

export interface ContractSummary {
  id: number;
  name: string;
  contract_type: string;
  jurisdiction: string;
  status: string;
  updated_at?: string | null;
}

export interface ContractDetail {
  kind: string;
  id: number;
  name: string;
  description?: string | null;
  contract_type: string;
  jurisdiction: string;
  language?: string;
  status: string;
  request_id?: number | null;
}

export interface ContractRequestResult {
  kind: string;
  id: number;
  name: string;
  contract_type: string;
  jurisdiction: string;
  facts: Record<string, string>;
  status: string;
}

export interface ConfirmResult {
  kind: string;
  id: number;
  name: string;
  contract_type: string;
  jurisdiction: string;
  status: string;
  section_count: number;
  sections: Array<{
    id: number;
    title: string;
    order_index: number;
    status: string;
  }>;
}

export interface ExtractResult {
  id: number;
  name?: string;
  description?: string | null;
  contract_type: string;
  jurisdiction: string;
  language?: string;
  status?: string;
  facts: Record<string, string>;
}

export interface FieldValidationIssue {
  field_name: string;
  error_message: string;
  severity: string;
}

export interface FieldValidationResponse {
  has_issue: boolean;
  validation?: FieldValidationIssue;
  message?: string;
}

export interface ContractSection {
  id: number;
  title: string;
  content: string;
  order_index: number;
  status: string;
  clause_ids: number[];
  evidence_ids: string[];
  facts_used: string[];
}

export interface EvidenceItem {
  id?: number | null;
  source_id: string;
  source_version?: string | null;
  title: string;
  jurisdiction?: string | null;
  language?: string | null;
  article?: string | null;
  page_start?: number | null;
  page_end?: number | null;
  excerpt: string;
  relevance_reason?: string | null;
  authority?: string | null;
  status?: string | null;
}

export interface EvidenceResponse {
  section_id: number;
  evidence: EvidenceItem[];
}

export interface ContractPlanResult {
  id: number;
  contract_id: number;
  sections_required: string[];
  sections_complete: string[];
  selected_clauses: number[];
  evidence_ids: string[];
  unresolved_decisions: unknown[];
  status: string;
}

export interface GenerateResult {
  contract_id: number;
  status: string;
  generated_sections: number;
  supported: number;
  needs_review: number;
  unsupported: number;
}

export interface RegenerateResult {
  section_id: number;
  title: string;
  status: string;
  content: string;
  clause_ids: number[];
  evidence_ids: string[];
  facts_used: string[];
  new_version_number?: number;
}

export interface ValidationFinding {
  id?: number | null;
  rule_id: string;
  severity: string;
  title: string;
  explanation: string;
  location?: string | null;
  recommendation?: string | null;
  status: string;
}

export interface ValidateResult {
  status: string;
  findings_count: number;
  blockers: number;
  high_risks: number;
  warnings: number;
  findings: ValidationFinding[];
}

export interface ValidationSummary {
  status: string;
  blockers: number;
  high_risks: number;
  warnings: number;
  passed_checks: number;
  total_checks: number;
}

export interface RiskRunResult {
  contract_id: number;
  risk_count: number;
  severity_summary: { blocker: number; high: number; warning: number };
  requires_human_review: boolean;
}

export interface RiskItem {
  id: number;
  title: string;
  severity: string;
  explanation: string;
  location?: string | null;
  recommendation?: string | null;
  status: string;
  section_id?: number | null;
}

export interface NegotiationItem {
  id: number;
  contract_id: number;
  section_id: number | null;
  original_clause_id: number | null;
  counterparty_clause: string | null;
  hannibal_analysis: string | null;
  proposed_text: string | null;
  status: string;
}

export interface ApprovalItem {
  id: number;
  contract_id: number;
  version_id: number | null;
  approver_id: number | null;
  approval_type: string;
  notes?: string | null;
  approved_at: string;
}

export interface ApproveResult {
  approval_id: number;
  contract_id: number;
  version_id: number | null;
  approver_id: number | null;
  approval_type: string;
  approved_at: string;
  status?: string;
}

export interface VersionItem {
  version_number: number;
  title?: string;
  is_active?: boolean;
  validated?: boolean;
  approved?: boolean;
  status?: string;
  created_at: string;
  snapshot?: unknown;
  content?: string | null;
}

export interface AuditEvent {
  id: number;
  event_type: string;
  event_data?: Record<string, unknown> | null;
  user_id?: number | null;
  created_at: string;
}

export interface ExportResult {
  export_id: number;
  contract_id: number;
  format: string;
  content_url?: string;
  status?: string;
  blockers?: unknown[];
}

export interface PackObject {
  id: number;
  name: string;
  description?: string | null;
  version: string;
  status: string;
  metadata?: Record<string, unknown>;
  contractTypes?: Array<{ id: number; name: string }>;
  clauseCount?: number;
  sourceCount?: number;
  validationRuleCount?: number;
  riskPlaybookName?: string | null;
}

export interface PackValidation {
  id: number;
  valid: boolean;
  issues: string[];
}

export interface SourceItem {
  id: number;
  title: string;
  jurisdiction: string;
  status: string;
  version?: string | null;
  chunk_count?: number;
  effective_date?: string | null;
}

export interface RetrievalHit {
  source_id: number | string;
  title: string;
  jurisdiction?: string | null;
  language?: string | null;
  article?: string | null;
  content: string;
  relevance?: number;
}

export interface RetrievalResult {
  query: string;
  hits: RetrievalHit[];
}

export interface ClauseItem {
  id: number;
  title: string;
  contract_type: string;
  clause_type?: string;
  status: string;
  version?: string;
}

export interface EvaluationFixture {
  id: string;
  name?: string;
  jurisdiction?: string;
  contractType?: string;
  input?: { description?: string };
  expectedSections?: string[];
  requiredClauses?: string[];
  expectedEvidence?: string[];
  expectedRisks?: string[];
  forbiddenClaims?: string[];
}

export type MetricGroup = Record<string, number>;

export interface EvaluationMetrics {
  extraction?: MetricGroup;
  retrieval?: MetricGroup;
  planning?: MetricGroup;
  generation?: MetricGroup;
  validation?: MetricGroup;
  system?: MetricGroup;
  forbidden_claims_hit_rate?: number;
  [key: string]: unknown;
}

export interface EvaluationRunResult {
  run_id: number;
  metrics: EvaluationMetrics;
  per_fixture: Array<Record<string, unknown>>;
}

export interface EvaluationRun {
  id: number;
  status: string;
  total_fixtures: number;
  metrics: EvaluationMetrics;
  started_at: string;
  completed_at?: string | null;
}
