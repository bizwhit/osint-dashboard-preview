create table if not exists investigations (
  id text primary key,
  name text not null,
  notes text default '',
  status text not null default 'open',
  consent_accepted boolean not null default false,
  consent_accepted_at timestamptz,
  consent_ip text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists cases (
  id text primary key,
  investigation_id text references investigations(id) on delete cascade,
  input_type text not null,
  query text not null,
  status text not null default 'queued',
  selected_tools jsonb not null default '[]'::jsonb,
  auto_pivot_enabled boolean not null default true,
  wmn_tags jsonb not null default '[]'::jsonb,
  discovered_via text,
  parent_case_id text references cases(id) on delete set null,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz
);

create table if not exists search_results (
  id text primary key,
  case_id text not null references cases(id) on delete cascade,
  tool text not null,
  target text not null,
  site text,
  url text,
  confidence text not null default 'medium',
  extracted_data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists leads (
  id text primary key,
  investigation_id text not null references investigations(id) on delete cascade,
  source_case_id text not null references cases(id) on delete cascade,
  lead_type text not null,
  value text not null,
  auto_searched boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists idx_cases_investigation on cases(investigation_id);
create index if not exists idx_results_case on search_results(case_id);
create index if not exists idx_leads_investigation on leads(investigation_id);
