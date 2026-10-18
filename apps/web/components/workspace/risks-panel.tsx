'use client';

import * as React from 'react';
import { StatusBadge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table';
import { ApiError } from '@/lib/api';
import { listRisks, runRiskAnalysis } from '@/lib/contracts';
import { useI18n } from '@/lib/i18n/context';
import type { RiskItem, RiskRunResult } from '@/lib/types';

export function RisksPanel({ contractId }: { contractId: number }) {
  const { t, tn } = useI18n();
  const [risks, setRisks] = React.useState<RiskItem[] | null>(null);
  const [lastRun, setLastRun] = React.useState<RiskRunResult | null>(null);
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    try {
      const result = await listRisks(contractId);
      setRisks(result);
      setError(null);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to load risks.');
      setRisks([]);
    }
  }, [contractId]);

  React.useEffect(() => {
    void load();
  }, [load]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const result = await runRiskAnalysis(contractId);
      setLastRun(result);
      await load();
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : t('risks.failed'));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">{t('risks.title')}</h2>
          <p className="text-sm text-muted">{t('risks.subtitle')}</p>
        </div>
        <Button
          variant="primary"
          onClick={() => void handleRun()}
          loading={running}
          loadingText={t('risks.analyzing')}
        >
          {t('risks.run')}
        </Button>
      </div>

      {error ? <Alert variant="danger">{error}</Alert> : null}

      {lastRun ? (
        <Alert
          variant={lastRun.requires_human_review ? 'warning' : 'success'}
          role="status"
          title={tn('risks.recorded', lastRun.risk_count)}
        >
          {t('risks.severityLine', {
            blocker: lastRun.severity_summary.blocker,
            high: lastRun.severity_summary.high,
            warning: lastRun.severity_summary.warning,
          })}{' '}
          {lastRun.requires_human_review ? t('risks.humanReview') : t('risks.noHigh')}
        </Alert>
      ) : null}

      {risks === null ? (
        <LoadingState label={t('risks.emptyTitle')} />
      ) : risks.length === 0 ? (
        <EmptyState title={t('risks.emptyTitle')} description={t('risks.emptyDescription')} />
      ) : (
        <Table caption={t('risks.tableCaption')}>
          <THead>
            <TR>
              <TH scope="col">{t('risks.colSeverity')}</TH>
              <TH scope="col">{t('risks.colRisk')}</TH>
              <TH scope="col">{t('risks.colExplanation')}</TH>
              <TH scope="col">{t('risks.colRecommendation')}</TH>
              <TH scope="col">{t('risks.colLocation')}</TH>
              <TH scope="col">{t('risks.colStatus')}</TH>
            </TR>
          </THead>
          <TBody>
            {risks.map((risk) => (
              <TR key={risk.id}>
                <TD>
                  <StatusBadge status={risk.severity} />
                </TD>
                <TD className="font-medium">{risk.title}</TD>
                <TD className="text-sm text-muted">{risk.explanation}</TD>
                <TD className="text-sm text-muted">{risk.recommendation || '—'}</TD>
                <TD className="whitespace-nowrap text-xs text-muted">{risk.location || '—'}</TD>
                <TD>
                  <StatusBadge status={risk.status} />
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
