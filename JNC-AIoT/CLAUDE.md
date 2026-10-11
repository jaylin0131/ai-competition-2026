# JNC-AIoT

開始工作前先讀 HANDOFF.md（背景、已確定的決定、目前狀態、下一步）。

- 回覆使用繁體中文
- 讀資料一律用 common/load_jnc.py 的 load()；data/raw/ 不要修改
- 進度與規劃改在團隊時程網站（https://ai-competition-schedule.jaylego0810.workers.dev/）上編輯；`schedule/tasks.csv` 每天由 GitHub Actions 從網站自動匯出並重產甘特圖，**不要手改 tasks.csv**（會被覆蓋）。要用程式大量修改時，改完 tasks.csv 後到 GitHub Actions 執行「匯入 tasks.csv 到網站」並勾選 replace
- 完成一個階段後更新 HANDOFF.md 的「目前狀態」「下一步」與 docs/progress.md
- 禁用中國或中資模型與工具（DeepSeek、Qwen 及其微調版；Breeze 2、TAIDE-R1 也不可用，清單見 docs/architecture.md 第 7 節）
