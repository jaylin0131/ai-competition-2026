# 交接文件：JNC-AIoT（銘祥科技企業命題）

> 用途：開新對話（Claude Code 或其他 AI 助手）或新成員加入時，先讀這份就能接著做。
> 最後更新：2026-11-17。每完成一個階段請更新「目前狀態」與「下一步」，詳細紀錄寫在 [docs/progress.md](docs/progress.md)。

## 給新對話的開場提示（可直接貼上）

```
我們在做 2026 全國 AI 專題創意競賽的企業命題（銘祥科技 AIoT 預測維護與異常診斷）。
專案在 JNC-AIoT/，請先讀 JNC-AIoT/HANDOFF.md，再讀它列出的文件，然後接著做「下一步」。
回覆請用繁體中文。
```

## 1. 背景

- 比賽：2026 全國 AI 專題創意競賽（國立臺南大學主辦），**企業命題類 AI 應用組**，命題企業銘祥科技（JNC）
- 題目：AIoT 智慧感測數據應用——預測維護與異常診斷
- 隊伍：同一隊最多 6 人，同時報本作品與資電組的 QKD 作品（另一個 repo）。本作品 5 人（名冊見 [docs/team.md](docs/team.md)）：周冠辰、林子桀（智慧自動化）、許程景、王端宏（電機）、何名綸（資工）；范語芸（通訊）未列入本作品，推測負責 QKD
- 時程：報名截止 2026/12/01 23:59:59（隊內 11/28）；初賽 12/11（五）書審＋線上展示；決賽 12/19（六）臺南大學中山館
- 企業獎勵：實習或工讀 2–3 名（時薪 210 元以上或月薪 38,000 元以上）

## 2. 已確定的決定（不要再重新討論）

1. **只做 AI 分析與決策，不自建硬體。** 企業命題頁寫明「資料由銘祥提供、AI 分析由參賽團隊執行」；執行端是 SCADA／PLC 或人工，我們用軟體模擬執行與歷史回測完成成效驗證。參賽進度分析報告的「11/15 ESP32 實機閉環」改為**回放器軟體閉環**；ESP32 實機列為選配（D5、任務 A4）。
2. **輸出照企業流程圖的規格**：五項輸出（狀態辨識、異常診斷、趨勢預測、行動控制、管理優先）、標準決策資料 9 欄、執行模式三級。細節在 [docs/architecture.md](docs/architecture.md)。
3. **場域範圍**：魚塭（專家系統）是核心、五項全做；河川、羊舍是擴充；育成北側與三個空品站是加分。先做完魚塭再擴充。
4. **角色**（10/11 名單，P5、P6 暫定）：P1 隊長＋文件＝周冠辰；P2 資料平台＝林子桀（歷史基準、回放器）＋許程景（Streamlit 平台）；P3 狀態辨識＝何名綸；P4 異常診斷＝王端宏；P5 趨勢預測＝林子桀（暫定）；P6 決策引擎＋成效驗證＝許程景（暫定）。每項任務的負責人在 `schedule/tasks.csv` 的 owner 欄。
5. **技術**：Python、pandas、scikit-learn、LightGBM、Streamlit；時間序列依時間先後切分；每個功能都要有基準比較。
6. **紅線**：禁用中國或中資模型與工具（DeepSeek、Qwen 及其微調版等，完整清單與 Breeze 2、TAIDE-R1 兩個陷阱見 architecture.md 第 7 節）；作品不得已商品化；簡報、海報、影片不露出校名、系所、指導老師。
7. **時程節點**（與參賽進度分析報告一致）：10/18 資料品質報告＋介面定稿、10/25 異常偵測與溶氧預測基準版、10/31 檢查點、11/8 回放器能觸發工單、11/15 閉環 demo、11/22 功能凍結、11/28 送出報名。

## 3. 目前狀態（2026-11-26）

- 魚塭閉環完成，平台可從回放一路示範到人工確認、執行回饋與重新學習；15 項測試通過
- **11/26 依指導老師建議重算成效**（詳見 [docs/progress.md](docs/progress.md) 11/26、[backtest/report.md](backtest/report.md)）：
  - 主打：探頭可信度（同一條固定門檻規則）無效告警 286 → 0 小時、用電 −11%；已知故障 9/9；合成故障 Recall 91%；DO 預測 MAE 比持續法低 9–11%
  - 預警改用新事件定義（15 個事件）並加簡單規則基準：AI 略好但樣本少，不當主打
  - 閉環同時列工程估計與資料估計；所有數字用上線參數 α = 0.1
  - 「已驗證」門檻改為比最好的基準省 5%：目前只省 1% → validated = false，增氧決策一律人工確認（危急 DO < 2.5 仍自動）
