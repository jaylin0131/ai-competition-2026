"""非 AI 的基準方法（B 組，任務 B2、B4）。所有 AI 成果都要和它們在「相同誤報率」下比較，見 ADR-0002。

1. 協定門檻：QBER > 11% 就中止（PNS、致盲完全看不到）
2. 基準線追蹤：指數平滑追蹤 QBER 的正常水準，偏離太多才告警（E3 的主要進步來源）
3. 物理規則表：每種狀態一條人工規則（例如誘騙比下降 → PNS），單一特徵的攻擊很強
"""

from __future__ import annotations

import pandas as pd

FIXED_THRESHOLD = 0.11  # BB84 常見的中止門檻


def predict_threshold(df: pd.DataFrame, threshold: float = FIXED_THRESHOLD) -> pd.Series:
    """QBER > 門檻 → True（判為攻擊）。門檻法本身無法區分原因。"""
    return df["qber"] > threshold


def ewma_baseline(qber: pd.Series, alpha: float = 0.05, k: float = 3.0) -> pd.Series:
    """指數平滑基準線：偏離基準超過 k 個標準差 → True。"""
    raise NotImplementedError("B2：基準線追蹤")


def predict_rules(df: pd.DataFrame) -> pd.Series:
    """物理規則表 → 七類標籤。規則與門檻寫在說明書裡，讓評審看得懂。"""
    raise NotImplementedError("B4：物理規則表")


def threshold_at_fpr(scores: pd.Series, is_benign: pd.Series, fpr: float) -> float:
    """在良性資料上找讓誤報率 = fpr 的門檻，用於同誤報率比較（10%、5%、2%）。"""
    raise NotImplementedError("B4：同誤報率比較")
