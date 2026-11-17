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

## 3. 目前狀態（2026-11-06）

- 進度 4/36（11%），沒有落後；進行中：S05 確認名冊與角色（P5、P6 暫定）
- 10/11 確定：指導老師為黃秋杰老師（D2）；取消 S06（寄信問主辦，Q1–Q7 暫不詢問，維修紀錄改用合成故障注入評估）與 S07（GitHub 等，已由上層私人儲存庫 `jaylin0131/ai-competition-2026`取代）；團隊時程網站見 ../site/ 與 ../deploy/
- 10/11 加入隊員名單：新增 [docs/team.md](docs/team.md)、tasks.csv 加 owner 欄、甘特圖顯示姓名。許程景、林子桀負擔過重，team.md 有重新分配建議（未套用）
- 10/11 依參賽進度分析報告修正：tasks.csv 改用報告的里程碑、architecture.md 移除 Breeze 並加入合規模型清單與技術路線、閉環改為回放器軟體閉環、D1／D3／D5／D6 更新建議、併入上層單一私人儲存庫（見 ../README.md）
- 10/16 完成 7 個場域的資料整理初稿：[notes/eda/](notes/eda/README.md)（每場域 1 頁＋圖，含已知事件表與共通規則），圖由 `scripts/build_eda_figures.py` 產生
- 已完成：規則與命題整理、規劃 PDF v2、下載 7 個 CSV、共用讀檔、資料整理、資料字典、架構文件、甘特圖
- **10/20 魚塭閉環第一版完成**（五項輸出都有，10/31 檢查點的要求已達成）：狀態辨識、異常診斷、DO 1–6 h 預測、決策引擎（標準決策資料 9 欄＋三級執行模式）、工單、模擬 SCADA 閉環與再學習、Streamlit 平台、7 個測試。架構對照見 [architecture.md](docs/architecture.md) 第 4 節
- 成效（[backtest/report.md](backtest/report.md)，自動產生）：9/9 已知故障事件偵測到；合成故障 Recall 88%、每週誤報 3.3 次；DO 預測 MAE 比持續法低 10–11%；低溶氧 77% 提前約 5 小時預警；閉環模擬（工程估計效果）低溶氧時數比歷史少 54%、危急時數少 87%，比「原始探頭固定門檻」省電 11%、無效告警 286→9 小時。**同樣用電量下 AI 只比調好的固定門檻略好**，說明書要照實寫
- **11/06 依企業規格對照修正**（[spec-compliance-82a4e31.md](docs/spec-compliance-82a4e31.md)）：I1 斷線工單當掉、I2 只有低風險可自動執行（採方案 1）、I8 平台注入故障、I3 增氧機故障機率、I4 營運風險、I6 環境資料進入預測都已修正；漂移偵測加 EWMA 管制圖（Recall 70%→80%）。12 個測試。commit d2f18fa、bb1abe6、1c84986、92d3c0b
- **11/17 I7 執行回饋接回再學習**：平台的核准／駁回／執行寫入 `backtest/feedback.csv`，回放經過 6 小時自動驗證預警是否成真，「重新學習」按鈕依資料與回饋更新 α、β 寫回 `decide/params.json`。閉環最後一段「結果回傳 → 再學習」已可在平台上完整示範
- 11/06 最新成效：合成故障 Recall 91%、每週誤報 4.0；預警 79% 事件、提前 5.2 小時；3 h MAE 0.195（加環境前 0.193，雜訊範圍）；閉環用電 1577 度（前 1566）。增氧機衰退提前 35–38 小時預警；營運風險分級與實際低溶氧時數一致
- 環境：`JNC-AIoT/.venv`（Python 3.11）。這台 Mac 的 LightGBM 缺 libomp，預測模組自動改用 scikit-learn HistGradientBoosting；要用 LightGBM 請 `brew install libomp`

## 4. 下一步

1. **D6 語言模型實測（S11）**：測試腳本 `scripts/llm_test.py` 已寫好，但這台 Mac 跑不了（Ollama 要 macOS 14 以上，這台 13.7.8、8 GB、硬碟只剩 2 GB）。請由有 macOS 14＋／Windows／Linux、16 GB 以上記憶體的隊員照 [notes/llm-test-howto.md](notes/llm-test-howto.md) 執行，結果寫進 notes/llm-test.md。gemma4:e4b 約 6.6–9.5 GB；TAIDE 12B 要本人在 Hugging Face 同意授權
2. 11/8 M4（回放觸發工單）程式面已達成；「推播」尚未做，可在平台加通知或寫說明書時說明以工單清單代替
3. 規格對照剩下：I9（pH 預測）、I10（說明書寫明以檔案模擬資料平台）、I11（逐筆成本比較，可接 ops_risk）、I5 等企業回覆 GI 定義
4. 閉環 demo 腳本：情境 7/19 18:00 → 核准增氧 → 回放往後 6 小時看驗證 → 按「重新學習」；再用「注入故障」示範 Fallback 與壞探頭排除
5. 待改進：SC 探頭誤報；預測在急降時低估；節能規則會在探頭清洗造成的 DO 假高點誤觸發；擴充場域（河川、羊舍）
6. 團隊時程網站的任務狀態落後實際進度，請到網站勾選（建議清單見 docs/progress.md 11/06）

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
