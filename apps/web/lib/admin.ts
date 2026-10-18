import { get, post } from './api';
import type { ClauseItem, PackObject, PackValidation, RetrievalResult, SourceItem } from './types';

export function listPacks(): Promise<PackObject[]> {
  return get<PackObject[]>('/admin/packs');
}

export function importPack(path: string): Promise<PackObject> {
  return post<PackObject>('/admin/packs/import', { path });
}

export function validatePack(packId: number): Promise<PackValidation> {
  return post<PackValidation>(`/admin/packs/${packId}/validate`);
}

export function activatePack(packId: number): Promise<PackObject> {
  return post<PackObject>(`/admin/packs/${packId}/activate`);
}

export function archivePack(packId: number): Promise<PackObject> {
  return post<PackObject>(`/admin/packs/${packId}/archive`);
}

export function listSources(): Promise<SourceItem[]> {
  return get<SourceItem[]>('/admin/sources');
}

export interface SourceCreatePayload {
  title: string;
  jurisdiction: string;
  source_type?: string;
  language?: string;
  version?: string;
  effective_date?: string;
  description?: string;
}

export function createSource(payload: SourceCreatePayload): Promise<{
  id: number;
  title: string;
  status: string;
}> {
  return post('/admin/sources', {
    title: payload.title,
    jurisdiction: payload.jurisdiction,
    source_type: payload.source_type ?? 'law',
    language: payload.language ?? 'fr',
    version: payload.version ?? '1.0.0',
    effective_date: payload.effective_date || null,
    description: payload.description || null,
  });
}

export function approveSource(sourceId: number): Promise<{ id: number; status: string }> {
  return post(`/admin/sources/${sourceId}/approve`);
}

export function archiveSource(sourceId: number): Promise<{ id: number; status: string }> {
  return post(`/admin/sources/${sourceId}/archive`);
}

export function testRetrieval(query: string, topK: number): Promise<RetrievalResult> {
  return post<RetrievalResult>('/admin/sources/test-retrieval', {
    query,
    top_k: topK,
  });
}

export function listClauses(): Promise<ClauseItem[]> {
  return get<ClauseItem[]>('/admin/clauses');
}

export interface ClauseCreatePayload {
  title: string;
  content: string;
  contract_type: string;
  clause_type?: string;
  jurisdiction?: string;
  status?: string;
}

export function createClause(payload: ClauseCreatePayload): Promise<{
  id: number;
  title: string;
  status: string;
}> {
  return post('/admin/clauses', {
    title: payload.title,
    content: payload.content,
    contract_type: payload.contract_type,
    clause_type: payload.clause_type ?? 'optional',
    jurisdiction: payload.jurisdiction ?? 'MA',
    status: payload.status ?? 'draft',
  });
}

export function archiveClause(clauseId: number): Promise<{ id: number; status: string }> {
  return post(`/admin/clauses/${clauseId}/archive`);
}
