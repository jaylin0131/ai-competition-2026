"""04 決策引擎：目標、規則、風險、成本 → 標準決策資料（9 欄）→ 執行模式分級。回答「現在該做什麼？」

標準決策資料：設備、動作、時間、幅度、理由、預期效果、風險、人工確認、Fallback
另附：類別（行動控制／管理優先）、執行模式（自動執行／人工確認／Fallback）、優先級（P1 最高）、能耗_kWh

執行模式分級（企業安全控制原則），由 _d() 統一把關：
- 風險「低」且已驗證 → 自動執行（例：DO 已低於門檻時啟動增氧機，方向安全）
- 風險「中」「高」→ 一律人工確認（預測性增氧在 DO 仍 ≥ 3.0 時屬「中」，也要人工確認）
- 系統失效（斷線、DO 探頭全部不可信）→ Fallback 安全規則，由 PLC 保留安全連鎖
任何規則若把非「低」風險標成自動執行，_d() 會自動降為人工確認。

判斷由規則與模型決定；工單文字見 decide/workorder.py（LLM 只負責寫成白話，數字必須來自這裡）。
"""

from __future__ import annotations

import json
from pathlib import Path

from common import config as C
from common.load_jnc import ROOT

PRIORITY_OF = {"DO": 1, "pH": 2, "ORP": 3, "SC": 4, "OA4": 5}
SPARE = {"DO": "DO 探頭膜片與電解液", "pH": "pH 校正液（pH 7／pH 10）", "ORP": "ORP 標準液",
         "SC": "導電度標準液", "OA4": "氣象站主機（備品）"}
FALLBACK_AERATOR = "DO 資料中斷超過 1 小時或 DO < 2.5：PLC 維持增氧機運轉並通知值班人員"


def load_params() -> dict:
    p = ROOT / C.PARAMS_FILE
    base = {"alpha": C.RISK_ALPHA, "beta": C.SAVE_BETA, "validated": False,
            "aerator_effect": 0.13, "effect_decay": 0.73}
    if p.exists():
        base.update(json.loads(p.read_text(encoding="utf-8")))
    return base


def _d(**kw) -> dict:
    order = ["設備", "動作", "時間", "幅度", "理由", "預期效果", "風險", "人工確認", "Fallback"]
    rec = {k: kw.pop(k, None) for k in order}
    rec.update(kw)
    if rec["執行模式"] == "自動執行" and rec["風險"] != "低":
        rec["執行模式"] = "人工確認"   # 安全控制原則：只有低風險可自動執行
    rec["人工確認"] = rec["執行模式"] == "人工確認"
    return rec


def _finalize(out: list[dict], state: dict) -> list[dict]:
    """依優先級排序並補上編號；每個 return 都要經過這裡（工單要用編號）。"""
    out = sorted(out, key=lambda r: r["優先級"])
    for i, r in enumerate(out):
        r["編號"] = f"{state['ts'][:13].replace('-', '').replace('T', '-')}-{i + 1:02d}"
    return out


def _quantity(target: str) -> str:
    for q in PRIORITY_OF:
        if target.startswith(q):
            return q
    return "DO"


