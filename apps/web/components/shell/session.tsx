'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ErrorState, LoadingState } from '@/components/ui/states';
import { getStoredUser, getToken } from '@/lib/api';
import { fetchMe, logout as logoutRequest } from '@/lib/auth';
import type { SessionUser } from '@/lib/types';

interface SessionContextValue {
  user: SessionUser | null;
  signOut: () => void;
}

const SessionContext = React.createContext<SessionContextValue>({
  user: null,
  signOut: () => undefined,
});

export function useSession(): SessionContextValue {
  return React.useContext(SessionContext);
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = React.useState<SessionUser | null>(null);
  const [status, setStatus] = React.useState<'checking' | 'ready' | 'error'>('checking');
  const [errorMessage, setErrorMessage] = React.useState('');
  const [attempt, setAttempt] = React.useState(0);
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  React.useEffect(() => {
    if (!mounted) return;
    if (!getToken()) {
      router.replace('/login');
      return;
    }
    let cancelled = false;
    setStatus('checking');
    fetchMe()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setStatus('ready');
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const stored = getStoredUser();
        if (stored) {
          setUser(stored);
          setStatus('ready');
          return;
        }
        setErrorMessage(error instanceof Error ? error.message : 'Unable to verify session.');
        setStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [router, attempt, mounted]);

  const signOut = React.useCallback(() => {
    logoutRequest();
    router.replace('/login');
  }, [router]);

  if (!mounted) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <LoadingState label="Loading Hannibal…" />
      </div>
    );
  }

  if (!getToken()) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <LoadingState label="Redirecting to sign-in…" />
      </div>
    );
  }

  if (status === 'checking') {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <LoadingState label="Verifying your session…" />
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <ErrorState message={errorMessage} onRetry={() => setAttempt((value) => value + 1)} />
      </div>
    );
  }

  return <SessionContext.Provider value={{ user, signOut }}>{children}</SessionContext.Provider>;
}
