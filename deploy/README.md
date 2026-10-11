# 團隊時程網站部署：Cloudflare Pages＋Supabase（不收集 email）

完成後：
- 網址 `https://ai-competition-schedule.<子網域>.workers.dev`（或 Pages 的 `.pages.dev`），任何拿到網址的人都能打開
- 第一次進入從選單選擇「你是哪一位」，之後在甘特圖上勾選完成，其他人即時看到，每次勾選與取消都記錄身分與時間
- 每天台灣時間 23:00，GitHub Actions 把勾選寫回兩個專案的 `tasks.csv`，並重產甘特圖
- 任何人改 `tasks.csv` 並 push，Cloudflare 會自動重新部署
- 全程不需要任何人的電腦開著，也不收集成員 email

| 服務 | 用途 | 費用 |
|---|---|---|
| GitHub（私人儲存庫） | 程式碼、`tasks.csv`、每日同步排程 | 免費 |
| Cloudflare Workers（或 Pages） | 放網站、寫入勾選的伺服器端程式（`worker/`、`functions/`） | 免費 |
| Supabase | 存勾選狀態與紀錄、即時同步 | 免費（7 天無存取會暫停，每日同步會避免） |

## 安全設計

| 誰 | 能做什麼 | 怎麼把關 |
|---|---|---|
| 拿到網址的人 | 看甘特圖、選身分後勾選完成 | 網址只給成員；網頁加了 noindex，搜尋引擎不收錄 |
| 直接連 Supabase 的人 | 只能讀勾選狀態，不能寫 | 資料表只開放讀取；寫入只有伺服器端的私密金鑰能做 |
| 其他網站 | 不能代替成員送出勾選 | `/api/status` 只接受本站頁面送出的請求 |

網站沒有密碼，身分也是自己選的：知道網址的人都能勾選，系統不會驗證「選何名綸的人真的是何名綸」。網址請只在團隊群組分享；若有人亂勾，從操作紀錄（`task_status_log`）查得到是用哪個身分、何時勾的，取消勾選即可還原。

依序做下面幾步，大約 25 分鐘。

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

## 4. GitHub：設定每日同步

到 GitHub 儲存庫 **Settings → Secrets and variables → Actions → New repository secret**，新增兩個：

| 名稱 | 值 |
|---|---|
| `SUPABASE_URL` | 第 1 步的 Project URL |
| `SUPABASE_SERVICE_KEY` | 第 1 步的 service_role 金鑰 |

設定後到 **Actions → 同步網頁勾選到 tasks.csv → Run workflow** 手動跑一次，看到綠色勾勾、輸出「網站上有 0 筆勾選紀錄」就對了。

---

## 5. 驗收

1. 用無痕視窗打開網址 → 跳出「你是哪一位？」→ 從選單選自己 → 按確定 → 上方顯示「目前身分」選單為自己，狀態燈「已連線」。
2. 用上方的「目前身分」選單換成別人再換回來，確認可以切換。
3. 勾一個任務 → 另一位成員的畫面幾秒內也打勾；點開該列，勾選紀錄顯示「○○○ 於 10/14 21:03 勾選完成」。
4. 到 GitHub Actions 手動跑一次同步 → 該任務在 `tasks.csv` 變成 `done`，儲存庫多一筆 bot commit，Cloudflare 自動重新部署。

## 日常使用

| 想做的事 | 怎麼做 |
|---|---|
| 標記完成 | 網頁上直接勾 |
| 換身分（例如借別人電腦） | 網頁上方「目前身分」選單 |
| 改日期、負責人、新增任務 | 在 GitHub 網頁上編輯 `JNC-AIoT/schedule/tasks.csv` 或 `QKD-Eavesdrop-AI/schedule/tasks.csv` → Commit，網站自動更新；或請 Claude（claude.ai/code 雲端）代改 |
| 新增或更換成員 | 改 `QKD-Eavesdrop-AI/schedule/team.csv` 並 commit，身分選單會自動更新 |
| 看誰勾了什麼 | 網頁點開任務列；或 Supabase **Table Editor → task_status_log** |
| 立刻寫回 tasks.csv | GitHub Actions 手動執行「同步網頁勾選到 tasks.csv」 |

## 疑難排解

| 狀況 | 原因與處理 |
|---|---|
| 勾選後顯示「沒有存到：網站尚未設定資料庫」 | Cloudflare 缺 `SUPABASE_URL` 或 `SUPABASE_SERVICE_KEY` |
| 勾選後顯示「沒有存到：資料庫寫入失敗」 | `supabase.sql` 沒執行成功，或 service_role 金鑰貼錯 |
| 狀態燈顯示「讀取失敗」 | `SUPABASE_ANON_KEY` 貼錯，或 `supabase.sql` 沒執行 |
| 狀態燈顯示即時同步中斷 | 勾選仍會儲存；重新整理即可看到別人的更新 |
| Supabase 顯示專案已暫停 | 到控制台按 Restore；確認每日同步排程有在跑 |
