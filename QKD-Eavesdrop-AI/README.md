# QKD-Eavesdrop-AI
QKD 鏈路 AI 健康診斷：分辨量子竊聽與通道劣化（2026 全國 AI 專題創意競賽・大會專題類資電領域組）

**核心論點：** 物理知識決定看什麼，AI 決定怎麼組合——多特徵診斷能分辨通道劣化與攻擊類型，並看見 QBER 門檻完全看不到的 PNS 與偵測器致盲攻擊。（2026/10/11 依參賽進度分析報告改題，見 [ADR-0004](docs/adr/0004-pivot-to-link-health-diagnosis.md)）

## 團隊

| 組別 | 成員（科系） |
|---|---|
| A 通訊組 | 林子桀（智慧自動化）、許程景（電機）、周冠辰（智慧自動化） |
| B 機器學習組 | 王端宏（電機）、何名綸（資工，兼任 PM） |
| PM | 范語芸（通訊） |

各人負責的任務見 [docs/team.md](docs/team.md) 與甘特圖的「人員分工」區。

## 重要日期

| 日期 | 事項 |
|---|---|
| 10/14 | M1：CSV 規格 v2 定稿、分工確定 |
| 10/18 | 基本 BB84 模擬器輸出一回合一列 CSV |
| 10/25 | M2：階段一完成（協定門檻 vs 基準線 vs 決策樹比較表） |
| 10/31 | M3：檢查點（未達標就停在階段一） |
| 11/8 | 階段二：誘騙態、PNS、致盲 |
| 11/15 | M4：閉環 demo、錄第一支影片 |
| 11/22 | M5：功能凍結 |
| 11/28 | M6：目標送出報名 |
| **12/1 23:59** | **報名＋所有文件繳交截止** |
| 12/11 | 初賽（書審＋線上展示） |
| 12/19 | 決賽與頒獎（臺南大學） |

## 文件

- [執行甘特圖](schedule/gantt.html)（瀏覽器開啟）／[Mermaid 版](schedule/gantt.md)
- [專案計畫與架構](docs/project-plan.md)
- [團隊與分工](docs/team.md)
- [待團隊決定事項](docs/decisions-pending.md) ← **10/14 前要決定 D1–D9**（D1、D2、D7、D9 已依報告更新建議）
- [進度紀錄](docs/progress.md)
- [CSV 欄位規格（A→B 介面）](docs/csv-schema.md)
- [比賽規則重點](docs/competition-rules.md)
- [作品說明書大綱、影片腳本、決賽 Q&A](docs/proposal-outline.md)
- [架構決策紀錄（ADR）](docs/adr/)
- [詞彙表](GLOSSARY.md)
- 官方範本：[docs/competition/](docs/competition/)
- 對話交接：[HANDOFF.md](HANDOFF.md)

## 目錄

```
common/     CSV 欄位與七類標籤的唯一定義（A＋B）
sim/        誘騙態 BB84 模擬器（A 組）；sim/reference/ 放老師的參考程式
ml/         特徵、三種基準（門檻、基準線、規則表）、決策樹＋梯度提升（B 組）
app/        Streamlit 儀表板與診斷後行動（C 組）
tests/      pytest 單元測試
data/       模擬產生的 CSV（不進 git）
models/     model.pkl（不進 git）
reports/    評估圖表，放進說明書
schedule/   tasks.csv（由網站每天自動匯出，勿手改）與產生的甘特圖
scripts/    build_gantt.py
notes/      會議紀錄
docs/       計畫、規格、決策、規則
```

## 開始開發

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

模擬器、訓練與儀表板目前是骨架，函式裡的 `NotImplementedError` 標註了對應的任務編號（例如 `A1`），對照甘特圖開工。

## 更新進度

到團隊時程網站 https://ai-competition-schedule.jaylego0810.workers.dev/ 勾選完成、修改或新增任務。`schedule/tasks.csv` 與甘特圖每天由 GitHub Actions 自動同步，不要手改。每週會議後在 [docs/progress.md](docs/progress.md) 新增當週紀錄。
