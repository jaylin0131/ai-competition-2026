# 交接文件：JNC-AIoT（銘祥科技企業命題）

> 用途：開新對話（Claude Code 或其他 AI 助手）或新成員加入時，先讀這份就能接著做。
> 最後更新：2026-10-11。每完成一個階段請更新「目前狀態」與「下一步」，詳細紀錄寫在 [docs/progress.md](docs/progress.md)。

## 給新對話的開場提示（可直接貼上）

```
我們在做 2026 全國 AI 專題創意競賽的企業命題（銘祥科技 AIoT 預測維護與異常診斷）。
專案在 JNC-AIoT/，請先讀 JNC-AIoT/HANDOFF.md，再讀它列出的文件，然後接著做「下一步」。
回覆請用繁體中文。
```

## 1. 背景

- 比賽：2026 全國 AI 專題創意競賽（國立臺南大學主辦），**企業命題類 AI 應用組**，命題企業銘祥科技（JNC）
- 題目：AIoT 智慧感測數據應用——預測維護與異常診斷
- 隊伍：同一隊最多 6 人，同時報本作品與資電組的 `../QKD-Eavesdrop-AI`。本作品 5 人（名冊見 [docs/team.md](docs/team.md)）：周冠辰、林子桀（智慧自動化）、許程景、王端宏（電機）、何名綸（資工）；范語芸（通訊）未列入本作品，推測負責 QKD
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

## 3. 目前狀態（2026-10-11）

- 進度 4/38（11%），沒有落後；進行中：S05 確認名冊與角色（P5、P6 暫定）、指導老師
- 10/11 加入隊員名單：新增 [docs/team.md](docs/team.md)、tasks.csv 加 owner 欄、甘特圖顯示姓名。許程景、林子桀負擔過重，team.md 有重新分配建議（未套用）
- 10/11 依參賽進度分析報告修正：tasks.csv 改用報告的里程碑、architecture.md 移除 Breeze 並加入合規模型清單與技術路線、閉環改為回放器軟體閉環、D1／D3／D5／D6 更新建議、併入上層單一私人儲存庫（見 ../README.md）
- 已完成：規則與命題整理、規劃 PDF v2、下載 7 個 CSV、共用讀檔、資料整理、資料字典、架構文件、甘特圖
- 程式現況：只有 `common/load_jnc.py`、`scripts/prepare_data.py`、`scripts/build_gantt.py`；`state/`、`diagnose/`、`forecast/`、`decide/`、`backtest/`、`app/` 都還是空的（只有 README）

## 4. 下一步

1. 10/12 會議：定案 P5、P6，決定是否採用 team.md 的重新分配建議（A1 給何名綸、E5 給王端宏），確認范語芸的歸屬與指導老師（D1、D2）→ 更新 team.md、tasks.csv owner 欄、decisions-pending.md，S05 改 done
2. P1 10/14 前寄信問主辦（Q1–Q7，特別是維修紀錄與 GI）；建立私人 GitHub 並推上本資料夾（`data/` 已被 .gitignore 排除）
3. 每人執行 `scripts/prepare_data.py`，10/18 前交 S09 資料品質報告（每組 1 頁），成果放 `notes/eda/`
4. 10/18 前定稿 [architecture.md](docs/architecture.md) 第 4 節的模組介面（S10、M1），並完成本地 LLM 實測（S11）
5. 10/19 起進入第一版開發；10/25 交基準版比較表，10/31 檢查點要求魚塭五項輸出都有第一版

## 5. 要先讀的檔案

| 檔案 | 內容 |
|---|---|
| [docs/team.md](docs/team.md) | 名冊、科系、角色、每人任務、工作量檢查與建議 |
| [docs/architecture.md](docs/architecture.md) | 企業規格、分層、模組介面、場域範圍、技術限制 |
| [docs/progress.md](docs/progress.md) | 進度紀錄與資料初步發現 |
| [docs/decisions-pending.md](docs/decisions-pending.md) | 待決定事項 D1–D6、待問主辦 Q1–Q7 |
| [docs/data-dictionary.md](docs/data-dictionary.md) | 7 個場域的欄位、期間、缺漏、異常值（自動產生） |
| [schedule/tasks.csv](schedule/tasks.csv) | 所有任務、負責人、日期、相依、狀態（進度唯一來源） |
| [docs/銘祥科技命題_AI分析與6人分工規劃_v2.pdf](docs/銘祥科技命題_AI分析與6人分工規劃_v2.pdf) | 給隊員看的完整規劃（每人交付物、成果數字、demo 流程） |
| `../2026全國AI專題創意競賽_參賽攻略手冊.pdf` | 指導老師課題組編的攻略手冊（注意：手冊主張自建硬體，已被決定 1 取代） |

## 6. 資料與程式的注意事項

- 原始檔 `data/raw/*.csv` 是 UTF-16 LE、Tab 分隔；**一律用 `common.load_jnc.load()` 讀**，不要各自寫 `pd.read_csv`
- 工地微氣候標題前有 2 列 HH／HI 要跳過；育成北側日期、小時有補零（已在 load_jnc 處理）
- 專家系統沒有增氧機開關欄位，要從「CPM 系統總和功率」推斷；無功功率為負是正常的
- 改了 `prepare_data.py` 或原始資料後要重跑它，`docs/data-dictionary.md` 與 `data/processed/` 會一起更新
- 改了 `schedule/tasks.csv` 後要重跑 `scripts/build_gantt.py`；`gantt.html`、`gantt.md` 不要手動改
- `scripts/build_plan_pdf_v*.py` 需要 `reportlab` 與 macOS 內建黑體，只在改規劃 PDF 時用
- 原始資料僅供競賽使用，不要上傳到公開的 repo（GitHub 請設為私人）

## 7. 相關專案（同一層資料夾）

- `../WorkSense-AI/`：另一個企業命題（富雅居 AI 工時辨識）
- `../QKD-Eavesdrop-AI/`：大會專題類作品；本專案的 `build_gantt.py` 是從那裡改來的
