# decide/（P6）
決策引擎：回答「現在該做什麼？」。目標、規則、風險、成本 → 標準決策資料（9 欄）→ 執行模式分級。

- `engine.py`：`decide(state, diagnoses, forecast)` 介面；規則順序：系統失效 Fallback → 危急（DO < 2.5）→ 預測性增氧（P(低溶氧) > α）→ 尖峰節能（β）→ 設備異常 → 探頭維護 → 預防性校正
  - 執行模式：低風險且已驗證＝自動執行；停機、備用機、派工＝人工確認；斷線或 DO 探頭全部不可信＝Fallback
  - `three_questions()`：企業圖的三個問題
- `workorder.py`：工單（派工、備品、能耗、電費）；範本產生，設定 `JNC_LLM_MODEL` 才用 Ollama 本機 LLM 改寫，數字守門員把關（禁用中資模型）
- `params.json`：再學習結果（α、β、是否已驗證、增氧機效果），由 `scripts/run_backtest.py` 產生
