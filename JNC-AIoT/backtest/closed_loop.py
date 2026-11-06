"""05 執行回饋：模擬 SCADA／PLC 執行＋結果回傳與成效驗證＋再學習。

在歷史資料上逐小時重播，比較三種策略的增氧機操作：
- 歷史實際：照現場當時的操作（不採取 AI 建議）
- 固定門檻（原始探頭）：一般 SCADA 做法，直接用三支 DO 探頭原始值平均判斷，不檢查探頭可信度
- 固定門檻：同上規則，但用 AI 狀態辨識排除故障探頭後的融合 DO
  規則：DO < 3.0 就開機（主機已開就再開備用機），DO ≥ 3.5 恢復現場排程
- AI 決策：6 小時內低溶氧機率 > α 就提前開機（主機已開則開備用機）；DO 充足、風險 < β 且尖峰時段建議停機節能

反事實 DO：DO_sim(t) = DO_obs(t) + Δ(t)，Δ(t) = decay·Δ(t−1) + effect·(u_策略 − u_歷史)(t−1)
其中 u 為運轉台數（0、1、2）。effect、decay 見 backtest/effect.py。
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import config as C
from common.load_jnc import ROOT
from forecast.pond import p_low_shifted

POLICIES = ["歷史實際", "固定門檻（原始探頭）", "固定門檻", "AI 決策"]


def simulate(f: pd.DataFrame, pred: pd.DataFrame, models: list, policy: str, effect: float, decay: float,
             alpha: float = C.RISK_ALPHA, beta: float = C.SAVE_BETA, start=None, end=None,
             energy_saving: bool = True, thr_on: float = C.DO_LOW) -> pd.DataFrame:
    idx = pred.loc[start:end].index
    do_obs = f["DO"].reindex(idx)
    do_raw = f["DO_raw"].reindex(idx)
    u_hist = f["aerator_on"].reindex(idx).astype(float).fillna(1.0)
    rows, delta, prev_gap, hold, saving, cool, latch = [], 0.0, 0.0, 0, 0, 0, False
    for t in idx:
        delta = decay * delta + effect * prev_gap
        obs = do_obs[t]
        sim = obs + delta if pd.notna(obs) else np.nan
        uh = u_hist[t]
        alarm, reason = False, ""
        if policy == "歷史實際":
            u = uh
        elif pd.isna(sim):
            u, reason = max(uh, 1.0), "Fallback：無資料，維持運轉"
        elif policy.startswith("固定門檻"):
            seen = do_raw[t] + delta if policy == "固定門檻（原始探頭）" else sim
            if seen < thr_on:
                latch = True
            elif seen >= thr_on + 0.5:
                latch = False
            u = uh
            if latch:
                alarm = True
                u = 2.0 if uh >= 1 else 1.0
                reason = "DO 低於門檻"
        else:
            row = pred.loc[t]
            m = models[int(row["fold"])]
            p = p_low_shifted(row, m, delta, decay)
            u = uh
            if sim < C.DO_CRIT or p > alpha:
                hold = 3
                alarm = True
            cool = max(cool - 1, 0)
            if hold > 0:
                u = 2.0 if uh >= 1 else 1.0
                reason = f"預測低溶氧機率 {p:.0%}"
                hold -= 1
                saving = 0
            elif (energy_saving and uh >= 1 and sim >= C.DO_HIGH and p < beta and t.hour in C.PEAK_HOURS
                  and cool == 0):
                u, reason = 0.0, "DO 充足，尖峰節能"
                saving += 1
                if saving >= 2:          # 每次最多停 2 小時，之後冷卻 4 小時
                    saving, cool = 0, 4
            else:
                saving = 0
        prev_gap = u - uh
        rows.append({"time": t, "do_obs": obs, "do_sim": sim, "u_hist": uh, "u": u, "alarm": alarm,
                     "reason": reason})
    return pd.DataFrame(rows).set_index("time")


def metrics(log: pd.DataFrame) -> dict:
    d = log["do_sim"]
    on_alarm = log["alarm"] & ~log["alarm"].shift(1, fill_value=False)
    kwh = log["u"].sum() * C.AERATOR_RATED_KW
    return {"低溶氧時數（DO<3）": int((d < C.DO_LOW).sum()), "危急時數（DO<2.5）": int((d < C.DO_CRIT).sum()),
            "最低 DO": round(float(d.min()), 2), "增氧機用電（度）": round(float(kwh), 1),
            "電費（元）": round(float(kwh * C.ELECTRICITY_PRICE), 0),
            "備用機啟動時數": int((log["u"] >= 2).sum()), "告警次數": int(on_alarm.sum()),
            "無效告警時數": int((log["alarm"] & (d >= C.DO_GOOD)).sum()),
            "操作切換次數": int((log["u"].diff().fillna(0) != 0).sum())}


def compare(f, pred, models, effect, decay, alpha=C.RISK_ALPHA, beta=C.SAVE_BETA, start=None, end=None):
    rows, logs = {}, {}
    for pol in POLICIES:
        logs[pol] = simulate(f, pred, models, pol, effect, decay, alpha, beta, start, end)
        rows[pol] = metrics(logs[pol])
    return pd.DataFrame(rows).T, logs


LOSS_PER_LOW_HOUR = C.LOSS_PER_LOW_HOUR   # 成本設定與營運風險共用（common/config.py）


def cost(m: dict) -> float:
    return m["低溶氧時數（DO<3）"] * LOSS_PER_LOW_HOUR + m["危急時數（DO<2.5）"] * C.LOSS_PER_CRIT_HOUR + m["電費（元）"]


def tune(f, pred, models, effect, decay, tune_period, valid_period,
         alphas=(0.1, 0.2, 0.3, 0.4, 0.5), betas=(0.02, 0.05, 0.1)) -> dict:
    """再學習：在調整期找成本最低的 (α, β)，到驗證期確認比兩個基準好才標記 validated。"""
    grid = []
    for a in alphas:
        for b in betas:
            m = metrics(simulate(f, pred, models, "AI 決策", effect, decay, a, b, *tune_period))
            grid.append({"alpha": a, "beta": b, "cost": cost(m), **m})
    grid = pd.DataFrame(grid).sort_values("cost")
    best = grid.iloc[0]
    val, _ = compare(f, pred, models, effect, decay, best["alpha"], best["beta"], *valid_period)
    c = {k: cost(v) for k, v in val.to_dict("index").items()}
    validated = c["AI 決策"] <= min(v for k, v in c.items() if k != "AI 決策")
    return {"alpha": float(best["alpha"]), "beta": float(best["beta"]), "validated": bool(validated),
            "grid": grid, "validation": val, "validation_cost": c}


def save_params(params: dict) -> None:
    p = ROOT / C.PARAMS_FILE
    p.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
