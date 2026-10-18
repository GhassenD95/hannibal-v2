'use client';

import * as React from 'react';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import { ApiError } from '@/lib/api';
import { createSection, regenerateSection, sectionEvidence, updateSection } from '@/lib/contracts';
import { useI18n } from '@/lib/i18n/context';
import type { ContractSection, EvidenceItem } from '@/lib/types';

type EvidenceState =
  | { kind: 'closed' }
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'open'; items: EvidenceItem[] };

export function SectionsPanel({
  contractId,
  sections,
  refresh,
}: {
  contractId: number;
  sections: ContractSection[];
  refresh: () => Promise<void>;
}) {
  const { t } = useI18n();
  const [evidenceState, setEvidenceState] = React.useState<Record<number, EvidenceState>>({});
  const [editingId, setEditingId] = React.useState<number | null>(null);
  const [editText, setEditText] = React.useState('');
  const [busyId, setBusyId] = React.useState<number | 'new' | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [panelError, setPanelError] = React.useState<string | null>(null);
  const [adding, setAdding] = React.useState(false);
  const [newTitle, setNewTitle] = React.useState('');
  const [newOrder, setNewOrder] = React.useState('');

  async function toggleEvidence(sectionId: number) {
    const current = evidenceState[sectionId];
    if (current && current.kind !== 'closed') {
      setEvidenceState((state) => ({
        ...state,
        [sectionId]: { kind: 'closed' },
      }));
      return;
    }
    setEvidenceState((state) => ({
      ...state,
      [sectionId]: { kind: 'loading' },
    }));
    try {
      const result = await sectionEvidence(contractId, sectionId);
      setEvidenceState((state) => ({
        ...state,
        [sectionId]: { kind: 'open', items: result.evidence ?? [] },
      }));
    } catch (exc) {
      setEvidenceState((state) => ({
        ...state,
        [sectionId]: {
          kind: 'error',
          message: exc instanceof ApiError ? exc.message : t('sections.unableLoadEvidence'),
        },
      }));
    }
  }

  function startEdit(section: ContractSection) {
    setEditingId(section.id);
    setEditText(section.content);
    setPanelError(null);
    setMessage(null);
  }

  async function saveEdit(sectionId: number) {
    setBusyId(sectionId);
    setPanelError(null);
    setMessage(null);
    try {
      await updateSection(contractId, sectionId, { content: editText });
      await refresh();
      setEditingId(null);
      setMessage(t('sections.saved'));
    } catch (exc) {
      setPanelError(exc instanceof ApiError ? exc.message : t('sections.saveFailed'));
    } finally {
      setBusyId(null);
    }
  }

  async function regenerate(sectionId: number) {
    setBusyId(sectionId);
    setPanelError(null);
    setMessage(null);
    try {
      const result = await regenerateSection(contractId, sectionId);
      await refresh();
      setEvidenceState((state) => ({
        ...state,
        [sectionId]: { kind: 'closed' },
      }));
      setMessage(
        t('sections.regenerated', {
          title: result.title,
          status: result.status.replace('_', ' '),
        }),
      );
    } catch (exc) {
      setPanelError(exc instanceof ApiError ? exc.message : t('sections.regenerationFailed'));
    } finally {
      setBusyId(null);
    }
  }

  async function addSection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newTitle.trim()) {
      setPanelError(t('sections.enterTitle'));
      return;
    }
    setBusyId('new');
    setPanelError(null);
    try {
      const order = newOrder.trim() ? Number(newOrder) : sections.length + 1;
      await createSection(
        contractId,
        newTitle.trim(),
        Number.isFinite(order) ? order : sections.length + 1,
      );
      await refresh();
      setAdding(false);
      setNewTitle('');
      setNewOrder('');
      setMessage(t('sections.added'));
    } catch (exc) {
      setPanelError(exc instanceof ApiError ? exc.message : t('sections.addFailed'));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">{t('sections.title')}</h2>
          <p className="text-sm text-muted">{t('sections.subtitle')}</p>
        </div>
        <Button variant="secondary" onClick={() => setAdding((value) => !value)}>
          {adding ? t('sections.cancel') : t('sections.addManual')}
        </Button>
      </div>

      {message ? (
        <p role="status" aria-live="polite" className="text-sm font-medium text-success">
          {message}
        </p>
      ) : null}
      {panelError ? <Alert variant="danger">{panelError}</Alert> : null}

      {adding ? (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle>{t('sections.addManual')}</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-wrap items-end gap-4"
              onSubmit={(event) => void addSection(event)}
            >
              <FormField
                id="section-title"
                label={t('sections.titleLabel')}
                required
                className="min-w-64 flex-1"
              >
                <Input
                  id="section-title"
                  value={newTitle}
                  onChange={(event) => setNewTitle(event.target.value)}
                  placeholder={t('sections.titlePlaceholder')}
                  required
                />
              </FormField>
              <FormField
                id="section-order"
                label={t('sections.orderLabel')}
                hint={t('sections.orderHint')}
              >
                <Input
                  id="section-order"
                  type="number"
                  min={1}
                  value={newOrder}
                  onChange={(event) => setNewOrder(event.target.value)}
                  className="w-28"
                />
              </FormField>
              <Button
                type="submit"
                variant="primary"
                loading={busyId === 'new'}
                loadingText={t('sections.adding')}
              >
                {t('sections.add')}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {sections.length === 0 ? (
        <EmptyState title={t('sections.emptyTitle')} description={t('sections.emptyDescription')} />
      ) : (
        <ol className="flex flex-col gap-4">
          {sections.map((section, index) => {
            const evidence = evidenceState[section.id] ?? { kind: 'closed' };
            const editing = editingId === section.id;
            const busy = busyId === section.id;
            const evidenceCount = section.evidence_ids?.length ?? 0;
            return (
              <li key={section.id}>
                <Card>
                  <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold text-muted">{index + 1}</span>
                      <CardTitle>{section.title}</CardTitle>
                      <StatusBadge status={section.status} />
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => void toggleEvidence(section.id)}
                        aria-expanded={evidence.kind !== 'closed'}
                      >
                        {evidence.kind === 'closed'
                          ? t('sections.evidence', { count: evidenceCount })
                          : t('sections.hideEvidence')}
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => (editing ? setEditingId(null) : startEdit(section))}
                        disabled={busy}
                      >
                        {editing ? t('sections.cancelEdit') : t('sections.edit')}
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => void regenerate(section.id)}
                        loading={busy}
                        loadingText={t('sections.regenerating')}
                        disabled={busy}
                      >
                        {t('sections.regenerate')}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    {editing ? (
                      <div className="flex flex-col gap-3">
                        <FormField id={`edit-${section.id}`} label={t('sections.contentLabel')}>
                          <Textarea
                            id={`edit-${section.id}`}
                            rows={10}
                            value={editText}
                            onChange={(event) => setEditText(event.target.value)}
                            className="font-serif"
                          />
                        </FormField>
                        <div className="flex gap-2">
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => void saveEdit(section.id)}
                            loading={busy}
                            loadingText={t('sections.saving')}
                          >
                            {t('sections.saveChanges')}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditingId(null)}
                            disabled={busy}
                          >
                            {t('sections.discard')}
                          </Button>
                        </div>
                      </div>
                    ) : section.content ? (
                      <div className="document-body rounded-md border border-line bg-surface px-4 py-3 text-ink">
                        {section.content}
                      </div>
                    ) : (
                      <p className="rounded-md border border-dashed border-line bg-surface px-4 py-3 text-sm text-muted">
                        {t('sections.noContent')}
                      </p>
                    )}

                    <div className="flex flex-wrap items-center gap-2">
                      {(section.clause_ids ?? []).map((clauseId) => (
                        <Badge key={`clause-${clauseId}`} variant="primary">
                          {t('sections.approvedClause', { id: clauseId })}
                        </Badge>
                      ))}
                      {(section.evidence_ids ?? []).map((evidenceId) => (
                        <Badge key={`ev-${evidenceId}`} variant="evidence">
                          {t('sections.sourceBadge', { id: evidenceId })}
                        </Badge>
                      ))}
                      {(section.facts_used ?? []).map((fact) => (
                        <Badge key={`fact-${fact}`} variant="neutral">
                          {t('sections.factBadge', { name: fact })}
                        </Badge>
                      ))}
                      {(section.clause_ids ?? []).length === 0 &&
                      (section.evidence_ids ?? []).length === 0 &&
                      (section.facts_used ?? []).length === 0 ? (
                        <span className="text-xs text-muted">{t('sections.noAttachments')}</span>
                      ) : null}
                    </div>

                    {evidence.kind === 'loading' ? (
                      <LoadingState label={t('sections.evidenceLoading')} />
                    ) : evidence.kind === 'error' ? (
                      <ErrorState
                        message={evidence.message}
                        onRetry={() => void toggleEvidence(section.id)}
                      />
                    ) : evidence.kind === 'open' ? (
                      evidence.items.length === 0 ? (
                        <EmptyState
                          title={t('sections.evidenceEmptyTitle')}
                          description={t('sections.evidenceEmptyDescription')}
                        />
                      ) : (
                        <div className="flex flex-col gap-3 animate-slide-in">
                          <h4 className="text-sm font-semibold text-evidence">
                            {t('sections.evidenceFor', { title: section.title })}
                          </h4>
                          <ul className="flex flex-col gap-3">
                            {evidence.items.map((item, itemIndex) => (
                              <li
                                key={`${item.source_id}-${itemIndex}`}
                                className="rounded-md border border-sky-200 bg-sky-50/60 px-4 py-3"
                              >
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge variant="evidence">
                                    {t('sections.sourceBadge', { id: item.source_id })}
                                  </Badge>
                                  <span className="text-sm font-medium text-ink">{item.title}</span>
                                  {item.jurisdiction ? (
                                    <Badge variant="neutral">{item.jurisdiction}</Badge>
                                  ) : null}
                                  {item.language ? (
                                    <Badge variant="neutral">{item.language}</Badge>
                                  ) : null}
                                  {item.article ? (
                                    <Badge variant="neutral">{item.article}</Badge>
                                  ) : null}
                                  {item.page_start ? (
                                    <span className="text-xs text-muted">
                                      p. {item.page_start}
                                      {item.page_end ? `–${item.page_end}` : ''}
                                    </span>
                                  ) : null}
                                </div>
                                <blockquote className="document-body mt-2 border-s-2 border-evidence/40 ps-3 text-ink">
                                  {item.excerpt}
                                </blockquote>
                                {item.relevance_reason ? (
                                  <p className="mt-2 text-xs text-muted">
                                    {t('sections.whyItApplies', { reason: item.relevance_reason })}
                                  </p>
                                ) : null}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )
                    ) : null}
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
