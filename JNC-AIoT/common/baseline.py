"""02 大數據：歷史基準。每個欄位、每個小時（0–23）的中位數與 MAD，只用訓練期資料計算。

用法：
    base = build_baseline(train_df, cols)
    z = robust_z(df, base)   # 偏離歷史同時段的程度
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_baseline(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """回傳 MultiIndex 欄 (col, median|mad)、index 為 hour 的表。"""
    g = df[cols].groupby(df.index.hour)
    med = g.median()
    mad = g.agg(lambda s: (s - s.median()).abs().median())
    mad = mad.where(mad > 0, df[cols].std() * 0.1 + 1e-6, axis=1)
    return pd.concat({"median": med, "mad": mad}, axis=1).swaplevel(axis=1).sort_index(axis=1)


def robust_z(df: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    cols = sorted({c for c, _ in base.columns})
    hours = df.index.hour
    out = {}
    for c in cols:
        med = base[(c, "median")].reindex(hours).to_numpy()
        mad = base[(c, "mad")].reindex(hours).to_numpy()
        out[c] = (df[c].to_numpy() - med) / (1.4826 * mad)
    return pd.DataFrame(out, index=df.index).replace([np.inf, -np.inf], np.nan)
