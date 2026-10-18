'use client';

import * as React from 'react';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState, LoadingState } from '@/components/ui/states';
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table';
import { ApiError } from '@/lib/api';
import { approveContract, listApprovals } from '@/lib/contracts';
import { useI18n } from '@/lib/i18n/context';
import type { ApprovalItem, ValidationSummary } from '@/lib/types';

export function ApprovalsPanel({
  contractId,
  summary,
  refreshSummary,
  onApproved,
}: {
  contractId: number;
  summary: ValidationSummary | null;
  refreshSummary: () => Promise<void>;
  onApproved?: () => Promise<void>;
}) {
  const { t, tn } = useI18n();
  const [approvals, setApprovals] = React.useState<ApprovalItem[] | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    try {
      const result = await listApprovals(contractId);
      setApprovals(result);
      setError(null);
    } catch (exc) {
      setApprovals([]);
      setError(exc instanceof ApiError ? exc.message : t('approvals.loadFailed'));
    }
  }, [contractId, t]);

  React.useEffect(() => {
    void load();
  }, [load]);

  const blockers = summary?.blockers ?? 0;

  async function handleApprove() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await approveContract(contractId);
      await Promise.all([load(), refreshSummary(), onApproved?.()]);
      setMessage(t('approvals.recorded', { id: result.approval_id }));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : t('approvals.approvalFailed'));
      await refreshSummary();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-ink">{t('approvals.title')}</h2>
        <p className="text-sm text-muted">{t('approvals.subtitle')}</p>
      </div>

      {error ? (
        <Alert variant="danger" title={t('approvals.errorTitle')}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <p role="status" aria-live="polite" className="text-sm font-medium text-success">
          {message}
        </p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t('approvals.approveTitle')}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {blockers > 0 ? (
            <Alert variant="warning" title={t('approvals.blockedTitle')}>
              {tn('approvals.blockers', blockers)}
            </Alert>
          ) : (
            <Alert variant="success" title={t('approvals.readyTitle')}>
              {t('approvals.readyDescription')}
            </Alert>
          )}
          <div>
            <Button
              variant="primary"
              onClick={() => void handleApprove()}
              loading={busy}
              loadingText={t('approvals.recording')}
              disabled={blockers > 0 || busy}
            >
              {t('approvals.approveAsReviewer')}
            </Button>
          </div>
        </CardContent>
      </Card>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-ink">{t('approvals.historyTitle')}</h3>
        {approvals === null ? (
          <LoadingState label={t('approvals.loading')} />
        ) : approvals.length === 0 ? (
          <EmptyState
            title={t('approvals.emptyTitle')}
            description={t('approvals.emptyDescription')}
          />
        ) : (
          <Table caption={t('approvals.tableCaption')}>
            <THead>
              <TR>
                <TH scope="col">{t('approvals.colApproval')}</TH>
                <TH scope="col">{t('approvals.colType')}</TH>
                <TH scope="col">{t('approvals.colVersion')}</TH>
                <TH scope="col">{t('approvals.colApprover')}</TH>
                <TH scope="col">{t('approvals.colApprovedAt')}</TH>
              </TR>
            </THead>
            <TBody>
              {approvals.map((approval) => (
                <TR key={approval.id}>
                  <TD>#{approval.id}</TD>
                  <TD>
                    <Badge variant="primary">{approval.approval_type}</Badge>
                  </TD>
                  <TD>
                    {approval.version_id ? (
                      <StatusBadge status={`version ${approval.version_id}`} />
                    ) : (
                      '—'
                    )}
                  </TD>
                  <TD className="text-sm text-muted">
                    {approval.approver_id ? `Reviewer #${approval.approver_id}` : '—'}
                  </TD>
                  <TD className="whitespace-nowrap text-sm text-muted">
                    {new Date(approval.approved_at).toLocaleString()}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </section>
    </div>
  );
}
