import * as React from 'react';
import { cn } from '@/lib/cn';

export type BadgeVariant =
  'neutral' | 'info' | 'primary' | 'success' | 'warning' | 'danger' | 'evidence';

const variantClasses: Record<BadgeVariant, string> = {
  neutral: 'border-line bg-surface text-muted',
  info: 'border-sky-200 bg-sky-50 text-evidence',
  primary: 'border-blue-200 bg-blue-50 text-primary',
  success: 'border-green-200 bg-green-50 text-success',
  warning: 'border-amber-200 bg-amber-50 text-warning',
  danger: 'border-red-200 bg-red-50 text-danger',
  evidence: 'border-sky-200 bg-sky-50 text-evidence',
};

export function Badge({
  variant = 'neutral',
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-xs font-medium',
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}

const statusVariantMap: Record<string, BadgeVariant> = {
  draft: 'neutral',
  requested: 'neutral',
  pending: 'neutral',
  confirmed: 'primary',
  drafted: 'primary',
  supported: 'success',
  validated: 'success',
  valid: 'success',
  approved: 'success',
  completed: 'success',
  active: 'success',
  indexed: 'info',
  needs_review: 'warning',
  review: 'warning',
  high: 'warning',
  warning: 'warning',
  escalated: 'warning',
  unsupported: 'danger',
  blocker: 'danger',
  archived: 'neutral',
  rejected: 'danger',
  failed: 'danger',
  open: 'warning',
  closed: 'neutral',
  accepted: 'success',
  exported: 'evidence',
};

export function statusVariant(status: string): BadgeVariant {
  return statusVariantMap[status] ?? 'neutral';
}

export function StatusBadge({ status }: { status: string }) {
  const label = status.replace(/_/g, ' ');
  return <Badge variant={statusVariant(status)}>{label}</Badge>;
}
