# forecast/（P5）
趨勢預測：回答「接下來會怎樣？」。時間序列一律依時間先後切分。

- `pond.py`：DO 1–6 小時預測（GBDT 預測變化量；LightGBM，缺 libomp 時自動改 scikit-learn HistGradientBoosting）
  - 基準：持續法、24 小時季節；`walk_forward()` 4 段滾動驗證（7/15 起樣本外）
  - `p_low`：校正期殘差分布估計 6 小時內 DO < 3 的機率；`hours_to_threshold`：預計超標時間
  - `probe_rul()`：探頭偏離量 72 小時趨勢外推 → 剩餘可用時間與故障機率（預測維護）
  - `forecast(window, site, model)` 介面
