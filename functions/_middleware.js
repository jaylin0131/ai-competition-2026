// 整個網站（頁面與 /api）都要先輸入團隊密碼才看得到。
// 密碼放在 Cloudflare Pages 的環境變數 SITE_PASSWORD（加密），帳號欄位填什麼都可以。
// 瀏覽器會記住密碼，同一台裝置之後不用再輸入。

const REALM = 'Basic realm="AI Team Schedule", charset="UTF-8"'; // 標頭只能用英數字

function unauthorized(message) {
  return new Response(message, {
    status: 401,
    headers: { "WWW-Authenticate": REALM, "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" },
  });
}

function passwordFrom(header) {
  if (!header || !header.startsWith("Basic ")) return null;
  try {
    const bytes = Uint8Array.from(atob(header.slice(6)), c => c.charCodeAt(0));
    const raw = new TextDecoder().decode(bytes);
    const i = raw.indexOf(":");
    return i < 0 ? null : raw.slice(i + 1);
  } catch {
    return null;
  }
}

async function same(a, b) {
  // 先各自雜湊再比較，長度不同也不會提早結束，避免從回應時間猜出密碼
  const enc = new TextEncoder();
  const [x, y] = await Promise.all([crypto.subtle.digest("SHA-256", enc.encode(a)), crypto.subtle.digest("SHA-256", enc.encode(b))]);
  return crypto.subtle.timingSafeEqual(x, y);
}

export async function onRequest({ request, env, next }) {
  const expected = env.SITE_PASSWORD;
  if (!expected) {
    return new Response("網站尚未設定 SITE_PASSWORD，請在 Cloudflare Pages 的環境變數加入團隊密碼。", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
  const given = passwordFrom(request.headers.get("Authorization"));
  if (given === null || !(await same(given, expected))) {
    return unauthorized("請輸入團隊密碼（帳號欄位填什麼都可以）。");
  }
  const res = await next();
  const out = new Response(res.body, res);
  out.headers.set("Cache-Control", "no-store");
  out.headers.set("X-Robots-Tag", "noindex");
  return out;
}
