"""通道劣化模型（A 組，任務 A2、A4）。

三種良性故障（參數範圍請在說明書註明文獻）：
- fiber_aging 光纖老化：損耗隨 timestamp 緩慢上升，所有強度的偵測率一起下降，誘騙比不變
- pol_drift 偏振對準漂移：只有單一基底（例如 X）的錯誤率升高
- stray_light 雜散光（階段二）：真空態計數暴增，QBER 微升

共同參數：光纖損耗約 0.2 dB/km（距離 5–80 km）、偵測效率、暗計數。
真實化要求：故障可以同時存在、強度隨機，並記錄在 faults／fault_severity（禁止當特徵）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class ChannelParams:
    distance_km: float
    detector_eff: float
    dark_count_prob: float
    base_flip_prob: float = 0.01            # 正常營運的背景錯誤率
    aging_loss_db: float = 0.0              # fiber_aging：額外損耗
    drift_flip_prob: dict[int, float] = field(default_factory=dict)  # pol_drift：{基底: 額外翻轉機率}
    stray_light_prob: float = 0.0           # stray_light：每脈衝額外誤觸發機率（階段二）


def sample_params(rng: np.random.Generator, timestamp: float, faults: list[str]) -> ChannelParams:
    """依同時存在的良性故障清單抽一組通道參數。"""
    raise NotImplementedError("A2：通道劣化模型（老化、對準漂移）；A4：雜散光")


def transmit(bits: np.ndarray, bases: np.ndarray, params: ChannelParams, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """套用損耗、翻轉、暗計數、雜散光。回傳 (bits, bases, detected)。"""
    raise NotImplementedError("A2：通道劣化模型")
