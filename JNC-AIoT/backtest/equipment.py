"""增氧機（設備）故障機率的驗證（I3）。

資料期間增氧機沒有真的故障過（運轉功率 714–796 W），所以：
- 誤報：在真實資料上逐小時計算，48 小時內故障機率 ≥ 門檻的小時比例
- 提前量：注入合成的功率衰退（72 小時內線性降到 600 W），看機率在功率實際低於 650 W 前多久超過門檻
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import config as C
from forecast.pond import aerator_health


def _probs(f: pd.DataFrame, idx) -> pd.Series:
    return pd.Series([aerator_health(f.loc[:t])["fail_prob"] for t in idx], index=idx, dtype=float)


def false_alarm_rate(f: pd.DataFrame, start, end, step: int = 3) -> float:
    idx = f.loc[start:end].index[::step]
    return float((_probs(f, idx) >= C.AERATOR_FAIL_ALERT).mean())


def synthetic_lead(f: pd.DataFrame, starts, hours: int = 72, to_w: float = 600.0) -> pd.DataFrame:
    rows = []
    for s in starts:
        s = pd.Timestamp(s)
        g = f.copy()
        seg = g.loc[s:s + pd.Timedelta(hours=hours - 1)].index
        start_w = g["power"].where(g["aerator_on"] == True).loc[:s].dropna().iloc[-24:].median()  # noqa: E712
        noise = np.random.default_rng(0).normal(0, 5, len(seg))
        g.loc[seg, "power"] = np.linspace(start_w, to_w, len(seg)) + noise
        g.loc[seg, "aerator_on"] = True
        cross = g.loc[seg].index[(g.loc[seg, "power"] < C.AERATOR_LOW_LOAD_W).to_numpy()]
        cross = cross[0] if len(cross) else seg[-1]
        p = _probs(g, g.loc[s:cross].index)
        hit = p[p >= C.AERATOR_FAIL_ALERT]
        rows.append({"衰退開始": f"{s:%m/%d %H:%M}", "功率低於 650 W": f"{cross:%m/%d %H:%M}",
                     "首次預警": "" if hit.empty else f"{hit.index[0]:%m/%d %H:%M}",
                     "提前小時": 0.0 if hit.empty else (cross - hit.index[0]).total_seconds() / 3600})
    return pd.DataFrame(rows)
