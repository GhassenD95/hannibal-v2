'use client';

import * as React from 'react';
import Link from 'next/link';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table';
import { ApiError } from '@/lib/api';
import { listContracts } from '@/lib/contracts';
import { useI18n } from '@/lib/i18n/context';
import type { ContractSummary } from '@/lib/types';

function formatUpdated(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value.replace(' ', 'T'));
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

const PAGE_SIZE = 25;

export default function DashboardPage() {
  const { t, tn } = useI18n();
  const [contracts, setContracts] = React.useState<ContractSummary[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);
  const [page, setPage] = React.useState(0);

  React.useEffect(() => {
    let cancelled = false;
    setError(null);
    listContracts()
      .then((result) => {
        if (!cancelled) setContracts(result);
      })
      .catch((exc: unknown) => {
        if (cancelled) return;
        setError(exc instanceof ApiError ? exc.message : t('dashboard.loadFailed'));
        setContracts([]);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt, t]);

  React.useEffect(() => {
    if (!contracts) return;
    const maxPage = Math.max(0, Math.ceil(contracts.length / PAGE_SIZE) - 1);
    setPage((current) => Math.min(current, maxPage));
  }, [contracts]);

  const newContractLink = (
    <Link
      href="/contracts/new"
      className="inline-flex h-9 items-center justify-center rounded-sm border border-primary bg-primary px-4 text-sm font-medium text-white transition-colors duration-150 hover:bg-[#1a44bb] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
    >
      {t('dashboard.new')}
    </Link>
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{t('dashboard.title')}</h1>
          <p className="mt-1 text-sm text-muted">{t('dashboard.subtitle')}</p>
        </div>
        {newContractLink}
      </div>

      {error ? (
        <ErrorState message={error} onRetry={() => setAttempt((value) => value + 1)} />
      ) : contracts === null ? (
        <LoadingState label={t('dashboard.loading')} />
      ) : contracts.length === 0 ? (
        <EmptyState
          title={t('dashboard.emptyTitle')}
          description={t('dashboard.emptyDescription')}
          action={newContractLink}
        />
      ) : (
        <>
          <p className="text-sm text-muted" role="status">
            {tn('dashboard.contracts', contracts.length)}
          </p>
          <Table>
            <caption className="sr-only">{t('dashboard.tableCaption')}</caption>
            <THead>
              <TR>
                <TH scope="col">{t('dashboard.colName')}</TH>
                <TH scope="col">{t('dashboard.colType')}</TH>
                <TH scope="col">{t('dashboard.colJurisdiction')}</TH>
                <TH scope="col">{t('dashboard.colStatus')}</TH>
                <TH scope="col">{t('dashboard.colUpdated')}</TH>
                <TH scope="col">
                  <span className="sr-only">{t('dashboard.colActions')}</span>
                </TH>
              </TR>
            </THead>
            <TBody>
              {contracts.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).map((contract) => (
                <TR key={contract.id}>
                  <TD>
                    <span className="font-medium">{contract.name}</span>
                    <span className="ms-2 text-xs text-muted">#{contract.id}</span>
                  </TD>
                  <TD>
                    <Badge variant="neutral">{contract.contract_type}</Badge>
                  </TD>
                  <TD>{contract.jurisdiction}</TD>
                  <TD>
                    <StatusBadge status={contract.status} />
                  </TD>
                  <TD className="whitespace-nowrap text-muted">
                    {formatUpdated(contract.updated_at)}
                  </TD>
                  <TD className="text-end">
                    <Link
                      href={`/contracts/${contract.id}`}
                      className="inline-flex h-8 items-center rounded-sm border border-line bg-white px-3 text-xs font-medium text-ink transition-colors duration-150 hover:bg-surface focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                    >
                      {t('dashboard.open')}
                    </Link>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
          {contracts.length > PAGE_SIZE ? (
            <nav
              aria-label={t('dashboard.pagesAria')}
              className="flex flex-wrap items-center justify-between gap-3"
            >
              <p className="text-sm text-muted">
                {t('dashboard.showing', {
                  from: page * PAGE_SIZE + 1,
                  to: Math.min((page + 1) * PAGE_SIZE, contracts.length),
                  total: contracts.length,
                })}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page === 0}
                  onClick={() => setPage((value) => Math.max(0, value - 1))}
                >
                  {t('dashboard.previous')}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={(page + 1) * PAGE_SIZE >= contracts.length}
                  onClick={() => setPage((value) => value + 1)}
                >
                  {t('dashboard.next')}
                </Button>
              </div>
            </nav>
          ) : null}
        </>
      )}

      {contracts && contracts.length > 0 && !error ? (
        <div className="flex justify-end">
          <Button variant="ghost" size="sm" onClick={() => setAttempt((value) => value + 1)}>
            {t('dashboard.refresh')}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
