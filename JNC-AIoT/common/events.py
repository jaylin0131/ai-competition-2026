"""已知事件（弱標籤），摘自 notes/eda/events.md，評估異常診斷用。只收可信度中、高且有明確欄位的事件。"""

from __future__ import annotations

import pandas as pd

# (編號, 開始, 結束, diagnose type, 受影響欄位；ALL＝整台主機)
POND_EVENTS = [
    ("P05", "2026-06-23 09:00", "2026-06-23 14:00", "offline", "ALL"),
    ("P07", "2026-06-24 00:00", "2026-07-01 15:00", "offline", "ALL"),
    ("P09", "2026-07-07 06:00", "2026-07-08 13:00", "sensor_drift", "DO2 即時值"),
    ("P12", "2026-08-09 14:00", "2026-09-02 15:00", "sensor_drift", "pH1 即時值"),
    ("P14", "2026-08-27 21:00", "2026-09-02 14:00", "sensor_drift", "DO2 即時值"),
    ("P17", "2026-09-12 12:00", "2026-09-19 11:00", "sensor_drift", "DO3 即時值"),
    ("P18", "2026-09-14 02:00", "2026-09-28 21:00", "sensor_fault", "OA4 氣象站"),
    ("P19", "2026-09-15 20:00", "2026-09-28 21:00", "sensor_drift", "SC1 即時值"),
    ("P20", "2026-09-19 12:00", "2026-09-25 11:00", "sensor_fault", "DO3 即時值"),
]


def pond_events() -> pd.DataFrame:
    df = pd.DataFrame(POND_EVENTS, columns=["id", "start", "end", "diag_type", "col"])
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    return df
