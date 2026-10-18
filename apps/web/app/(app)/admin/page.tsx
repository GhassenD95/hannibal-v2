'use client';

import * as React from 'react';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import { Table, TBody, TD, TH, THead, TR } from '@/components/ui/table';
import { Tabs, TabItem, TabsPanel } from '@/components/ui/tabs';
import { ApiError } from '@/lib/api';
import {
  activatePack,
  archiveClause,
  archivePack,
  archiveSource,
  approveSource,
  createClause,
  createSource,
  importPack,
  listClauses,
  listPacks,
  listSources,
  testRetrieval,
  validatePack,
} from '@/lib/admin';
import { useI18n } from '@/lib/i18n/context';
import type { ClauseItem, PackObject, RetrievalHit, SourceItem } from '@/lib/types';

function useAsyncList<T>(loader: () => Promise<T[]>) {
  const { t } = useI18n();
  const [items, setItems] = React.useState<T[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);

  React.useEffect(() => {
    let cancelled = false;
    setItems(null);
    loader()
      .then((result) => {
        if (!cancelled) {
          setItems(result);
          setError(null);
        }
      })
      .catch((exc: unknown) => {
        if (!cancelled) {
          setItems([]);
          setError(exc instanceof ApiError ? exc.message : t('admin.loadListFailed'));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [loader, attempt, t]);

  return {
    items,
    error,
    retry: () => setAttempt((value) => value + 1),
    setItems,
    setError,
  };
}

export default function AdminPage() {
  const { t, tn } = useI18n();
  const [tab, setTab] = React.useState('packs');

  const loadPacks = React.useCallback(() => listPacks(), []);
  const loadSources = React.useCallback(() => listSources(), []);
  const loadClauses = React.useCallback(() => listClauses(), []);

  const packs = useAsyncList<PackObject>(loadPacks);
  const sources = useAsyncList<SourceItem>(loadSources);
  const clauses = useAsyncList<ClauseItem>(loadClauses);

  const tabs: TabItem[] = [
    { value: 'packs', label: t('admin.tabPacks') },
    { value: 'sources', label: t('admin.tabSources') },
    { value: 'clauses', label: t('admin.tabClauses') },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-muted">
          {t('admin.eyebrow')}
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-ink">{t('admin.title')}</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted">{t('admin.subtitle')}</p>
      </div>

      <Tabs items={tabs} value={tab} onChange={setTab} label={t('admin.sectionsAria')}>
        <TabsPanel value="packs">
          <PacksTab state={packs} />
        </TabsPanel>
        <TabsPanel value="sources">
          <SourcesTab state={sources} />
        </TabsPanel>
        <TabsPanel value="clauses">
          <ClausesTab state={clauses} />
        </TabsPanel>
      </Tabs>
    </div>
  );
}

interface ListState<T> {
  items: T[] | null;
  error: string | null;
  retry: () => void;
}

function PacksTab({ state }: { state: ListState<PackObject> }) {
  const { t, tn } = useI18n();
  const { items, error, retry } = state;
  const [message, setMessage] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [busyId, setBusyId] = React.useState<number | null>(null);
  const [importPath, setImportPath] = React.useState('');
  const [importing, setImporting] = React.useState(false);
  const [issues, setIssues] = React.useState<Record<number, string[]>>({});

  async function runAction(packId: number, action: 'validate' | 'activate' | 'archive') {
    setBusyId(packId);
    setActionError(null);
    setMessage(null);
    try {
      if (action === 'validate') {
        const result = await validatePack(packId);
        setIssues((current) => ({ ...current, [packId]: result.issues }));
        setMessage(
          result.valid
            ? `${t('adminPacks.validationPrefix', { id: packId })} ${t('adminPacks.noIssues')}`
            : `${t('adminPacks.validationPrefix', { id: packId })} ${tn(
                'adminPacks.issueCount',
                result.issues.length,
              )}.`,
        );
      } else if (action === 'activate') {
        const pack = await activatePack(packId);
        state.retry();
        setMessage(t('adminPacks.activated', { name: pack.name }));
      } else {
        const pack = await archivePack(packId);
        state.retry();
        setMessage(t('adminPacks.archived', { name: pack.name }));
      }
    } catch (exc) {
      setActionError(
        exc instanceof ApiError ? exc.message : t('adminPacks.actionFailed', { action }),
      );
    } finally {
      setBusyId(null);
    }
  }

  async function handleImport(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!importPath.trim()) {
      setActionError(t('adminPacks.pathRequired'));
      return;
    }
    setImporting(true);
    setActionError(null);
    setMessage(null);
    try {
      const pack = await importPack(importPath.trim());
      setImportPath('');
      state.retry();
      setMessage(t('adminPacks.imported', { name: pack.name, id: pack.id }));
    } catch (exc) {
      setActionError(exc instanceof ApiError ? exc.message : t('adminPacks.importFailed'));
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>{t('adminPacks.importTitle')}</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(event) => void handleImport(event)}
          >
            <FormField
              id="pack-path"
              label={t('adminPacks.pathLabel')}
              hint={t('adminPacks.pathHint')}
              className="w-full sm:w-auto sm:flex-1 sm:min-w-72"
            >
              <Input
                id="pack-path"
                value={importPath}
                onChange={(event) => setImportPath(event.target.value)}
                placeholder={t('adminPacks.pathPlaceholder')}
              />
            </FormField>
            <Button
              type="submit"
              variant="primary"
              loading={importing}
              loadingText={t('adminPacks.importing')}
            >
              {t('adminPacks.import')}
            </Button>
          </form>
        </CardContent>
      </Card>

      {message ? (
        <p role="status" aria-live="polite" className="text-sm font-medium text-success">
          {message}
        </p>
      ) : null}
      {actionError ? <Alert variant="danger">{actionError}</Alert> : null}
      {error ? <ErrorState message={error} onRetry={retry} /> : null}

      {items === null ? (
        <LoadingState label={t('adminPacks.loading')} />
      ) : items.length === 0 ? (
        <EmptyState
          title={t('adminPacks.emptyTitle')}
          description={t('adminPacks.emptyDescription')}
        />
      ) : (
        <ul className="flex flex-col gap-4">
          {items.map((pack) => (
            <li key={pack.id}>
              <Card>
                <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <CardTitle>{pack.name}</CardTitle>
                    <StatusBadge status={pack.status} />
                    <Badge variant="neutral">
                      {t('adminPacks.version', { version: pack.version })}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => void runAction(pack.id, 'validate')}
                      loading={busyId === pack.id}
                      loadingText={t('adminPacks.validating')}
                      disabled={busyId !== null}
                    >
                      {t('adminPacks.validate')}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => void runAction(pack.id, 'activate')}
                      loading={busyId === pack.id}
                      loadingText={t('adminPacks.activating')}
                      disabled={pack.status === 'active' || busyId !== null}
                    >
                      {t('adminPacks.activate')}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void runAction(pack.id, 'archive')}
                      loading={busyId === pack.id}
                      loadingText={t('adminPacks.archiving')}
                      disabled={pack.status === 'archived' || busyId !== null}
                    >
                      {t('adminPacks.archive')}
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  {pack.description ? (
                    <p className="text-sm text-muted">{pack.description}</p>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="primary">
                      {Array.isArray(pack.contractTypes)
                        ? tn('adminPacks.contractTypeCount', pack.contractTypes.length)
                        : t('adminPacks.contractTypesUnknown')}
                    </Badge>
                    <Badge variant="neutral">
                      {t('adminPacks.clauses', { count: pack.clauseCount ?? 0 })}
                    </Badge>
                    <Badge variant="neutral">
                      {t('adminPacks.sources', { count: pack.sourceCount ?? 0 })}
                    </Badge>
                    <Badge variant="neutral">
                      {t('adminPacks.rules', { count: pack.validationRuleCount ?? 0 })}
                    </Badge>
                    {pack.riskPlaybookName ? (
                      <Badge variant="evidence">
                        {t('adminPacks.playbook', { name: pack.riskPlaybookName })}
                      </Badge>
                    ) : null}
                  </div>
                  {issues[pack.id]?.length ? (
                    <Alert variant="warning" title={t('adminPacks.issuesTitle')}>
                      <ul className="list-disc ps-5">
                        {issues[pack.id].map((issue) => (
                          <li key={issue}>{issue}</li>
                        ))}
                      </ul>
                    </Alert>
                  ) : null}
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SourcesTab({ state }: { state: ListState<SourceItem> }) {
  const { t } = useI18n();
  const { items, error, retry } = state;
  const [query, setQuery] = React.useState('');
  const [topK, setTopK] = React.useState('5');
  const [searching, setSearching] = React.useState(false);
  const [hits, setHits] = React.useState<RetrievalHit[] | null>(null);
  const [searchError, setSearchError] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busyId, setBusyId] = React.useState<number | null>(null);
  const [adding, setAdding] = React.useState(false);
  const [newTitle, setNewTitle] = React.useState('');
  const [newJurisdiction, setNewJurisdiction] = React.useState('MA');
  const [newType, setNewType] = React.useState('law');

  async function runAction(sourceId: number, action: 'approve' | 'archive') {
    setBusyId(sourceId);
    setActionError(null);
    setMessage(null);
    try {
      if (action === 'approve') {
        await approveSource(sourceId);
        setMessage(t('adminSources.approved', { id: sourceId }));
      } else {
        await archiveSource(sourceId);
        setMessage(t('adminSources.archived', { id: sourceId }));
      }
      state.retry();
    } catch (exc) {
      setActionError(
        exc instanceof ApiError ? exc.message : t('adminSources.actionFailed', { action }),
      );
    } finally {
      setBusyId(null);
    }
  }

  async function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) {
      setSearchError(t('adminSources.queryRequired'));
      return;
    }
    setSearching(true);
    setSearchError(null);
    setHits(null);
    try {
      const result = await testRetrieval(query.trim(), Number(topK) || 5);
      setHits(result.hits);
    } catch (exc) {
      setSearchError(exc instanceof ApiError ? exc.message : t('adminSources.searchFailed'));
    } finally {
      setSearching(false);
    }
  }

  async function handleAdd(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newTitle.trim()) {
      setActionError(t('adminSources.titleRequired'));
      return;
    }
    setActionError(null);
    try {
      const created = await createSource({
        title: newTitle.trim(),
        jurisdiction: newJurisdiction.trim() || 'MA',
        source_type: newType,
      });
      setNewTitle('');
      setAdding(false);
      state.retry();
      setMessage(t('adminSources.created', { id: created.id, status: created.status }));
    } catch (exc) {
      setActionError(exc instanceof ApiError ? exc.message : t('adminSources.createFailed'));
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>{t('adminSources.testTitle')}</CardTitle>
          <Button variant="secondary" size="sm" onClick={() => setAdding((value) => !value)}>
            {adding ? t('adminSources.cancel') : t('adminSources.addSource')}
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(event) => void handleSearch(event)}
          >
            <FormField
              id="retrieval-query"
              label={t('adminSources.queryLabel')}
              className="w-full sm:w-auto sm:flex-1 sm:min-w-72"
            >
              <Input
                id="retrieval-query"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t('adminSources.queryPlaceholder')}
              />
            </FormField>
            <FormField id="retrieval-topk" label={t('adminSources.topK')}>
              <Input
                id="retrieval-topk"
                type="number"
                min={1}
                max={20}
                value={topK}
                onChange={(event) => setTopK(event.target.value)}
                className="w-24"
              />
            </FormField>
            <Button
              type="submit"
              variant="primary"
              loading={searching}
              loadingText={t('adminSources.searching')}
            >
              {t('adminSources.runRetrieval')}
            </Button>
          </form>

          {searchError ? <Alert variant="danger">{searchError}</Alert> : null}

          {hits !== null ? (
            hits.length === 0 ? (
              <EmptyState
                title={t('adminSources.noHitsTitle')}
                description={t('adminSources.noHitsDescription')}
              />
            ) : (
              <ul className="flex flex-col gap-3">
                {hits.map((hit, index) => (
                  <li
                    key={`${hit.source_id}-${index}`}
                    className="rounded-md border border-sky-200 bg-sky-50/60 px-4 py-3"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="evidence">
                        {t('adminSources.sourceBadge', { id: hit.source_id })}
                      </Badge>
                      <span className="text-sm font-medium text-ink">{hit.title}</span>
                      {hit.jurisdiction ? (
                        <Badge variant="neutral">{hit.jurisdiction}</Badge>
                      ) : null}
                      {hit.article ? <Badge variant="neutral">{hit.article}</Badge> : null}
                      {typeof hit.relevance === 'number' ? (
                        <span className="text-xs text-muted">
                          {t('adminSources.relevance', { value: hit.relevance.toFixed(3) })}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm text-ink">{hit.content}</p>
                  </li>
                ))}
              </ul>
            )
          ) : null}

          {adding ? (
            <form
              className="flex flex-wrap items-end gap-3 border-t border-line pt-4"
              onSubmit={(event) => void handleAdd(event)}
            >
              <FormField
                id="source-title"
                label={t('adminSources.titleLabel')}
                className="min-w-64 flex-1"
              >
                <Input
                  id="source-title"
                  value={newTitle}
                  onChange={(event) => setNewTitle(event.target.value)}
                  placeholder={t('adminSources.titlePlaceholder')}
                />
              </FormField>
              <FormField id="source-jurisdiction" label={t('adminSources.jurisdictionLabel')}>
                <Input
                  id="source-jurisdiction"
                  value={newJurisdiction}
                  onChange={(event) => setNewJurisdiction(event.target.value)}
                  className="w-28"
                />
              </FormField>
              <FormField id="source-type" label={t('adminSources.typeLabel')}>
                <Select
                  id="source-type"
                  value={newType}
                  onChange={(event) => setNewType(event.target.value)}
                >
                  <option value="law">law</option>
                  <option value="regulation">regulation</option>
                  <option value="code">code</option>
                </Select>
              </FormField>
              <Button type="submit" variant="primary">
                {t('adminSources.createSource')}
              </Button>
            </form>
          ) : null}
        </CardContent>
      </Card>

      {message ? (
        <p role="status" aria-live="polite" className="text-sm font-medium text-success">
          {message}
        </p>
      ) : null}
      {actionError ? <Alert variant="danger">{actionError}</Alert> : null}
      {error ? <ErrorState message={error} onRetry={retry} /> : null}

      {items === null ? (
        <LoadingState label={t('adminSources.loading')} />
      ) : items.length === 0 ? (
        <EmptyState
          title={t('adminSources.emptyTitle')}
          description={t('adminSources.emptyDescription')}
        />
      ) : (
        <Table caption={t('adminSources.tableCaption')}>
          <THead>
            <TR>
              <TH scope="col">{t('adminSources.colSource')}</TH>
              <TH scope="col">{t('adminSources.colJurisdiction')}</TH>
              <TH scope="col">{t('adminSources.colVersion')}</TH>
              <TH scope="col">{t('adminSources.colChunks')}</TH>
              <TH scope="col">{t('adminSources.colEffective')}</TH>
              <TH scope="col">{t('adminSources.colStatus')}</TH>
              <TH scope="col">{t('adminSources.colActions')}</TH>
            </TR>
          </THead>
          <TBody>
            {items.map((source) => (
              <TR key={source.id}>
                <TD>
                  <span className="font-medium">{source.title}</span>
                  <span className="ms-2 text-xs text-muted">#{source.id}</span>
                </TD>
                <TD>{source.jurisdiction}</TD>
                <TD className="text-sm text-muted">{source.version || '—'}</TD>
                <TD className="text-sm text-muted">{source.chunk_count ?? 0}</TD>
                <TD className="text-sm text-muted">
                  {source.effective_date
                    ? new Date(source.effective_date).toLocaleDateString()
                    : '—'}
                </TD>
                <TD>
                  <StatusBadge status={source.status} />
                </TD>
                <TD>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => void runAction(source.id, 'approve')}
                      loading={busyId === source.id}
                      loadingText={t('adminSources.approving')}
                      disabled={source.status === 'approved' || busyId !== null}
                    >
                      {t('adminSources.approve')}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void runAction(source.id, 'archive')}
                      loading={busyId === source.id}
                      loadingText={t('adminSources.archiving')}
                      disabled={source.status === 'archived' || busyId !== null}
                    >
                      {t('adminSources.archive')}
                    </Button>
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}

function ClausesTab({ state }: { state: ListState<ClauseItem> }) {
  const { t } = useI18n();
  const { items, error, retry } = state;
  const [adding, setAdding] = React.useState(false);
  const [title, setTitle] = React.useState('');
  const [content, setContent] = React.useState('');
  const [contractType, setContractType] = React.useState('service_agreement');
  const [clauseType, setClauseType] = React.useState('optional');
  const [saving, setSaving] = React.useState(false);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busyId, setBusyId] = React.useState<number | null>(null);

  async function handleAdd(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !content.trim()) {
      setActionError(t('adminClauses.required'));
      return;
    }
    setSaving(true);
    setActionError(null);
    try {
      const created = await createClause({
        title: title.trim(),
        content: content.trim(),
        contract_type: contractType,
        clause_type: clauseType,
      });
      setTitle('');
      setContent('');
      setAdding(false);
      state.retry();
      setMessage(t('adminClauses.created', { id: created.id, status: created.status }));
    } catch (exc) {
      setActionError(exc instanceof ApiError ? exc.message : t('adminClauses.createFailed'));
    } finally {
      setSaving(false);
    }
  }

  async function handleArchive(clauseId: number) {
    setBusyId(clauseId);
    setActionError(null);
    setMessage(null);
    try {
      await archiveClause(clauseId);
      state.retry();
      setMessage(t('adminClauses.archived', { id: clauseId }));
    } catch (exc) {
      setActionError(exc instanceof ApiError ? exc.message : t('adminClauses.archiveFailed'));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">{t('adminClauses.subtitle')}</p>
        <Button variant="secondary" onClick={() => setAdding((value) => !value)}>
          {adding ? t('adminClauses.cancel') : t('adminClauses.addClause')}
        </Button>
      </div>

      {message ? (
        <p role="status" aria-live="polite" className="text-sm font-medium text-success">
          {message}
        </p>
      ) : null}
      {actionError ? <Alert variant="danger">{actionError}</Alert> : null}

      {adding ? (
        <Card>
          <CardHeader>
            <CardTitle>{t('adminClauses.newTitle')}</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="flex flex-col gap-4" onSubmit={(event) => void handleAdd(event)}>
              <div className="grid gap-4 sm:grid-cols-3">
                <FormField id="clause-title" label={t('adminClauses.titleLabel')} required>
                  <Input
                    id="clause-title"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    required
                  />
                </FormField>
                <FormField id="clause-type" label={t('adminClauses.contractTypeLabel')}>
                  <Select
                    id="clause-type"
                    value={contractType}
                    onChange={(event) => setContractType(event.target.value)}
                  >
                    <option value="service_agreement">service_agreement</option>
                    <option value="nda">nda</option>
                  </Select>
                </FormField>
                <FormField id="clause-kind" label={t('adminClauses.clauseTypeLabel')}>
                  <Select
                    id="clause-kind"
                    value={clauseType}
                    onChange={(event) => setClauseType(event.target.value)}
                  >
                    <option value="optional">optional</option>
                    <option value="mandatory">mandatory</option>
                  </Select>
                </FormField>
              </div>
              <FormField id="clause-content" label={t('adminClauses.contentLabel')} required>
                <Textarea
                  id="clause-content"
                  rows={6}
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                  required
                  className="font-serif"
                />
              </FormField>
              <div>
                <Button
                  type="submit"
                  variant="primary"
                  loading={saving}
                  loadingText={t('adminClauses.saving')}
                >
                  {t('adminClauses.create')}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {error ? <ErrorState message={error} onRetry={retry} /> : null}

      {items === null ? (
        <LoadingState label={t('adminClauses.loading')} />
      ) : items.length === 0 ? (
        <EmptyState
          title={t('adminClauses.emptyTitle')}
          description={t('adminClauses.emptyDescription')}
        />
      ) : (
        <Table caption={t('adminClauses.tableCaption')}>
          <THead>
            <TR>
              <TH scope="col">{t('adminClauses.colClause')}</TH>
              <TH scope="col">{t('adminClauses.colContractType')}</TH>
              <TH scope="col">{t('adminClauses.colKind')}</TH>
              <TH scope="col">{t('adminClauses.colVersion')}</TH>
              <TH scope="col">{t('adminClauses.colStatus')}</TH>
              <TH scope="col">{t('adminClauses.colActions')}</TH>
            </TR>
          </THead>
          <TBody>
            {items.map((clause) => (
              <TR key={clause.id}>
                <TD>
                  <span className="font-medium">{clause.title}</span>
                  <span className="ms-2 text-xs text-muted">#{clause.id}</span>
                </TD>
                <TD className="text-sm text-muted">{clause.contract_type}</TD>
                <TD className="text-sm text-muted">{clause.clause_type || '—'}</TD>
                <TD className="text-sm text-muted">{clause.version || '—'}</TD>
                <TD>
                  <StatusBadge status={clause.status} />
                </TD>
                <TD>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => void handleArchive(clause.id)}
                    loading={busyId === clause.id}
                    loadingText={t('adminClauses.archiving')}
                    disabled={clause.status === 'archived' || busyId !== null}
                  >
                    {t('adminClauses.archive')}
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
