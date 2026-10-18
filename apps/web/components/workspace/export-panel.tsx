'use client';

import * as React from 'react';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ApiError, saveBlob } from '@/lib/api';
import { createExport, fetchExportContent } from '@/lib/contracts';
import { useI18n } from '@/lib/i18n/context';
import type { ValidationSummary } from '@/lib/types';

export function ExportPanel({
  contractId,
  status,
  summary,
}: {
  contractId: number;
  status: string;
  summary: ValidationSummary | null;
}) {
  const { t, tn } = useI18n();
  const [busyFormat, setBusyFormat] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const blockers = summary?.blockers ?? 0;
  const approved = status === 'approved' || status === 'exported';

  const formats = [
    {
      id: 'docx' as const,
      label: t('export.formatDocx'),
      note: t('export.noteDocx'),
      needsApproval: true,
    },
    {
      id: 'pdf' as const,
      label: t('export.formatPdf'),
      note: t('export.notePdf'),
      needsApproval: true,
    },
    {
      id: 'html' as const,
      label: t('export.formatHtml'),
      note: t('export.noteHtml'),
      needsApproval: false,
    },
  ];

  async function handleExport(format: 'html' | 'docx' | 'pdf') {
    setBusyFormat(format);
    setError(null);
    setMessage(null);
    try {
      const result = await createExport(contractId, format);
      const blob = await fetchExportContent(contractId, result.export_id);
      saveBlob(blob, `contract-${contractId}.${format}`);
      setMessage(t('export.success', { format: format.toUpperCase(), id: result.export_id }));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : t('export.failed'));
    } finally {
      setBusyFormat(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-ink">{t('export.title')}</h2>
        <p className="text-sm text-muted">{t('export.subtitle')}</p>
      </div>

      {error ? (
        <Alert variant="danger" title={t('export.errorTitle')}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <p role="status" aria-live="polite" className="text-sm font-medium text-success">
          {message}
        </p>
      ) : null}

      {blockers > 0 ? (
        <Alert variant="warning" title={tn('export.blockers', blockers)}>
          {t('export.resolveBlockers')}
        </Alert>
      ) : null}

      <ul className="grid gap-4 sm:grid-cols-3">
        {formats.map((format) => {
          const disabled =
            blockers > 0 || (format.needsApproval && !approved) || busyFormat !== null;
          return (
            <li key={format.id}>
              <Card>
                <CardHeader>
                  <CardTitle>{format.label}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  <p className="text-sm text-muted">{format.note}</p>
                  {format.needsApproval && !approved ? (
                    <p className="text-sm font-medium text-warning">{t('export.needsApproval')}</p>
                  ) : null}
                  <Button
                    variant="primary"
                    onClick={() => void handleExport(format.id)}
                    loading={busyFormat === format.id}
                    loadingText={t('export.exporting')}
                    disabled={disabled}
                  >
                    {t('export.button', { format: format.id.toUpperCase() })}
                  </Button>
                </CardContent>
              </Card>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
