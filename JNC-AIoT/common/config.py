"""全隊共用的門檻與參數（魚塭 pond）。

數值依 notes/eda/pond.md 的資料分布與一般養殖經驗訂定，企業未提供正式規格（見 decisions-pending Q2、Q3、Q5），
改動要在週會提出，並重跑 scripts/run_backtest.py 確認成效。
"""

from __future__ import annotations

# ---- 欄位 ----
PROBES: dict[str, list[str]] = {
    "DO": ["DO1 即時值", "DO2 即時值", "DO3 即時值"],
    "pH": ["pH1 即時值", "pH2 即時值", "pH3 即時值"],
    "ORP": ["ORP1 即時值", "ORP2 即時值", "ORP3 即時值"],
    "SC": ["SC1 即時值", "SC2 即時值", "SC3 即時值"],
}
TEMP = "DO1水溫"
POWER = "CPM 系統總和功率"
ENERGY = "CPM 總用電度數"
WEATHER = ["OA4 溫度", "OA4 濕度", "OA4 大氣壓力", "OA4 熱指數"]
WATER_LEVEL = "水位高度"
DROP_COLS = ["CPM 釋放有功電度"]  # 全期間都是 0

# ---- 物理範圍（超出＝感測器異常；0 視為失效） ----
PHYS_RANGE: dict[str, tuple[float, float]] = {
    "DO": (0.05, 20.0),
    "pH": (4.0, 10.0),
    "ORP": (50.0, 700.0),
    "SC": (0.5, 60.0),
    "temp": (10.0, 40.0),
}
# 同物理量探頭與其他探頭中位數的容許差（超過＝不一致）
PEER_TOL: dict[str, float] = {"DO": 1.0, "pH": 0.4, "ORP": 80.0, "SC": 3.0}
# 卡值：連續幾小時完全相同，且同期間其他探頭有在變化（變化 > 解析度 × 3）
STUCK_HOURS: dict[str, int] = {"DO": 6, "pH": 12, "ORP": 6, "SC": 12}
RESOLUTION: dict[str, float] = {"DO": 0.01, "pH": 0.01, "ORP": 0.1, "SC": 0.01}
# 跳點：與前 12 小時中位數差距 > max(SPIKE_K × MAD, 2 × 容許差)
SPIKE_K = 8
# 診斷可信度低於此值只當資料品質提示，不發告警、不派工
ALARM_MIN_CONF = 0.5

# ---- 水質門檻（mg/L） ----
DO_GOOD = 3.5      # 以上為綠燈
DO_LOW = 3.0       # 低溶氧門檻：低於此值計為「低溶氧時數」，紅燈
DO_CRIT = 2.5      # 危急：立即增氧，不等預測
DO_HIGH = 4.5      # 溶氧充足，可考慮節能停機（約為全期 80 百分位）

# ---- 增氧機（由 CPM 功率推斷，約 760 W 運轉、17 W 停機） ----
AERATOR_ON_W = 200.0
AERATOR_RATED_KW = 0.76
AERATOR_LOW_LOAD_W = 650.0   # 運轉中但功率明顯偏低＝疑似設備異常
ELECTRICITY_PRICE = 4.0      # 元／度（估計值，用於能耗成本）
PEAK_HOURS = range(9, 21)    # 尖峰時段（簡化）

# ---- 決策 ----
RISK_ALPHA = 0.30            # P(DO < DO_LOW, 6 h 內) 超過 α 即建議增氧；由 backtest 調整
SAVE_BETA = 0.05             # 風險低於 β 且 DO 充足才建議節能停機
PARAMS_FILE = "decide/params.json"  # backtest 調整後的 α、β 寫在這裡

# ---- 營運風險（預期損失，元）：估計值，待企業確認；回測的成本函數也用這組 ----
LOSS_PER_LOW_HOUR = 100.0      # 每 1 小時低溶氧（DO < 3）的損失
LOSS_PER_CRIT_HOUR = 300.0     # 每 1 小時危急（DO < 2.5）的損失
AERATOR_FAILURE_COST = 3000.0  # 增氧機故障（檢修＋停機期間風險）
OPS_RISK_MID = 150.0           # 6 小時預期損失 ≥ 此值為「中」
OPS_RISK_HIGH = 500.0          # ≥ 此值為「高」
AERATOR_FAIL_ALERT = 0.5       # 增氧機 48 小時內故障機率 ≥ 此值就排預防性檢修
