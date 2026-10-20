# diagnose/（P4）
異常診斷：回答「是感測器壞了，還是水質真的出事？」，每筆附可能原因、判斷證據、診斷可信度。

- `pond.py`：魚塭第一版。type：`offline`、`sensor_fault`、`sensor_drift`、`water_event`、`equipment_fault`、`multivariate`（Isolation Forest）
  - `diagnose_frame()` 逐小時、`to_episodes()` 合併事件、`diagnose(window)` 介面
- 可信度 < `ALARM_MIN_CONF`（0.5）只當資料品質提示、不派工
- 評估在 `backtest/detection.py`（合成故障注入＋已知事件），結果見 `backtest/report.md`
