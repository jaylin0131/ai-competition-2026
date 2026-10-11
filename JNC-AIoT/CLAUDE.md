# JNC-AIoT

開始工作前先讀 HANDOFF.md（背景、已確定的決定、目前狀態、下一步）。

- 回覆使用繁體中文
- 讀資料一律用 common/load_jnc.py 的 load()；data/raw/ 不要修改
- 進度只改 schedule/tasks.csv，改完執行 python3 scripts/build_gantt.py
- 完成一個階段後更新 HANDOFF.md 的「目前狀態」「下一步」與 docs/progress.md
- 禁用中國或中資模型與工具（DeepSeek、Qwen 及其微調版；Breeze 2、TAIDE-R1 也不可用，清單見 docs/architecture.md 第 7 節）
