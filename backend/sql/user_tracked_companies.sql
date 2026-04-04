create table if not exists public.user_tracked_companies (
  id bigserial primary key,
  user_id uuid not null,
  company_name text not null,
  created_at timestamptz not null default now(),
  unique (user_id, company_name)
);

create index if not exists idx_user_tracked_companies_user_id
  on public.user_tracked_companies (user_id);
