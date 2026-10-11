// 任務規劃的寫入入口：POST /api/tasks
//   {"action": "create", "task": {...}, "by": "何名綸"}
//   {"action": "update", "key": "jnc_S09", "task": {...}, "expected": "<updated_at>", "by": "何名綸"}
//   {"action": "status", "key": "jnc_S09", "done": true, "by": "何名綸"}
//   {"action": "delete", "key": "jnc_S09", "by": "何名綸"}
// 以 Supabase 私密金鑰寫入，金鑰不會出現在網頁；只接受本站頁面送出的請求。
// 合法的組別、成員與不可刪除的截止里程碑來自網站建置時產生的 /meta.json（site/build_site.py）。
// 環境變數：SUPABASE_URL、SUPABASE_SERVICE_KEY（加密）。

const ID_RE = /^[A-Z]+[0-9]+$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const STATUSES = ["todo", "doing", "done", "optional"];

class Bad extends Error {
  constructor(message, status = 400) { super(message); this.status = status; }
}

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8" } });

function db(env) {
  const base = `${env.SUPABASE_URL.replace(/\/$/, "")}/rest/v1/tasks`;
  const headers = { apikey: env.SUPABASE_SERVICE_KEY, Authorization: `Bearer ${env.SUPABASE_SERVICE_KEY}`, "Content-Type": "application/json" };
  return async (query, init = {}) => {
    const res = await fetch(`${base}${query}`, { ...init, headers: { ...headers, ...(init.headers || {}) } });
    const text = await res.text();
    if (!res.ok) throw new Bad(res.status === 409 ? "編號已存在" : "資料庫錯誤：" + text.slice(0, 160), res.status === 409 ? 409 : 502);
    return text ? JSON.parse(text) : null;
  };
}

async function loadMeta(request, env) {
  if (!env.ASSETS) throw new Bad("網站設定缺少 ASSETS", 503);
  const res = await env.ASSETS.fetch(new Request(new URL("/meta.json", request.url)));
  if (!res.ok) throw new Bad("找不到網站設定 meta.json", 503);
  return res.json();
}

const text = (v, max, label, required = false) => {
  const s = String(v ?? "").trim();
  if (required && !s) throw new Bad(`${label}不能空白`);
  if (s.length > max) throw new Bad(`${label}最多 ${max} 個字`);
  return s;
};

const isDate = s => DATE_RE.test(s) && !isNaN(Date.parse(s + "T00:00:00Z"));

// 驗證並整理成資料表欄位
function clean(project, t, meta) {
  const groups = meta.groups[project] || [];
  const members = new Set([...meta.members, "全員"]);
  const row = {
    phase: text(t.phase, 30, "階段", true),
    grp: text(t.group, 10, "組別", true),
    task: text(t.task, 120, "任務名稱", true),
    start_date: text(t.start, 10, "開始日", true),
    end_date: text(t.end, 10, "結束日", true),
    status: text(t.status, 10, "狀態", true),
    deliverable: text(t.deliverable, 200, "交付物"),
  };
  if (!groups.includes(row.grp)) throw new Bad(`組別只能是：${groups.join("、")}`);
  if (!isDate(row.start_date) || !isDate(row.end_date)) throw new Bad("日期格式要是 YYYY-MM-DD");
  if (row.end_date < row.start_date) throw new Bad("結束日不能早於開始日");
  if (!STATUSES.includes(row.status)) throw new Bad("狀態不正確");

  const owners = (Array.isArray(t.owners) ? t.owners : []).map(o => String(o).trim()).filter(Boolean);
  if (owners.length > 8) throw new Bad("負責人最多 8 位");
  for (const o of owners) {
    if (!members.has(o.replace(/（暫定）$/, ""))) throw new Bad(`負責人「${o}」不在名冊上`);
  }
  row.owners = owners.join("、");

  const depends = (Array.isArray(t.depends) ? t.depends : []).map(d => String(d).trim().toUpperCase()).filter(Boolean);
  for (const d of depends) if (!ID_RE.test(d)) throw new Bad(`需先完成的任務編號「${d}」格式不正確`);
  row.depends = [...new Set(depends)].join(";");

  if (t.sort !== undefined) {
    const n = Number(t.sort);
    if (!Number.isFinite(n)) throw new Bad("排序值不正確");
    row.sort = n;
  }
  return row;
}

