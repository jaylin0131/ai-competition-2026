"""模擬器正確性測試（A 組，任務 A1）。A1 完成後移除 skip。以文獻已知行為驗證物理模型。"""

import pytest

pytestmark = pytest.mark.skip(reason="A1 尚未完成")


def test_no_noise_no_eve_qber_near_zero():
    """無雜訊、無 Eve → QBER < 0.5%"""


def test_full_intercept_qber_near_25_percent():
    """完整攔截重送 → QBER 在 22%–28%"""


def test_sift_ratio_near_half():
    """基底相同比例約 0.5"""
