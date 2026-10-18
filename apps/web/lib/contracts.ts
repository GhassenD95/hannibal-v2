import { fetchBlob, get, patch, post } from './api';
import type {
  ApprovalItem,
  ApproveResult,
  AuditEvent,
  ConfirmResult,
  ContractDetail,
  ContractPlanResult,
  ContractRequestResult,
  ContractSection,
  ContractSummary,
  EvidenceResponse,
  ExportResult,
  GenerateResult,
  NegotiationItem,
  RegenerateResult,
  RiskItem,
  RiskRunResult,
  ValidateResult,
  ValidationSummary,
  VersionItem,
} from './types';

export interface CreateRequestPayload {
  name: string;
  contract_type: string;
  jurisdiction: string;
  mode: 'guided' | 'ai';
  facts: Record<string, string>;
  description?: string;
  language?: string;
}

export function createContractRequest(
  payload: CreateRequestPayload,
): Promise<ContractRequestResult> {
  return post<ContractRequestResult>('/contracts', {
    name: payload.name,
    contract_type: payload.contract_type,
    jurisdiction: payload.jurisdiction,
    mode: payload.mode,
    facts: payload.facts,
    description: payload.description,
    language: payload.language ?? 'fr',
  });
}

export function interpretRequest(
  requestId: number,
  description: string,
): Promise<ContractRequestResult> {
  return post<ContractRequestResult>(`/contracts/${requestId}/interpret`, {
    description,
  });
}

export function confirmRequest(requestId: number): Promise<ConfirmResult> {
  return post<ConfirmResult>(`/contracts/${requestId}/confirm-request`);
}

export function listContracts(): Promise<ContractSummary[]> {
  return get<ContractSummary[]>('/contracts');
}

export function getContract(id: number): Promise<ContractDetail> {
  return get<ContractDetail>(`/contracts/${id}`);
}

export function createPlan(contractId: number): Promise<ContractPlanResult> {
  return post<ContractPlanResult>(`/contracts/${contractId}/plan`);
}

export function generateContract(contractId: number): Promise<GenerateResult> {
  return post<GenerateResult>(`/contracts/${contractId}/generate`);
}

export function listSections(contractId: number): Promise<ContractSection[]> {
  return get<ContractSection[]>(`/contracts/${contractId}/sections`);
}

export function createSection(
  contractId: number,
  title: string,
  orderIndex: number,
): Promise<{ id: number; title: string; status: string }> {
  return post(`/contracts/${contractId}/sections`, {
    title,
    content: '',
    order_index: orderIndex,
  });
}

export function updateSection(
  contractId: number,
  sectionId: number,
  payload: { title?: string; content?: string; status?: string },
): Promise<{ id: number; title: string; status: string }> {
  return patch(`/contracts/${contractId}/sections/${sectionId}`, payload);
}

export function sectionEvidence(contractId: number, sectionId: number): Promise<EvidenceResponse> {
  return get<EvidenceResponse>(`/contracts/${contractId}/sections/${sectionId}/evidence`);
}

export function regenerateSection(
  contractId: number,
  sectionId: number,
): Promise<RegenerateResult> {
  return post<RegenerateResult>(`/contracts/${contractId}/sections/${sectionId}/regenerate`);
}

export function runValidation(contractId: number): Promise<ValidateResult> {
  return post<ValidateResult>(`/contracts/${contractId}/validate`);
}

export function validationSummary(contractId: number): Promise<ValidationSummary> {
  return get<ValidationSummary>(`/contracts/${contractId}/validation/summary`);
}

export function runRiskAnalysis(contractId: number): Promise<RiskRunResult> {
  return post<RiskRunResult>(`/contracts/${contractId}/risk`);
}

export function listRisks(contractId: number): Promise<RiskItem[]> {
  return get<RiskItem[]>(`/contracts/${contractId}/risks`);
}

export function listNegotiations(contractId: number): Promise<NegotiationItem[]> {
  return get<NegotiationItem[]>(`/contracts/${contractId}/negotiations`);
}

export function createNegotiation(
  contractId: number,
  sectionId: number,
  counterpartyClause: string,
): Promise<NegotiationItem> {
  return post<NegotiationItem>(`/contracts/${contractId}/negotiations`, {
    section_id: sectionId,
    counterparty_clause: counterpartyClause,
  });
}

export function analyzeNegotiation(contractId: number, itemId: number): Promise<NegotiationItem> {
  return post<NegotiationItem>(`/contracts/${contractId}/negotiations/${itemId}/analyze`);
}

export function proposeNegotiation(contractId: number, itemId: number): Promise<NegotiationItem> {
  return post<NegotiationItem>(`/contracts/${contractId}/negotiations/${itemId}/propose`);
}

export type NegotiationDecision = 'accepted' | 'rejected' | 'escalated';

export function decideNegotiation(
  contractId: number,
  itemId: number,
  decision: NegotiationDecision,
): Promise<NegotiationItem> {
  return post<NegotiationItem>(`/contracts/${contractId}/negotiations/${itemId}/decide`, {
    decision,
  });
}

export function approveContract(contractId: number, notes?: string): Promise<ApproveResult> {
  return post<ApproveResult>(`/contracts/${contractId}/approve`, {
    notes: notes ?? null,
  });
}

export function listApprovals(contractId: number): Promise<ApprovalItem[]> {
  return get<ApprovalItem[]>(`/contracts/${contractId}/approvals`);
}

export function listVersions(contractId: number): Promise<VersionItem[]> {
  return get<VersionItem[]>(`/contracts/${contractId}/versions`);
}

export function listAudit(contractId: number): Promise<AuditEvent[]> {
  return get<AuditEvent[]>(`/contracts/${contractId}/audit`);
}

export function createExport(
  contractId: number,
  format: 'html' | 'docx' | 'pdf',
): Promise<ExportResult> {
  return post<ExportResult>(`/contracts/${contractId}/export`, { format });
}

export function fetchExportContent(contractId: number, exportId: number): Promise<Blob> {
  return fetchBlob(`/contracts/${contractId}/export/${exportId}/content`);
}
