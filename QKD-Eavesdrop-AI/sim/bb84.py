"""BB84 協定核心（A 組，任務 A1）。

一個回合的流程：Alice 產生隨機位元與基底 → 經過通道（channel.py）與可能的 Eve（eve.py）
→ Bob 用隨機基底量測 → 基底比對（sifting）→ 抽樣估算 QBER。

階段一（A1，10/18）：單光子理想光源，一回合一列輸出。
階段二（A3，11/4）：弱相干光源＋誘騙態，每個脈衝隨機選訊號 μ≈0.5／誘騙 ν≈0.1／真空 0，
光子數依卜瓦松分布抽樣；分別統計三種強度的偵測率與錯誤率（見 docs/csv-schema.md）。

約定：基底 0 = Z（直線）、1 = X（對角）。所有隨機性都來自傳入的 numpy Generator，確保可重現。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class BatchResult:
    """一個回合的原始結果，交給 generate_dataset.py 轉成 CSV 一列。"""

    n_sent: int
    detected: np.ndarray      # bool，Bob 是否偵測到光子
    alice_bits: np.ndarray
    alice_bases: np.ndarray
    bob_bits: np.ndarray
    bob_bases: np.ndarray
    intensity: np.ndarray | None = None  # 階段二：每個脈衝的強度類別 0=訊號、1=誘騙、2=真空


INTENSITIES = {"signal": 0.5, "decoy": 0.1, "vacuum": 0.0}


def alice_prepare(n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """回傳 (bits, bases)，各為長度 n 的 0/1 陣列。"""
    raise NotImplementedError("A1：BB84 基本流程")


def bob_measure(photon_bits: np.ndarray, photon_bases: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Bob 以隨機基底量測。基底相同 → 得到原位元；基底不同 → 隨機 0/1。"""
    raise NotImplementedError("A1：BB84 基本流程")


def sift(result: BatchResult) -> np.ndarray:
    """回傳「有偵測到且基底相同」的索引。"""
    raise NotImplementedError("A1：BB84 基本流程")


def estimate_qber(result: BatchResult, sample_ratio: float, rng: np.random.Generator) -> dict[str, float]:
    """從 sifted 位元抽樣比對，回傳 {'qber', 'qber_z', 'qber_x'}。"""
    raise NotImplementedError("A1：BB84 基本流程")
