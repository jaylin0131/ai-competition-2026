# 團隊時程網站部署：Cloudflare Pages＋Supabase

完成後：
- 網址 `https://<專案名稱>.pages.dev`，只有名單上的成員能打開（Cloudflare Access）
- 成員用 email 登入連結登入，就能在甘特圖上勾選完成，其他人即時看到（Supabase）
- 每天台灣時間 23:00，GitHub Actions 把勾選寫回兩個專案的 `tasks.csv`，並重產甘特圖
- 任何人改 `tasks.csv` 並 push，Cloudflare 會自動重新部署
- 全程不需要任何人的電腦開著

| 服務 | 用途 | 費用 |
|---|---|---|
| GitHub（私人儲存庫） | 程式碼、`tasks.csv`、每日同步排程 | 免費 |
| Cloudflare Pages | 建置並放網站 | 免費 |
| Cloudflare Zero Trust（Access） | 只讓成員打開網站 | 免費（50 人內） |
| Supabase | 勾選資料、登入、即時同步 | 免費（7 天無存取會暫停，每日同步會避免） |

依序做下面五步，大約 40 分鐘。

---

## 1. Supabase：建立專案與資料表

1. 到 https://supabase.com 登入，按 **New project**。名稱例如 `team-schedule`，區域選 **Northeast Asia (Tokyo)** 或 **Southeast Asia (Singapore)**，設定一組資料庫密碼（自己保存，網站用不到）。
2. 打開 `deploy/supabase.sql`，把最後一段的 6 個 `memberN@example.com` 改成成員實際收得到信的 email（姓名要和 `tasks.csv` 的 owner 一致）。
3. 左側 **SQL Editor** → **New query** → 貼上整份 `supabase.sql` → **Run**。看到 `Success` 即可（可重複執行）。
4. 左側 **Project Settings → API**，記下：
   - **Project URL**（`https://xxxx.supabase.co`）→ 之後叫 `SUPABASE_URL`
   - **anon public** 金鑰 → `SUPABASE_ANON_KEY`（公開金鑰，會出現在網頁裡，安全靠資料表權限）
   - **service_role** 金鑰 → `SUPABASE_SERVICE_KEY`（**私密**，只放 GitHub Secrets，不要貼在聊天、網頁或程式碼）

### 1-1. 讓登入信寄得出去（重要）

Supabase 內建的寄信服務只寄給 Supabase 專案的團隊成員，而且每小時只能寄幾封。成員要收到登入連結，二選一：

- **用一個 Gmail 寄信（建議）**：該 Gmail 開啟兩步驟驗證 → Google 帳戶「應用程式密碼」產生一組密碼 → Supabase **Authentication → Emails → SMTP Settings** 開啟 Custom SMTP：
  - Host `smtp.gmail.com`、Port `587`、Username＝該 Gmail、Password＝應用程式密碼、Sender email＝該 Gmail、Sender name＝`AI 競賽團隊時程`
- **把 6 位成員邀請進 Supabase 組織**（Organization → Team → Invite）：內建寄信就會寄給他們，但每小時仍只有少量額度。

### 1-2. 設定登入後回到網站

完成第 3 步拿到網址後，回到 **Authentication → URL Configuration**：
- **Site URL**：`https://<專案名稱>.pages.dev`
- **Redirect URLs**：加入 `https://<專案名稱>.pages.dev/**`

---

## 2. GitHub：設定 Secrets

儲存庫已建立為私人（見 README）。到 GitHub 儲存庫 **Settings → Secrets and variables → Actions → New repository secret**，新增兩個：

| 名稱 | 值 |
|---|---|
| `SUPABASE_URL` | 第 1 步的 Project URL |
| `SUPABASE_SERVICE_KEY` | 第 1 步的 service_role 金鑰 |

設定後到 **Actions → 同步網頁勾選到 tasks.csv → Run workflow** 手動跑一次，看到綠色勾勾、輸出「網站上有 0 筆勾選紀錄」就對了。

---

## 3. Cloudflare Pages：連接儲存庫並部署

