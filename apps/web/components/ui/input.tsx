import * as React from 'react';
import { cn } from '@/lib/cn';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, invalid, id, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      id={id}
      aria-invalid={invalid || undefined}
      className={cn(
        'flex h-9 w-full rounded-sm border border-line bg-white px-3 py-1 text-sm text-ink shadow-sm',
        'placeholder:text-muted/70 transition-colors duration-150',
        'hover:border-muted/50',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary',
        'disabled:cursor-not-allowed disabled:bg-surface disabled:text-muted',
        invalid && 'border-danger hover:border-danger',
        className,
      )}
      {...props}
    />
  );
});
