'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { FactsEditor } from '@/components/wizard/facts-editor';
import { ApiError } from '@/lib/api';
import { extractFacts, validateField } from '@/lib/collector';
import { confirmRequest, createContractRequest } from '@/lib/contracts';
import { cn } from '@/lib/cn';
import { useI18n } from '@/lib/i18n/context';

type Step = 'mode' | 'guided' | 'ai-describe' | 'ai-review';
type Mode = 'guided' | 'ai';

const steps: Array<{ id: Step; key: string }> = [
  { id: 'mode', key: 'stepMode' },
  { id: 'guided', key: 'stepFacts' },
  { id: 'ai-describe', key: 'stepDescription' },
  { id: 'ai-review', key: 'stepReview' },
];

function stepNumber(step: Step): number {
  if (step === 'mode') return 1;
  if (step === 'guided') return 2;
  if (step === 'ai-describe') return 2;
  return 3;
}

export default function NewContractPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [step, setStep] = React.useState<Step>('mode');
  const [mode, setMode] = React.useState<Mode>('guided');

  const [name, setName] = React.useState('');
  const [contractType, setContractType] = React.useState('service_agreement');
  const [jurisdiction, setJurisdiction] = React.useState('MA');
  const [facts, setFacts] = React.useState<Record<string, string>>({});
  const [description, setDescription] = React.useState('');

  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  async function checkField(field: 'contract_type' | 'jurisdiction', value: string) {
    try {
      const result = await validateField(field, value);
      setFieldErrors((current) => {
        const next = { ...current };
        if (result.has_issue && result.validation) {
          next[field] = result.validation.error_message;
        } else {
          delete next[field];
        }
        return next;
      });
    } catch {
      setFieldErrors((current) => {
        const next = { ...current };
        delete next[field];
        return next;
      });
    }
  }

  function validateRequired(): boolean {
    const errors: Record<string, string> = {};
    if (!name.trim()) errors.name = t('new.nameRequired');
    if (!contractType) errors.contract_type = t('new.typeRequired');
    if (!jurisdiction) errors.jurisdiction = t('new.jurisdictionRequired');
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function finishCreate() {
    if (!validateRequired()) {
      setActionError(t('new.fixFields'));
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      setStatus(t('new.creatingRequest'));
      const request = await createContractRequest({
        name: name.trim(),
        contract_type: contractType,
        jurisdiction,
        mode,
        facts,
        description: description.trim() || undefined,
      });
      setStatus(t('new.confirming'));
      const contract = await confirmRequest(request.id);
      setStatus(t('new.createdOpening'));
      router.push(`/contracts/${contract.id}`);
    } catch (exc) {
      setStatus(null);
      setBusy(false);
      setActionError(exc instanceof ApiError ? exc.message : t('new.createFailed'));
    }
  }

  async function handleExtract() {
    if (!description.trim()) {
      setActionError(t('new.describeRequired'));
      return;
    }
    setBusy(true);
    setActionError(null);
    setStatus(t('new.extracting'));
    try {
      const result = await extractFacts({
        description: description.trim(),
        jurisdiction,
      });
      if (!result || !result.id) {
        throw new ApiError(502, t('new.collectorEmpty'));
      }
      setName((current) => current || result.name || t('new.extractedName'));
      setContractType(result.contract_type || contractType);
      setJurisdiction(result.jurisdiction || jurisdiction);
      setFacts(result.facts ?? {});
      setStatus(null);
      setBusy(false);
      setStep('ai-review');
    } catch (exc) {
      setStatus(null);
      setBusy(false);
      setActionError(exc instanceof ApiError ? exc.message : t('new.extractFailed'));
    }
  }

  const visibleSteps =
    mode === 'guided'
      ? steps.filter((item) => item.id !== 'ai-describe' && item.id !== 'ai-review')
      : steps.filter((item) => item.id !== 'guided');
  const currentNumber = stepNumber(step);

  const contractTypes = [
    { value: 'service_agreement', label: t('new.typeService') },
    { value: 'nda', label: t('new.typeNda') },
  ];
  const jurisdictions = [
    { value: 'MA', label: t('new.jurisdictionMA') },
    { value: 'TN', label: t('new.jurisdictionTN') },
    { value: 'FR', label: t('new.jurisdictionFR') },
    { value: 'US', label: t('new.jurisdictionUS') },
  ];

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink">{t('new.title')}</h1>
        <p className="mt-1 text-sm text-muted">{t('new.subtitle')}</p>
      </div>

      <ol
        className="flex flex-wrap gap-4 border-b border-line pb-4"
        aria-label={t('new.wizardAria')}
      >
        {visibleSteps.map((item, index) => {
          const number = index + 1;
          const active = number === currentNumber;
          const done = number < currentNumber;
          return (
            <li
              key={item.id}
              aria-current={active ? 'step' : undefined}
              className={cn(
                'flex items-center gap-2 text-sm',
                active ? 'font-semibold text-primary' : done ? 'text-success' : 'text-muted',
              )}
            >
              <span
                className={cn(
                  'flex h-6 w-6 items-center justify-center rounded-full border text-xs',
                  active
                    ? 'border-primary bg-primary text-white'
                    : done
                      ? 'border-success bg-green-50 text-success'
                      : 'border-line bg-white',
                )}
                aria-hidden="true"
              >
                {done ? '✓' : number}
              </span>
              {t(`new.${item.key}`)}
            </li>
          );
        })}
      </ol>

      {status ? (
        <p role="status" aria-live="polite" className="text-sm font-medium text-primary">
          {status}
        </p>
      ) : null}
      {actionError ? <Alert variant="danger">{actionError}</Alert> : null}

      {step === 'mode' ? (
        <Card>
          <CardHeader>
            <CardTitle>{t('new.howStart')}</CardTitle>
            <CardDescription>{t('new.howStartDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            <fieldset className="flex flex-col gap-3">
              <legend className="sr-only">{t('new.modeLegend')}</legend>
              {[
                {
                  value: 'guided' as Mode,
                  title: t('new.guidedTitle'),
                  description: t('new.guidedDescription'),
                },
                {
                  value: 'ai' as Mode,
                  title: t('new.aiTitle'),
                  description: t('new.aiDescription'),
                },
              ].map((option) => (
                <label
                  key={option.value}
                  className={cn(
                    'flex cursor-pointer gap-3 rounded-md border bg-white p-4 transition-colors duration-150',
                    mode === option.value
                      ? 'border-primary ring-1 ring-primary'
                      : 'border-line hover:border-muted/50',
                  )}
                >
                  <input
                    type="radio"
                    name="mode"
                    value={option.value}
                    checked={mode === option.value}
                    onChange={() => setMode(option.value)}
                    className="mt-1 h-4 w-4 accent-[var(--color-primary)]"
                  />
                  <span>
                    <span className="block text-sm font-semibold text-ink">{option.title}</span>
                    <span className="mt-1 block text-sm text-muted">{option.description}</span>
                  </span>
                </label>
              ))}
            </fieldset>
            <div className="mt-6 flex justify-end">
              <Button
                variant="primary"
                onClick={() => setStep(mode === 'guided' ? 'guided' : 'ai-describe')}
              >
                {t('new.continue')}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {step === 'guided' ? (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle>{t('new.factsTitle')}</CardTitle>
            <CardDescription>{t('new.factsDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-col gap-5"
              noValidate
              onSubmit={(event) => {
                event.preventDefault();
                void finishCreate();
              }}
            >
              <FormField
                id="contract-name"
                label={t('new.contractName')}
                required
                error={fieldErrors.name ?? null}
              >
                <Input
                  id="contract-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder={t('new.namePlaceholder')}
                  invalid={Boolean(fieldErrors.name)}
                  required
                />
              </FormField>

              <div className="grid gap-5 sm:grid-cols-2">
                <FormField
                  id="contract-type"
                  label={t('new.contractType')}
                  required
                  error={fieldErrors.contract_type ?? null}
                  hint={t('new.typeHint')}
                >
                  <Select
                    id="contract-type"
                    value={contractType}
                    onChange={(event) => setContractType(event.target.value)}
                    onBlur={() => void checkField('contract_type', contractType)}
                    invalid={Boolean(fieldErrors.contract_type)}
                  >
                    {contractTypes.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </FormField>

                <FormField
                  id="jurisdiction"
                  label={t('new.jurisdiction')}
                  required
                  error={fieldErrors.jurisdiction ?? null}
                >
                  <Select
                    id="jurisdiction"
                    value={jurisdiction}
                    onChange={(event) => setJurisdiction(event.target.value)}
                    onBlur={() => void checkField('jurisdiction', jurisdiction)}
                    invalid={Boolean(fieldErrors.jurisdiction)}
                  >
                    {jurisdictions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </FormField>
              </div>

              <FactsEditor facts={facts} onChange={setFacts} idPrefix="guided" />

              <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
                <Button
                  type="submit"
                  variant="primary"
                  loading={busy}
                  loadingText={t('new.creating')}
                >
                  {t('new.createContract')}
                </Button>
                <Button variant="ghost" onClick={() => setStep('mode')} disabled={busy}>
                  {t('new.back')}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {step === 'ai-describe' ? (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle>{t('new.describeTitle')}</CardTitle>
            <CardDescription>{t('new.describeDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-col gap-5"
              noValidate
              onSubmit={(event) => {
                event.preventDefault();
                void handleExtract();
              }}
            >
              <FormField
                id="description"
                label={t('new.description')}
                required
                hint={t('new.descriptionHint')}
              >
                <Textarea
                  id="description"
                  rows={7}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder={t('new.descriptionPlaceholder')}
                  required
                />
              </FormField>

              <FormField
                id="ai-jurisdiction"
                label={t('new.jurisdiction')}
                required
                hint={t('new.jurisdictionHint')}
              >
                <Select
                  id="ai-jurisdiction"
                  value={jurisdiction}
                  onChange={(event) => setJurisdiction(event.target.value)}
                >
                  {jurisdictions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              </FormField>

              <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
                <Button
                  type="submit"
                  variant="primary"
                  loading={busy}
                  loadingText={t('new.extractingBtn')}
                >
                  {t('new.extractFacts')}
                </Button>
                <Button variant="ghost" onClick={() => setStep('mode')} disabled={busy}>
                  {t('new.back')}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {step === 'ai-review' ? (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle>{t('new.reviewTitle')}</CardTitle>
            <CardDescription>{t('new.reviewDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-col gap-5"
              noValidate
              onSubmit={(event) => {
                event.preventDefault();
                void finishCreate();
              }}
            >
              <FormField
                id="ai-name"
                label={t('new.contractName')}
                required
                error={fieldErrors.name ?? null}
              >
                <Input
                  id="ai-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  invalid={Boolean(fieldErrors.name)}
                  required
                />
              </FormField>

              <div className="grid gap-5 sm:grid-cols-2">
                <FormField
                  id="ai-contract-type"
                  label={t('new.contractType')}
                  required
                  error={fieldErrors.contract_type ?? null}
                >
                  <Select
                    id="ai-contract-type"
                    value={contractType}
                    onChange={(event) => setContractType(event.target.value)}
                    onBlur={() => void checkField('contract_type', contractType)}
                    invalid={Boolean(fieldErrors.contract_type)}
                  >
                    {contractTypes.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </FormField>
                <FormField
                  id="ai-review-jurisdiction"
                  label={t('new.jurisdiction')}
                  required
                  error={fieldErrors.jurisdiction ?? null}
                >
                  <Select
                    id="ai-review-jurisdiction"
                    value={jurisdiction}
                    onChange={(event) => setJurisdiction(event.target.value)}
                    onBlur={() => void checkField('jurisdiction', jurisdiction)}
                    invalid={Boolean(fieldErrors.jurisdiction)}
                  >
                    {jurisdictions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </FormField>
              </div>

              <FactsEditor facts={facts} onChange={setFacts} idPrefix="ai" />

              <div className="rounded-md border border-line bg-surface px-3 py-3">
                <h3 className="text-sm font-semibold text-ink">{t('new.originalDescription')}</h3>
                <p className="mt-1 whitespace-pre-wrap text-sm text-muted">{description}</p>
              </div>

              <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
                <Button
                  type="submit"
                  variant="primary"
                  loading={busy}
                  loadingText={t('new.creating')}
                >
                  {t('new.createContract')}
                </Button>
                <Button variant="secondary" onClick={() => setStep('ai-describe')} disabled={busy}>
                  {t('new.editDescription')}
                </Button>
                <Button variant="ghost" onClick={() => setStep('mode')} disabled={busy}>
                  {t('new.cancel')}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
