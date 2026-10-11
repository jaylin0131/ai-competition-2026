# 團隊時程網站

把 `JNC-AIoT` 與 `QKD-Eavesdrop-AI` 兩個專案的 `schedule/tasks.csv` 合併成一頁甘特圖，成員可在網頁上勾選完成。

網址：https://ai-competition-schedule.jaylego0810.workers.dev/

| 檔案 | 用途 |
|---|---|
| `template.html` | 版面與程式（要改外觀改這裡） |
| `build_site.py` | 讀兩份 tasks.csv 與 `QKD-Eavesdrop-AI/schedule/team.csv`，產生網頁 |
| `sync_status.py` | 把網站勾選寫回 tasks.csv（GitHub Actions 每天執行） |

建置指令（Cloudflare 每次 push 後自動執行）：`python3 site/build_site.py --mode supabase --out site/dist/index.html`

勾選存在 Supabase；進入時從選單選身分（不收集 email、沒有密碼），寫入經 `functions/api/status.js`。部署步驟見 [deploy/README.md](../deploy/README.md)。產生出來的 `dist/` 不進版控，不要手改。

> 10/11 前曾有 Claude Artifact 版（claude.ai 連結），已停用並刪除，統一使用上面的網址。
