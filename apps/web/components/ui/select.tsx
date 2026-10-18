import * as React from 'react';
import { cn } from '@/lib/cn';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, invalid, id, children, ...props },
  ref,
) {
  return (
    <select
      ref={ref}
      id={id}
      aria-invalid={invalid || undefined}
      className={cn(
        'flex h-9 w-full rounded-sm border border-line bg-white px-2 py-1 text-sm text-ink shadow-sm',
        'transition-colors duration-150 hover:border-muted/50',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary',
        'disabled:cursor-not-allowed disabled:bg-surface disabled:text-muted',
        invalid && 'border-danger hover:border-danger',
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
});
