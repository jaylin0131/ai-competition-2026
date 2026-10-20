"""把企業流程圖的 5 個階段串成一條閉環（魚塭）。

01 IoT 感測（回放器）→ 02 大數據（清洗、歷史基準）→ 03 AI 分析（狀態、診斷、預測）
→ 04 決策引擎（標準決策資料）→ 05 執行回饋（模擬 SCADA／PLC、成效驗證、再學習）

    pipe = PondPipeline.build()        # 第一次約 2 分鐘（訓練 4 段滾動模型），之後讀快取
    out = pipe.step("2026-07-20 05:00")   # 某一小時的完整輸出
"""

from __future__ import annotations

import hashlib
import pickle
from dataclasses import dataclass

import pandas as pd

from common import config as C
from common.clean import load_clean
from common.load_jnc import ROOT
from decide.engine import decide, load_params, three_questions
from decide.workorder import work_orders
from diagnose.pond import IForest, diagnose, diagnose_frame
from forecast.pond import FOLDS, forecast, walk_forward
from state.pond import assess, state

CACHE = ROOT / ".cache"


@dataclass
class PondPipeline:
    df: pd.DataFrame
    frame: pd.DataFrame
    hourly_diag: pd.DataFrame
    pred: pd.DataFrame
    models: list
    params: dict

    @classmethod
    def build(cls, use_cache: bool = True) -> "PondPipeline":
        df = load_clean("pond")
        frame = assess(df)
        key = hashlib.md5(pd.util.hash_pandas_object(frame.select_dtypes("number"), index=True)
                          .values.tobytes() + str(FOLDS).encode()).hexdigest()[:10]
        path = CACHE / f"pond_{key}.pkl"
        if use_cache and path.exists():
            hourly_diag, pred, models = pickle.loads(path.read_bytes())
        else:
            iforest = IForest().fit(frame.loc[:pd.Timestamp(FOLDS[0][0]) - pd.Timedelta(hours=1)])
            hourly_diag = diagnose_frame(df, frame, iforest)
            pred, models = walk_forward(frame)
            CACHE.mkdir(exist_ok=True)
            path.write_bytes(pickle.dumps((hourly_diag, pred, models)))
        return cls(df, frame, hourly_diag, pred, models, load_params())

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
