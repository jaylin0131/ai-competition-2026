# 2026 全國 AI 專題創意競賽

同一支隊伍的兩件作品與團隊時程網站。

| 資料夾 | 內容 |
|---|---|
| [JNC-AIoT/](JNC-AIoT/) | 企業命題類 AI 應用組：銘祥科技 AIoT 預測維護與異常診斷 |
| [QKD-Eavesdrop-AI/](QKD-Eavesdrop-AI/) | 大會專題類資電領域組：QKD 鏈路 AI 健康診斷 |
| [site/](site/) | 團隊時程網站：合併兩份 `tasks.csv` 的甘特圖，成員可勾選完成 |
| [deploy/](deploy/) | 網站部署說明（Cloudflare Pages＋Supabase）與資料庫 SQL |
| [functions/](functions/)、[worker/](worker/)、`wrangler.jsonc` | Cloudflare 伺服器端程式：寫入勾選（Workers 與 Pages 共用） |
| `.github/workflows/` | 每日把網站勾選寫回 `tasks.csv` |

- 進度唯一來源：各專案的 `schedule/tasks.csv`
- 企業原始資料（`JNC-AIoT/data/raw/*.csv`）不進版控，請從命題頁下載後執行 `JNC-AIoT/scripts/prepare_data.py`
- 本儲存庫為私人，請勿改成公開
