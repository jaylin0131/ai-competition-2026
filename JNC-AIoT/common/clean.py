"""02 大數據：清洗。套用 notes/eda/README.md 的跨場域共通規則。

- 補齊每小時時間軸（缺漏的小時＝斷線，填 NaN）
- 全部欄位都是 0 的列＝斷線，改成 NaN
- 刪除無資訊的欄位
- 回傳 `offline` 欄（True＝這一小時沒有資料）
"""

from __future__ import annotations

import pandas as pd

from common import config
from common.load_jnc import hourly, load


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = hourly(df).drop(columns=[c for c in config.DROP_COLS if c in df.columns])
    all_zero = (df.fillna(0) == 0).all(axis=1)
    df.loc[all_zero] = float("nan")
    df["offline"] = df.drop(columns="offline", errors="ignore").isna().all(axis=1)
    return df


def load_clean(site: str = "pond") -> pd.DataFrame:
    return clean(load(site))
