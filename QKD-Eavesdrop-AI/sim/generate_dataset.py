"""產生資料集 CSV，一回合一列（A 組，任務 A2、A5）。

用法：
    python -m sim.generate_dataset --stage 1 --n-per-class 3000 --seed 42 --out data/raw/dataset_v1.csv
    python -m sim.generate_dataset --stage 2 --n-per-class 3000 --seed 42 --out data/raw/dataset_v2.csv
    python -m sim.generate_dataset --stage 2 --n-per-class 1000 --seed 2026 --out data/raw/holdout_v2.csv

欄位必須完全符合 common/schema.py 的 ALL_COLUMNS。
"""

from __future__ import annotations

import argparse

from common.schema import ALL_COLUMNS, STAGE1_LABELS, STAGE2_LABELS


def simulate_one_round(label: str, round_id: int, seed: int, n_pulses: int, stage: int) -> dict:
    """跑一個回合（bb84 + channel + eve），回傳一列 dict，key 為 ALL_COLUMNS。

    label 決定主要狀態；另外隨機加入並存的良性故障（記在 faults）。階段一的誘騙態欄位填 NaN。
    """
    raise NotImplementedError("A2：回合產生器")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, choices=(1, 2), default=1)
    ap.add_argument("--n-per-class", type=int, default=3000)
    ap.add_argument("--n-pulses", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    labels = STAGE1_LABELS if args.stage == 1 else STAGE2_LABELS
    # TODO(A2)：對每個 label 跑 n_per_class 次 simulate_one_round，用 pandas 存成 CSV，欄位順序 = ALL_COLUMNS
    raise NotImplementedError(f"A2：產生 {labels} 共 {len(labels)} 類資料")


if __name__ == "__main__":
    main()
