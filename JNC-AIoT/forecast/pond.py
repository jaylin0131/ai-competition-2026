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


def features(f: pd.DataFrame) -> pd.DataFrame:
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
    return x


class DOForecaster:
    def __init__(self, seed: int = 0):
        self.seed = seed
        self.models: dict[int, object] = {}
        self.resid: dict[int, np.ndarray] = {}
        self.resid_sorted: dict[int, np.ndarray] = {}
        self.engine = ""

    def fit(self, f: pd.DataFrame, calib_frac: float = 0.2) -> "DOForecaster":
        x = features(f)
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
        x = features(f)
        ok = x["do_lag0"].notna()
        out = pd.DataFrame(index=f.index)
        p_low = pd.Series(0.0, index=f.index)
        for h in HORIZONS:
            yhat = pd.Series(np.nan, index=f.index)
            if ok.any():
                yhat[ok] = f["DO"][ok] + self.models[h].predict(x[ok])
            out[f"h{h}"] = yhat
            r = self.resid_sorted[h]
            p = np.searchsorted(r, (thr - yhat[ok]).to_numpy()) / len(r)
            ph = pd.Series(np.nan, index=f.index)
            ph[ok] = p
            out[f"p{h}"] = ph
            p_low = np.fmax(p_low, ph)
        out["p_low"] = p_low.where(ok)
        below = pd.concat([out[f"h{h}"] < thr for h in HORIZONS], axis=1).to_numpy()
        first = np.where(below.any(axis=1), below.argmax(axis=1) + 1, np.nan)
        out["hours_to_threshold"] = np.where(f["DO"] < thr, 0, first)
        return out


FOLDS = [("2026-07-15", "2026-07-31"), ("2026-08-01", "2026-08-15"),
         ("2026-08-16", "2026-08-31"), ("2026-09-01", "2026-09-28 23:00")]


def walk_forward(f: pd.DataFrame, folds=FOLDS, seed: int = 0) -> tuple[pd.DataFrame, list[DOForecaster]]:
    """依時間前進的滾動驗證：每段測試期只用它之前的資料訓練。

    回傳 (拼接後的樣本外預測, 每段的模型)。預測多一欄 fold＝用第幾個模型。"""
    parts, models = [], []
    for i, (a, b) in enumerate(folds):
        train = f.loc[:pd.Timestamp(a) - pd.Timedelta(hours=1)]
        m = DOForecaster(seed).fit(train)
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


def forecast(df: pd.DataFrame, site: str, model: DOForecaster, frame: pd.DataFrame | None = None,
             pred: pd.DataFrame | None = None) -> dict:
    """介面（architecture.md 第 4 節）。"""
    from state.pond import assess, sensor_checks
    f = assess(df) if frame is None else frame.loc[:df.index[-1]]
    p = model.predict(f.iloc[-48:]) if pred is None else pred.loc[:df.index[-1]]
    r = p.iloc[-1]
    rul = probe_rul(f, sensor_checks(df.iloc[-96:]))
    worst = min(rul.items(), key=lambda kv: kv[1]["rul_h"] if kv[1]["rul_h"] is not None else 1e9, default=None)
    v = lambda k: None if pd.isna(r[k]) else round(float(r[k]), 2)
    return {"ts": f.index[-1].isoformat(), "site": site, "target": "DO",
            "now": None if pd.isna(f["DO"].iloc[-1]) else round(float(f["DO"].iloc[-1]), 2),
            "h1": v("h1"), "h3": v("h3"), "h6": v("h6"), "path": [v(f"h{h}") for h in HORIZONS],
            "hours_to_threshold": None if pd.isna(r["hours_to_threshold"]) else int(r["hours_to_threshold"]),
            "p_low": v("p_low"), "threshold": C.DO_LOW,
            "fail_prob": worst[1]["fail_prob"] if worst else None,
            "fail_target": worst[0] if worst else None,
            "probe_rul": rul, "engine": model.engine}
