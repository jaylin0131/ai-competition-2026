# 團隊時程網站部署：Cloudflare Pages＋Supabase（不收集 email）

目前網址：https://ai-competition-schedule.jaylego0810.workers.dev/

完成後：
- 網址 `https://ai-competition-schedule.<子網域>.workers.dev`（或 Pages 的 `.pages.dev`），任何拿到網址的人都能打開
- 第一次進入從選單選擇「你是哪一位」，之後可以在甘特圖上勾選完成、修改、新增、刪除任務，其他人即時看到，每一筆都記錄身分與時間
- 規劃的唯一來源是網站（Supabase `tasks` 表）；每天台灣時間 23:00，GitHub Actions 把它匯出到兩個專案的 `tasks.csv` 並重產甘特圖（tasks.csv 不要手改）
- 全程不需要任何人的電腦開著，也不收集成員 email

| 服務 | 用途 | 費用 |
|---|---|---|
| GitHub（私人儲存庫） | 程式碼、`tasks.csv` 副本、每日匯出排程 | 免費 |
| Cloudflare Workers（或 Pages） | 放網站、驗證並寫入修改的伺服器端程式（`worker/`、`functions/`） | 免費 |
| Supabase | 存任務規劃與修改紀錄、即時同步 | 免費（7 天無存取會暫停，每日同步會避免） |

## 安全設計

| 誰 | 能做什麼 | 怎麼把關 |
|---|---|---|
| 拿到網址的人 | 看甘特圖、選身分後勾選、修改、新增、刪除任務 | 網址只給成員；網頁加了 noindex，搜尋引擎不收錄 |
| 直接連 Supabase 的人 | 只能讀任務，不能寫 | 資料表只開放讀取；寫入只有伺服器端的私密金鑰能做 |
| 其他網站 | 不能代替成員送出修改 | `/api/tasks` 只接受本站頁面送出的請求 |
| 任何人 | 不能刪除報名截止里程碑、被其他任務依賴的任務；不能填不存在的組別、負責人、相依任務 | `/api/tasks` 伺服器端驗證 |
| 兩人同時改同一項 | 後送出的人會收到「剛被○○修改」並看到最新內容，不會無聲覆蓋 | 以最後修改時間比對 |

網站沒有密碼，身分也是自己選的：知道網址的人都能修改規劃，系統不會驗證「選何名綸的人真的是何名綸」。網址請只在團隊群組分享；若有人亂改，Supabase 的 `task_log` 記錄了每一次修改前後的完整內容、身分與時間，可以照著改回來。

依序做下面幾步，大約 30 分鐘。

---

## 1. Supabase：建立專案與資料表

1. 到 https://supabase.com 登入，按 **New project**。名稱例如 `team-schedule`，區域選 **Northeast Asia (Tokyo)** 或 **Southeast Asia (Singapore)**，設定一組資料庫密碼（自己保存，網站用不到）。
2. 左側 **SQL Editor** → **New query** → 貼上整份 `deploy/supabase.sql` → **Run**。看到 `Success` 即可（可重複執行，不會刪掉已有的勾選）。
3. 左側 **Project Settings → API**，記下：
   - **Project URL**（`https://xxxx.supabase.co`）→ `SUPABASE_URL`
   - **anon public** 金鑰 → `SUPABASE_ANON_KEY`（公開金鑰，會出現在網頁裡，只能讀）
   - **service_role** 金鑰 → `SUPABASE_SERVICE_KEY`（**私密**，只放 Cloudflare 與 GitHub 的加密設定，不要貼在聊天、網頁或程式碼）

不需要設定 Supabase 的登入（Authentication）或寄信。

---

## 3. Cloudflare：連接儲存庫並部署

Cloudflare 現在預設走 **Workers** 建立流程（畫面標題「設定您的應用程式」），本儲存庫兩種都支援，建議用 Workers。

### 3-A. Workers（建議）

1. https://dash.cloudflare.com → **Workers & Pages → 建立 → 匯入存放庫（GitHub）**，選 `ai-competition-2026`。
2. 「設定您的應用程式」畫面：

| 欄位 | 值 |
|---|---|
| 專案名稱 | `ai-competition-schedule`（必須和 `wrangler.jsonc` 的 `name` 相同） |
| 組建命令 | `python3 site/build_site.py --mode supabase --out site/dist/index.html` |
| 部署命令 | `npx wrangler deploy`（預設值） |
| 預覽指令 | `npx wrangler preview`（預設值） |
| 啟用預覽建置 | 建議關閉：預覽網址也能勾選，會寫進同一個資料庫 |

   按 **部署**。部署完成後網站就能瀏覽，但要設好下面的變數才能勾選。

3. 到該 Worker → **設定 → 變數和秘密 → 新增**：

| 類型 | 名稱 | 值 |
|---|---|---|
| 秘密 | `SUPABASE_SERVICE_KEY` | 第 1 步的 service_role 金鑰 |
| 文字 | `SUPABASE_URL` | 第 1 步的 Project URL |
| 文字 | `SUPABASE_ANON_KEY` | 第 1 步的 anon public 金鑰 |

   儲存後立即生效（`wrangler.jsonc` 設了 `keep_vars`，之後自動部署不會清掉這些變數）。網址是 `https://ai-competition-schedule.<你的子網域>.workers.dev`，在 Worker 首頁可看到。

