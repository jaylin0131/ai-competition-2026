# backtest/（P6、P5）
成效驗證：在歷史資料上比較「照 AI 建議做」與「不做／固定門檻」。

- `detection.py`：異常診斷 Precision／Recall（合成故障注入）、已知事件召回率
- `effect.py`：增氧機對 DO 的影響（資料估計＋工程估計兩組）
- `closed_loop.py`：模擬 SCADA／PLC 執行，比較 4 種策略（歷史實際、原始探頭固定門檻、固定門檻、AI 決策）；`tune()` 再學習 α、β
- `report.md`、`figures/`：由 `scripts/run_backtest.py` 自動產生，勿手改
