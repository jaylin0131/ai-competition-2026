-- 團隊時程網站的 Supabase 資料表與權限（不收集 email 版）
-- 第 3 段（任務規劃）是後來加的：已執行過舊版的專案，整份重新執行一次即可，不會刪掉既有資料。
-- 用法：Supabase 控制台 → SQL Editor → 貼上全部 → Run。可重複執行，不會刪掉已有的勾選。
--
-- 權限設計：
-- - 讀取：網頁用公開金鑰（anon）讀任務並即時同步
-- - 寫入：只有 Cloudflare 伺服器端程式（functions/api/tasks.js）用私密金鑰寫入，網頁無法直接寫
-- - 記錄：每次新增、修改、勾選、刪除，都記下身分（成員在網頁上選的名字）與時間
-- 第 1、2 段（task_status）是早期只有勾選功能時的資料表，第 3 段的 tasks 取代它；保留以便匯入舊勾選。

-- 1. 勾選狀態：一個任務一列，key = <jnc|qkd>_<任務編號>，例如 jnc_S09
create table if not exists public.task_status (
  key             text primary key,
  project         text not null check (project in ('jnc', 'qkd')),
  task_id         text not null,
  done            boolean not null,
  updated_by_name text,
  updated_at      timestamptz not null default now()
);

-- 2. 操作紀錄：誰在何時勾選或取消，只增不改
create table if not exists public.task_status_log (
  id      bigint generated always as identity primary key,
  key     text not null,
  done    boolean not null,
  by_name text,
  at      timestamptz not null default now()
);

-- 從舊版（email 登入）升級：移除 email 欄位與成員名單
alter table public.task_status     add column if not exists updated_by_name text;
alter table public.task_status     drop column if exists updated_by_email;
alter table public.task_status_log add column if not exists by_name text;
alter table public.task_status_log drop column if exists by_email;
drop function if exists public.is_member() cascade;
drop table if exists public.members;

-- 寫入時由資料庫填時間並寫紀錄
create or replace function public.stamp_task_status()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  new.updated_at := now();
  insert into public.task_status_log (key, done, by_name) values (new.key, new.done, new.updated_by_name);
  return new;
end;
$$;

drop trigger if exists trg_stamp_task_status on public.task_status;
create trigger trg_stamp_task_status
  before insert or update on public.task_status
  for each row execute function public.stamp_task_status();

-- 權限：開放讀取；沒有任何寫入政策，所以只有私密金鑰（伺服器端）能寫
alter table public.task_status     enable row level security;
alter table public.task_status_log enable row level security;

drop policy if exists "members read status"   on public.task_status;
drop policy if exists "members insert status" on public.task_status;
drop policy if exists "members update status" on public.task_status;
drop policy if exists "members read log"      on public.task_status_log;
drop policy if exists "anyone read status"    on public.task_status;
drop policy if exists "anyone read log"       on public.task_status_log;

create policy "anyone read status" on public.task_status     for select to anon, authenticated using (true);
create policy "anyone read log"    on public.task_status_log for select to anon, authenticated using (true);

-- 即時同步：讓網頁收到其他成員的勾選
do $$
begin
  alter publication supabase_realtime add table public.task_status;
exception when duplicate_object then null;
end $$;

-- ===========================================================================
-- 3. 任務規劃（網站上可新增、修改、刪除；每天自動匯出回兩個專案的 tasks.csv）
--    key = <jnc|qkd>_<任務編號>；寫入一樣只經過伺服器端（functions/api/tasks.js）
-- ===========================================================================
create table if not exists public.tasks (
  key             text primary key,
  project         text not null check (project in ('jnc', 'qkd')),
  id              text not null,
  phase           text not null,
  grp             text not null,
  owners          text not null default '',   -- 多人用「、」分隔，與 tasks.csv 的 owner 欄相同
  task            text not null,
  start_date      date not null,
  end_date        date not null,
  depends         text not null default '',   -- 多個用「;」分隔
  status          text not null check (status in ('todo', 'doing', 'done', 'optional')),
  deliverable     text not null default '',
  sort            double precision not null default 0,
  updated_by_name text,
  updated_at      timestamptz not null default now(),
  unique (project, id),
  check (end_date >= start_date)
);

-- 每次新增、修改、刪除的完整紀錄（改之前與改之後的內容）
create table if not exists public.task_log (
  id      bigint generated always as identity primary key,
  key     text not null,
  action  text not null,
  by_name text,
  at      timestamptz not null default now(),
  before  jsonb,
  after   jsonb
);

create or replace function public.touch_task()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create or replace function public.log_task()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  if tg_op = 'DELETE' then
    insert into public.task_log (key, action, by_name, before) values (old.key, 'delete', old.updated_by_name, to_jsonb(old));
    return old;
  elsif tg_op = 'UPDATE' then
    insert into public.task_log (key, action, by_name, before, after) values (new.key, 'update', new.updated_by_name, to_jsonb(old), to_jsonb(new));
  else
    insert into public.task_log (key, action, by_name, after) values (new.key, 'insert', new.updated_by_name, to_jsonb(new));
  end if;
  return new;
end;
$$;

drop trigger if exists trg_touch_task on public.tasks;
create trigger trg_touch_task before insert or update on public.tasks
  for each row execute function public.touch_task();
drop trigger if exists trg_log_task on public.tasks;
create trigger trg_log_task after insert or update or delete on public.tasks
  for each row execute function public.log_task();

alter table public.tasks    enable row level security;
alter table public.task_log enable row level security;
drop policy if exists "anyone read tasks"    on public.tasks;
drop policy if exists "anyone read task log" on public.task_log;
create policy "anyone read tasks"    on public.tasks    for select to anon, authenticated using (true);
create policy "anyone read task log" on public.task_log for select to anon, authenticated using (true);

do $$
begin
  alter publication supabase_realtime add table public.tasks;
exception when duplicate_object then null;
end $$;
