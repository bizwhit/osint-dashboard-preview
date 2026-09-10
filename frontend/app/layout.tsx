import './globals.css';
import Link from 'next/link';

export const metadata = { title: 'OSINT Unified', description: 'Authorized investigation workspace' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><div className="min-h-screen"><header className="border-b border-line bg-[#091725]"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4"><Link href="/" className="font-bold tracking-[0.22em] text-cyan">OSINT//UNIFIED</Link><nav className="flex gap-4 text-xs text-slate-300"><Link href="/">SEARCH</Link><Link href="/investigations">INVESTIGATIONS</Link><Link href="/admin">ADMIN</Link></nav></div></header><main className="mx-auto max-w-7xl px-5 py-8">{children}</main></div></body></html>;
}
