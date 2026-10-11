// Cloudflare Workers 版入口（wrangler.jsonc 的 main）。
// 寫入沿用 functions/api/tasks.js，Pages 與 Workers 兩種部署共用同一份邏輯。
//
// 執行時讀取的變數（Worker → 設定 → 變數和秘密）：
//   SUPABASE_SERVICE_KEY（秘密）、SUPABASE_URL、SUPABASE_ANON_KEY

import { onRequestPost as saveTask, onRequest as tasksOther } from "../functions/api/tasks.js";

// 網頁在執行時從這裡取得 Supabase 連線資訊，所以建置時不需要設定環境變數
function configJs(env) {
  const cfg = { url: env.SUPABASE_URL || "", anonKey: env.SUPABASE_ANON_KEY || "" };
  return new Response(`window.SITE_CONFIG = ${JSON.stringify(cfg)};`, {
    headers: { "Content-Type": "text/javascript; charset=utf-8", "Cache-Control": "no-store" },
  });
}

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === "/api/tasks") return request.method === "POST" ? saveTask({ request, env }) : tasksOther();
    if (pathname === "/config.js") return configJs(env);
    return env.ASSETS.fetch(request);
  },
};
