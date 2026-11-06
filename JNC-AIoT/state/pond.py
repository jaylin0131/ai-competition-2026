"""03 AI 分析：狀態辨識（魚塭）。回答「現在發生什麼事？」

輸出：WQI、燈號、感測器可信度（0–100）、融合後水質值、增氧機狀態、設備健康度。
所有計算都只用當下與過去的資料（回放時不會偷看未來）。

    frame = assess(df)          # 全期間逐小時（回測、畫圖用）
    s = state(window, "pond")   # 介面：最後一小時的狀態 dict
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import config as C

# WQI 子指標：(數值點, 分數點)，np.interp 線性內插
SUB_INDEX = {
    "DO": ([2.0, 2.5, 3.0, 3.5, 4.0, 5.0], [0, 30, 50, 70, 85, 100]),
    "pH": ([5.5, 6.0, 6.5, 7.0, 8.5, 9.0, 9.5, 10.0], [0, 20, 60, 100, 100, 60, 20, 0]),
    "temp": ([18, 22, 25, 32, 33, 35], [30, 70, 100, 100, 70, 30]),
    "ORP": ([0, 100, 200, 300], [0, 20, 60, 100]),
}
WQI_WEIGHT = {"DO": 0.5, "pH": 0.2, "temp": 0.15, "ORP": 0.15}
LIGHTS = {"green": "綠燈・正常", "yellow": "黃燈・注意", "red": "紅燈・警戒", "gray": "灰燈・無資料"}


def run_length(x: pd.Series) -> pd.Series:
    """目前這個值已連續出現幾小時（NaN 算 0）。"""
    grp = (x != x.shift()).cumsum()
    rl = x.groupby(grp).cumcount() + 1
    return rl.where(x.notna(), 0)


def sensor_checks(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """每支探頭逐小時的檢查結果。回傳 {col: DataFrame[range, stuck, spike, dev, dev6, trust]}。"""
    out = {}
    for q, cols in C.PROBES.items():
        lo, hi = C.PHYS_RANGE[q]
        tol = C.PEER_TOL[q]
        x = df[cols]
        bad_range = x.notna() & ((x < lo) | (x > hi))
        valid = x.where(~bad_range)
        peer = valid.median(axis=1)
        for c in cols:
            s = df[c]
            n = C.STUCK_HOURS[q]
            rl = run_length(s)
            peer_moves = (peer.rolling(n).max() - peer.rolling(n).min()) > 3 * C.RESOLUTION[q]
            stuck = (rl >= n) & peer_moves.where(rl < 2 * n, True)
            prev = s.shift(1)
            med = prev.rolling(12, min_periods=6).median()
            mad = (prev - med).abs().rolling(12, min_periods=6).median()
            spike = (s - med).abs() > np.maximum(C.SPIKE_K * 1.4826 * mad, 2 * tol)
            dev = valid[c] - peer
            dev6 = dev.rolling(6, min_periods=3).mean()
            ratio = (dev6.abs() / tol).fillna(0)
            trust = (100
                     - 100 * bad_range[c]
                     - 60 * stuck
                     - 40 * (spike & ~bad_range[c])
                     - np.clip((ratio - 0.5) * 80, 0, 70))
            trust = trust.clip(0, 100).where(s.notna())
            out[c] = pd.DataFrame({"range": bad_range[c], "stuck": stuck, "spike": spike,
                                   "dev": dev, "dev6": dev6, "trust": trust})
    for c in C.WEATHER:
        if c in df:
            stuck = run_length(df[c]) >= 12
            out[c] = pd.DataFrame({"range": False, "stuck": stuck, "spike": False, "dev": np.nan,
                                   "dev6": np.nan, "trust": (100 - 90 * stuck).where(df[c].notna())})
    return out


def fused(df: pd.DataFrame, checks: dict[str, pd.DataFrame], min_trust: float = 50) -> pd.DataFrame:
    """可信度 ≥ min_trust 的探頭取中位數，得到每個物理量的代表值。"""
    out = {}
    for q, cols in C.PROBES.items():
        ok = pd.concat({c: df[c].where(checks[c]["trust"] >= min_trust) for c in cols}, axis=1)
        out[q] = ok.median(axis=1)
        out[f"{q}_n"] = ok.notna().sum(axis=1)
    t = df[C.TEMP]
    out["temp"] = t.where(t.between(*C.PHYS_RANGE["temp"]))
    return pd.DataFrame(out, index=df.index)


def wqi(f: pd.DataFrame) -> pd.Series:
    num = pd.Series(0.0, index=f.index)
    den = pd.Series(0.0, index=f.index)
    for q, w in WQI_WEIGHT.items():
        xp, fp = SUB_INDEX[q]
        sub = pd.Series(np.interp(f[q], xp, fp), index=f.index).where(f[q].notna())
        num += (sub * w).fillna(0)
        den += w * sub.notna()
    return (num / den).where(den >= 0.5)


def light(do: pd.Series, w: pd.Series) -> pd.Series:
    lt = pd.Series("green", index=do.index)
    lt[(do < C.DO_GOOD) | (w < 70)] = "yellow"
    lt[(do < C.DO_LOW) | (w < 50)] = "red"
    lt[do.isna() | w.isna()] = "gray"
    return lt


def assess(df: pd.DataFrame) -> pd.DataFrame:
    checks = sensor_checks(df)
    f = fused(df, checks)
    f["DO_raw"] = df[C.PROBES["DO"]].mean(axis=1)   # 不檢查可信度的三探頭平均（一般 SCADA 的做法，當基準）
    f["wqi"] = wqi(f)
    f["light"] = light(f["DO"], f["wqi"])
    p = df[C.POWER]
    f["power"] = p
    f["aerator_on"] = (p > C.AERATOR_ON_W).where(p.notna())
    trust = pd.DataFrame({c: v["trust"] for c, v in checks.items()})
    for c in trust:
        f[f"trust:{c}"] = trust[c]
    probe_cols = [c for cols in C.PROBES.values() for c in cols]
    f["device_health"] = trust[probe_cols].mean(axis=1)
    f["offline"] = df["offline"] if "offline" in df else df.isna().all(axis=1)
    # 環境（OA4 氣象站）：氣象站凍結或讀到 0 時當缺值，不讓壞資料進入預測與決策（I6）
    ok_w = (trust[C.WEATHER].min(axis=1) >= 50) if set(C.WEATHER) <= set(trust) else False
    for col, name in [("OA4 溫度", "air_temp"), ("OA4 濕度", "humidity"), ("OA4 大氣壓力", "pressure"),
                      ("OA4 熱指數", "heat_index")]:
        v = df[col] if col in df else pd.Series(np.nan, index=df.index)
        f[name] = v.where(ok_w & (v > 0))
    return f


def state(df: pd.DataFrame, site: str = "pond", frame: pd.DataFrame | None = None) -> dict:
    """介面（architecture.md 第 4 節）：最後一小時的狀態。"""
    f = assess(df) if frame is None else frame.loc[:df.index[-1]]
    r = f.iloc[-1]
    trust = {k.split(":", 1)[1]: (None if pd.isna(v) else round(float(v)))
             for k, v in r.items() if str(k).startswith("trust:")}
    val = lambda k, d=2: None if pd.isna(r[k]) else round(float(r[k]), d)
    return {
        "ts": f.index[-1].isoformat(), "site": site,
        "wqi": val("wqi", 0), "light": r["light"], "light_text": LIGHTS[r["light"]],
        "values": {q: val(q) for q in ["DO", "pH", "ORP", "SC", "temp"]},
        "environment": {"氣溫": val("air_temp", 1), "濕度": val("humidity", 0), "氣壓": val("pressure", 1),
                        "熱指數": val("heat_index", 1)},
        "probes_used": {q: int(r[f"{q}_n"]) for q in C.PROBES},
        "aerator_on": None if pd.isna(r["aerator_on"]) else bool(r["aerator_on"]),
        "power_w": val("power", 0),
        "device_health": val("device_health", 0),
        "sensor_trust": trust,
        "offline": bool(r["offline"]),
    }
