-- 團隊時程網站的 Supabase 資料表與權限
-- 用法：Supabase 控制台 → SQL Editor → 貼上全部 → Run。可重複執行。
-- 最後一段的成員 email 請改成 6 位成員實際登入用的信箱。

-- 1. 成員名單：只有名單上的 email 能讀寫勾選狀態
create table if not exists public.members (
  email text primary key,
  name  text not null
);

-- 2. 勾選狀態：一個任務一列，key = <jnc|qkd>_<任務編號>，例如 jnc_S09
create table if not exists public.task_status (
  key              text primary key,
  project          text not null check (project in ('jnc', 'qkd')),
  task_id          text not null,
  done             boolean not null,
  updated_by_email text,
  updated_at       timestamptz not null default now()
);

-- 3. 勾選紀錄（誰在何時勾或取消），只能新增不能改
create table if not exists public.task_status_log (
  id         bigint generated always as identity primary key,
  key        text not null,
  done       boolean not null,
  by_email   text,
  at         timestamptz not null default now()
);

-- 目前登入者是否在成員名單上
create or replace function public.is_member()
returns boolean
language sql stable security definer set search_path = public
as $$
  select exists (
    select 1 from public.members
    where lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

-- 寫入時由伺服器填「誰、何時」，不信任瀏覽器送來的值，並寫一筆紀錄
create or replace function public.stamp_task_status()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  new.updated_by_email := lower(auth.jwt() ->> 'email');
  new.updated_at := now();
  insert into public.task_status_log (key, done, by_email) values (new.key, new.done, new.updated_by_email);
  return new;
end;
$$;

drop trigger if exists trg_stamp_task_status on public.task_status;
create trigger trg_stamp_task_status
  before insert or update on public.task_status
  for each row execute function public.stamp_task_status();

-- 權限（Row Level Security）
alter table public.members         enable row level security;
alter table public.task_status     enable row level security;
alter table public.task_status_log enable row level security;

drop policy if exists "members read members"   on public.members;
drop policy if exists "members read status"    on public.task_status;
drop policy if exists "members insert status"  on public.task_status;
drop policy if exists "members update status"  on public.task_status;
drop policy if exists "members read log"       on public.task_status_log;

create policy "members read members"  on public.members         for select to authenticated using (public.is_member());
create policy "members read status"   on public.task_status     for select to authenticated using (public.is_member());
create policy "members insert status" on public.task_status     for insert to authenticated with check (public.is_member());
create policy "members update status" on public.task_status     for update to authenticated using (public.is_member()) with check (public.is_member());
create policy "members read log"      on public.task_status_log for select to authenticated using (public.is_member());
-- 沒有 delete 政策：網頁上不能刪除；取消勾選是把 done 改成 false

-- 即時同步：讓網頁收到其他成員的勾選
do $$
begin
  alter publication supabase_realtime add table public.task_status;
exception when duplicate_object then null;
end $$;

-- 4. 成員名單（請改成實際 email；姓名需和 tasks.csv 的 owner 一致）
insert into public.members (email, name) values
  ('member1@example.com', '林子桀'),
  ('member2@example.com', '許程景'),
  ('member3@example.com', '周冠辰'),
  ('member4@example.com', '王端宏'),
  ('member5@example.com', '何名綸'),
  ('member6@example.com', '范語芸')
on conflict (email) do update set name = excluded.name;
-- 填好真實 email 後，刪除範例列：
-- delete from public.members where email like 'member%@example.com';