1. 到 https://dash.cloudflare.com 登入 → **Workers & Pages → Create → Pages → Connect to Git**，授權 GitHub 並選這個儲存庫。
2. 建置設定：

| 欄位 | 值 |
|---|---|
| Production branch | `main` |
| Framework preset | `None` |
| Build command | `python3 site/build_site.py --mode supabase --out site/dist/index.html` |
| Build output directory | `site/dist` |

3. **Environment variables**（Production 與 Preview 都要加）：

| 名稱 | 值 |
|---|---|
| `SUPABASE_URL` | 第 1 步的 Project URL |
| `SUPABASE_ANON_KEY` | 第 1 步的 anon public 金鑰 |
| `PYTHON_VERSION` | `3.12` |

4. **Save and Deploy**。完成後得到 `https://<專案名稱>.pages.dev`，回去做第 1-2 步。
5. 之後只要 push 到 `main`（包含每日同步的 commit），Cloudflare 都會自動重新部署。

> 建置紀錄若出現「警告：沒有設定 SUPABASE_URL」，代表環境變數沒加到，網站會是唯讀。

---

## 4. Cloudflare Access：只讓成員打開

1. Cloudflare 左側 **Zero Trust**（第一次會要求選免費方案並取一個團隊名稱）。
2. **Access → Applications → Add an application → Self-hosted**：
   - Application domain：`<專案名稱>.pages.dev`
   - 再加一筆 `*.<專案名稱>.pages.dev`（預覽部署也保護起來）
3. 新增 Policy：Action **Allow**，Include **Emails**，填入 6 位成員的 email。
4. 登入方式用預設的 **One-time PIN**（輸入 email 收驗證碼）。

成員第一次打開網站要過兩道：Cloudflare 驗證碼（能不能看）→ 網頁上的「寄登入連結」（能不能勾）。兩邊的 email 名單要一致。

---

## 5. 驗收

1. 用名單外的 email 打開網址 → 應該被 Cloudflare 擋下。
2. 成員打開網址 → 在網頁上方輸入 email → 收信點連結 → 回到網站，右上顯示自己的名字、狀態燈「已連線」。
3. 勾一個任務 → 另一位成員的畫面幾秒內也打勾。
4. 到 GitHub Actions 手動跑一次同步 → 該任務在 `tasks.csv` 變成 `done`，儲存庫多一筆 bot commit，Cloudflare 自動重新部署。

## 日常使用

| 想做的事 | 怎麼做 |
|---|---|
| 標記完成 | 網頁上直接勾 |
| 改日期、負責人、新增任務 | 在 GitHub 網頁上編輯 `JNC-AIoT/schedule/tasks.csv` 或 `QKD-Eavesdrop-AI/schedule/tasks.csv` → Commit，網站自動更新；或請 Claude（claude.ai/code 雲端）代改 |
| 新增或更換成員 | Supabase SQL Editor：`insert into public.members (email, name) values ('新信箱', '姓名');`，並同步更新 Cloudflare Access 名單 |
| 看誰勾了什麼 | 網頁點開任務列；或 Supabase **Table Editor → task_status_log** |
| 立刻寫回 tasks.csv | GitHub Actions 手動執行「同步網頁勾選到 tasks.csv」 |

## 疑難排解

| 狀況 | 原因與處理 |
|---|---|
| 收不到登入信 | 沒設定 Custom SMTP（第 1-1 步），或信被歸到垃圾郵件 |
| 點連結後回到 localhost 或錯誤頁 | 第 1-2 步的 Site URL／Redirect URLs 沒設 |
| 登入後顯示「這個 email 不在成員名單上」 | `members` 表沒有這個 email（大小寫不影響） |
| 勾選後顯示「沒有寫入權限」 | 同上；或 `supabase.sql` 沒執行成功 |
| 狀態燈顯示即時同步中斷 | 勾選仍會儲存；重新整理即可看到別人的更新 |
| Supabase 顯示專案已暫停 | 到控制台按 Restore；確認每日同步排程有在跑 |
