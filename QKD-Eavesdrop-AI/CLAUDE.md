# QKD-Eavesdrop-AI

回覆一律使用繁體中文（台灣用語）。

先讀交接檔掌握專案背景、已做的決定與目前狀態：

@HANDOFF.md

## 工作規則

- 負責人姓名必須和 `schedule/team.csv` 一致（網站上的負責人選單就是讀這份名冊）
- 進度與規劃改在團隊時程網站（https://ai-competition-schedule.jaylego0810.workers.dev/）上編輯；`schedule/tasks.csv` 每天由 GitHub Actions 從網站自動匯出並重產甘特圖，**不要手改 tasks.csv**（會被覆蓋）。要用程式大量修改時，改完 tasks.csv 後到 GitHub Actions 執行「匯入 tasks.csv 到網站」並勾選 replace；也不要手改 `schedule/gantt.html`、`schedule/gantt.md`
- CSV 欄位名稱只能從 `common/schema.py` 引用；`attack_ratio`、`fault_severity`、`faults`、`noise_level` 不可當特徵；一律以回合為單位，不可逐光子標記
- 新增任何模型或 AI 套件前確認不是中國／中資來源（ADR-0003，含 Breeze 2 與 TAIDE-R1 兩個陷阱）
- 不可寫「AI 讓 QKD 更安全」；AI 的定位見 ADR-0004
- 對話結束前更新 `HANDOFF.md` 的「目前狀態」與「對話紀錄」
