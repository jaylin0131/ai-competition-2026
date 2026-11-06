# D6／S11 語言模型實測：在其他電腦執行

> 為什麼不在原本那台 Mac 跑：Ollama 要 macOS 14（Sonoma）以上，那台是 macOS 13、8 GB 記憶體、硬碟只剩 2 GB。
> 結果請寫回 `notes/llm-test.md`（腳本會自動產生），再 commit。

## 1. 電腦需求

| 項目 | 需求 |
|---|---|
| 作業系統 | macOS 14 以上、Windows 10／11 或 Linux |
| 記憶體 | 只測 Gemma 4 E4B：16 GB 以上；加測 TAIDE 12B：建議有 8–12 GB 顯示卡，或 32 GB 記憶體 |
| 硬碟 | 至少 20 GB 可用（gemma4:e4b 約 6.6–9.5 GB，TAIDE 12B 量化版約 7–8 GB） |
| 網路 | 下載模型時需要；測試本身離線即可 |

## 2. 準備專案與資料

1. clone 私人儲存庫 `jaylin0131/ai-competition-2026`，進入 `JNC-AIoT/`
2. 企業原始 CSV 不在 repo 裡：從企業命題頁（https://phpweb4.nutn.edu.tw/ilt/wordpress/?page_id=4359）下載 7 個 CSV 放到 `JNC-AIoT/data/raw/`（檔名見 `data/raw/SOURCES.md`）
3. 建立環境並整理資料

macOS／Linux：

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python scripts/prepare_data.py
```

Windows（PowerShell）：

```powershell
py -m venv .venv; .venv\Scripts\pip install -r requirements.txt
```

```powershell
.venv\Scripts\python scripts\prepare_data.py
```

## 3. 安裝 Ollama 與下載模型

1. 從 https://ollama.com/download 安裝 Ollama（macOS 把 `Ollama.app` 拖到「應用程式」；Windows、Linux 照網站步驟）
2. 下載 Gemma 4 E4B（預設候選）：

```bash
ollama pull gemma4:e4b
```

3. TAIDE（選測）：`Gemma-3-TAIDE-12b-Chat-2602` 在 Hugging Face 上需要**先登入並同意授權條款**才能下載，請由使用這台電腦的隊員本人同意（說明書的 AI 工具揭露要註明）。
   - 若官方或可信來源有提供 GGUF 量化檔，可以用 `ollama pull hf.co/<帳號>/<儲存庫>:<量化>` 下載；需要授權的儲存庫要先依 Hugging Face 說明把 Ollama 的金鑰加到自己的帳號
   - 只有原始權重時，要先轉成 GGUF 再用 Modelfile 匯入，比較費時，時間不夠可以只測 E4B
   - **不可用**：Llama-3.1-TAIDE-R1（含 DeepSeek 權重）、Breeze 2、任何 Qwen、DeepSeek 衍生模型（完整清單見 `docs/architecture.md` 第 7 節）

## 4. 執行測試

先確認 Ollama 在背景執行（macOS／Windows 開啟 Ollama 程式即可；Linux 執行 `ollama serve`），然後在 `JNC-AIoT/` 執行：

```bash
.venv/bin/python scripts/llm_test.py gemma4:e4b
```

同時測兩個模型（第二個名稱換成你匯入時取的名字）：

```bash
.venv/bin/python scripts/llm_test.py gemma4:e4b taide-12b
```

- Windows 把 `.venv/bin/python` 換成 `.venv\Scripts\python`
- 第一次執行會先訓練預測模型（約 2–5 分鐘），之後讀 `.cache/`
- 每張工單預設最多等 180 秒；筆電很慢時可以加長：macOS／Linux 在指令前加 `JNC_LLM_TIMEOUT=600 `

## 5. 填寫結果

腳本會產生：

- `notes/llm-test.md`：每個模型的成功回應數、守門員擋下次數、含中文數字次數、平均秒數、token/s，以及每張工單的原文與輸出
- `notes/llm-test/<模型>.json`：原始輸出

人工要補的兩件事：

1. 「中文品質」欄：讀 10 則輸出，依通順、用詞是否像給現場人員看的工單、有沒有改動動作或時間，給 1–5 分
2. 「結論」段：選哪個模型、平台是否預設開啟 LLM 改寫（設 `JNC_LLM_MODEL`）、決賽離線時用哪台電腦

另外記下電腦規格（腳本會自動寫 CPU、記憶體、作業系統與 Ollama 版本；有顯示卡請手動補上型號）。

## 6. 判讀重點

- **守門員擋下**：輸出出現原始決策沒有的數字，平台會自動退回範本，不會出錯，但次數多代表模型不可靠
- **含中文數字**：例如「五小時」不會被守門員擋下，要人工確認數字是否正確；若常出錯，要在提示詞加「數字一律用阿拉伯數字」
- **速度**：決賽現場一次要改寫 1–3 張工單，平均 30 秒以內比較可接受
