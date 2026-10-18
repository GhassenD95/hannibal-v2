import { get, post } from './api';
import type { ExtractResult, FieldValidationResponse } from './types';

export interface ExtractPayload {
  description: string;
  contract_type?: string;
  jurisdiction?: string;
}

export function extractFacts(payload: ExtractPayload): Promise<ExtractResult> {
  return post<ExtractResult>('/information-collector/extract', {
    description: payload.description,
    contract_type: payload.contract_type ?? '',
    jurisdiction: payload.jurisdiction ?? 'MA',
  });
}

export function validateField(
  fieldName: string,
  fieldValue: string,
): Promise<FieldValidationResponse> {
  return post<FieldValidationResponse>(
    `/information-collector/validate/${encodeURIComponent(fieldName)}`,
    { field_name: fieldName, field_value: fieldValue },
  );
}
