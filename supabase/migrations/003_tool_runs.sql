create table if not exists tool_runs (
  id text primary key,
  case_id text not null references cases(id) on delete cascade,
  tool text not null,
  status text not null default 'queued',
  results_count integer not null default 0,
  started_at timestamptz,
  completed_at timestamptz,
  error_message text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(case_id, tool)
);

create index if not exists idx_tool_runs_case on tool_runs(case_id);
