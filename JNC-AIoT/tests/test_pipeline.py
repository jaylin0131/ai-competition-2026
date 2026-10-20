"""基本測試：.venv/bin/python -m pytest tests -q（需要 data/processed/pond.csv）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from common import config as C
from common.clean import load_clean
from common.replay import Replayer, inject_faults
from decide.engine import decide
from decide.workorder import number_guard
from diagnose.pond import diagnose_frame, to_episodes
from state.pond import assess, state

NINE = ["設備", "動作", "時間", "幅度", "理由", "預期效果", "風險", "人工確認", "Fallback"]


@pytest.fixture(scope="module")
def df():
    return load_clean("pond")


@pytest.fixture(scope="module")
def frame(df):
    return assess(df)


def test_clean_marks_offline(df):
    assert df.loc["2026-06-23 09:00", "offline"]
    assert not df.loc["2026-07-15 09:00", "offline"]


def test_state_interface(df):
    s = state(df.loc[:"2026-08-30 06:00"])
    assert {"ts", "site", "wqi", "light", "sensor_trust"} <= s.keys()
    # pH1 漂移、DO2 劣化期間可信度要被壓低
    assert s["sensor_trust"]["pH1 即時值"] < 50
    assert s["sensor_trust"]["DO2 即時值"] < 50
    assert s["sensor_trust"]["pH2 即時值"] >= 80


def test_dead_probe_excluded(frame):
    # DO3 = 0 期間，融合 DO 不可被拉到 0
    assert frame.loc["2026-09-20":"2026-09-24", "DO"].min() > 2.5


def test_replayer_no_future(df):
    for ts, w in Replayer(df, "2026-07-20 00:00", "2026-07-20 03:00", 24).stream():
        assert w.index.max() == ts


def test_injected_faults_detected(df):
    cols = C.PROBES["DO"]
    bad, labels = inject_faults(df, cols, n=5, seed=1, start="2026-07-10", end="2026-08-08")
    ep = to_episodes(diagnose_frame(bad))
    hit = 0
    for lb in labels.itertuples():
        m = (ep["start"] <= lb.end + pd.Timedelta(hours=3)) & (ep["end"] >= lb.start - pd.Timedelta(hours=1))
        m &= (ep["target"] == lb.col) if lb.col != "ALL" else (ep["type"] == "offline")
        hit += m.any()
    assert hit >= 4


def _fc(p_low, h_thr=None, do=3.4):
    return {"p_low": p_low, "hours_to_threshold": h_thr, "h1": do, "h3": do - 0.2, "h6": do - 0.4,
            "probe_rul": {}}


def _state(do, on, offline=False, n=3, hour=5):
    return {"ts": f"2026-07-20T{hour:02d}:00:00", "values": {"DO": do}, "aerator_on": on,
            "probes_used": {"DO": n}, "offline": offline, "light_text": "", "wqi": 80}


def test_decide_nine_fields_and_modes():
    params = {"alpha": 0.3, "beta": 0.05, "validated": True, "aerator_effect": 0.13, "effect_decay": 0.73}
    d = decide(_state(3.4, False), [], _fc(0.6, 3), params)
    top = d[0]
    assert all(k in top for k in NINE)
    assert top["設備"] == "增氧機" and top["動作"] == "啟動" and top["執行模式"] == "自動執行"
    # 未驗證時改人工確認
    d = decide(_state(3.4, False), [], _fc(0.6, 3), {**params, "validated": False})
    assert d[0]["執行模式"] == "人工確認" and d[0]["人工確認"] is True
    # 斷線走 Fallback
    d = decide(_state(None, True, offline=True, n=0), [], _fc(None), params)
    assert d[0]["執行模式"] == "Fallback"
    # 尖峰時段 DO 充足 → 節能建議需人工確認
    d = decide(_state(4.8, True, hour=13), [], _fc(0.0, None, 4.8), params)
    assert d[0]["動作"] == "暫停" and d[0]["人工確認"]


def test_number_guard():
    src = "DO = 2.61 mg/L，持續 3 小時"
    assert number_guard("溶氧 2.61，請開機 3 小時", src)
    assert not number_guard("溶氧 2.4，請開機 3 小時", src)
