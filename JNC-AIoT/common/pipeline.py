"""把企業流程圖的 5 個階段串成一條閉環（魚塭）。

01 IoT 感測（回放器）→ 02 大數據（清洗、歷史基準）→ 03 AI 分析（狀態、診斷、預測）
→ 04 決策引擎（標準決策資料）→ 05 執行回饋（模擬 SCADA／PLC、成效驗證、再學習）

    pipe = PondPipeline.build()        # 第一次約 2 分鐘（訓練 4 段滾動模型），之後讀快取
    out = pipe.step("2026-07-20 05:00")   # 某一小時的完整輸出
"""

from __future__ import annotations

import hashlib
import pickle
from dataclasses import dataclass, replace

import pandas as pd

from common import config as C
from common.clean import load_clean
from common.load_jnc import ROOT
from common.replay import apply_fault
from decide.engine import decide, load_params, three_questions
from decide.workorder import work_orders
from diagnose.pond import IForest, diagnose, diagnose_frame
from forecast.pond import FOLDS, forecast, walk_forward
from state.pond import assess, state

CACHE = ROOT / ".cache"


def _settings_key() -> bytes:
    """影響診斷與預測的設定；改了就重算快取。"""
    from forecast.pond import WEATHER_FEATURES
    keys = sorted(k for k in dir(C) if k.isupper())
    return (repr([(k, getattr(C, k)) for k in keys]) + repr(WEATHER_FEATURES)).encode()


@dataclass
class PondPipeline:
    df: pd.DataFrame
    frame: pd.DataFrame
    hourly_diag: pd.DataFrame
    pred: pd.DataFrame
    models: list
    params: dict
    iforest: object = None
    fault: dict | None = None    # 平台注入的故障（示範用）

    @classmethod
    def build(cls, use_cache: bool = True) -> "PondPipeline":
        df = load_clean("pond")
        frame = assess(df)
        key = hashlib.md5(pd.util.hash_pandas_object(frame.select_dtypes("number"), index=True)
                          .values.tobytes() + str(FOLDS).encode() + b"v2" + _settings_key()).hexdigest()[:10]
        path = CACHE / f"pond_{key}.pkl"
        if use_cache and path.exists():
            hourly_diag, pred, models, iforest = pickle.loads(path.read_bytes())
        else:
            iforest = IForest().fit(frame.loc[:pd.Timestamp(FOLDS[0][0]) - pd.Timedelta(hours=1)])
            hourly_diag = diagnose_frame(df, frame, iforest)
            pred, models = walk_forward(frame)
            CACHE.mkdir(exist_ok=True)
            path.write_bytes(pickle.dumps((hourly_diag, pred, models, iforest)))
        return cls(df, frame, hourly_diag, pred, models, load_params(), iforest)

    def with_fault(self, kind: str, col: str, end, hours: int) -> "PondPipeline":
        """注入故障（到 end 為止已持續 hours 小時），重算該段的狀態、診斷與預測。

        決賽示範用：例如注入「主機斷線」看 Fallback、注入「DO2 掉到 0」看壞探頭被自動排除。"""
        end = pd.Timestamp(end)
        start = end - pd.Timedelta(hours=hours - 1)
        bad = apply_fault(self.df, kind, col, start, hours)
        lo = start - pd.Timedelta(hours=120)
        sub = bad.loc[lo:end + pd.Timedelta(hours=6)]
        f_sub = assess(sub)
        frame = self.frame.copy()
        frame.loc[f_sub.index, f_sub.columns] = f_sub
        hd_sub = diagnose_frame(sub, f_sub, self.iforest)
        hd = self.hourly_diag
        keep = (hd["ts"] < sub.index[0]) | (hd["ts"] > sub.index[-1])
        hourly = pd.concat([hd[keep], hd_sub]).sort_values(["ts", "type"]).reset_index(drop=True)
        pred = self.pred.copy()
        rows = pred.loc[start:end + pd.Timedelta(hours=6)].index
        for fold, idx in pd.Series(pred.loc[rows, "fold"]).groupby(pred.loc[rows, "fold"]):
            p = self.models[int(fold)].predict(
                frame.loc[idx.index[0] - pd.Timedelta(hours=48):idx.index[-1]]).loc[idx.index]
            pred.loc[idx.index, p.columns] = p
        return replace(self, df=bad, frame=frame, hourly_diag=hourly, pred=pred,
                       fault={"kind": kind, "col": col, "start": start, "end": end, "hours": hours})

    @property
    def replay_index(self) -> pd.DatetimeIndex:
        """有樣本外預測的期間（7/15 起），回放從這裡開始。"""
        return self.pred.index

    def step(self, ts) -> dict:
        ts = pd.Timestamp(ts)
        window = self.df.loc[ts - pd.Timedelta(hours=95):ts]
        s = state(window, "pond", frame=self.frame)
        d = diagnose(window, "pond", hourly=self.hourly_diag)
        fold = int(self.pred.loc[ts, "fold"])
        fc = forecast(window, "pond", self.models[fold], frame=self.frame, pred=self.pred)
        dec = decide(s, d, fc, self.params)
        return {"ts": ts, "state": s, "diagnoses": d, "forecast": fc, "decisions": dec,
                "work_orders": work_orders(dec), "answers": three_questions(s, d, fc, dec)}
