// 勾選完成的寫入入口：POST /api/status  {"key": "jnc_S09", "done": true, "by": "何名綸"}
// 以 Supabase 私密金鑰寫入，金鑰不會出現在網頁；只接受本站頁面送出的請求。
// 環境變數：SUPABASE_URL、SUPABASE_SERVICE_KEY（加密）。

const KEY_RE = /^(jnc|qkd)_[A-Z]+[0-9]+$/;

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8" } });

export async function onRequestPost({ request, env }) {
  // 只接受從本站頁面送出的請求
  const origin = request.headers.get("Origin");
  if (origin && origin !== new URL(request.url).origin) return json({ error: "不接受其他網站送來的請求" }, 403);
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) return json({ error: "網站尚未設定資料庫" }, 503);

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "資料格式錯誤" }, 400);
  }
  const key = String(body.key || "");
  const by = String(body.by || "").trim();
  if (!KEY_RE.test(key) || typeof body.done !== "boolean" || !by || by.length > 20) {
    return json({ error: "資料不正確" }, 400);
  }
  const i = key.indexOf("_");
  const row = { key, project: key.slice(0, i), task_id: key.slice(i + 1), done: body.done, updated_by_name: by };

  const res = await fetch(`${env.SUPABASE_URL.replace(/\/$/, "")}/rest/v1/task_status?on_conflict=key`, {
    method: "POST",
    headers: {
      apikey: env.SUPABASE_SERVICE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal",
    },
    body: JSON.stringify(row),
  });
  if (!res.ok) return json({ error: "資料庫寫入失敗", detail: (await res.text()).slice(0, 200) }, 502);
  return json({ ok: true });
}

export function onRequest() {
  return json({ error: "只支援 POST" }, 405);
}
