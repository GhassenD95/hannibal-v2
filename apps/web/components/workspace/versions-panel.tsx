'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { EmptyState, LoadingState } from '@/components/ui/states';
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table';
import { ApiError } from '@/lib/api';
import { listVersions } from '@/lib/contracts';
import { useI18n } from '@/lib/i18n/context';
import type { VersionItem } from '@/lib/types';

export function VersionsPanel({ contractId }: { contractId: number }) {
  const { t } = useI18n();
  const [versions, setVersions] = React.useState<VersionItem[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [rawId, setRawId] = React.useState<number | null>(null);
  const [raw, setRaw] = React.useState<string | null>(null);
  const [rawLoading, setRawLoading] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setVersions(null);
    listVersions(contractId)
      .then((result) => {
        if (!cancelled) {
          setVersions(result);
          setError(null);
        }
      })
      .catch((exc: unknown) => {
        if (!cancelled) {
          setVersions([]);
          setError(exc instanceof ApiError ? exc.message : t('versions.loadFailed'));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [contractId, t]);

  async function loadRaw(version: VersionItem) {
    if (rawId === version.version_number) {
      setRawId(null);
      setRaw(null);
      return;
    }
    setRawId(version.version_number);
    setRaw(null);
    setRawLoading(true);
    try {
      const response = await listVersions(contractId);
      setRaw(JSON.stringify(response, null, 2));
    } catch (exc) {
      setRaw(
        t('versions.loadFailedMessage', {
          error: exc instanceof ApiError ? exc.message : 'request failed',
        }),
      );
    } finally {
      setRawLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-ink">{t('versions.title')}</h2>
        <p className="text-sm text-muted">{t('versions.subtitle')}</p>
      </div>

      <Alert variant="warning" title={t('versions.metadataAlert')}>
        {t('versions.metadataDescription')}
      </Alert>

      {error ? <Alert variant="danger">{error}</Alert> : null}

      {versions === null ? (
        <LoadingState label={t('versions.loading')} />
      ) : versions.length === 0 ? (
        <EmptyState title={t('versions.emptyTitle')} description={t('versions.emptyDescription')} />
      ) : (
        <Table caption={t('versions.tableCaption')}>
          <THead>
            <TR>
              <TH scope="col">{t('versions.colVersion')}</TH>
              <TH scope="col">{t('versions.colTitle')}</TH>
              <TH scope="col">{t('versions.colValidated')}</TH>
              <TH scope="col">{t('versions.colApproved')}</TH>
              <TH scope="col">{t('versions.colCreated')}</TH>
              <TH scope="col"> </TH>
            </TR>
          </THead>
          <TBody>
            {versions.map((version) => (
              <TR key={version.version_number}>
                <TD className="whitespace-nowrap font-medium">
                  v{version.version_number}
                  {version.is_active ? (
                    <Badge variant="primary" className="ms-2">
                      {t('versions.active')}
                    </Badge>
                  ) : null}
                </TD>
                <TD>{version.title || '—'}</TD>
                <TD>
                  <Badge variant={version.validated ? 'success' : 'neutral'}>
                    {version.validated ? t('versions.validated') : t('versions.notValidated')}
                  </Badge>
                </TD>
                <TD>
                  <Badge variant={version.approved ? 'success' : 'neutral'}>
                    {version.approved ? t('versions.approved') : t('versions.notApproved')}
                  </Badge>
                </TD>
                <TD className="whitespace-nowrap text-sm text-muted">
                  {new Date(version.created_at).toLocaleString()}
                </TD>
                <TD>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => void loadRaw(version)}
                    aria-expanded={rawId === version.version_number}
                  >
                    {rawId === version.version_number
                      ? t('versions.hideResponse')
                      : t('versions.viewRaw')}
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {rawId !== null ? (
        rawLoading ? (
          <LoadingState label={t('versions.loadingResponse')} />
        ) : raw !== null ? (
          <pre className="overflow-x-auto rounded-md border border-line bg-ink px-4 py-3 text-xs text-white">
            {raw}
          </pre>
        ) : null
      ) : null}
    </div>
  );
}
