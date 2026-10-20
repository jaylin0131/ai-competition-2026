# app/（P2）
Streamlit 平台：資料回放、5 階段閉環、三個問題、決策卡（人工確認可核准／駁回）、工單、狀態燈號與探頭可信度、診斷卡、預測曲線、執行回饋、成效驗證。

```bash
.venv/bin/streamlit run app/streamlit_app.py
```

第一次啟動約 2 分鐘（訓練滾動預測模型），之後讀 `.cache/`。側欄「跳到展示情境」有 5 個預設的 demo 時間點。