async function checkDepends(q, project, id, depends) {
  if (!depends) return;
  const list = depends.split(";");
  if (list.includes(id)) throw new Bad("任務不能相依於自己");
  const rows = await q(`?project=eq.${project}&select=id`);
  const ids = new Set(rows.map(r => r.id));
  const missing = list.filter(d => !ids.has(d));
  if (missing.length) throw new Bad(`需先完成的任務不存在：${missing.join("、")}`);
}

function splitKey(key) {
  const m = /^(jnc|qkd)_([A-Z]+[0-9]+)$/.exec(String(key || ""));
  if (!m) throw new Bad("任務代號不正確");
  return { project: m[1], id: m[2] };
}

export async function onRequestPost({ request, env }) {
  const origin = request.headers.get("Origin");
  if (origin && origin !== new URL(request.url).origin) return json({ error: "不接受其他網站送來的請求" }, 403);
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) return json({ error: "網站尚未設定資料庫" }, 503);

  try {
    let body;
    try { body = await request.json(); } catch { throw new Bad("資料格式錯誤"); }
    const by = text(body.by, 20, "身分", true);
    const q = db(env);
    const minimal = { Prefer: "return=minimal" };
    const repr = { Prefer: "return=representation" };

    if (body.action === "status") {
      const { project, id } = splitKey(body.key);
      if (typeof body.done !== "boolean") throw new Bad("資料不正確");
      const [cur] = await q(`?key=eq.${project}_${id}&select=status,start_date`);
      if (!cur) throw new Bad("找不到這項任務，可能已被刪除", 404);
      const today = new Date().toISOString().slice(0, 10);
      const status = body.done ? "done" : (cur.status === "done" ? (cur.start_date <= today ? "doing" : "todo") : cur.status);
      await q(`?key=eq.${project}_${id}`, { method: "PATCH", headers: minimal, body: JSON.stringify({ status, updated_by_name: by }) });
      return json({ ok: true, status });
    }

    const meta = await loadMeta(request, env);

    if (body.action === "create") {
      const project = String(body.task?.project || "");
      if (!meta.groups[project]) throw new Bad("作品不正確");
      const id = text(body.task?.id, 10, "編號", true).toUpperCase();
      if (!ID_RE.test(id)) throw new Bad("編號格式要像 A5、S12、M3（英文大寫加數字）");
      const row = clean(project, body.task, meta);
      await checkDepends(q, project, id, row.depends);
      await q("", { method: "POST", headers: minimal, body: JSON.stringify({ ...row, key: `${project}_${id}`, project, id, updated_by_name: by }) });
      return json({ ok: true, key: `${project}_${id}` });
    }

    if (body.action === "update") {
      const { project, id } = splitKey(body.key);
      const row = clean(project, body.task || {}, meta);
      await checkDepends(q, project, id, row.depends);
      const guard = body.expected ? `&updated_at=eq.${encodeURIComponent(body.expected)}` : "";
      const out = await q(`?key=eq.${project}_${id}${guard}`, { method: "PATCH", headers: repr, body: JSON.stringify({ ...row, updated_by_name: by }) });
      if (!out || !out.length) {
        const [cur] = await q(`?key=eq.${project}_${id}&select=updated_by_name`);
        if (!cur) throw new Bad("找不到這項任務，可能已被刪除", 404);
        throw new Bad(`這項任務剛被${cur.updated_by_name || "其他人"}修改，已重新載入，請確認後再改一次`, 409);
      }
      return json({ ok: true });
    }

    if (body.action === "delete") {
      const { project, id } = splitKey(body.key);
      if ((meta.protected[project] || []).includes(id)) throw new Bad(`${id} 是報名截止里程碑，不能刪除`);
      const rows = await q(`?project=eq.${project}&select=id,depends`);
      const users = rows.filter(r => r.depends.split(";").includes(id)).map(r => r.id);
      if (users.length) throw new Bad(`還有任務需要先完成 ${id}：${users.join("、")}。請先修改它們的「需先完成」再刪除`);
      // 先記下是誰刪的，紀錄表才寫得到名字
      await q(`?key=eq.${project}_${id}`, { method: "PATCH", headers: minimal, body: JSON.stringify({ updated_by_name: by }) });
      await q(`?key=eq.${project}_${id}`, { method: "DELETE", headers: minimal });
      return json({ ok: true });
    }

    throw new Bad("不支援的操作");
  } catch (e) {
    if (e instanceof Bad) return json({ error: e.message }, e.status);
    return json({ error: "伺服器錯誤" }, 500);
  }
}

export function onRequest() {
  return json({ error: "只支援 POST" }, 405);
}
