"""竊聽者 Eve 的攻擊模型（A 組，任務 A2、A4）。

真實化要求：攻擊只作用於部分時間或部分光子，比例寫在 attack_ratio（禁止當特徵）。
單元測試以文獻已知行為驗證，例如完整截取重送 → QBER 約 25%。
"""

from __future__ import annotations

import numpy as np


def intercept_resend(bits: np.ndarray, bases: np.ndarray, ratio: float, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """截取重送（階段一，A2）。ratio=1 為完整攔截（QBER≈25%）；弱攻擊只攔截部分光子。

    被攔截的光子：Eve 用隨機基底量測，再以她的基底與結果重送給 Bob。兩基底錯誤率同步升高。
    """
    raise NotImplementedError("A2：截取重送")


def photon_number_splitting(*args, **kwargs):
    """PNS 光子數分離（階段二，A4）：從多光子脈衝分走光子、阻擋單光子脈衝。

    QBER 完全不變，但誘騙／訊號計數比由約 0.20 掉到約 0.13。
    """
    raise NotImplementedError("A4：PNS")


def detector_blinding(*args, **kwargs):
    """偵測器致盲（階段二，A4）：強光讓偵測器變成古典模式，Eve 控制 Bob 的結果。

    暗計數歸零、QBER 低於物理下限（反而降低）。
    """
    raise NotImplementedError("A4：偵測器致盲")
