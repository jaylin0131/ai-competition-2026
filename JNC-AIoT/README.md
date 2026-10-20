# JNC-AIoT
AIoT 預測維護與異常診斷（2026 全國 AI 專題創意競賽・企業命題類 AI 應用組・銘祥科技）

用銘祥科技提供的 7 個場域感測資料，以 AI 回答「現在發生什麼事、接下來可能發生什麼事、現在應該採取什麼行動」，並依企業的「標準決策資料」格式輸出可執行的決策。本作品只做 AI 分析與決策，不自建硬體。

- 報名截止 **2026/12/01 23:59:59**（隊內目標 11/28）｜初賽 12/11｜決賽 12/19（臺南大學中山館）
- 接手對話或新成員請先讀 [HANDOFF.md](HANDOFF.md)

## 文件

- [交接文件（繼承對話用）](HANDOFF.md)
- [進度紀錄](docs/progress.md)｜[執行甘特圖](schedule/gantt.html)（[Mermaid 版](schedule/gantt.md)）
- [團隊分工](docs/team.md)
- [系統架構與模組介面](docs/architecture.md)
- [資料字典](docs/data-dictionary.md)（自動產生）
- [成效驗證報告](backtest/report.md)（自動產生）
- [待決定與待確認事項](docs/decisions-pending.md)
- [AI 分析與 6 人分工規劃 v2](docs/銘祥科技命題_AI分析與6人分工規劃_v2.pdf)（目前版本；人力與時程以 decisions-pending D1 與 tasks.csv 為準）｜[v1 舊版](docs/舊版/銘祥科技命題_6人分工規劃_v1.pdf)（含硬體，已取代）

## 資料夾

```
JNC-AIoT/
├── HANDOFF.md            交接文件：背景、決定、現況、下一步
├── data/
│   ├── raw/              企業原始 CSV（UTF-16，勿修改）＋ SOURCES.md
│   └── processed/        整理後 UTF-8 CSV（<site>.csv）＋ sites.json
├── common/load_jnc.py    全隊共用讀檔：load("pond")、SITES、hourly()
├── state/                P3 狀態辨識
├── diagnose/             P4 異常診斷
├── forecast/             P5 趨勢預測
├── decide/               P6 決策引擎
├── backtest/             P6＋P5 成效驗證
├── app/                  P2 Streamlit 平台
├── tests/
├── notes/eda/            資料初探（每個資料集 1 頁）
├── notes/meetings/       週會紀錄
├── schedule/             tasks.csv（由網站每天自動匯出，勿手改）、gantt.html、gantt.md
├── scripts/              prepare_data.py、build_gantt.py、build_plan_pdf_v*.py
└── docs/                 架構、資料字典、進度、待決事項、規劃 PDF
```

## 常用指令（在本資料夾執行）

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

平台（回放 demo）：

```bash
.venv/bin/streamlit run app/streamlit_app.py
```

成效驗證報告（產生 backtest/report.md 與 decide/params.json）：

```bash
.venv/bin/python scripts/run_backtest.py
```

測試：

```bash
.venv/bin/python -m pytest tests -q
```

```bash
python3 scripts/prepare_data.py
```

```bash
python3 scripts/build_gantt.py
```

讀資料：

```python
from common.load_jnc import load, SITES
df = load("pond")   # pond / river / goat / yucheng_north / yucheng1 / northeast / construction
```

更新進度：到團隊時程網站 https://ai-competition-schedule.jaylego0810.workers.dev/ 勾選完成、修改或新增任務；`schedule/tasks.csv` 與甘特圖每天自動同步。

## 參考來源

- 企業命題頁（含 7 個 CSV）：https://phpweb4.nutn.edu.tw/ilt/wordpress/?page_id=4359
- 競賽總覽：https://phpweb4.nutn.edu.tw/ilt/wordpress/?page_id=4308
- 參賽攻略手冊：`../2026全國AI專題創意競賽_參賽攻略手冊.pdf`
- 主辦聯絡：aittc.nutn@gmail.com、06-2130019
