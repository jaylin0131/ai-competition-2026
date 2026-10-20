"""成效驗證：異常診斷的 Precision／Recall（合成故障注入）與已知事件召回率。

企業沒有維修紀錄（Q1），依參賽進度分析報告 3.3：在乾淨區段注入合成故障當正確答案，
另外用 notes/eda/events.md 的已知事件當弱標籤。
"""

from __future__ import annotations

import pandas as pd

from common import config as C
from common.events import pond_events
from common.replay import inject_faults
from diagnose.pond import diagnose_frame, to_episodes

SENSOR_TYPES = {"sensor_fault", "sensor_drift", "offline"}
CLEAN_WINDOW = ("2026-07-10", "2026-08-08")   # 斷線後、pH1 漂移前，已知事件最少的一段


def _overlap(ep: pd.DataFrame, start, end, target, slack_h: int = 3) -> pd.DataFrame:
    s, e = start - pd.Timedelta(hours=1), end + pd.Timedelta(hours=slack_h)
    m = (ep["start"] <= e) & (ep["end"] >= s)
    if target != "ALL":
        m &= ep["target"] == target
    else:
        m &= ep["type"] == "offline"
    return ep[m]


def synthetic_eval(df: pd.DataFrame, seeds=range(5), n: int = 10) -> tuple[pd.DataFrame, dict]:
    cols = [c for cols in C.PROBES.values() for c in cols]
    recs, fp, weeks = [], 0, 0.0
    for seed in seeds:
        bad, labels = inject_faults(df, cols, n=n, seed=seed, start=CLEAN_WINDOW[0], end=CLEAN_WINDOW[1])
        ep = to_episodes(diagnose_frame(bad))
        ep = ep[ep["type"].isin(SENSOR_TYPES) & (ep["confidence"] >= C.ALARM_MIN_CONF)
                & (ep["start"] >= CLEAN_WINDOW[0]) & (ep["start"] <= CLEAN_WINDOW[1])]
        matched = set()
        for lb in labels.itertuples():
            hit = _overlap(ep, lb.start, lb.end, lb.col)
            matched |= set(hit.index)
            delay = (hit["start"].min() - lb.start).total_seconds() / 3600 if len(hit) else None
            recs.append({"seed": seed, "fault": lb.type, "col": lb.col, "detected": len(hit) > 0,
                         "type_ok": bool((hit["type"] == lb.diag_type).any()), "delay_h": delay})
        fp += len(ep) - len(matched)
        weeks += (pd.Timestamp(CLEAN_WINDOW[1]) - pd.Timestamp(CLEAN_WINDOW[0])).days / 7
    r = pd.DataFrame(recs)
    tp = int(r["detected"].sum())
    summary = {"labels": len(r), "recall": tp / len(r), "precision": tp / max(tp + fp, 1),
               "false_alarms_per_week": fp / weeks, "type_accuracy": r.loc[r.detected, "type_ok"].mean(),
               "median_delay_h": r["delay_h"].median()}
    by_type = r.groupby("fault").agg(n=("detected", "size"), recall=("detected", "mean"),
                                     type_acc=("type_ok", "mean"), delay_h=("delay_h", "median"))
    return by_type, summary


def known_event_eval(df: pd.DataFrame, hourly: pd.DataFrame | None = None) -> pd.DataFrame:
    ep = to_episodes(diagnose_frame(df) if hourly is None else hourly)
    ep = ep[ep["type"].isin(SENSOR_TYPES) & (ep["confidence"] >= C.ALARM_MIN_CONF)]
    rows = []
    for ev in pond_events().itertuples():
        hit = _overlap(ep, ev.start, ev.end, ev.col, slack_h=6)
        first = hit["start"].min() if len(hit) else None
        rows.append({"事件": ev.id, "欄位": ev.col, "期間": f"{ev.start:%m/%d %H:%M}–{ev.end:%m/%d %H:%M}",
                     "偵測到": "是" if len(hit) else "否",
                     "首次偵測": "" if first is None else f"{first:%m/%d %H:%M}",
                     "判定類型": "、".join(sorted(hit["type"].unique()))})
    return pd.DataFrame(rows)
