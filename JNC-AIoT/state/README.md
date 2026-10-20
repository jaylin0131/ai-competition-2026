# state/（P3）
狀態辨識：回答「現在發生什麼事？」。介面見 docs/architecture.md 第 4 節。

- `pond.py`：魚塭第一版（2026-10-20）
  - `sensor_checks(df)`：每支探頭的物理範圍、卡值（其他探頭在變、這支不動）、跳點、與另外兩支的偏離 → 可信度 0–100
  - `fused()`：可信度 ≥ 50 的探頭取中位數；`wqi()`：DO 50%、pH 20%、水溫 15%、ORP 15%；`light()`：綠／黃／紅／灰
  - `assess(df)` 全期間逐小時、`state(window)` 介面
- 門檻都在 `common/config.py`
