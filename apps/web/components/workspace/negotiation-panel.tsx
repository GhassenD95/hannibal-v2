'use client';

import * as React from 'react';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FormField } from '@/components/ui/form-field';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { EmptyState, LoadingState } from '@/components/ui/states';
import { ApiError } from '@/lib/api';
import {
  analyzeNegotiation,
  createNegotiation,
  decideNegotiation,
  listNegotiations,
  proposeNegotiation,
  type NegotiationDecision,
} from '@/lib/contracts';
import { useI18n } from '@/lib/i18n/context';
import type { ContractSection, NegotiationItem } from '@/lib/types';

function parseAnalysis(raw: string | null): Record<string, unknown> | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (parsed && typeof parsed === 'object') return parsed as Record<string, unknown>;
    return null;
  } catch {
    return null;
  }
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

export function NegotiationPanel({
  contractId,
  sections,
  refreshSections,
}: {
  contractId: number;
  sections: ContractSection[];
  refreshSections: () => Promise<void>;
}) {
  const { t } = useI18n();
  const [items, setItems] = React.useState<NegotiationItem[] | null>(null);
  const [sectionId, setSectionId] = React.useState('');
  const [counterparty, setCounterparty] = React.useState('');
  const [creating, setCreating] = React.useState(false);
  const [busyId, setBusyId] = React.useState<number | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    try {
      const result = await listNegotiations(contractId);
      setItems(result);
      setError(null);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : t('negotiation.loadFailed'));
      setItems([]);
    }
  }, [contractId, t]);

  React.useEffect(() => {
    void load();
  }, [load]);

  React.useEffect(() => {
    if (!sectionId && sections.length > 0) {
      setSectionId(String(sections[0].id));
    }
  }, [sections, sectionId]);

  function replaceItem(updated: NegotiationItem) {
    setItems((current) => (current ?? []).map((item) => (item.id === updated.id ? updated : item)));
  }

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sectionId) {
      setError(t('negotiation.needSection'));
      return;
    }
    if (!counterparty.trim()) {
      setError(t('negotiation.needText'));
      return;
    }
    setCreating(true);
    setError(null);
    setMessage(null);
    try {
      const item = await createNegotiation(contractId, Number(sectionId), counterparty.trim());
      setItems((current) => [...(current ?? []), item]);
      setCounterparty('');
      setMessage(t('negotiation.created'));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : t('negotiation.createFailed'));
    } finally {
      setCreating(false);
    }
  }

  async function runItemAction(
    item: NegotiationItem,
    action: 'analyze' | 'propose' | NegotiationDecision,
  ) {
    setBusyId(item.id);
    setError(null);
    setMessage(null);
    try {
      let updated: NegotiationItem;
      let outcome: string;
      if (action === 'analyze') {
        updated = await analyzeNegotiation(contractId, item.id);
        outcome = t('negotiation.analyzed');
      } else if (action === 'propose') {
        updated = await proposeNegotiation(contractId, item.id);
        outcome = t('negotiation.proposed');
      } else {
        updated = await decideNegotiation(contractId, item.id, action);
        outcome = t('negotiation.decision', { decision: action });
        if (action === 'accepted') {
          await refreshSections();
          outcome = t('negotiation.accepted');
        }
      }
      replaceItem(updated);
      setMessage(outcome);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : t('negotiation.actionFailed'));
    } finally {
      setBusyId(null);
    }
  }

  if (items === null) return <LoadingState label={t('negotiation.loading')} />;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-ink">{t('negotiation.title')}</h2>
        <p className="text-sm text-muted">{t('negotiation.subtitle')}</p>
      </div>

      {error ? <Alert variant="danger">{error}</Alert> : null}
      {message ? (
        <p role="status" aria-live="polite" className="text-sm font-medium text-success">
          {message}
        </p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t('negotiation.newTitle')}</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={(event) => void handleCreate(event)}>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField id="nego-section" label={t('negotiation.sectionLabel')} required>
                <Select
                  id="nego-section"
                  value={sectionId}
                  onChange={(event) => setSectionId(event.target.value)}
                >
                  <option value="">{t('negotiation.selectSection')}</option>
                  {sections.map((section) => (
                    <option key={section.id} value={section.id}>
                      {section.title}
                    </option>
                  ))}
                </Select>
              </FormField>
            </div>
            <FormField
              id="nego-counterparty"
              label={t('negotiation.counterpartyLabel')}
              required
              hint={t('negotiation.counterpartyHint')}
            >
              <Textarea
                id="nego-counterparty"
                rows={3}
                value={counterparty}
                onChange={(event) => setCounterparty(event.target.value)}
                required
              />
            </FormField>
            <div>
              <Button
                type="submit"
                variant="primary"
                loading={creating}
                loadingText={t('negotiation.creating')}
              >
                {t('negotiation.addItem')}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {items.length === 0 ? (
        <EmptyState
          title={t('negotiation.emptyTitle')}
          description={t('negotiation.emptyDescription')}
        />
      ) : (
        <ul className="flex flex-col gap-4">
          {items.map((item) => {
            const analysis = parseAnalysis(item.hannibal_analysis);
            const busy = busyId === item.id;
            const sectionTitle =
              sections.find((section) => section.id === item.section_id)?.title ??
              (item.section_id
                ? t('negotiation.sectionRef', { id: item.section_id })
                : t('negotiation.noSection'));
            return (
              <li key={item.id}>
                <Card>
                  <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <CardTitle>{sectionTitle}</CardTitle>
                      <StatusBadge status={item.status} />
                      <Badge variant="neutral">{t('negotiation.itemBadge', { id: item.id })}</Badge>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => void runItemAction(item, 'analyze')}
                        loading={busy}
                        loadingText={t('negotiation.analyzing')}
                        disabled={busy}
                      >
                        {t('negotiation.analyze')}
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => void runItemAction(item, 'propose')}
                        loading={busy}
                        loadingText={t('negotiation.proposing')}
                        disabled={busy}
                      >
                        {t('negotiation.propose')}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wide text-muted">
                        {t('negotiation.counterpartyWording')}
                      </h4>
                      <blockquote className="document-body mt-1 border-s-2 border-line ps-3 text-ink">
                        {item.counterparty_clause || '—'}
                      </blockquote>
                    </div>

                    {analysis ? (
                      <div className="rounded-md border border-line bg-surface px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="text-sm font-semibold text-ink">
                            {t('negotiation.hannibalAnalysis')}
                          </h4>
                          {typeof analysis.risk_assessment === 'string' ? (
                            <StatusBadge status={analysis.risk_assessment} />
                          ) : null}
                          {analysis.requires_human_decision === true ? (
                            <Badge variant="warning">{t('negotiation.humanDecision')}</Badge>
                          ) : null}
                        </div>
                        {asStringArray(analysis.deviations).length > 0 ? (
                          <ul className="mt-2 list-disc ps-5 text-sm text-muted">
                            {asStringArray(analysis.deviations).map((deviation) => (
                              <li key={deviation}>{deviation}</li>
                            ))}
                          </ul>
                        ) : null}
                        {typeof analysis.recommendation === 'string' ? (
                          <p className="mt-2 text-sm text-muted">
                            {t('negotiation.recommendation', { text: analysis.recommendation })}
                          </p>
                        ) : null}
                      </div>
                    ) : (
                      <p className="text-sm text-muted">{t('negotiation.noAnalysis')}</p>
                    )}

                    {item.proposed_text ? (
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted">
                          {t('negotiation.proposedText')}
                        </h4>
                        <div className="document-body mt-1 rounded-md border border-line bg-white px-4 py-3 text-ink">
                          {item.proposed_text}
                        </div>
                      </div>
                    ) : null}

                    <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
                      <span className="text-xs font-semibold uppercase tracking-wide text-muted">
                        {t('negotiation.decide')}
                      </span>
                      {(['accepted', 'rejected', 'escalated'] as NegotiationDecision[]).map(
                        (decision) => (
                          <Button
                            key={decision}
                            variant={decision === 'accepted' ? 'secondary' : 'ghost'}
                            size="sm"
                            onClick={() => void runItemAction(item, decision)}
                            disabled={busy}
                            aria-label={t('negotiation.decisionAria', {
                              decision,
                              id: item.id,
                            })}
                          >
                            {t(`status.${decision}`)}
                          </Button>
                        ),
                      )}
                      {item.status !== 'pending' ? (
                        <span className="text-xs text-muted">
                          {t('negotiation.currentDecision', { status: item.status })}
                        </span>
                      ) : null}
                    </div>
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
