'use client';

import * as React from 'react';
import { dictionaries, type Dictionary, type Language } from './dictionaries';

export const I18N_STORAGE_KEY = 'hannibal.lang';

interface I18nContextValue {
  lang: Language;
  dir: 'ltr' | 'rtl';
  setLang: (lang: Language) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  tn: (key: string, count: number, params?: Record<string, string | number>) => string;
}

const I18nContext = React.createContext<I18nContextValue | null>(null);

function isLanguage(value: unknown): value is Language {
  return value === 'en' || value === 'fr' || value === 'ar';
}

function detectInitialLang(): Language {
  if (typeof window !== 'undefined') {
    try {
      const stored = window.localStorage.getItem(I18N_STORAGE_KEY);
      if (isLanguage(stored)) return stored;
    } catch {
      // localStorage unavailable — fall through to navigator detection.
    }
    const navigatorLang = window.navigator.language?.toLowerCase() ?? '';
    if (navigatorLang.startsWith('ar')) return 'ar';
    if (navigatorLang.startsWith('fr')) return 'fr';
  }
  return 'en';
}

function lookup(dictionary: Dictionary, key: string): string {
  const value = key.split('.').reduce<unknown>((acc, part) => {
    if (acc && typeof acc === 'object' && part in acc) {
      return (acc as Record<string, unknown>)[part];
    }
    return undefined;
  }, dictionary);
  return typeof value === 'string' ? value : key;
}

function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => {
    return name in params ? String(params[name]) : match;
  });
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = React.useState<Language>('en');

  React.useEffect(() => {
    setLangState(detectInitialLang());
  }, []);

  const setLang = React.useCallback((next: Language) => {
    setLangState(next);
    try {
      window.localStorage.setItem(I18N_STORAGE_KEY, next);
    } catch {
      // Storage unavailable — the change still applies for this session.
    }
  }, []);

  const dir: 'ltr' | 'rtl' = lang === 'ar' ? 'rtl' : 'ltr';

  React.useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dir;
  }, [lang, dir]);

  const t = React.useCallback(
    (key: string, params?: Record<string, string | number>) =>
      interpolate(lookup(dictionaries[lang], key), params),
    [lang],
  );

  const tn = React.useCallback(
    (key: string, count: number, params?: Record<string, string | number>) => {
      const pluralKey = count === 1 ? `${key}One` : `${key}Other`;
      return interpolate(lookup(dictionaries[lang], pluralKey), { ...params, count });
    },
    [lang],
  );

  const value = React.useMemo(() => ({ lang, dir, setLang, t, tn }), [lang, dir, setLang, t, tn]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = React.useContext(I18nContext);
  if (!context) throw new Error('useI18n must be used within an I18nProvider');
  return context;
}
