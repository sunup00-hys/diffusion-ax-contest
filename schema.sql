-- DIFFUSION AX Contest V2
-- 기존 Supabase 프로젝트에서 SQL Editor > New query에 전체 붙여넣고 Run 하세요.

-- 1) 작품 수를 6개까지 허용
alter table public.agents
  drop constraint if exists agents_slot_check;

alter table public.agents
  add constraint agents_slot_check
  check (slot between 1 and 6);

alter table public.agents
  add column if not exists team text default '',
  add column if not exists presenter text default '',
  add column if not exists title text default '';

insert into public.agents (slot, name, team, presenter, title)
values (6, 'Agent 6', '', '', '')
on conflict (slot) do nothing;

-- 2) DIFF_CHAMPION 가중치를 설정값으로 사용할 수 있도록 범위 확장
alter table public.scores
  drop constraint if exists scores_weight_check;

alter table public.scores
  add constraint scores_weight_check
  check (weight between 1 and 10);

-- 3) 앱 설정값 저장 테이블
create table if not exists public.app_settings (
  key text primary key,
  value_int integer not null,
  updated_at timestamptz not null default now()
);

insert into public.app_settings (key, value_int)
values ('champion_weight', 3)
on conflict (key) do nothing;

-- 4) service_role key 사용 전제
alter table public.agents enable row level security;
alter table public.scores enable row level security;
alter table public.app_settings enable row level security;