4. 之後只要 push 到 `main`（包含每日同步的 commit），Cloudflare 都會自動重新建置部署。

### 3-B. Pages（替代做法）

在「建立」頁面底部找 Pages 入口 → **Connect to Git**：

| 欄位 | 值 |
|---|---|
| Framework preset | `None` |
| Build command | `python3 site/build_site.py --mode supabase --out site/dist/index.html` |
| Build output directory | `site/dist` |

環境變數（Production 與 Preview 都加，私密的按 Encrypt）：`SUPABASE_URL`、`SUPABASE_ANON_KEY`、`SUPABASE_SERVICE_KEY`（加密）、`PYTHON_VERSION=3.12`。Pages 會使用 `functions/` 資料夾，改了環境變數要 **Retry deployment** 才生效。

---

## 4. GitHub：設定 Secrets 並匯入任務

到 GitHub 儲存庫 **Settings → Secrets and variables → Actions → New repository secret**，新增兩個：

| 名稱 | 值 |
|---|---|
| `SUPABASE_URL` | 第 1 步的 Project URL |
| `SUPABASE_SERVICE_KEY` | 第 1 步的 service_role 金鑰 |

接著到 **Actions** 分頁：

1. **匯入 tasks.csv 到網站 → Run workflow**（replace 不要勾）→ 看到綠色勾勾、輸出「已匯入 88 項任務」。這一步只要做一次，把目前兩個專案的規劃放進網站資料庫；之前在網站上勾選過的完成狀態也會一起帶入。
2. **網站規劃同步到 tasks.csv → Run workflow** → 確認可以從網站匯出（之後每天 23:00 自動執行）。

> 已經部署過舊版（只有勾選功能）的專案：先把整份 `deploy/supabase.sql` 在 SQL Editor 重新執行一次（會新增 `tasks`、`task_log` 兩張表，不會刪資料），再做上面兩步。

---

## 5. 驗收

1. 用無痕視窗打開網址 → 跳出「你是哪一位？」→ 從選單選自己 → 按確定 → 上方顯示「目前身分」選單為自己，狀態燈「已連線」。
2. 用上方的「目前身分」選單換成別人再換回來，確認可以切換。
3. 勾一個任務 → 另一位成員的畫面幾秒內也打勾；點開該列，「最後修改」顯示「○○○ 於 10/14 21:03」。
4. 點開任務 →「編輯這項任務」→ 改名稱或日期 → 儲存，另一位成員畫面即時更新；按甘特圖右上「＋ 新增任務」新增一項，再刪掉它。
5. 到 GitHub Actions 手動跑一次「網站規劃同步到 tasks.csv」→ `tasks.csv` 出現剛才的修改，儲存庫多一筆 bot commit，Cloudflare 自動重新部署。

## 日常使用

| 想做的事 | 怎麼做 |
|---|---|
| 標記完成 | 網頁上直接勾 |
| 換身分（例如借別人電腦） | 網頁上方「目前身分」選單 |
| 改名稱、日期、負責人、相依、交付物 | 點開任務 →「編輯這項任務」→ 儲存 |
| 新增任務 | 甘特圖右上「＋ 新增任務」；編號用英文大寫加數字，里程碑用 M 開頭 |
| 刪除任務 | 編輯畫面左下「刪除這項任務」，再按一次確認；報名截止里程碑與被依賴的任務不能刪 |
| 大量修改（例如請 Claude 一次重排） | 改 `tasks.csv` 後到 Actions 執行「匯入 tasks.csv 到網站」並勾選 replace（會覆蓋網站上未匯出的修改，先執行一次同步再改） |
| 新增或更換成員 | 改 `QKD-Eavesdrop-AI/schedule/team.csv` 並 commit，身分選單會自動更新 |
| 看誰改了什麼 | 網頁點開任務列看最後修改；完整紀錄（改前改後）在 Supabase **Table Editor → task_log** |
| 立刻寫回 tasks.csv | GitHub Actions 手動執行「網站規劃同步到 tasks.csv」 |

## 疑難排解

| 狀況 | 原因與處理 |
|---|---|
| 網站顯示「網站資料庫還沒有任務」 | 還沒執行 Actions 的「匯入 tasks.csv 到網站」（第 4 步） |
| 儲存時顯示「剛被○○修改」 | 有人同時改了同一項；畫面已更新成最新內容，確認後再按一次儲存 |
| 每日同步失敗 | 打開 Actions 的紀錄看錯誤；常見原因是 Secrets 沒設或 Supabase 專案被暫停 |
| 勾選後顯示「沒有存到：網站尚未設定資料庫」 | Cloudflare 缺 `SUPABASE_URL` 或 `SUPABASE_SERVICE_KEY` |
| 勾選後顯示「沒有存到：資料庫寫入失敗」 | `supabase.sql` 沒執行成功，或 service_role 金鑰貼錯 |
| 狀態燈顯示「讀取失敗」 | `SUPABASE_ANON_KEY` 貼錯，或 `supabase.sql` 沒執行 |
| 狀態燈顯示即時同步中斷 | 勾選仍會儲存；重新整理即可看到別人的更新 |
| Supabase 顯示專案已暫停 | 到控制台按 Restore；確認每日同步排程有在跑 |
