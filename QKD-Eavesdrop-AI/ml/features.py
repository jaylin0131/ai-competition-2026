"""從 CSV 取出特徵 X 與標籤 y（B 組，任務 B2）。"""

from __future__ import annotations

import pandas as pd

from common.schema import FEATURE_COLUMNS, LABEL_COLUMN, STAGE1_FEATURES, check_no_leakage


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """衍生特徵：兩基底錯誤率差（E4：分辨偏振漂移與截取重送的關鍵）。"""
    df = df.copy()
    df["qber_basis_gap"] = (df["qber_z"] - df["qber_x"]).abs()
    return df


def to_xy(df: pd.DataFrame, stage: int = 2) -> tuple[pd.DataFrame, pd.Series]:
    """stage=1 只用基本 BB84 的特徵；stage=2 加上誘騙態特徵。"""
    df = add_derived(df)
    cols = (STAGE1_FEATURES if stage == 1 else FEATURE_COLUMNS) + ["qber_basis_gap"]
    check_no_leakage(cols)
    return df[cols], df[LABEL_COLUMN]
