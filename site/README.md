# 團隊時程網站

兩件作品的甘特圖。成員選好身分後，可以在網頁上勾選完成、修改、新增、刪除任務，修改會即時同步給所有人，每一筆都記錄是誰、何時改的。

網址：https://ai-competition-schedule.jaylego0810.workers.dev/

| 檔案 | 用途 |
|---|---|
| `template.html` | 版面與程式（要改外觀改這裡） |
| `build_site.py` | 產生網頁（嵌入目前的 tasks.csv 當作備用顯示）與伺服器驗證用的 `meta.json` |
| `tasks_db.py` | `import`：tasks.csv → 網站資料庫（第一次）；`export`：網站資料庫 → tasks.csv（每天） |

建置指令（Cloudflare 每次 push 後自動執行）：`python3 site/build_site.py --mode supabase --out site/dist/index.html`

規劃存在 Supabase 的 `tasks` 表（唯一來源），每次修改寫進 `task_log`；進入時從選單選身分（不收集 email、沒有密碼），寫入經 `functions/api/tasks.js` 驗證。部署步驟見 [deploy/README.md](../deploy/README.md)。產生出來的 `dist/` 不進版控，不要手改。

> 10/11 前曾有 Claude Artifact 版（claude.ai 連結），已停用並刪除，統一使用上面的網址。
