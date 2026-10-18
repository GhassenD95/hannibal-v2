import * as React from 'react';
import { cn } from '@/lib/cn';

export function Table({
  className,
  children,
  caption,
}: {
  className?: string;
  children: React.ReactNode;
  caption?: string;
}) {
  return (
    <div
      className={cn(
        'relative w-full overflow-x-auto rounded-md border border-line bg-white',
        className,
      )}
    >
      <table className="w-full text-start text-sm">
        {caption ? (
          <caption className="border-b border-line px-4 py-3 text-start text-sm font-medium text-ink">
            {caption}
          </caption>
        ) : null}
        {children}
      </table>
    </div>
  );
}

export function THead({ children }: { children: React.ReactNode }) {
  return <thead className="border-b border-line bg-surface">{children}</thead>;
}

export function TBody({ children }: { children: React.ReactNode }) {
  return <tbody className="divide-y divide-line">{children}</tbody>;
}

export function TR({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <tr className={cn('transition-colors duration-150 hover:bg-surface', className)}>{children}</tr>
  );
}

export function TH({
  children,
  className,
  scope = 'col',
}: {
  children?: React.ReactNode;
  className?: string;
  scope?: 'col' | 'row';
}) {
  return (
    <th
      scope={scope}
      className={cn(
        'px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted',
        className,
      )}
    >
      {children}
    </th>
  );
}

export function TD({ children, className }: { children?: React.ReactNode; className?: string }) {
  return <td className={cn('px-4 py-2.5 align-top text-ink', className)}>{children}</td>;
}
