import { get, post } from './api';
import type { EvaluationFixture, EvaluationRun, EvaluationRunResult } from './types';

export function listFixtures(): Promise<EvaluationFixture[]> {
  return get<EvaluationFixture[]>('/admin/evaluation/fixtures');
}

export function runEvaluation(): Promise<EvaluationRunResult> {
  return post<EvaluationRunResult>('/admin/evaluation/run');
}

export function listRuns(): Promise<EvaluationRun[]> {
  return get<EvaluationRun[]>('/admin/evaluation/runs');
}
