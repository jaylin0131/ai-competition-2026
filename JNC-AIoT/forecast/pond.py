"""03 AI 分析：趨勢預測（魚塭）。回答「接下來會怎樣？」

- 溶氧 1–6 小時預測：預測「h 小時後與現在的差」，梯度提升（LightGBM；本機缺 libomp 時改用 scikit-learn HistGradientBoosting，同為 GBDT）
- 基準：持續法（DO 不變）、24 小時季節基準（昨天同時段）
- 超標時間：預測值第一次低於 DO_LOW 的小時數
- 低溶氧機率：用校正期的殘差分布估計 P(DO < DO_LOW)，取 1–6 小時的最大值
- 探頭剩餘可用時間（預測維護）：探頭偏離量的 72 小時線性趨勢外推到容許差

時間序列一律依時間先後切分；特徵只用當下與過去。

    fc = DOForecaster().fit(frame.loc[:split])
    pred = fc.predict(frame)               # 逐小時 h1..h6、p_low
    f = forecast(window, "pond", fc, frame)   # 介面
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import config as C

HORIZONS = range(1, 7)


def _regressor(seed: int = 0):
    """小資料（約 2,000 小時）要強正則化；用絕對誤差損失，對探頭殘留的跳點較不敏感。"""
    try:
        import lightgbm as lgb
        lgb.LGBMRegressor  # 觸發載入 dylib
        return lgb.LGBMRegressor(objective="l1", n_estimators=150, learning_rate=0.05, num_leaves=7,
                                 min_child_samples=60, random_state=seed, verbose=-1), "LightGBM"
    except (ImportError, OSError):
        from sklearn.ensemble import HistGradientBoostingRegressor
        return HistGradientBoostingRegressor(loss="absolute_error", max_iter=150, learning_rate=0.05,
                                             max_leaf_nodes=7, min_samples_leaf=60,
                                             random_state=seed), "HistGradientBoosting"


WEATHER_FEATURES = ["air_minus_water", "pressure_d3", "pressure_d6", "humidity"]  # 比較過全套 6 項，這組最穩


def features(f: pd.DataFrame, weather: bool | list[str] = True) -> pd.DataFrame:
    do = f["DO"]
    x = pd.DataFrame(index=f.index)
    for lag in [0, 1, 2, 3, 6, 12, 23, 24]:
        x[f"do_lag{lag}"] = do.shift(lag)
    x["do_d1"] = do.diff(1)
    x["do_d3"] = do.diff(3)
    x["do_m6"] = do.rolling(6, min_periods=3).mean()
    x["do_m24"] = do.rolling(24, min_periods=12).mean()
    x["do_s6"] = do.rolling(6, min_periods=3).std()
    for q in ["temp", "pH", "ORP", "SC"]:
        x[q] = f[q]
    x["temp_d3"] = f["temp"].diff(3)
    x["orp_d3"] = f["ORP"].diff(3)
    on = f["aerator_on"].astype(float)
    x["aerator_on"] = on
    x["aerator_6h"] = on.rolling(6, min_periods=1).sum()
    x["power"] = f["power"]
    h = f.index.hour
    x["hour_sin"] = np.sin(2 * np.pi * h / 24)
    x["hour_cos"] = np.cos(2 * np.pi * h / 24)
    if weather and "air_temp" in f:
        # 環境：氣溫、氣溫與水溫差、濕度、氣壓與其 3／6 小時變化（悶熱、低壓常伴隨低溶氧）
        cols = WEATHER_FEATURES if weather is True else weather
        w = {"air_temp": f["air_temp"], "air_minus_water": f["air_temp"] - f["temp"],
             "humidity": f["humidity"], "pressure": f["pressure"],
             "pressure_d3": f["pressure"].diff(3), "pressure_d6": f["pressure"].diff(6)}
        for c in cols:
            x[c] = w[c]
    return x


class DOForecaster:
    def __init__(self, seed: int = 0, weather: bool | list[str] = True):
        self.seed = seed
        self.weather = weather
        self.models: dict[int, object] = {}
        self.resid: dict[int, np.ndarray] = {}
        self.resid_sorted: dict[int, np.ndarray] = {}
        self.engine = ""

    def fit(self, f: pd.DataFrame, calib_frac: float = 0.2) -> "DOForecaster":
        x = features(f, self.weather)
        n_cal = int(len(f) * (1 - calib_frac))
        for h in HORIZONS:
            y = f["DO"].shift(-h) - f["DO"]
            ok = x["do_lag0"].notna() & y.notna()
            xi, yi = x[ok], y[ok]
            cut = xi.index[min(n_cal, len(xi) - 1)]
            # 先用前段擬合、後段算殘差（校正機率），再用全部訓練資料重擬合
            m, self.engine = _regressor(self.seed)
            m.fit(xi.loc[:cut], yi.loc[:cut])
            self.resid[h] = (yi.loc[cut:] - m.predict(xi.loc[cut:])).to_numpy()
            self.resid_sorted[h] = np.sort(self.resid[h])
            m, _ = _regressor(self.seed)
            self.models[h] = m.fit(xi, yi)
        return self

    def predict(self, f: pd.DataFrame, thr: float = C.DO_LOW) -> pd.DataFrame:
        x = features(f, self.weather)
        ok = x["do_lag0"].notna()
        out = pd.DataFrame(index=f.index)
        p_low = pd.Series(0.0, index=f.index)
        exp_low = pd.Series(0.0, index=f.index)
        exp_crit = pd.Series(0.0, index=f.index)
        for h in HORIZONS:
            yhat = pd.Series(np.nan, index=f.index)
            if ok.any():
                yhat[ok] = f["DO"][ok] + self.models[h].predict(x[ok])
            out[f"h{h}"] = yhat
            r = self.resid_sorted[h]
            ph = pd.Series(np.nan, index=f.index)
            ph[ok] = np.searchsorted(r, (thr - yhat[ok]).to_numpy()) / len(r)
            pc = pd.Series(np.nan, index=f.index)
            pc[ok] = np.searchsorted(r, (C.DO_CRIT - yhat[ok]).to_numpy()) / len(r)
            out[f"p{h}"] = ph
            p_low = np.fmax(p_low, ph)
            exp_low += ph.fillna(0)
            exp_crit += pc.fillna(0)
        out["p_low"] = p_low.where(ok)
        # 未來 6 小時的期望低溶氧／危急時數＝各小時機率加總（營運風險用，I4）
        out["exp_low_h"] = exp_low.where(ok)
        out["exp_crit_h"] = exp_crit.where(ok)
        below = pd.concat([out[f"h{h}"] < thr for h in HORIZONS], axis=1).to_numpy()
        first = np.where(below.any(axis=1), below.argmax(axis=1) + 1, np.nan)
        out["hours_to_threshold"] = np.where(f["DO"] < thr, 0, first)
        return out


FOLDS = [("2026-07-15", "2026-07-31"), ("2026-08-01", "2026-08-15"),
         ("2026-08-16", "2026-08-31"), ("2026-09-01", "2026-09-28 23:00")]


def walk_forward(f: pd.DataFrame, folds=FOLDS, seed: int = 0,
                 weather: bool | list[str] = True) -> tuple[pd.DataFrame, list[DOForecaster]]:
    """依時間前進的滾動驗證：每段測試期只用它之前的資料訓練。

    回傳 (拼接後的樣本外預測, 每段的模型)。預測多一欄 fold＝用第幾個模型。"""
    parts, models = [], []
    for i, (a, b) in enumerate(folds):
        train = f.loc[:pd.Timestamp(a) - pd.Timedelta(hours=1)]
        m = DOForecaster(seed, weather).fit(train)
        models.append(m)
        ctx = f.loc[pd.Timestamp(a) - pd.Timedelta(hours=48):b]
        parts.append(m.predict(ctx).loc[a:b].assign(fold=i))
    return pd.concat(parts), models


def p_low_shifted(pred_row: pd.Series, model: DOForecaster, shift: float, decay: float,
                  thr: float = C.DO_LOW) -> float:
    """閉環模擬用：DO 被策略改變 shift 後（隨時間以 decay 衰減），重新估計 6 小時內低溶氧機率。"""
    p = 0.0
    for h in HORIZONS:
        y = pred_row[f"h{h}"] + shift * decay ** h
        r = model.resid_sorted[h]
        p = max(p, np.searchsorted(r, thr - y) / len(r))
    return p


def baselines(f: pd.DataFrame) -> dict[str, pd.DataFrame]:
    do = f["DO"]
    return {"持續法": pd.DataFrame({f"h{h}": do for h in HORIZONS}),
            "24 小時季節": pd.DataFrame({f"h{h}": do.shift(24 - h) for h in HORIZONS})}


def evaluate(f: pd.DataFrame, preds: dict[str, pd.DataFrame], start) -> pd.DataFrame:
    rows = []
    for name, p in preds.items():
        for h in HORIZONS:
            y = f["DO"].shift(-h)
            m = pd.concat([y, p[f"h{h}"]], axis=1).loc[start:].dropna()
            e = m.iloc[:, 1] - m.iloc[:, 0]
            rows.append({"模型": name, "預測時距": f"{h} h", "MAE": e.abs().mean(),
                         "RMSE": np.sqrt((e ** 2).mean()), "n": len(e)})
    return pd.DataFrame(rows)


def warning_eval(f: pd.DataFrame, pred: pd.DataFrame, start, alpha: float = C.RISK_ALPHA) -> dict:
    """低溶氧事件（DO 由 ≥ 門檻跌破門檻）的提前預警：事件前 6 小時內 p_low > α 即算有預警。"""
    do = f["DO"].loc[start:]
    onset = do.index[(do < C.DO_LOW) & (do.shift(1) >= C.DO_LOW)]
    leads, hit = [], 0
    for t in onset:
        win = pred["p_low"].loc[t - pd.Timedelta(hours=6):t - pd.Timedelta(hours=1)]
        warned = win[win > alpha]
        if len(warned):
            hit += 1
            leads.append((t - warned.index[0]).total_seconds() / 3600)
    alarms = (pred["p_low"].loc[start:] > alpha)
    alarm_on = alarms & ~alarms.shift(1, fill_value=False)
    false = 0
    for t in alarm_on[alarm_on].index:
        if not (do.loc[t:t + pd.Timedelta(hours=6)] < C.DO_LOW).any():
            false += 1
    weeks = (do.index[-1] - do.index[0]).days / 7
    return {"低溶氧事件數": len(onset), "提前預警數": hit, "預警率": hit / max(len(onset), 1),
            "平均提前小時": float(np.mean(leads)) if leads else 0.0,
            "誤報（每週）": false / weeks, "α": alpha}


def probe_rul(frame: pd.DataFrame, checks: dict, window: int = 72) -> dict:
    """探頭剩餘可用時間：偏離量線性趨勢外推到容許差。回傳 {col: {rul_h, slope, fail_prob}}。"""
    out = {}
    for q, cols in C.PROBES.items():
        tol = C.PEER_TOL[q]
        for c in cols:
            dev = checks[c]["dev"].iloc[-window:].dropna()
            if len(dev) < window // 2:
                continue
            t = (dev.index - dev.index[-1]).total_seconds().to_numpy() / 3600
            slope, icpt = np.polyfit(t, dev.to_numpy(), 1)
            now = icpt
            if abs(now) >= tol:
                rul = 0.0
            elif abs(slope) < 1e-6 or np.sign(slope) != np.sign(now or slope):
                rul = np.inf
            else:
                rul = (np.sign(slope) * tol - now) / slope
            p = float(1 / (1 + np.exp(np.clip((rul - 48) / 12, -50, 50))))
            out[c] = {"rul_h": None if np.isinf(rul) else round(float(rul), 1),
                      "slope_per_day": round(float(slope * 24), 3), "fail_prob": round(p, 2)}
    return out


def aerator_health(f: pd.DataFrame, window: int = 24, baseline_h: int = 168) -> dict:
    """增氧機（設備）故障機率（I3）：運轉時功率的 24 小時趨勢外推到低負載門檻（650 W）。

    24 小時比 36／48／72 小時提早 5–15 小時預警，真實資料上誤報仍為 0（backtest/equipment.py）。

    資料期間增氧機沒有真的故障過（運轉功率 714–796 W），所以用合成的功率衰退驗證（backtest/report.md）。
    回傳 rul_h（預計幾小時後低於門檻）、fail_prob（48 小時內）、與前 7 天基準相比的功率變化。"""
    on = f["power"].where(f["aerator_on"] == True).iloc[-window:].dropna()  # noqa: E712
    base = f["power"].where(f["aerator_on"] == True).iloc[-(window + baseline_h):-window].median()  # noqa: E712
    if len(on) < window // 4:
        return {"rul_h": None, "fail_prob": None, "slope_w_per_day": None, "now_w": None,
                "baseline_w": None, "evidence": "運轉資料不足，無法估計"}
    t = (on.index - on.index[-1]).total_seconds().to_numpy() / 3600
    slope, now = np.polyfit(t, on.to_numpy(), 1)
    lim = C.AERATOR_LOW_LOAD_W
    if now <= lim:
        rul = 0.0
    elif slope < -1e-3:
        rul = (now - lim) / -slope
    else:
        rul = np.inf
    p = float(1 / (1 + np.exp(np.clip((rul - 48) / 12, -50, 50))))
    chg = "" if pd.isna(base) else f"，比前 7 天基準 {base:.0f} W {'低' if now < base else '高'} {abs(base - now):.0f} W"
    ev = (f"運轉功率約 {now:.0f} W，{window} 小時趨勢每天 {slope * 24:+.1f} W{chg}"
          + (f"，預計 {rul:.0f} 小時後低於 {lim:.0f} W" if np.isfinite(rul) and rul > 0 else ""))
    return {"rul_h": None if np.isinf(rul) else round(float(rul), 1), "fail_prob": round(p, 2),
            "slope_w_per_day": round(float(slope * 24), 1), "now_w": round(float(now), 0),
            "baseline_w": None if pd.isna(base) else round(float(base), 0), "evidence": ev}


def ops_risk(p_row: pd.Series, aerator_on: bool | None, aerator_fail_prob: float | None) -> dict:
    """營運風險（I4）：未來 6 小時的預期損失（元）＝低溶氧 × 單價 ＋ 危急 × 單價 ＋ 增氧電費 ＋ 設備故障風險。

    單價沿用回測的成本設定（common/config.py），都是估計值、待企業確認。"""
    lo, cr = p_row.get("exp_low_h"), p_row.get("exp_crit_h")
    if lo is None or pd.isna(lo) or cr is None or pd.isna(cr):
        # 無資料（斷線、DO 探頭全部不可信）：風險無法估計，本身就是高風險，由 Fallback 處理
        return {"expected_low_h": None, "expected_crit_h": None, "expected_loss": None, "level": "高",
                "breakdown": {}, "note": "無水質資料，風險無法估計，依 Fallback 規則處理"}
    lo, cr = float(lo), float(cr)
    water = lo * C.LOSS_PER_LOW_HOUR + cr * C.LOSS_PER_CRIT_HOUR
    power = (6 * C.AERATOR_RATED_KW * C.ELECTRICITY_PRICE) if aerator_on else 0.0
    equip = (aerator_fail_prob or 0.0) * C.AERATOR_FAILURE_COST
    total = water + power + equip
    level = "高" if total >= C.OPS_RISK_HIGH else "中" if total >= C.OPS_RISK_MID else "低"
    return {"expected_low_h": round(lo, 1), "expected_crit_h": round(cr, 1),
            "expected_loss": round(total), "level": level,
            "breakdown": {"水質損失": round(water), "增氧電費": round(power), "設備故障風險": round(equip)}}


def forecast(df: pd.DataFrame, site: str, model: DOForecaster, frame: pd.DataFrame | None = None,
             pred: pd.DataFrame | None = None) -> dict:
    """介面（architecture.md 第 4 節）。"""
    from state.pond import assess, sensor_checks
    f = assess(df) if frame is None else frame.loc[:df.index[-1]]
    p = model.predict(f.iloc[-48:]) if pred is None else pred.loc[:df.index[-1]]
    r = p.iloc[-1]
    rul = probe_rul(f, sensor_checks(df.iloc[-96:]))
    aer = aerator_health(f)
    worst = min(rul.items(), key=lambda kv: kv[1]["rul_h"] if kv[1]["rul_h"] is not None else 1e9, default=None)
    v = lambda k: None if pd.isna(r[k]) else round(float(r[k]), 2)
    return {"ts": f.index[-1].isoformat(), "site": site, "target": "DO",
            "now": None if pd.isna(f["DO"].iloc[-1]) else round(float(f["DO"].iloc[-1]), 2),
            "h1": v("h1"), "h3": v("h3"), "h6": v("h6"), "path": [v(f"h{h}") for h in HORIZONS],
            "hours_to_threshold": None if pd.isna(r["hours_to_threshold"]) else int(r["hours_to_threshold"]),
            "p_low": v("p_low"), "threshold": C.DO_LOW,
            "fail_prob": worst[1]["fail_prob"] if worst else None,
            "fail_target": worst[0] if worst else None,
            "probe_rul": rul, "engine": model.engine,
            "aerator": aer, "aerator_fail_prob": aer["fail_prob"],
            "ops_risk": ops_risk(r, None if pd.isna(f["aerator_on"].iloc[-1]) else bool(f["aerator_on"].iloc[-1]),
                                 aer["fail_prob"])}
