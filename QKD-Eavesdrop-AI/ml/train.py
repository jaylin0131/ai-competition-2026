"""訓練決策樹與梯度提升並輸出 models/model.pkl（B 組，任務 B3、B5）。

用法：python -m ml.train --data data/raw/dataset_v1.csv --out models/model.pkl

要點：
- Pipeline 包含前處理，C 組直接 load 後呼叫 predict / predict_proba
- 七類多類別分類；class_weight 加重三種攻擊
- 主模型決策樹（可解釋），對照梯度提升（scikit-learn HistGradientBoosting）
- 5-fold 交叉驗證 + 網格搜尋 max_depth(3–12)、min_samples_leaf、ccp_alpha
- holdout 測試集只在最後由 evaluate.py 使用，這裡不碰
"""

from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="models/model.pkl")
    args = ap.parse_args()
    raise NotImplementedError("B2：訓練流程")


if __name__ == "__main__":
    main()
