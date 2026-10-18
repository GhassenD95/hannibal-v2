import * as React from 'react';
import { cn } from '@/lib/cn';

export function Label({
  className,
  htmlFor,
  children,
  required,
}: {
  className?: string;
  htmlFor: string;
  children: React.ReactNode;
  required?: boolean;
}) {
  return (
    <label htmlFor={htmlFor} className={cn('text-sm font-medium text-ink', className)}>
      {children}
      {required ? (
        <span className="ms-1 text-danger" aria-hidden="true">
          *
        </span>
      ) : null}
    </label>
  );
}
