import SearchConsole from '@/components/SearchConsole';

export default function Home() { return <div className="space-y-8"><section><p className="text-xs tracking-[0.28em] text-lime">AUTHORIZED COLLECTION WORKSPACE</p><h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-tight text-slate-100">Turn public signals into accountable investigation records.</h1><p className="mt-4 max-w-2xl text-slate-400">Every request is consent-gated, rate-limited, recorded in audit telemetry, and stored as a case with reproducible tool-level outcomes.</p></section><SearchConsole /></div>; }
