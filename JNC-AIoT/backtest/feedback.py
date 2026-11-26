"""05 執行回饋：執行紀錄 → 結果驗證 → 再學習（I7）。

企業流程圖的最後一段「結果回傳與成效驗證」要回到起點。平台上每一次核准、駁回、送 SCADA 執行都寫進
backtest/feedback.csv，連同當下 AI 的判斷（DO、低溶氧機率、預期回升）。之後：

1. verify()：回放時間過了決策後 6 小時，自動驗證
   - 預警是否成真：6 小時內融合 DO 是否真的低於門檻（歷史資料，真實結果）
   - 3 小時後的 DO：歷史實際值（真實）與「執行後」值（歷史＋增氧機效果，模擬）
2. relearn()：
   - 只用回放時間以前的資料，前 2 週調 α、β，最後 1 週驗證（backtest/closed_loop.tune）
   - 再依回饋修正 α：預警成真率太低 → 提高 α（少報）；現場常駁回預測性增氧 → 提高 α；
     成真率很高且沒有被駁回 → 降低 α（更早預警）
   - 寫回 decide/params.json，並把每次再學習記在 backtest/relearn_log.csv

回放資料是歷史紀錄，AI 的行動沒有真的發生，所以「執行後的 DO」只能模擬；預警成真率與人工駁回率是真實回饋。
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from backtest import closed_loop as CL
from common import config as C
from common.load_jnc import ROOT

FEEDBACK_CSV = ROOT / "backtest" / "feedback.csv"
RELEARN_LOG = ROOT / "backtest" / "relearn_log.csv"
COLUMNS = ["編號", "決策時間", "設備", "動作", "類別", "執行模式", "風險", "結果", "決策時DO", "低溶氧機率",
           "預期回升", "紀錄時間"]
AERATORS = ("增氧機", "備用增氧機")
ALPHA_RANGE = (0.05, 0.6)
STEP = 0.05
MIN_N = 3            # 回饋至少幾筆才拿來修正 α


def load(path=FEEDBACK_CSV) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path, parse_dates=["決策時間"])
    return df.reindex(columns=COLUMNS)


def record(decision: dict, result: str, ts, forecast: dict, state: dict, params: dict,
           path=FEEDBACK_CSV) -> pd.DataFrame:
    """記一筆執行紀錄（同一個編號只記一次）。result：核准執行、駁回、自動執行、PLC 安全規則。"""
    log = load(path)
    if decision["編號"] in set(log["編號"].astype(str)):
        return log
    eff, decay = params["aerator_effect"], params["effect_decay"]
    starts = decision["設備"] in AERATORS and decision["動作"].startswith("啟動")
    row = {"編號": decision["編號"], "決策時間": pd.Timestamp(ts), "設備": decision["設備"], "動作": decision["動作"],
           "類別": decision["類別"], "執行模式": decision["執行模式"], "風險": decision["風險"], "結果": result,
           "決策時DO": state["values"].get("DO"), "低溶氧機率": forecast.get("p_low"),
           "預期回升": round(eff * sum(decay ** k for k in range(3)), 3) if starts else 0.0,
           "紀錄時間": datetime.now().isoformat(timespec="seconds")}
    log = pd.concat([log, pd.DataFrame([row])], ignore_index=True) if len(log) else pd.DataFrame([row])
    path.parent.mkdir(exist_ok=True)
    log.to_csv(path, index=False, encoding="utf-8")
    return log


def clear(path=FEEDBACK_CSV) -> None:
    if path.exists():
        path.unlink()


def verify(log: pd.DataFrame, frame: pd.DataFrame, now) -> pd.DataFrame:
    """依回放時間 now 驗證已到期的紀錄。"""
    now = pd.Timestamp(now)
    do = frame["DO"]
    out = log.copy()
    warn, d3h, d3s = [], [], []
    for r in log.itertuples():
        t = pd.Timestamp(r.決策時間)
        is_warn = r.設備 in AERATORS and str(r.動作).startswith("啟動") and pd.notna(r.低溶氧機率)
        if not is_warn:
            warn.append("—")
        elif now < t + pd.Timedelta(hours=6):
            warn.append("待驗證")
        else:
            nxt = do.loc[t + pd.Timedelta(hours=1):t + pd.Timedelta(hours=6)]
            warn.append("無資料" if nxt.isna().all() else ("成真" if (nxt < C.DO_LOW).any() else "未發生"))
        d0, d3 = do.get(t), do.get(t + pd.Timedelta(hours=3))
        if now < t + pd.Timedelta(hours=3) or pd.isna(d0) or pd.isna(d3):
            d3h.append("待驗證" if now < t + pd.Timedelta(hours=3) else "—")
            d3s.append(d3h[-1])
        else:
            gain = float(r.預期回升 or 0) if r.結果 != "駁回" else 0.0
            d3h.append(f"{d0:.2f} → {d3:.2f}")
            d3s.append(f"{d0:.2f} → {d3 + gain:.2f}")
    out["預警驗證（6 h 內 DO<3）"] = warn
    out["DO 3 h 後：歷史實際"] = d3h
    out["DO 3 h 後：模擬執行"] = d3s
    return out


def summary(verified: pd.DataFrame) -> dict:
    w = verified["預警驗證（6 h 內 DO<3）"] if len(verified) else pd.Series(dtype=str)
    hit, miss = int((w == "成真").sum()), int((w == "未發生").sum())
    decided = verified[verified["結果"].isin(["核准執行", "駁回"])
                       & verified["設備"].isin(AERATORS)] if len(verified) else verified
    rej = int((decided["結果"] == "駁回").sum()) if len(decided) else 0
    return {"紀錄": len(verified), "預警已驗證": hit + miss, "預警成真": hit,
            "預警成真率": hit / (hit + miss) if hit + miss else None,
            "增氧決策人工處理": len(decided), "駁回": rej,
            "駁回率": rej / len(decided) if len(decided) else None}


def relearn(pipe, now, log: pd.DataFrame | None = None, save: bool = True) -> dict:
    """用回放時間 now 以前的資料與執行回饋重新學習 α、β。回傳更新前後與理由。"""
    now = pd.Timestamp(now)
    before = dict(pipe.params)
    p = dict(before)
    notes = []
    first = pipe.pred.index[0]
    t0, t1 = max(first, now - pd.Timedelta(days=21)), now - pd.Timedelta(days=7)
    validation = None
    if t1 - t0 >= pd.Timedelta(days=7):
        r = CL.tune(pipe.frame, pipe.pred, pipe.models, p["aerator_effect"], p["effect_decay"],
                    (t0, t1), (t1 + pd.Timedelta(hours=1), now))
        has_event = r["validation"].loc["歷史實際", "低溶氧時數（DO<3）"] > 0
        verdict = (f"比最好的基準省 {r['margin']:.1%}，"
                   f"{'達到' if r['validated'] else '未達'} {C.VALIDATE_MARGIN:.0%} 驗證門檻") if has_event else \
            f"驗證期沒有低溶氧事件，無法驗證，維持原判定（{'已驗證' if before.get('validated') else '未驗證'}）"
        notes.append(f"資料再學習：{t0:%m/%d}–{t1:%m/%d} 調參、{t1:%m/%d}–{now:%m/%d} 驗證 → "
                     f"α {before['alpha']} → {r['alpha']}、β {before['beta']} → {r['beta']}（{verdict}）")
        p.update(alpha=r["alpha"], beta=r["beta"],
                 validated=r["validated"] if has_event else before.get("validated", False))
        validation = r["validation"]
    else:
        notes.append(f"回放時間 {now:%m/%d} 以前的樣本外資料不足 2 週，不重調 α、β，只用執行回饋修正")

    v = verify(log if log is not None else load(), pipe.frame, now)
    s = summary(v)
    a = p["alpha"]
    if s["預警已驗證"] >= MIN_N and s["預警成真率"] is not None:
        if s["預警成真率"] < 0.3:
            a += STEP
            notes.append(f"預警成真率 {s['預警成真率']:.0%}（{s['預警成真']}/{s['預警已驗證']}）偏低 → α 提高 {STEP}，少報")
        elif s["預警成真率"] > 0.8 and (s["駁回率"] or 0) == 0:
            a -= STEP
            notes.append(f"預警成真率 {s['預警成真率']:.0%} 很高且沒有被駁回 → α 降低 {STEP}，更早預警")
    if s["增氧決策人工處理"] >= MIN_N and (s["駁回率"] or 0) > 0.5:
        a += STEP
        notes.append(f"現場駁回 {s['駁回']}/{s['增氧決策人工處理']} 筆增氧決策 → α 提高 {STEP}")
    if len(notes) == 1 and s["紀錄"] < MIN_N:
        notes.append(f"執行回饋只有 {s['紀錄']} 筆（少於 {MIN_N} 筆），暫不修正 α")
    p["alpha"] = float(np.clip(round(a, 2), *ALPHA_RANGE))
    p["updated"] = datetime.now().date().isoformat()
    p["note"] = f"平台依執行回饋再學習（回放時間 {now:%Y-%m-%d %H:00}）"
    if save:
        CL.save_params(p)
        entry = {"時間": datetime.now().isoformat(timespec="seconds"), "回放時間": now,
                 "α 前": before["alpha"], "α 後": p["alpha"], "β 前": before["beta"], "β 後": p["beta"],
                 "validated": p["validated"], "回饋筆數": s["紀錄"], "說明": "；".join(notes)}
        old = pd.read_csv(RELEARN_LOG) if RELEARN_LOG.exists() else pd.DataFrame()
        pd.concat([old, pd.DataFrame([entry])], ignore_index=True).to_csv(RELEARN_LOG, index=False, encoding="utf-8")
    return {"before": before, "after": p, "notes": notes, "summary": s, "validation": validation}
