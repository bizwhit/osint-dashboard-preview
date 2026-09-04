create table if not exists audit_logs (
  id text primary key,
  investigation_id text references investigations(id) on delete set null,
  case_id text references cases(id) on delete set null,
  action text not null,
  input_type text,
  query text,
  tool text,
  consent_accepted boolean not null default false,
  client_ip text,
  user_agent text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_audit_investigation on audit_logs(investigation_id);
create index if not exists idx_audit_created on audit_logs(created_at desc);