def decide(state: dict, diagnoses: list[dict], forecast: dict, params: dict | None = None) -> list[dict]:
    """介面（architecture.md 第 4 節）：回傳標準決策資料清單，依優先級排序。"""
    P = params or load_params()
    out: list[dict] = []
    do = state["values"]["DO"]
    on = state["aerator_on"]
    n_do = state["probes_used"]["DO"]
    p_low = forecast.get("p_low") or 0.0
    eff, decay = P["aerator_effect"], P["effect_decay"]
    gain3 = eff * sum(decay ** k for k in range(3))
    off_diag = next((d for d in diagnoses if d["type"] == "offline"), None)

    # A. 系統失效 → Fallback
    if state["offline"] or n_do == 0 or do is None:
        why = (f"感測主機斷線（已 {off_diag['duration_h']} 小時）" if off_diag
               else "三支 DO 探頭皆不可信") + "，無法判斷水質"
        out.append(_d(設備="增氧機", 動作="維持運轉" if on else "啟動並維持運轉", 時間="立即，直到資料恢復",
                      幅度="全速", 理由=why, 預期效果="避免在無監測下發生低溶氧",
                      風險="高", Fallback="PLC 安全連鎖：維持增氧機運轉，值班人員 30 分鐘內到場確認",
                      類別="行動控制", 執行模式="Fallback", 優先級=1,
                      能耗_kWh=0.0 if on else C.AERATOR_RATED_KW * 6))
        out.append(_d(設備="感測主機", 動作="檢查通訊與電源", 時間="1 小時內", 幅度="—",
                      理由=why, 預期效果="恢復監測", 風險="中", Fallback="恢復前維持 Fallback 規則",
                      類別="管理優先", 執行模式="人工確認", 優先級=1, 派工="值班人員", 備品="—", 能耗_kWh=0.0))
        return _finalize(out, state)

    h_thr = forecast.get("hours_to_threshold")
    fc_txt = (f"預測 1／3／6 小時 DO 為 {forecast['h1']}／{forecast['h3']}／{forecast['h6']} mg/L，"
              f"6 小時內低於 {C.DO_LOW} 的機率 {p_low:.0%}")
    trust_txt = f"{n_do} 支可信探頭一致（融合 DO = {do} mg/L）"

    # B. 危急：DO 已低於 DO_CRIT
    if do < C.DO_CRIT:
        if not on:
            out.append(_d(設備="增氧機", 動作="啟動", 時間="立即，持續 3 小時", 幅度="全速",
                          理由=f"DO = {do} mg/L 低於危急值 {C.DO_CRIT}；{trust_txt}",
                          預期效果=f"3 小時內 DO 約回升 {gain3:.2f} mg/L", 風險="低",
                          Fallback=FALLBACK_AERATOR, 類別="行動控制", 執行模式="自動執行", 優先級=1,
                          能耗_kWh=C.AERATOR_RATED_KW * 3))
        else:
            out.append(_d(設備="備用增氧機／進水閘", 動作="啟動備用增氧機或注入新水", 時間="立即",
                          幅度="依現場", 理由=f"增氧機已在運轉但 DO = {do} mg/L 仍低於危急值 {C.DO_CRIT}；{trust_txt}",
                          預期效果="避免魚群缺氧", 風險="高", Fallback="無法執行時立即通知場長",
                          類別="行動控制", 執行模式="人工確認", 優先級=1, 能耗_kWh=C.AERATOR_RATED_KW * 3))
        out.append(_d(設備="投餌機", 動作="暫停投餵", 時間="立即，直到 DO ≥ 3.5", 幅度="停止",
                      理由=f"DO = {do} mg/L，投餵會增加耗氧", 預期效果="降低耗氧", 風險="低",
                      Fallback="—", 類別="行動控制", 執行模式="人工確認", 優先級=1, 能耗_kWh=0.0))

    # C. 預測性增氧：P(低溶氧) > α
    elif p_low > P["alpha"] or (do < C.DO_LOW):
        when = "已低於門檻" if do < C.DO_LOW else (f"預計 {h_thr} 小時後低於門檻" if h_thr else "6 小時內可能低於門檻")
        if not on:
            # DO 已低於門檻＝低風險（方向安全、已發生）；只是預測會低＝中風險，要人工確認
            risk = "低" if do < C.DO_LOW else "中"
            mode = "自動執行" if (P["validated"] and risk == "低") else "人工確認"
            out.append(_d(設備="增氧機", 動作="啟動", 時間="立即，持續 3 小時", 幅度="全速",
                          理由=f"{when}；{fc_txt}；{trust_txt}",
                          預期效果=f"3 小時內 DO 約回升 {gain3:.2f} mg/L，避開低溶氧",
                          風險=risk, Fallback=FALLBACK_AERATOR,
                          類別="行動控制", 執行模式=mode, 優先級=2, 能耗_kWh=C.AERATOR_RATED_KW * 3))
        else:
            out.append(_d(設備="備用增氧機", 動作="啟動", 時間="立即，持續 3 小時", 幅度="全速",
                          理由=f"主增氧機已運轉；{when}；{fc_txt}；{trust_txt}",
                          預期效果=f"3 小時內 DO 約再回升 {gain3:.2f} mg/L", 風險="中",
                          Fallback=FALLBACK_AERATOR, 類別="行動控制", 執行模式="人工確認", 優先級=2,
                          能耗_kWh=C.AERATOR_RATED_KW * 3))
            out.append(_d(設備="投餌機", 動作="延後下一餐投餵", 時間="未來 3 小時", 幅度="減量 50%",
                          理由=f"{when}，投餵會增加耗氧", 預期效果="降低耗氧，減緩 DO 下降",
                          風險="低", Fallback="DO < 2.5 時改走危急規則",
                          類別="行動控制", 執行模式="人工確認", 優先級=3, 能耗_kWh=0.0))

    # D. 節能：DO 充足、風險極低、尖峰時段
    elif on and do >= C.DO_HIGH and p_low < P["beta"] and _hour(state) in C.PEAK_HOURS:
        out.append(_d(設備="增氧機", 動作="暫停", 時間="2 小時後自動恢復", 幅度="停機",
                      理由=f"DO = {do} mg/L 充足；{fc_txt}；目前為尖峰電價時段",
                      預期效果=f"節省約 {C.AERATOR_RATED_KW * 2:.2f} 度電（約 {C.AERATOR_RATED_KW * 2 * C.ELECTRICITY_PRICE:.0f} 元）",
                      風險="中", Fallback="DO < 3.5 或資料中斷：PLC 立即恢復運轉",
                      類別="行動控制", 執行模式="人工確認", 優先級=4, 能耗_kWh=-C.AERATOR_RATED_KW * 2))

    # E. 設備異常
    for d in diagnoses:
        if d["type"] == "equipment_fault" and d["confidence"] >= C.ALARM_MIN_CONF:
            out.append(_d(設備="增氧機", 動作="現場檢修", 時間="今日內", 幅度="—",
                          理由=d["evidence"][0], 預期效果="恢復增氧能力", 風險="中",
                          Fallback="檢修期間啟動備用增氧機", 類別="管理優先", 執行模式="人工確認",
                          優先級=2, 派工="維修技師", 備品="葉輪、馬達軸承", 能耗_kWh=0.0))

    # F. 感測器維護（診斷）＋ G. 預防性維護（剩餘可用時間）
    seen = set()
    for d in diagnoses:
        if d["type"] not in ("sensor_fault", "sensor_drift") or d["confidence"] < C.ALARM_MIN_CONF:
            continue
        tgt = d["target"]
        if tgt in seen:
            continue
        seen.add(tgt)
        q = _quantity(tgt)
        long = d.get("duration_h", 1) >= 24
        act = "清洗並校正" if d["type"] == "sensor_drift" else ("檢查或更換" if long else "現場檢查")
        out.append(_d(設備=tgt.replace(" 即時值", " 探頭"), 動作=act,
                      時間="24 小時內" if q == "DO" else "3 天內", 幅度="—",
                      理由=f"{d['cause']}：{d['evidence'][0]}（診斷可信度 {d['confidence']:.2f}）",
                      預期效果="恢復三探頭互相比對；維修前已自動排除此探頭", 風險="低",
                      Fallback="維修前以其餘探頭中位數判斷", 類別="管理優先", 執行模式="人工確認",
                      優先級=2 + (PRIORITY_OF[q] > 1), 派工="水質技術員", 備品=SPARE[q], 能耗_kWh=0.0))
    for col, r in (forecast.get("probe_rul") or {}).items():
        if col in seen or r["fail_prob"] < 0.7 or r["rul_h"] in (None, 0.0):
            continue
        q = _quantity(col)
        out.append(_d(設備=col.replace(" 即時值", " 探頭"), 動作="預防性校正", 時間=f"{max(1, int(r['rul_h']))} 小時內",
                      幅度="—", 理由=f"偏離量每天 {r['slope_per_day']:+.3f}，預計 {r['rul_h']} 小時後超出容許差（機率 {r['fail_prob']:.0%}）",
                      預期效果="在失準前完成校正", 風險="低", Fallback="超出容許差後自動排除此探頭",
                      類別="管理優先", 執行模式="人工確認", 優先級=3, 派工="水質技術員", 備品=SPARE[q], 能耗_kWh=0.0))

    if not any(r["類別"] == "行動控制" for r in out):
        out.append(_d(設備="增氧機", 動作="維持運轉" if on else "維持停機", 時間="下一小時重新評估", 幅度="—",
                      理由=f"{trust_txt}；{fc_txt}", 預期效果="水質穩定", 風險="低",
                      Fallback=FALLBACK_AERATOR, 類別="行動控制", 執行模式="自動執行", 優先級=4, 能耗_kWh=0.0))
    return _finalize(out, state)


def _hour(state: dict) -> int:
    return int(state["ts"][11:13])


def three_questions(state: dict, diagnoses: list[dict], forecast: dict, decisions: list[dict]) -> dict:
    """企業流程圖「AI 決策回答三個問題」。"""
    bad = [d for d in diagnoses if d["confidence"] >= C.ALARM_MIN_CONF and d["type"] != "water_event"]
    now = f"{state['light_text']}，WQI {state['wqi']}，DO {state['values']['DO']} mg/L"
    if bad:
        now += "；" + "、".join(sorted({"感測主機" if d["target"] == "ALL" else d["target"] for d in bad})) + " 異常"
    nxt = (f"6 小時內 DO 低於 {C.DO_LOW} 的機率 {forecast['p_low']:.0%}" if forecast.get("p_low") is not None
           else "資料不足，無法預測")
    if forecast.get("hours_to_threshold"):
        nxt += f"，預計 {forecast['hours_to_threshold']} 小時後超標"
    top = decisions[0] if decisions else None
    act = f"{top['設備']}：{top['動作']}（{top['執行模式']}）" if top else "維持現狀"
    return {"現在發生什麼？": now, "接下來會怎樣？": nxt, "現在該做什麼？": act}
