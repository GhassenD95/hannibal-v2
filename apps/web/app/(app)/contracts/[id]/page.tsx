'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { ErrorState, LoadingState } from '@/components/ui/states';
import { Tabs, TabItem, TabsPanel } from '@/components/ui/tabs';
import { ApprovalsPanel } from '@/components/workspace/approvals-panel';
import { AuditPanel } from '@/components/workspace/audit-panel';
import { ExportPanel } from '@/components/workspace/export-panel';
import { NegotiationPanel } from '@/components/workspace/negotiation-panel';
import { RisksPanel } from '@/components/workspace/risks-panel';
import { SectionsPanel } from '@/components/workspace/sections-panel';
import { ValidationPanel } from '@/components/workspace/validation-panel';
import { VersionsPanel } from '@/components/workspace/versions-panel';
import { ApiError } from '@/lib/api';
import {
  createPlan,
  generateContract,
  getContract,
  listSections,
  validationSummary,
} from '@/lib/contracts';
import { useI18n } from '@/lib/i18n/context';
import type {
  ContractDetail,
  ContractSection,
  GenerateResult,
  ValidationSummary,
} from '@/lib/types';

export default function ContractWorkspacePage() {
  const params = useParams<{ id: string }>();
  const { t } = useI18n();
  const contractId = Number(params.id);

  const [contract, setContract] = React.useState<ContractDetail | null>(null);
  const [sections, setSections] = React.useState<ContractSection[]>([]);
  const [summary, setSummary] = React.useState<ValidationSummary | null>(null);
  const [tab, setTab] = React.useState('sections');
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [attempt, setAttempt] = React.useState(0);
  const [workflowBusy, setWorkflowBusy] = React.useState<'plan' | 'generate' | null>(null);
  const [workflowMessage, setWorkflowMessage] = React.useState<string | null>(null);
  const [workflowError, setWorkflowError] = React.useState<string | null>(null);
  const [generateResult, setGenerateResult] = React.useState<GenerateResult | null>(null);

  const refreshSections = React.useCallback(async () => {
    const result = await listSections(contractId);
    setSections(result);
  }, [contractId]);

  const refreshSummary = React.useCallback(async () => {
    try {
      const result = await validationSummary(contractId);
      setSummary(result);
    } catch {
      setSummary(null);
    }
  }, [contractId]);

  React.useEffect(() => {
    if (!Number.isFinite(contractId)) {
      setError(t('workspace.invalidId'));
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      getContract(contractId),
      listSections(contractId),
      validationSummary(contractId).catch(() => null),
    ])
      .then(([detail, sectionList, summaryResult]) => {
        if (cancelled) return;
        setContract(detail);
        setSections(sectionList);
        setSummary(summaryResult);
        setLoading(false);
      })
      .catch((exc: unknown) => {
        if (cancelled) return;
        setError(exc instanceof ApiError ? exc.message : t('workspace.loadFailed'));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [contractId, attempt, t]);

  async function handlePlan() {
    setWorkflowBusy('plan');
    setWorkflowError(null);
    setWorkflowMessage(null);
    try {
      const plan = await createPlan(contractId);
      setWorkflowMessage(
        t('workspace.planReady', {
          required: plan.sections_required.length,
          clauses: plan.selected_clauses.length,
          evidence: plan.evidence_ids.length,
        }),
      );
      await refreshSections();
    } catch (exc) {
      setWorkflowError(exc instanceof ApiError ? exc.message : t('workspace.planningFailed'));
    } finally {
      setWorkflowBusy(null);
    }
  }

  async function handleGenerate() {
    setWorkflowBusy('generate');
    setWorkflowError(null);
    setWorkflowMessage(null);
    try {
      const result = await generateContract(contractId);
      setGenerateResult(result);
      setWorkflowMessage(
        t('workspace.generatedSections', {
          generated: result.generated_sections,
          supported: result.supported,
          needsReview: result.needs_review,
          unsupported: result.unsupported,
        }),
      );
      await Promise.all([
        refreshSections(),
        getContract(contractId).then(setContract),
        refreshSummary(),
      ]);
    } catch (exc) {
      setWorkflowError(exc instanceof ApiError ? exc.message : t('workspace.generationFailed'));
    } finally {
      setWorkflowBusy(null);
    }
  }

  if (loading) {
    return <LoadingState label={t('workspace.loading')} />;
  }
  if (error || !contract) {
    return (
      <ErrorState
        message={error ?? t('workspace.notFound')}
        onRetry={() => setAttempt((value) => value + 1)}
      />
    );
  }

  const tabs: TabItem[] = [
    { value: 'sections', label: t('workspace.tabSections') },
    {
      value: 'validation',
      label: t('workspace.tabValidation'),
      badge:
        summary && summary.blockers > 0 ? <Badge variant="danger">{summary.blockers}</Badge> : null,
    },
    { value: 'risks', label: t('workspace.tabRisks') },
    { value: 'negotiation', label: t('workspace.tabNegotiation') },
    { value: 'approvals', label: t('workspace.tabApprovals') },
    { value: 'versions', label: t('workspace.tabVersions') },
    { value: 'export', label: t('workspace.tabExport') },
    { value: 'audit', label: t('workspace.tabAudit') },
  ];

  const showWorkflowActions = tab === 'sections';

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-muted">
            {t('workspace.contractLabel', { id: contract.id })}
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-ink">{contract.name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={contract.status} />
            <Badge variant="neutral">{contract.contract_type}</Badge>
            <Badge variant="neutral">{contract.jurisdiction}</Badge>
            <Badge variant="neutral">
              {t('workspace.lang', { lang: contract.language ?? 'fr' })}
            </Badge>
          </div>
        </div>
        {showWorkflowActions ? (
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="secondary"
              onClick={() => void handlePlan()}
              loading={workflowBusy === 'plan'}
              loadingText={t('workspace.planning')}
              disabled={workflowBusy !== null}
            >
              {t('workspace.plan')}
            </Button>
            <Button
              variant="primary"
              onClick={() => void handleGenerate()}
              loading={workflowBusy === 'generate'}
              loadingText={t('workspace.generating')}
              disabled={workflowBusy !== null}
            >
              {t('workspace.generateDraft')}
            </Button>
          </div>
        ) : null}
      </div>

      {generateResult ? (
        <Alert variant="warning" role="status">
          {t('workspace.generationAlert', {
            needsReview: generateResult.needs_review,
            unsupported: generateResult.unsupported,
          })}
        </Alert>
      ) : null}
      {workflowMessage ? (
        <p role="status" aria-live="polite" className="text-sm font-medium text-success">
          {workflowMessage}
        </p>
      ) : null}
      {workflowError ? <Alert variant="danger">{workflowError}</Alert> : null}

      <Tabs items={tabs} value={tab} onChange={setTab} label={t('workspace.tabsAria')}>
        <TabsPanel value="sections">
          <SectionsPanel
            contractId={contractId}
            sections={sections}
            refresh={async () => {
              await refreshSections();
            }}
          />
        </TabsPanel>
        <TabsPanel value="validation">
          <ValidationPanel
            contractId={contractId}
            summary={summary}
            refreshSummary={refreshSummary}
          />
        </TabsPanel>
        <TabsPanel value="risks">
          <RisksPanel contractId={contractId} />
        </TabsPanel>
        <TabsPanel value="negotiation">
          <NegotiationPanel
            contractId={contractId}
            sections={sections}
            refreshSections={refreshSections}
          />
        </TabsPanel>
        <TabsPanel value="approvals">
          <ApprovalsPanel
            contractId={contractId}
            summary={summary}
            refreshSummary={refreshSummary}
            onApproved={async () => {
              const detail = await getContract(contractId);
              setContract(detail);
            }}
          />
        </TabsPanel>
        <TabsPanel value="versions">
          <VersionsPanel contractId={contractId} />
        </TabsPanel>
        <TabsPanel value="export">
          <ExportPanel contractId={contractId} status={contract.status} summary={summary} />
        </TabsPanel>
        <TabsPanel value="audit">
          <AuditPanel contractId={contractId} />
        </TabsPanel>
      </Tabs>
    </div>
  );
}
