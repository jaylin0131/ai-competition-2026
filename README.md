# 2026 全國 AI 專題創意競賽

同一支隊伍的兩件作品與團隊時程網站。

**團隊時程網站：** https://ai-competition-schedule.jaylego0810.workers.dev/

| 資料夾 | 內容 |
|---|---|
| [JNC-AIoT/](JNC-AIoT/) | 企業命題類 AI 應用組：銘祥科技 AIoT 預測維護與異常診斷 |
| [QKD-Eavesdrop-AI/](QKD-Eavesdrop-AI/) | 只剩團隊時程網站用的 QKD 時程與名冊；QKD 作品的程式與文件已搬到另一個 repo |
| [site/](site/) | 團隊時程網站：兩件作品的甘特圖，成員可在線上勾選、修改、新增、刪除任務 |
| [deploy/](deploy/) | 網站部署說明（Cloudflare Pages＋Supabase）與資料庫 SQL |
| [functions/](functions/)、[worker/](worker/)、`wrangler.jsonc` | Cloudflare 伺服器端程式：驗證並寫入規劃的修改（Workers 與 Pages 共用） |
| `.github/workflows/` | 每天把網站規劃匯出到 `tasks.csv`；一次性把 `tasks.csv` 匯入網站 |

- 進度與規劃的唯一來源：團隊時程網站（Supabase 資料庫）。各專案的 `schedule/tasks.csv` 每天自動匯出，不要手改
- 企業原始資料（`JNC-AIoT/data/raw/*.csv`）不進版控，請從命題頁下載後執行 `JNC-AIoT/scripts/prepare_data.py`
- 本儲存庫為私人，請勿改成公開
