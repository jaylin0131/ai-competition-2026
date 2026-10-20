"""增氧機對溶氧的影響（閉環模擬用）。

DO 每小時變化 = 各小時的日夜項 + effect × 增氧機台數 − (1 − decay) × (DO − 72 小時平均)
用最小平方法估計。注意：現場通常在 DO 已經下降時才開機，effect 會被低估（操作時機混淆），
所以回測同時報「資料估計值」與「工程估計值」兩組結果。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# 工程估計：0.76 kW 葉輪式增氧機標準充氧效率約 1.3 kg O2/kWh → 約 1 kg O2/h；
# 假設池面 0.5 公頃、水深 1.5 m（7,500 m³）→ 約 +0.13 mg/L/h。池子大小待企業確認（Q5）。
ENGINEERING = {"aerator_effect": 0.13, "effect_decay": 0.73, "source": "工程估計（假設 0.5 公頃、水深 1.5 m）"}


def estimate(f: pd.DataFrame, end=None) -> dict:
    f = f.loc[:end]
    do = f["DO"]
    u = f["aerator_on"].astype(float)
    d = do.shift(-1) - do
    x = pd.DataFrame({"u": u, "lvl": do - do.rolling(72, min_periods=24).mean()}, index=f.index)
    hours = pd.get_dummies(f.index.hour, prefix="h").astype(float)
    hours.index = f.index
    x = pd.concat([x, hours], axis=1)
    ok = x.notna().all(axis=1) & d.notna()
    b, *_ = np.linalg.lstsq(x[ok].to_numpy(), d[ok].to_numpy(), rcond=None)
    return {"aerator_effect": round(float(max(b[0], 0.0)), 4), "effect_decay": round(float(1 + b[1]), 3),
            "source": f"資料估計（{ok.sum()} 小時，受操作時機混淆，偏低）"}
