'use client';

import { useI18n } from '@/lib/i18n/context';

export function Footer() {
  const { t } = useI18n();
  return (
    <footer className="border-t border-line bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-xs text-muted sm:px-6 lg:px-8">
        <p>{t('footer.evidenceGrounded')}</p>
        <p>{t('footer.humanApproval')}</p>
      </div>
    </footer>
  );
}
