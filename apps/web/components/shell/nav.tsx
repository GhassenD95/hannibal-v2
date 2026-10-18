'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import { useI18n } from '@/lib/i18n/context';
import { LanguageSwitcher } from './language-switcher';
import { useSession } from './session';

export function Nav() {
  const pathname = usePathname();
  const { user, signOut } = useSession();
  const { t } = useI18n();

  const links = [
    { href: '/', key: 'dashboard' as const },
    { href: '/contracts/new', key: 'newContract' as const },
    { href: '/admin', key: 'admin' as const },
    { href: '/evaluation', key: 'evaluation' as const },
  ];

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="flex items-baseline gap-2 rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          <span className="text-base font-semibold tracking-tight text-ink">Hannibal</span>
          <span className="text-xs font-medium uppercase tracking-widest text-primary">V2</span>
        </Link>
        <nav
          aria-label={t('nav.primary')}
          className="-mx-1 flex flex-1 flex-wrap items-center gap-1"
        >
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={isActive(link.href) ? 'page' : undefined}
              className={cn(
                'rounded-sm px-3 py-1.5 text-sm font-medium transition-colors duration-150',
                'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
                isActive(link.href)
                  ? 'bg-blue-50 text-primary'
                  : 'text-muted hover:bg-surface hover:text-ink',
              )}
            >
              {t(`nav.${link.key}`)}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          {user ? (
            <span className="hidden text-xs text-muted sm:inline">
              {user.full_name || user.email}
              {user.roles?.length ? ` · ${user.roles.join(', ')}` : ''}
            </span>
          ) : null}
          <Button variant="ghost" size="sm" onClick={signOut}>
            {t('nav.logOut')}
          </Button>
        </div>
      </div>
    </header>
  );
}
