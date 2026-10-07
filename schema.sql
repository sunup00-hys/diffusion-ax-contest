
-- DIFFUSION AX Contest shared database
-- Supabase > SQL Editor 에서 전체 실행

create table if not exists public.agents (
  slot smallint primary key check (slot between 1 and 5),
  name text not null
);

insert into public.agents (slot, name) values
  (1, 'Agent 1'),
  (2, 'Agent 2'),
  (3, 'Agent 3'),
  (4, 'Agent 4'),
  (5, 'Agent 5')
on conflict (slot) do nothing;

create table if not exists public.scores (
  judge text not null,
  agent_slot smallint not null references public.agents(slot) on delete cascade,
  c1 smallint not null check (c1 between 1 and 5),
  c2 smallint not null check (c2 between 1 and 5),
  c3 smallint not null check (c3 between 1 and 5),
  c4 smallint not null check (c4 between 1 and 5),
  c5 smallint not null check (c5 between 1 and 5),
  total smallint not null check (total between 5 and 25),
  weight smallint not null check (weight in (1,3)),
  weighted_total smallint not null,
  comment text default '',
  updated_at timestamptz not null default now(),
  primary key (judge, agent_slot)
);

create index if not exists idx_scores_agent_slot on public.scores(agent_slot);
create index if not exists idx_scores_judge on public.scores(judge);

-- 앱은 서버의 service_role key를 사용하도록 구성합니다.
-- 브라우저에서 DB를 직접 접근하지 않도록 RLS를 켜고 공개 정책은 만들지 않습니다.
alter table public.agents enable row level security;
alter table public.scores enable row level security;