- **D6 定案**：只用工單範本，語言模型改寫不上線（S11 實測 PR #1、#2 已合併）
- 說明書用稿 [docs/proposal-draft.md](docs/proposal-draft.md)（創新點、成效、AI 深度、限制、未來工作）；錄影腳本 [docs/demo-script.md](docs/demo-script.md)
- 規格對照：I1–I4、I6–I8 已修正；I9、I10、I11 未處理；I5 等企業回覆
- 環境：`JNC-AIoT/.venv`（Python 3.11）。這台 Mac 的 LightGBM 缺 libomp，預測模組自動改用 scikit-learn HistGradientBoosting

## 4. 下一步

0. **11/27 前定案 D4 作品名稱**。D7–D10 已於 11/26 定案：驗證門檻省 5%、目前 α = 0.1、新版主打成果須附模擬條件、手機推播列未來工作（見 docs/decisions-pending.md）。
1. **11/28 送出報名**：說明書照 docs/proposal-draft.md 改寫創新點與成效，**不要再用「79%」「54%」「286 → 9」**；切結書、學生證、影片連結
2. 錄影：照 docs/demo-script.md 錄完整版（初賽備援）與 3 分鐘剪輯版，上傳 YouTube 不公開
3. 12/11 初賽線上展示：平台只能本機執行，備援錄影存在筆電與隨身碟
4. 送件後可做：推播（LINE／Telegram）、I9 pH 預測、I11 逐筆成本比較；預警再評估要等更多事件
5. 團隊時程網站的任務狀態落後實際進度，請到網站勾選

## 5. 要先讀的檔案

| 檔案 | 內容 |
|---|---|
| [docs/team.md](docs/team.md) | 名冊、科系、角色、每人任務、工作量檢查與建議 |
| [docs/architecture.md](docs/architecture.md) | 企業規格、分層、模組介面、場域範圍、技術限制 |
| [docs/progress.md](docs/progress.md) | 進度紀錄與資料初步發現 |
| [docs/decisions-pending.md](docs/decisions-pending.md) | 待決定事項 D1–D6、待問主辦 Q1–Q7 |
| [docs/spec-compliance-82a4e31.md](docs/spec-compliance-82a4e31.md) | 魚塭閉環第一版對照企業規格的問題清單 I1–I11（I1 會當掉，先修） |
| [docs/data-dictionary.md](docs/data-dictionary.md) | 7 個場域的欄位、期間、缺漏、異常值（自動產生） |
| [backtest/report.md](backtest/report.md) | 成效驗證報告（自動產生）：偵測、預測、閉環的數字與圖 |
| [schedule/tasks.csv](schedule/tasks.csv) | 所有任務、負責人、日期、相依、狀態（網站規劃每天自動匯出的副本，勿手改；要改請到 https://ai-competition-schedule.jaylego0810.workers.dev/） |
| [docs/銘祥科技命題_AI分析與6人分工規劃_v2.pdf](docs/銘祥科技命題_AI分析與6人分工規劃_v2.pdf) | 給隊員看的完整規劃（每人交付物、成果數字、demo 流程） |
| `../2026全國AI專題創意競賽_參賽攻略手冊.pdf` | 指導老師課題組編的攻略手冊（注意：手冊主張自建硬體，已被決定 1 取代） |

## 6. 資料與程式的注意事項

- 原始檔 `data/raw/*.csv` 是 UTF-16 LE、Tab 分隔；**一律用 `common.load_jnc.load()` 讀**，不要各自寫 `pd.read_csv`
- 工地微氣候標題前有 2 列 HH／HI 要跳過；育成北側日期、小時有補零（已在 load_jnc 處理）
- 專家系統沒有增氧機開關欄位，要從「CPM 系統總和功率」推斷；無功功率為負是正常的
- 改了 `prepare_data.py` 或原始資料後要重跑它，`docs/data-dictionary.md` 與 `data/processed/` 會一起更新
- 規劃在團隊時程網站上修改；`tasks.csv`、`gantt.html`、`gantt.md` 都是每天自動產生的，不要手動改
- `scripts/build_plan_pdf_v*.py` 需要 `reportlab` 與 macOS 內建黑體，只在改規劃 PDF 時用
- 原始資料僅供競賽使用，不要上傳到公開的 repo（GitHub 請設為私人）

## 7. 相關專案（同一層資料夾）

- `../WorkSense-AI/`：另一個企業命題（富雅居 AI 工時辨識）
- QKD 作品（大會專題類）：程式與文件在另一個 repo；這裡的 `../QKD-Eavesdrop-AI/` 只剩時程網站用的 schedule/。本專案的 `build_gantt.py` 是從那裡改來的
