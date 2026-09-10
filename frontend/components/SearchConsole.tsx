'use client';
import { FormEvent, useEffect, useState } from 'react';
import { api, Tool } from '@/lib/api';

const labels: Record<string, string> = { username: 'Username', email: 'Email address', phone: 'Phone number', domain: 'Domain' };

export default function SearchConsole() {
  const [inputType, setInputType] = useState('username');
  const [query, setQuery] = useState('');
  const [tools, setTools] = useState<Tool[]>([]);
  const [chosen, setChosen] = useState<string[]>([]);
  const [tags, setTags] = useState('');
  const [pivot, setPivot] = useState(true);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { api.tools(inputType).then((items) => { setTools(items); setChosen(items.filter((x) => x.default_enabled).map((x) => x.id)); }).catch((e) => setError(e.message)); }, [inputType]);
  const toggle = (id: string) => setChosen((old) => old.includes(id) ? old.filter((x) => x !== id) : [...old, id]);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    if (!consent) return setError('Confirm authorized use before running a search.');
    if (!query.trim()) return setError('Enter a search target.');
    if (!chosen.length) return setError('Select at least one tool.');
    setBusy(true);
    try {
      const data = await api.createSearch({ query: query.trim(), input_type: inputType, selected_tools: chosen, auto_pivot: pivot, consent_accepted: consent, wmn_tags: tags.split(',').map((x) => x.trim()).filter(Boolean) });
      window.location.assign(`/cases/${data.case_id}`);
    } catch (e) { setError(e instanceof Error ? e.message : 'Search request failed.'); } finally { setBusy(false); }
  }
  return <form onSubmit={submit} className="space-y-6 rounded-xl border border-line bg-panel p-6 shadow-2xl shadow-black/30"><div className="flex flex-wrap gap-2">{Object.keys(labels).map((type) => <button type="button" key={type} onClick={() => setInputType(type)} className={`rounded px-3 py-2 text-xs ${inputType === type ? 'bg-cyan text-ink' : 'border border-line text-slate-300'}`}>{labels[type].toUpperCase()}</button>)}</div><label className="block"><span className="mb-2 block text-xs text-slate-400">TARGET · {labels[inputType].toUpperCase()}</span><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={inputType === 'domain' ? 'example.org' : inputType === 'email' ? 'name@example.org' : inputType === 'phone' ? '+1 555 010 0000' : 'username'} className="w-full rounded border border-line bg-ink px-4 py-3 outline-none focus:border-cyan" /></label><div><p className="mb-3 text-xs text-slate-400">SELECTED COLLECTION TOOLS</p><div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{tools.map((tool) => <label key={tool.id} className={`flex cursor-pointer gap-3 rounded border p-3 ${chosen.includes(tool.id) ? 'border-cyan bg-cyan/5' : 'border-line'}`}><input type="checkbox" checked={chosen.includes(tool.id)} onChange={() => toggle(tool.id)} /><span><span className="block text-sm text-slate-100">{tool.name}</span><span className="text-xs text-slate-400">{tool.description}</span></span></label>)}</div></div>{inputType === 'username' && <label className="block"><span className="mb-2 block text-xs text-slate-400">WHATSMYNAME TAG FILTERS · OPTIONAL</span><input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="social, developer, gaming" className="w-full rounded border border-line bg-ink px-4 py-3 outline-none focus:border-cyan" /></label>}<div className="flex flex-col gap-3 rounded border border-amber/40 bg-amber/5 p-4 text-xs text-slate-300"><label className="flex gap-2"><input type="checkbox" checked={pivot} onChange={(e) => setPivot(e.target.checked)} />Enable controlled one-hop lead pivots</label><label className="flex gap-2"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />I confirm I am authorized to investigate this target and will comply with applicable law and service terms.</label></div>{error && <p className="rounded border border-red-400/50 bg-red-500/10 p-3 text-sm text-red-200">{error}</p>}<button disabled={busy} className="rounded bg-lime px-5 py-3 text-sm font-bold text-ink disabled:opacity-50">{busy ? 'QUEUING CASE…' : 'START AUTHORIZED SEARCH'}</button></form>;
}
