'use client';

import * as React from 'react';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table';
import { ApiError } from '@/lib/api';
import { listFixtures, listRuns, runEvaluation } from '@/lib/evaluation';
import { useI18n } from '@/lib/i18n/context';
import type { EvaluationMetrics, EvaluationRun, EvaluationRunResult } from '@/lib/types';

const GROUP_KEYS: Array<keyof EvaluationMetrics | 'forbidden_claims_hit_rate'> = [
  'extraction',
  'retrieval',
  'planning',
  'generation',
  'validation',
  'system',
  'forbidden_claims_hit_rate',
];

function formatValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(3);
}

function renderMetricValue(value: unknown): React.ReactNode {
  if (typeof value === 'number') return formatValue(value);
  if (typeof value === 'string') return value;
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return '—';
    return (
      <ul className="flex flex-col gap-0.5">
        {entries.map(([name, nested]) => (
          <li key={name} className="flex items-baseline justify-between gap-3">
            <span className="text-xs text-muted">{name}</span>
            <span className="text-xs font-medium text-ink">{renderMetricValue(nested)}</span>
          </li>
        ))}
      </ul>
    );
  }
  return '—';
}

export default function EvaluationPage() {
  const { t } = useI18n();
  const [runs, setRuns] = React.useState<EvaluationRun[] | null>(null);
  const [runsError, setRunsError] = React.useState<string | null>(null);
  const [runsAttempt, setRunsAttempt] = React.useState(0);
  const [lastRun, setLastRun] = React.useState<EvaluationRunResult | null>(null);
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [fixtureCount, setFixtureCount] = React.useState<number | null>(null);

  const groupLabels: Record<(typeof GROUP_KEYS)[number], string> = {
    extraction: t('evaluation.extraction'),
    retrieval: t('evaluation.retrieval'),
    planning: t('evaluation.planning'),
    generation: t('evaluation.generation'),
    validation: t('evaluation.validation'),
    system: t('evaluation.system'),
    forbidden_claims_hit_rate: t('evaluation.forbiddenRate'),
  };

  React.useEffect(() => {
    let cancelled = false;
    listRuns()
      .then((result) => {
        if (!cancelled) {
          setRuns(result);
          setRunsError(null);
        }
      })
      .catch((exc: unknown) => {
        if (!cancelled) {
          setRuns([]);
          setRunsError(exc instanceof ApiError ? exc.message : t('evaluation.loadRunsFailed'));
        }
      });
    listFixtures()
      .then((result) => {
        if (!cancelled) setFixtureCount(result.length);
      })
      .catch(() => {
        if (!cancelled) setFixtureCount(null);
      });
    return () => {
      cancelled = true;
    };
  }, [runsAttempt, t]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const result = await runEvaluation();
      setLastRun(result);
      const refreshed = await listRuns().catch(() => null);
      if (refreshed) setRuns(refreshed);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : t('evaluation.runFailed'));
    } finally {
      setRunning(false);
    }
  }

  const metrics = lastRun?.metrics ?? null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-muted">
            {t('evaluation.eyebrow')}
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-ink">{t('evaluation.title')}</h1>
          <p className="mt-2 text-sm text-muted">{t('evaluation.subtitle')}</p>
        </div>
        <Button
          variant="primary"
          onClick={() => void handleRun()}
          loading={running}
          loadingText={t('evaluation.running')}
          disabled={running}
        >
          {t('evaluation.run')}
        </Button>
      </div>

      {error ? (
        <Alert variant="danger" title={t('evaluation.runFailedTitle')}>
          {error}
        </Alert>
      ) : null}

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="rounded-md border border-line bg-white px-4 py-3">
          <dt className="text-xs uppercase tracking-wide text-muted">{t('evaluation.fixtures')}</dt>
          <dd className="text-xl font-semibold text-ink">
            {fixtureCount === null ? '—' : fixtureCount}
          </dd>
        </div>
        <div className="rounded-md border border-line bg-white px-4 py-3">
          <dt className="text-xs uppercase tracking-wide text-muted">
            {t('evaluation.runsRecorded')}
          </dt>
          <dd className="text-xl font-semibold text-ink">{runs === null ? '…' : runs.length}</dd>
        </div>
        <div className="rounded-md border border-line bg-white px-4 py-3">
          <dt className="text-xs uppercase tracking-wide text-muted">
            {t('evaluation.lastStatus')}
          </dt>
          <dd className="text-xl font-semibold text-ink">
            {lastRun ? t('evaluation.finished') : runs && runs[0] ? runs[0].status : '—'}
          </dd>
        </div>
      </dl>

      {metrics ? (
        <section aria-labelledby="metrics-heading" className="flex flex-col gap-3">
          <h2 id="metrics-heading" className="text-lg font-semibold text-ink">
            {t('evaluation.metricsTitle', { id: lastRun?.run_id ?? '' })}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {GROUP_KEYS.map((key) => {
              const group = metrics[key];
              const isForbidden = key === 'forbidden_claims_hit_rate';
              let body: React.ReactNode;
              if (typeof group === 'number') {
                body = (
                  <p className="text-2xl font-semibold text-ink">
                    {formatValue(group)}
                    {group >= 0 && group <= 1 ? (
                      <span className="ms-1 text-sm text-muted">{t('evaluation.rate')}</span>
                    ) : null}
                  </p>
                );
              } else if (group && typeof group === 'object') {
                const entries = Object.entries(group as Record<string, number>);
                body =
                  entries.length === 0 ? (
                    <p className="text-sm text-muted">{t('evaluation.noMetrics')}</p>
                  ) : (
                    <ul className="flex flex-col gap-1">
                      {entries.map(([name, value]) => (
                        <li key={name} className="flex items-baseline justify-between gap-3">
                          <span className="text-sm text-muted">{name}</span>
                          <span className="text-sm font-medium text-ink">{formatValue(value)}</span>
                        </li>
                      ))}
                    </ul>
                  );
              } else {
                body = <p className="text-sm text-muted">{t('evaluation.notRecorded')}</p>;
              }
              return (
                <div
                  key={key}
                  className={`rounded-md border px-4 py-3 ${
                    isForbidden ? 'border-amber-200 bg-amber-50/60' : 'border-line bg-white'
                  }`}
                >
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
                    {groupLabels[key]}
                  </h3>
                  <div className="mt-2">{body}</div>
                  {isForbidden && typeof group === 'number' && group > 0 ? (
                    <p className="mt-2 text-xs font-medium text-warning">
                      {t('evaluation.forbiddenWarning', { count: formatValue(group) })}
                    </p>
                  ) : null}
                </div>
              );
            })}
          </div>

          {lastRun && lastRun.per_fixture.length > 0 ? (
            <div className="mt-2">
              <h3 className="mb-2 text-sm font-semibold text-ink">{t('evaluation.perFixture')}</h3>
              <Table caption={t('evaluation.tableCaption')}>
                <THead>
                  <TR>
                    <TH scope="col">{t('evaluation.colFixture')}</TH>
                    <TH scope="col">{t('evaluation.colScores')}</TH>
                  </TR>
                </THead>
                <TBody>
                  {lastRun.per_fixture.map((row, index) => {
                    const id = typeof row.id === 'string' ? row.id : String(index);
                    return (
                      <TR key={id}>
                        <TD className="font-medium">
                          {typeof row.name === 'string'
                            ? row.name
                            : typeof row.id === 'string'
                              ? row.id
                              : `#${index}`}
                        </TD>
                        <TD>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(row)
                              .filter(([name]) => !['id', 'name'].includes(name))
                              .map(([name, value]) => (
                                <Badge key={name} variant="neutral">
                                  {name}: {renderMetricValue(value)}
                                </Badge>
                              ))}
                          </div>
                        </TD>
                      </TR>
                    );
                  })}
                </TBody>
              </Table>
            </div>
          ) : null}
        </section>
      ) : null}

      <section aria-labelledby="runs-heading" className="flex flex-col gap-3">
        <h2 id="runs-heading" className="text-lg font-semibold text-ink">
          {t('evaluation.runHistory')}
        </h2>
        {runsError ? (
          <ErrorState message={runsError} onRetry={() => setRunsAttempt((value) => value + 1)} />
        ) : runs === null ? (
          <LoadingState label={t('evaluation.loadingRuns')} />
        ) : runs.length === 0 ? (
          <EmptyState
            title={t('evaluation.noRunsTitle')}
            description={t('evaluation.noRunsDescription')}
          />
        ) : (
          <Table caption={t('evaluation.historyCaption')}>
            <THead>
              <TR>
                <TH scope="col">{t('evaluation.colRun')}</TH>
                <TH scope="col">{t('evaluation.colStatus')}</TH>
                <TH scope="col">{t('evaluation.colFixtures')}</TH>
                <TH scope="col">{t('evaluation.colStarted')}</TH>
                <TH scope="col">{t('evaluation.colCompleted')}</TH>
                <TH scope="col">{t('evaluation.colHeadline')}</TH>
              </TR>
            </THead>
            <TBody>
              {runs.map((run) => (
                <TR key={run.id}>
                  <TD className="font-medium">#{run.id}</TD>
                  <TD>
                    <StatusBadge status={run.status} />
                  </TD>
                  <TD>{run.total_fixtures}</TD>
                  <TD className="whitespace-nowrap text-sm text-muted">
                    {new Date(run.started_at).toLocaleString()}
                  </TD>
                  <TD className="whitespace-nowrap text-sm text-muted">
                    {run.completed_at ? new Date(run.completed_at).toLocaleString() : '—'}
                  </TD>
                  <TD>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(run.metrics ?? {})
                        .filter(
                          (entry): entry is [string, Record<string, number>] =>
                            Boolean(entry[1]) && typeof entry[1] === 'object',
                        )
                        .slice(0, 3)
                        .map(([name, group]) => (
                          <Badge key={name} variant="neutral">
                            {t('evaluation.metricCount', {
                              name,
                              count: Object.values(group).length,
                            })}
                          </Badge>
                        ))}
                    </div>
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
