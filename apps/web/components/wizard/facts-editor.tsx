'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { validateField } from '@/lib/collector';
import { useI18n } from '@/lib/i18n/context';

const VALIDATED_KEYS = new Set(['contract_type', 'jurisdiction', 'amount', 'duration']);

interface RowState {
  message: string | null;
  severity: string;
  checking: boolean;
}

export function FactsEditor({
  facts,
  onChange,
  idPrefix,
}: {
  facts: Record<string, string>;
  onChange: (facts: Record<string, string>) => void;
  idPrefix: string;
}) {
  const { t } = useI18n();
  const entries = Object.entries(facts);
  const [rows, setRows] = React.useState<Record<string, RowState>>({});

  const setRowState = (key: string, state: RowState | null) => {
    setRows((current) => {
      const next = { ...current };
      if (state === null) delete next[key];
      else next[key] = state;
      return next;
    });
  };

  const updateValue = (key: string, value: string) => {
    onChange({ ...facts, [key]: value });
  };

  const updateKey = (oldKey: string, newKey: string) => {
    const next: Record<string, string> = {};
    for (const [key, value] of Object.entries(facts)) {
      if (key === oldKey) next[newKey] = value;
      else next[key] = value;
    }
    onChange(next);
    setRowState(oldKey, null);
  };

  const checkField = async (key: string, value: string) => {
    if (!VALIDATED_KEYS.has(key) || !value) {
      setRowState(key, null);
      return;
    }
    setRowState(key, { message: null, severity: 'info', checking: true });
    try {
      const result = await validateField(key, value);
      if (result.has_issue && result.validation) {
        setRowState(key, {
          message: result.validation.error_message,
          severity: result.validation.severity,
          checking: false,
        });
      } else {
        setRowState(key, null);
      }
    } catch {
      setRowState(key, null);
    }
  };

  const addRow = () => {
    let index = 1;
    while (facts[`fact_${index}`] !== undefined) index += 1;
    onChange({ ...facts, [`fact_${index}`]: '' });
  };

  const removeRow = (key: string) => {
    const next = { ...facts };
    delete next[key];
    onChange(next);
    setRowState(key, null);
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">{t('facts.title')}</h3>
          <p className="text-xs text-muted">{t('facts.hint')}</p>
        </div>
        <Button variant="secondary" size="sm" onClick={addRow}>
          {t('facts.add')}
        </Button>
      </div>

      {entries.length === 0 ? (
        <p className="rounded-md border border-dashed border-line bg-surface px-3 py-4 text-sm text-muted">
          {t('facts.empty')}
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {entries.map(([key, value]) => {
            const state = rows[key];
            const errorId = `${idPrefix}-fact-${key}-error`;
            return (
              <li
                key={key}
                className="flex flex-col gap-1 rounded-md border border-line bg-white p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <label className="sr-only" htmlFor={`${idPrefix}-key-${key}`}>
                    {t('facts.nameLabel')}
                  </label>
                  <Input
                    id={`${idPrefix}-key-${key}`}
                    value={key}
                    onChange={(event) => updateKey(key, event.target.value)}
                    className="w-40"
                    aria-label={t('facts.nameLabel')}
                  />
                  <label className="sr-only" htmlFor={`${idPrefix}-value-${key}`}>
                    {t('facts.valueFor', { key })}
                  </label>
                  <Input
                    id={`${idPrefix}-value-${key}`}
                    value={value}
                    onChange={(event) => updateValue(key, event.target.value)}
                    onBlur={() => void checkField(key, value)}
                    className="min-w-48 flex-1"
                    aria-label={t('facts.valueFor', { key })}
                    invalid={Boolean(state?.message)}
                    aria-describedby={state?.message ? errorId : undefined}
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeRow(key)}
                    aria-label={t('facts.removeFor', { key })}
                  >
                    {t('facts.remove')}
                  </Button>
                </div>
                {state?.checking ? (
                  <p className="text-xs text-muted" role="status">
                    {t('facts.checking', { key })}
                  </p>
                ) : null}
                {state?.message ? (
                  <p
                    id={errorId}
                    role="alert"
                    className={`text-xs font-medium ${
                      state.severity === 'warning' ? 'text-warning' : 'text-danger'
                    }`}
                  >
                    {state.severity === 'warning' ? `${t('facts.warningPrefix')}: ` : ''}
                    {state.message}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
