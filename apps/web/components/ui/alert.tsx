import * as React from 'react';
import { cn } from '@/lib/cn';

export type AlertVariant = 'info' | 'success' | 'warning' | 'danger';

const variantClasses: Record<AlertVariant, string> = {
  info: 'border-sky-200 bg-sky-50 text-evidence',
  success: 'border-green-200 bg-green-50 text-success',
  warning: 'border-amber-200 bg-amber-50 text-warning',
  danger: 'border-red-200 bg-red-50 text-danger',
};

const variantLabels: Record<AlertVariant, string> = {
  info: 'Note',
  success: 'Success',
  warning: 'Warning',
  danger: 'Error',
};

export function Alert({
  variant = 'info',
  title,
  children,
  className,
  role,
  actions,
}: {
  variant?: AlertVariant;
  title?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  role?: 'alert' | 'status';
  actions?: React.ReactNode;
}) {
  return (
    <div
      role={role ?? (variant === 'danger' ? 'alert' : undefined)}
      className={cn(
        'rounded-md border px-4 py-3 text-sm animate-fade-in',
        variantClasses[variant],
        className,
      )}
    >
      <div className="flex items-start gap-2">
        <span className="mt-0.5 text-xs font-semibold uppercase tracking-wide">
          {variantLabels[variant]}
        </span>
      </div>
      {title ? <p className="mt-1 font-medium text-ink">{title}</p> : null}
      {children ? (
        <div className={cn(title ? 'mt-1' : 'mt-1.5', 'text-muted')}>{children}</div>
      ) : null}
      {actions ? <div className="mt-3 flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
