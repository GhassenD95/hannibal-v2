'use client';

import * as React from 'react';
import { cn } from '@/lib/cn';

interface TabsContextValue {
  value: string;
  setValue: (value: string) => void;
  idBase: string;
}

const TabsContext = React.createContext<TabsContextValue | null>(null);

function useTabs(): TabsContextValue {
  const ctx = React.useContext(TabsContext);
  if (!ctx) throw new Error('Tabs components must be used inside <Tabs>');
  return ctx;
}

export interface TabItem {
  value: string;
  label: string;
  badge?: React.ReactNode;
}

export function Tabs({
  items,
  value,
  onChange,
  label,
  children,
  className,
}: {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  const idBase = React.useId();
  const refs = React.useRef<Record<string, HTMLButtonElement | null>>({});

  const move = (direction: 1 | -1 | 'first' | 'last') => {
    const index = items.findIndex((item) => item.value === value);
    let nextIndex: number;
    if (direction === 'first') nextIndex = 0;
    else if (direction === 'last') nextIndex = items.length - 1;
    else nextIndex = (index + direction + items.length) % items.length;
    const next = items[nextIndex];
    if (!next) return;
    onChange(next.value);
    window.requestAnimationFrame(() => {
      refs.current[next.value]?.focus();
    });
  };

  return (
    <TabsContext.Provider value={{ value, setValue: onChange, idBase }}>
      <div className={className}>
        <div
          role="tablist"
          aria-label={label}
          className="flex flex-wrap gap-1 border-b border-line"
          onKeyDown={(event) => {
            if (event.key === 'ArrowRight') {
              event.preventDefault();
              move(1);
            } else if (event.key === 'ArrowLeft') {
              event.preventDefault();
              move(-1);
            } else if (event.key === 'Home') {
              event.preventDefault();
              move('first');
            } else if (event.key === 'End') {
              event.preventDefault();
              move('last');
            }
          }}
        >
          {items.map((item) => (
            <button
              key={item.value}
              ref={(node) => {
                refs.current[item.value] = node;
              }}
              type="button"
              role="tab"
              id={`${idBase}-tab-${item.value}`}
              aria-controls={`${idBase}-panel-${item.value}`}
              aria-selected={item.value === value}
              tabIndex={item.value === value ? 0 : -1}
              onClick={() => onChange(item.value)}
              className={cn(
                '-mb-px inline-flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors duration-150',
                'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-primary',
                item.value === value
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted hover:border-line hover:text-ink',
              )}
            >
              {item.label}
              {item.badge}
            </button>
          ))}
        </div>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

export function TabsPanel({
  value,
  children,
  className,
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
}) {
  const ctx = useTabs();
  if (ctx.value !== value) return null;
  return (
    <div
      role="tabpanel"
      id={`${ctx.idBase}-panel-${value}`}
      aria-labelledby={`${ctx.idBase}-tab-${value}`}
      tabIndex={0}
      className={cn('pt-6', className)}
    >
      {children}
    </div>
  );
}
