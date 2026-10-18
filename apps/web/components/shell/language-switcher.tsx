'use client';

import * as React from 'react';
import { useI18n } from '@/lib/i18n/context';
import type { Language } from '@/lib/i18n/dictionaries';
import { cn } from '@/lib/cn';

const OPTIONS: Array<{ value: Language; label: string }> = [
  { value: 'en', label: 'EN' },
  { value: 'fr', label: 'FR' },
  { value: 'ar', label: 'AR' },
];

export function LanguageSwitcher() {
  const { lang, setLang, t } = useI18n();

  return (
    <div
      role="group"
      aria-label={t('lang.switcher')}
      className="flex items-center rounded-sm border border-line bg-white p-0.5"
    >
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => setLang(option.value)}
          aria-pressed={lang === option.value}
          className={cn(
            'rounded-sm px-2 py-1 text-xs font-medium transition-colors duration-150',
            'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
            lang === option.value
              ? 'bg-primary text-white'
              : 'text-muted hover:bg-surface hover:text-ink',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
