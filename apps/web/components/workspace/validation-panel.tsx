'use client';

import * as React from 'react';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { EmptyState, LoadingState } from '@/components/ui/states';
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table';
import { ApiError, get } from '@/lib/api';
import { runValidation } from '@/lib/contracts';
import { useI18n } from '@/lib/i18n/context';
import type { ValidateResult, ValidationSummary } from '@/lib/types';

interface FindingsResponse {
  findings?: ValidateResult['findings'];
  count?: number;
}

export function ValidationPanel({
  contractId,
  summary,
  refreshSummary,
}: {
  contractId: number;
  summary: ValidationSummary | null;
  refreshSummary: () => Promise<void>;
}) {
  const { t, tn } = useI18n();
  const [result, setResult] = React.useState<ValidateResult | null>(null);
  const [findings, setFindings] = React.useState<ValidateResult['findings'] | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    get<FindingsResponse | ValidateResult['findings']>(`/validation/${contractId}/findings`, false)
      .then((response) => {
        if (cancelled) return;
        const list = Array.isArray(response) ? response : (response.findings ?? []);
        setFindings(list);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setFindings(null);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [contractId]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const runResult = await runValidation(contractId);
      setResult(runResult);
      setFindings(runResult.findings);
      await refreshSummary();
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : t('validation.failed'));
    } finally {
      setRunning(false);
    }
  }

  const blockers = result?.blockers ?? summary?.blockers ?? 0;
  const allFindings = result?.findings ?? findings ?? [];
  const counts =
    result ??
    (summary
      ? {
          status: summary.status,
          findings_count: summary.blockers + summary.high_risks + summary.warnings,
          blockers: summary.blockers,
          high_risks: summary.high_risks,
          warnings: summary.warnings,
          findings: [],
        }
      : null);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">{t('validation.title')}</h2>
          <p className="text-sm text-muted">{t('validation.subtitle')}</p>
        </div>
        <Button
          variant="primary"
          onClick={() => void handleRun()}
          loading={running}
          loadingText={t('validation.validating')}
        >
          {t('validation.run')}
        </Button>
      </div>

      {error ? <Alert variant="danger">{error}</Alert> : null}

      {blockers > 0 ? (
        <Alert variant="danger" title={tn('validation.blockers', blockers)}>
          {t('validation.blockedDescription')}
        </Alert>
      ) : counts ? (
        <Alert variant="success" role="status" title={t('validation.noBlockers')}>
          {t('validation.noBlockersDescription')}
        </Alert>
      ) : null}

      {counts ? (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-md border border-line bg-white px-4 py-3">
            <dt className="text-xs uppercase tracking-wide text-muted">
              {t('validation.findings')}
            </dt>
            <dd className="text-xl font-semibold text-ink">{counts.findings_count}</dd>
          </div>
          <div className="rounded-md border border-line bg-white px-4 py-3">
            <dt className="text-xs uppercase tracking-wide text-muted">
              {t('validation.blockers')}
            </dt>
            <dd className="text-xl font-semibold text-danger">{counts.blockers}</dd>
          </div>
          <div className="rounded-md border border-line bg-white px-4 py-3">
            <dt className="text-xs uppercase tracking-wide text-muted">
              {t('validation.highRisks')}
            </dt>
            <dd className="text-xl font-semibold text-warning">{counts.high_risks}</dd>
          </div>
          <div className="rounded-md border border-line bg-white px-4 py-3">
            <dt className="text-xs uppercase tracking-wide text-muted">
              {t('validation.warnings')}
            </dt>
            <dd className="text-xl font-semibold text-muted">{counts.warnings}</dd>
          </div>
        </dl>
      ) : null}

      {loading ? (
        <LoadingState label={t('validation.loading')} />
      ) : allFindings.length === 0 ? (
        <EmptyState
          title={t('validation.emptyTitle')}
          description={t('validation.emptyDescription')}
        />
      ) : (
        <Table caption={t('validation.tableCaption')}>
          <THead>
            <TR>
              <TH scope="col">{t('validation.colSeverity')}</TH>
              <TH scope="col">{t('validation.colRule')}</TH>
              <TH scope="col">{t('validation.colFinding')}</TH>
              <TH scope="col">{t('validation.colLocation')}</TH>
              <TH scope="col">{t('validation.colRecommendation')}</TH>
              <TH scope="col">{t('validation.colStatus')}</TH>
            </TR>
          </THead>
          <TBody>
            {allFindings.map((finding, index) => (
              <TR key={finding.id ?? `${finding.rule_id}-${index}`}>
                <TD>
                  <StatusBadge status={finding.severity} />
                </TD>
                <TD className="whitespace-nowrap text-xs text-muted">{finding.rule_id}</TD>
                <TD>
                  <span className="font-medium">{finding.title}</span>
                  <p className="mt-1 text-sm text-muted">{finding.explanation}</p>
                </TD>
                <TD className="whitespace-nowrap text-xs text-muted">{finding.location || '—'}</TD>
                <TD className="text-sm text-muted">{finding.recommendation || '—'}</TD>
                <TD>
                  <Badge variant={finding.status === 'open' ? 'warning' : 'neutral'}>
                    {finding.status}
                  </Badge>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
