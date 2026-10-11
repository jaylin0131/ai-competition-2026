"""依 CSV 規格產生七類假資料，讓 B 組不必等 A 組（任務 B1）。

假資料只用來把流程寫通，數值分布不代表真實情況，不可拿來報告成果。
用法：python -m ml.fake_data --n-per-class 500 --out data/processed/fake.csv
"""

from __future__ import annotations

import argparse

from common.schema import ALL_COLUMNS


def make_fake(n_per_class: int, seed: int = 0):
    """回傳 pandas DataFrame，欄位 = ALL_COLUMNS。"""
    raise NotImplementedError("B1：假資料產生器")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-class", type=int, default=500)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    make_fake(args.n_per_class).to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
