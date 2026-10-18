import type { Metadata } from 'next';
import { I18nProvider } from '@/lib/i18n/context';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Hannibal V2',
    template: '%s · Hannibal V2',
  },
  description: 'Evidence-grounded Legal Contract Reasoning Engine',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" dir="ltr">
      <body className="min-h-screen bg-surface text-ink antialiased">
        <I18nProvider>
          <a href="#main" className="skip-link">
            Skip to main content
          </a>
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
