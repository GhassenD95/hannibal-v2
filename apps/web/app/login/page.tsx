'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { ApiError, getStoredUser, getToken } from '@/lib/api';
import { login } from '@/lib/auth';
import { useI18n } from '@/lib/i18n/context';

export default function LoginPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [email, setEmail] = React.useState('admin@hannibal.local');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (getToken()) {
      const user = getStoredUser();
      if (user) router.replace('/');
    }
  }, [router]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!email.trim() || !password) {
      setError(t('login.emptyError'));
      return;
    }
    setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace('/');
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : t('login.failed'));
      setLoading(false);
    }
  }

  return (
    <main id="main" className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <p className="text-sm font-semibold uppercase tracking-widest text-primary">
            {t('login.eyebrow')}
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-ink">{t('login.title')}</h1>
          <p className="mt-1 text-sm text-muted">{t('login.subtitle')}</p>
        </div>
        <Card className="shadow-panel">
          <CardHeader>
            <CardTitle>{t('login.account')}</CardTitle>
            <CardDescription>{t('login.accountDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
              {error ? <Alert variant="danger">{error}</Alert> : null}
              <FormField id="email" label={t('login.email')} required>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  invalid={Boolean(error)}
                  required
                />
              </FormField>
              <FormField id="password" label={t('login.password')} required>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  invalid={Boolean(error)}
                  required
                />
              </FormField>
              <Button
                type="submit"
                variant="primary"
                loading={loading}
                loadingText={t('login.signingIn')}
                className="w-full"
              >
                {t('login.signIn')}
              </Button>
              <p className="text-xs text-muted">{t('login.auditNote')}</p>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
