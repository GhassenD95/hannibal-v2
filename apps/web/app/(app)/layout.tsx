import { Footer } from '@/components/shell/footer';
import { Nav } from '@/components/shell/nav';
import { SessionProvider } from '@/components/shell/session';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <div className="flex min-h-screen flex-col">
        <Nav />
        <main id="main" className="flex-1">
          <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">{children}</div>
        </main>
        <Footer />
      </div>
    </SessionProvider>
  );
}
