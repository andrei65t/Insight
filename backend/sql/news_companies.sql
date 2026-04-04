create table if not exists public.news_companies (
  id bigserial primary key,
  company text not null,
  title text not null,
  link text not null,
  source text not null,
  date date,
  fact_label text not null default 'Unknown'
);

alter table public.news_companies
  add column if not exists date date;

alter table public.news_companies
  add column if not exists fact_label text not null default 'Unknown';

alter table public.news_companies
  drop column if exists created_at;

create index if not exists idx_news_companies_company
  on public.news_companies (company);
