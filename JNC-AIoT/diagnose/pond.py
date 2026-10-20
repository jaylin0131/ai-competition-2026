"""03 AI 分析：異常診斷（魚塭）。回答「是感測器壞了，還是水質真的出事？」

逐小時判斷，每筆診斷都附可能原因、判斷證據、診斷可信度：
- offline         主機斷線（整列無資料）
- sensor_fault    探頭失效：超出物理範圍／掉到 0、卡值、跳點；氣象站凍結
- sensor_drift    探頭漂移：與另外兩支探頭中位數持續偏離
- water_event     真實水質事件：多支可信探頭一致顯示低溶氧或 pH 異常
- equipment_fault 增氧機運轉中但功率明顯偏低
- multivariate    多變量異常（Isolation Forest，附貢獻最大的欄位）

    hourly = diagnose_frame(df)        # 逐小時長表（回測用）
    episodes = to_episodes(hourly)     # 連續小時合併成事件
    d = diagnose(window, "pond")       # 介面：最後一小時有效的診斷
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import config as C
from state.pond import assess, sensor_checks

CAUSE = {
    "offline": "感測主機斷線或通訊中斷",
    "sensor_fault": "探頭失效（離水、損壞、接線鬆脫或主機凍結）",
    "sensor_drift": "探頭漂移或結垢，需要清洗或校正",
    "water_event": "真實水質事件（多支探頭一致）",
    "equipment_fault": "增氧機負載異常（葉輪卡住、馬達缺相或部分停機）",
    "multivariate": "多個欄位同時偏離歷史同時段",
}
QUANTITY = {c: q for q, cols in C.PROBES.items() for c in cols}


def _rows(mask: pd.Series, typ: str, target: str, conf, evidence) -> list[dict]:
    idx = mask[mask.fillna(False).astype(bool)].index
    if len(idx) == 0:
        return []
    conf = conf if isinstance(conf, pd.Series) else pd.Series(conf, index=mask.index)
    ev = evidence if isinstance(evidence, pd.Series) else pd.Series(evidence, index=mask.index)
    return [{"ts": t, "type": typ, "target": target, "cause": CAUSE[typ],
             "evidence": ev[t], "confidence": round(float(conf[t]), 2)} for t in idx]


def diagnose_frame(df: pd.DataFrame, frame: pd.DataFrame | None = None, iforest=None) -> pd.DataFrame:
    f = assess(df) if frame is None else frame
    checks = sensor_checks(df)
    rows: list[dict] = []
    rows += _rows(f["offline"], "offline", "ALL", 0.95, "整列無資料（缺漏或全部為 0）")
    online = ~f["offline"].astype(bool)

    for c, ch in checks.items():
        if c in C.WEATHER:
            continue
        q = QUANTITY[c]
        tol = C.PEER_TOL[q]
        s = df[c]
        rows += _rows(ch["range"] & online, "sensor_fault", c, 0.9,
                      s.map(lambda v: f"{c} = {v:.2f}，超出物理範圍 {C.PHYS_RANGE[q]}"))
        rows += _rows(ch["stuck"] & ~ch["range"] & online, "sensor_fault", c, 0.8,
                      s.map(lambda v: f"{c} 連續 {C.STUCK_HOURS[q]} 小時以上固定為 {v:.2f}，其他探頭仍在變化"))
        prev = s.shift(1).rolling(12, min_periods=6).median()
        jump = (s - prev).abs()
        rows += _rows(ch["spike"] & ~ch["range"] & online, "sensor_fault", c,
                      (0.3 + 0.1 * jump / (2 * tol)).clip(0.3, 0.9),
                      pd.Series([f"{c} 單點跳變到 {v:.2f}（前 12 小時中位數 {m:.2f}）" for v, m in zip(s, prev)],
                                index=df.index))
        # 漂移：6 小時平均偏離 ≥ 容許差，且持續 ≥ 6 小時
        off = (ch["dev6"].abs() >= tol) & ~ch["range"] & ~ch["stuck"]
        persist = off.astype(int).groupby((~off).cumsum()).cumsum()
        drift = persist >= 6
        conf = (0.5 + 0.05 * persist.clip(upper=8) + 0.1 * (ch["dev6"].abs() / tol - 1).clip(0, 1)).clip(upper=0.95)
        ev = pd.Series([f"{c} 與其他探頭中位數相差 {d:+.2f}（容許 ±{tol}），已持續 {p} 小時"
                        for d, p in zip(ch["dev6"].fillna(0), persist)], index=df.index)
        rows += _rows(drift & online, "sensor_drift", c, conf, ev)

    ws = [c for c in C.WEATHER if c in checks]
    if ws:
        stuck_all = pd.concat([checks[c]["stuck"] for c in ws], axis=1).all(axis=1)
        rows += _rows(stuck_all & online, "sensor_fault", "OA4 氣象站", 0.85,
                      "氣象站溫度、濕度、氣壓、熱指數同時連續 12 小時以上不變（凍結）")

    n_do = f["DO_n"]
    low = (f["DO"] < C.DO_LOW) & (n_do >= 2)
    conf = (0.55 + 0.15 * (n_do - 1)).clip(upper=0.9)
    ev = pd.Series([f"{n} 支可信探頭一致，融合 DO = {v:.2f} mg/L（門檻 {C.DO_LOW}）" if pd.notna(v) else ""
                    for n, v in zip(n_do, f["DO"])], index=df.index)
    rows += _rows(low, "water_event", "DO", conf, ev)
    ph_bad = ((f["pH"] < 6.5) | (f["pH"] > 9.0)) & (f["pH_n"] >= 2)
    rows += _rows(ph_bad, "water_event", "pH", 0.7,
                  f["pH"].map(lambda v: f"融合 pH = {v:.2f}，超出 6.5–9.0" if pd.notna(v) else ""))

    p = df[C.POWER]
    weak = (p > C.AERATOR_ON_W) & (p < C.AERATOR_LOW_LOAD_W)
    rows += _rows(weak, "equipment_fault", "增氧機", 0.7,
                  p.map(lambda v: f"增氧機運轉中但功率只有 {v:.0f} W（正常約 760 W）"))

    if iforest is not None:
        score, contrib = iforest.score(f)
        mv = score > iforest.threshold
        ev = pd.Series([f"異常分數 {s:.2f}（門檻 {iforest.threshold:.2f}），偏離最大：{c}"
                        for s, c in zip(score, contrib)], index=f.index)
        conf = (0.5 + (score - iforest.threshold) * 2).clip(0.5, 0.85)
        rows += _rows(mv & online, "multivariate", "多變量", conf, ev)

    out = pd.DataFrame(rows, columns=["ts", "type", "target", "cause", "evidence", "confidence"])
    return out.sort_values(["ts", "type"]).reset_index(drop=True)


def to_episodes(hourly: pd.DataFrame, max_gap: int = 2) -> pd.DataFrame:
    """同一 (type, target) 連續（間隔 ≤ max_gap 小時）的診斷合併成一個事件。"""
    eps = []
    for (typ, tgt), g in hourly.groupby(["type", "target"]):
        ts = g["ts"].sort_values()
        brk = ts.diff() > pd.Timedelta(hours=max_gap)
        for _, seg in g.loc[ts.index].groupby(brk.cumsum().to_numpy()):
            eps.append({"type": typ, "target": tgt, "start": seg["ts"].iloc[0], "end": seg["ts"].iloc[-1],
                        "hours": len(seg), "confidence": seg["confidence"].max(),
                        "evidence": seg["evidence"].iloc[-1], "cause": seg["cause"].iloc[0]})
    return pd.DataFrame(eps).sort_values("start").reset_index(drop=True) if eps else pd.DataFrame(
        columns=["type", "target", "start", "end", "hours", "confidence", "evidence", "cause"])


def diagnose(df: pd.DataFrame, site: str = "pond", hourly: pd.DataFrame | None = None) -> list[dict]:
    """介面（architecture.md 第 4 節）：最後一小時有效的診斷清單。"""
    ts = df.index[-1]
    h = diagnose_frame(df) if hourly is None else hourly
    now = h[h["ts"] == ts]
    out = []
    for r in now.itertuples():
        # 已持續幾小時
        same = h[(h["type"] == r.type) & (h["target"] == r.target) & (h["ts"] <= ts)]["ts"]
        run = 1
        for a, b in zip(same.iloc[::-1].iloc[1:], same.iloc[::-1]):
            if b - a > pd.Timedelta(hours=1):
                break
            run += 1
        out.append({"ts": ts.isoformat(), "type": r.type, "target": r.target, "cause": r.cause,
                    "evidence": [r.evidence], "confidence": r.confidence, "duration_h": run})
    return out


class IForest:
    """多變量異常：Isolation Forest，特徵為融合值與「偏離歷史同時段」的 robust z。只用訓練期擬合。"""

    FEATURES = ["DO", "pH", "ORP", "SC", "temp", "power"]

    def __init__(self, contamination: float = 0.01, seed: int = 0):
        self.contamination = contamination
        self.seed = seed

    def _x(self, f: pd.DataFrame) -> pd.DataFrame:
        from common.baseline import robust_z
        z = robust_z(f, self.base)
        return z[self.FEATURES].fillna(0).clip(-10, 10)

    def fit(self, f: pd.DataFrame) -> "IForest":
        from sklearn.ensemble import IsolationForest
        from common.baseline import build_baseline
        ok = f.dropna(subset=self.FEATURES)
        self.base = build_baseline(ok, self.FEATURES)
        x = self._x(ok)
        self.model = IsolationForest(n_estimators=200, contamination=self.contamination,
                                     random_state=self.seed).fit(x)
        s = -self.model.score_samples(x)
        self.threshold = float(np.quantile(s, 1 - self.contamination))
        return self

    def score(self, f: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        x = self._x(f)
        s = pd.Series(-self.model.score_samples(x), index=f.index)
        top = x.abs().apply(lambda r: "、".join(f"{k}({x.loc[r.name, k]:+.1f}σ)"
                                                for k in r.nlargest(2).index), axis=1)
        return s.where(f[self.FEATURES].notna().all(axis=1), 0), top
