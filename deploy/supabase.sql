-- 團隊時程網站的 Supabase 資料表與權限（不收集 email 版）
-- 用法：Supabase 控制台 → SQL Editor → 貼上全部 → Run。可重複執行，不會刪掉已有的勾選。
--
-- 權限設計：
-- - 讀取：網頁用公開金鑰（anon）讀勾選狀態並即時同步；網頁本身已由 Cloudflare 的團隊密碼保護
-- - 寫入：只有 Cloudflare 伺服器端程式（functions/api/status.js）用私密金鑰寫入，網頁無法直接寫
-- - 記錄：每次勾選或取消，伺服器自動記下身分（成員在網頁上選的名字）與時間

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
