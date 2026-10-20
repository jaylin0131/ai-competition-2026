"""01 IoT 感測：資料回放器＋合成故障注入。

本作品不自建硬體（HANDOFF 決定 1），以回放銘祥 CSV 模擬即時感測：
    for ts, window in Replayer(df, start="2026-09-01").stream():
        ...   # window 只含 ts 以前的資料，模組看不到未來

企業沒有維修紀錄（Q1），評估異常偵測時用 inject_faults() 在乾淨區段注入已知故障，
回傳的 labels 就是正確答案。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
import pandas as pd

FAULT_TYPES = ["stuck", "drift", "spike", "dropout", "offline"]
# 注入的故障對應到 diagnose 的 type
FAULT_TO_DIAG = {"stuck": "sensor_fault", "spike": "sensor_fault", "dropout": "sensor_fault",
                 "drift": "sensor_drift", "offline": "offline"}


@dataclass
class Replayer:
    df: pd.DataFrame
    start: str | pd.Timestamp | None = None
    end: str | pd.Timestamp | None = None
    window_hours: int = 72

    def stream(self) -> Iterator[tuple[pd.Timestamp, pd.DataFrame]]:
        idx = self.df.loc[self.start:self.end].index
        for ts in idx:
            yield ts, self.df.loc[ts - pd.Timedelta(hours=self.window_hours - 1):ts]


def inject_faults(df: pd.DataFrame, cols: list[str], n: int = 12, seed: int = 0,
                  start=None, end=None, min_gap: int = 48) -> tuple[pd.DataFrame, pd.DataFrame]:
    """在 [start, end] 內隨機注入 n 個不重疊的故障。回傳 (注入後資料, labels)。

    labels 欄位：type、diag_type、col、start、end。offline 會讓整列變 NaN。
    """
    rng = np.random.default_rng(seed)
    out = df.copy()
    span = out.loc[start:end].index
    rows, used = [], np.zeros(len(span), bool)
    tries = 0
    while len(rows) < n and tries < 1000:
        tries += 1
        kind = FAULT_TYPES[len(rows) % len(FAULT_TYPES)]
        dur = {"stuck": rng.integers(8, 24), "drift": rng.integers(36, 96), "spike": 1,
               "dropout": rng.integers(6, 24), "offline": rng.integers(3, 12)}[kind]
        i0 = int(rng.integers(0, len(span) - dur))
        lo, hi = max(0, i0 - min_gap), min(len(span), i0 + dur + min_gap)
        if used[lo:hi].any():
            continue
        seg = span[i0:i0 + dur]
        col = cols[int(rng.integers(0, len(cols)))]
        if out.loc[seg, col].isna().any():
            continue
        used[i0:i0 + dur] = True
        x = out.loc[seg, col].to_numpy(float)
        scale = float(np.nanstd(out[col])) or 1.0
        if kind == "stuck":
            out.loc[seg, col] = x[0]
        elif kind == "drift":
            out.loc[seg, col] = x + np.linspace(0, -3 * scale, dur)
        elif kind == "spike":
            out.loc[seg, col] = x + 8 * scale * rng.choice([-1, 1])
        elif kind == "dropout":
            out.loc[seg, col] = 0.0
        elif kind == "offline":
            num = out.columns.drop("offline", errors="ignore")
            out.loc[seg, num] = np.nan
            if "offline" in out:
                out.loc[seg, "offline"] = True
            col = "ALL"
        rows.append({"type": kind, "diag_type": FAULT_TO_DIAG[kind], "col": col,
                     "start": seg[0], "end": seg[-1]})
    return out, pd.DataFrame(rows).sort_values("start").reset_index(drop=True)
