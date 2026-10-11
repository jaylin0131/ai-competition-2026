// Cloudflare Workers 版入口（wrangler.jsonc 的 main）。
// 寫入沿用 functions/api/status.js，Pages 與 Workers 兩種部署共用同一份邏輯。
//
// 執行時讀取的變數（Worker → 設定 → 變數和秘密）：
//   SUPABASE_SERVICE_KEY（秘密）、SUPABASE_URL、SUPABASE_ANON_KEY

import { onRequestPost as saveStatus, onRequest as statusOther } from "../functions/api/status.js";

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
    if (pathname === "/api/status") return request.method === "POST" ? saveStatus({ request, env }) : statusOther();
    if (pathname === "/config.js") return configJs(env);
    return env.ASSETS.fetch(request);
  },
};
