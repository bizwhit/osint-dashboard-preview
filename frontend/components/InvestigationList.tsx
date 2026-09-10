'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Investigation = { id: string; name: string; status: string; created_at: string };
export default function InvestigationList() { const [items, setItems] = useState<Investigation[]>([]); const [error, setError] = useState(''); useEffect(() => { api.investigations().then(setItems).catch((e) => setError(e.message)); }, []); return <section className="rounded-xl border border-line bg-panel p-6"><p className="text-xs tracking-[0.2em] text-lime">CASE ARCHIVE</p><h1 className="mt-2 text-2xl text-slate-100">Investigations</h1>{error && <p className="mt-4 text-red-200">{error}</p>}<div className="mt-5 space-y-3">{items.map((item) => <Link key={item.id} href={`/?investigation_id=${item.id}`} className="block rounded border border-line bg-ink p-4 hover:border-cyan"><div className="flex justify-between gap-4"><span>{item.name}</span><span className="text-xs text-slate-400">{item.status}</span></div><p className="mt-2 text-xs text-slate-500">{item.id} · {new Date(item.created_at).toLocaleString()}</p></Link>)}{!items.length && !error && <p className="text-slate-400">No investigations are available.</p>}</div></section>; }
