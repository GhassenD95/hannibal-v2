'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { EmptyState, LoadingState } from '@/components/ui/states';
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table';
import { ApiError } from '@/lib/api';
import { listAudit } from '@/lib/contracts';
import { useI18n } from '@/lib/i18n/context';
import type { AuditEvent } from '@/lib/types';

export function AuditPanel({ contractId }: { contractId: number }) {
  const { t } = useI18n();
  const [events, setEvents] = React.useState<AuditEvent[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [rawOpen, setRawOpen] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setEvents(null);
    listAudit(contractId)
      .then((result) => {
        if (cancelled) return;
        setEvents(result);
        setError(null);
      })
      .catch((exc: unknown) => {
        if (cancelled) return;
        setEvents([]);
        setError(exc instanceof ApiError ? exc.message : t('audit.loadFailed'));
      });
    return () => {
      cancelled = true;
    };
  }, [contractId, t]);

  if (events === null) return <LoadingState label={t('audit.loading')} />;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">{t('audit.title')}</h2>
          <p className="text-sm text-muted">{t('audit.subtitle')}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setRawOpen((value) => !value)}>
          {rawOpen ? t('audit.hideRaw') : t('audit.viewRaw')}
        </Button>
      </div>

      {error ? <Alert variant="danger">{error}</Alert> : null}

      {events.length === 0 ? (
        <EmptyState title={t('audit.emptyTitle')} description={t('audit.emptyDescription')} />
      ) : (
        <Table caption={t('audit.tableCaption')}>
          <THead>
            <TR>
              <TH scope="col">{t('audit.colEvent')}</TH>
              <TH scope="col">{t('audit.colActor')}</TH>
              <TH scope="col">{t('audit.colWhen')}</TH>
            </TR>
          </THead>
          <TBody>
            {events.map((event) => (
              <TR key={event.id}>
                <TD>
                  <Badge variant="neutral">{event.event_type}</Badge>
                </TD>
                <TD className="text-sm text-muted">
                  {event.user_id ? `User #${event.user_id}` : t('audit.system')}
                </TD>
                <TD className="whitespace-nowrap text-sm text-muted">
                  {new Date(event.created_at).toLocaleString()}
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {rawOpen ? (
        <pre className="overflow-x-auto rounded-md border border-line bg-ink px-4 py-3 text-xs text-white">
          {JSON.stringify(events, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
