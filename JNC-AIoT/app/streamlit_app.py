"""JNC AIoT 決策大腦（魚塭）— Streamlit 平台。

    .venv/bin/streamlit run app/streamlit_app.py

回放銘祥魚塭資料，逐小時展示 IoT 感測 → 大數據 → AI 分析 → 決策引擎 → 執行回饋 的閉環。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import config as C
from backtest import feedback as FB
from common.pipeline import PondPipeline
from common.replay import FAULT_NAMES

ROOT = Path(__file__).resolve().parent.parent
LIGHT_COLOR = {"green": "#1f9d6b", "yellow": "#e0a800", "red": "#d64545", "gray": "#8a8a8a"}
MODE_COLOR = {"自動執行": "#1f9d6b", "人工確認": "#e08a00", "Fallback": "#d64545"}
STAGES = [("01 IoT 感測", "#1f5fa8"), ("02 大數據", "#2a9fc9"), ("03 AI 分析", "#2fa66b"),
          ("04 決策引擎", "#e0a020"), ("05 執行回饋", "#d9534f")]
DEMO_POINTS = {
    "預測性增氧：7/19 18:00 DO 開始下滑": "2026-07-19 18:00",
    "危急低溶氧：7/20 03:00": "2026-07-20 03:00",
    "pH1 漂移＋DO2 劣化：8/30 14:00": "2026-08-30 14:00",
    "DO3 失效、氣象站凍結：9/20 06:00": "2026-09-20 06:00",
    "水質正常：9/10 13:00": "2026-09-10 13:00",
}

st.set_page_config(page_title="JNC AIoT 決策大腦", page_icon="🐟", layout="wide")


@st.cache_resource(show_spinner="第一次啟動要訓練預測模型（約 2 分鐘），之後會讀快取…")
def get_pipe() -> PondPipeline:
    return PondPipeline.build()


pipe = get_pipe()
idx = pipe.replay_index
ss = st.session_state
ss.setdefault("i", int(idx.get_loc(pd.Timestamp("2026-07-19 18:00"))))

# ---------------- 側欄：回放器 ----------------
with st.sidebar:
    st.markdown("### 01 IoT 感測・資料回放")
    st.caption("以銘祥魚塭（專家系統）歷史資料模擬即時感測；模組只看得到當下以前的資料。")
    def _jump():
        if ss.demo in DEMO_POINTS:
            ss.i = int(idx.get_loc(pd.Timestamp(DEMO_POINTS[ss.demo])))

    def _move(k: int):
        ss.i = min(max(ss.i + k, 0), len(idx) - 1)

    st.selectbox("跳到展示情境", ["（自選時間）"] + list(DEMO_POINTS), key="demo", on_change=_jump)
    st.slider("回放時間", 0, len(idx) - 1, key="i", help="7/15 之後為樣本外期間（預測模型沒看過）")
    c1, c2, c3 = st.columns(3)
    c1.button("◀ 前 1 h", on_click=_move, args=(-1,))
    c2.button("後 1 h ▶", on_click=_move, args=(1,))
    auto = c3.toggle("播放")
    st.markdown(f"**{idx[ss.i]:%Y/%m/%d %H:00}**")
    st.divider()
    st.markdown("### 注入故障（示範）")
    st.caption("在目前回放時間注入感測器或主機故障，看 AI 如何排除壞探頭、改走 Fallback。")
    fault_kind = st.selectbox("故障類型", ["（不注入）"] + list(FAULT_NAMES), key="fault_kind",
                              format_func=lambda k: FAULT_NAMES.get(k, k))
    probe_cols = [c for cols in C.PROBES.values() for c in cols]
    fault_col = st.selectbox("探頭", probe_cols, key="fault_col", disabled=fault_kind in ("（不注入）", "offline"),
                             format_func=lambda c: c.replace(" 即時值", ""))
    fault_hours = st.slider("到目前為止已持續（小時）", 1, 24, 6, key="fault_hours",
                            disabled=fault_kind in ("（不注入）", "spike"))
    p = pipe.params
    st.divider()
    st.markdown("### 決策參數（再學習結果）")
    st.caption(f"α＝{p['alpha']}（低溶氧機率超過就增氧）、β＝{p['beta']}（節能門檻）、"
               f"{'已驗證：DO 已低於門檻的增氧自動執行，只是預測會低仍需人工確認' if p.get('validated') else '未驗證：增氧決策一律人工確認'}")

ts = idx[ss.i]


@st.cache_resource(max_entries=8, show_spinner="注入故障，重新計算狀態、診斷與預測…")
def faulted(_pipe: PondPipeline, kind: str, col: str, end: pd.Timestamp, hours: int) -> PondPipeline:
    return _pipe.with_fault(kind, col, end, hours)


if fault_kind == "（不注入）":
    view = pipe
else:
    view = faulted(pipe, fault_kind, fault_col, ts, 1 if fault_kind == "spike" else fault_hours)
    where = "主機" if fault_kind == "offline" else fault_col.replace(" 即時值", "")
    st.warning(f"示範模式：已在 {where} 注入「{FAULT_NAMES[fault_kind]}」"
               f"（{view.fault['start']:%m/%d %H:00}–{ts:%m/%d %H:00}），以下結果都是注入後重新計算的。")
out = view.step(ts)
fb_log = FB.load()
s, fc, decs = out["state"], out["forecast"], out["decisions"]

# ---------------- 標題與閉環 ----------------
st.markdown("## IoT 大數據 × AI 決策・魚塭守門員")
cols = st.columns(5)
stage_txt = [
    f"{len(view.df.columns) - 1} 個欄位<br>主機{'斷線' if s['offline'] else '連線中'}",
    f"清洗、歷史基準<br>可用 DO 探頭 {s['probes_used']['DO']}/3",
    f"{s['light_text']}<br>{len([d for d in out['diagnoses'] if d['confidence'] >= C.ALARM_MIN_CONF and d['type'] != 'water_event'])} 項設備異常",
    f"{len(decs)} 筆決策<br>{sum(d['執行模式'] != '自動執行' for d in decs)} 筆待人工／Fallback",
    f"{len(fb_log)} 筆執行紀錄<br>α＝{pipe.params['alpha']}，可依回饋再學習",
]
for c, (name, color), txt in zip(cols, STAGES, stage_txt):
    c.markdown(f"<div style='background:{color};color:white;border-radius:10px;padding:10px 12px;"
               f"min-height:92px'><b>{name}</b><br><span style='font-size:0.85em'>{txt}</span></div>",
               unsafe_allow_html=True)

st.write("")
q = st.columns(3)
for c, (k, v), n in zip(q, out["answers"].items(), ["01", "02", "03"]):
    c.markdown(f"<div style='border:1px solid #ddd;border-radius:10px;padding:10px 14px;min-height:96px'>"
               f"<span style='color:#888'>{n}</span> <b>{k}</b><br>{v}</div>", unsafe_allow_html=True)

tab = st.tabs(["決策與工單", "狀態辨識", "異常診斷", "趨勢預測", "執行回饋", "成效驗證"])

# ---------------- 決策與工單 ----------------
with tab[0]:
    st.markdown("#### 標準決策資料")
    for d in decs:
        color = MODE_COLOR[d["執行模式"]]
        with st.container(border=True):
            h1, h2 = st.columns([5, 2])
            h1.markdown(f"**P{d['優先級']}｜{d['類別']}｜{d['設備']} → {d['動作']}**　"
                        f"<span style='background:{color};color:white;border-radius:6px;padding:2px 8px'>"
                        f"{d['執行模式']}</span>", unsafe_allow_html=True)
            key = f"{d['編號']}"
            done = set(fb_log["編號"].astype(str))
            if key in done:
                h2.success("已處理（見執行回饋）")
            elif d["執行模式"] == "人工確認":
                b1, b2 = h2.columns(2)
                if b1.button("核准", key="ok" + key):
                    FB.record(d, "核准執行", ts, fc, s, pipe.params)
                    st.rerun()
                if b2.button("駁回", key="no" + key):
                    FB.record(d, "駁回", ts, fc, s, pipe.params)
                    st.rerun()
            elif h2.button("送 SCADA 執行", key="run" + key):
                FB.record(d, "自動執行" if d["執行模式"] == "自動執行" else "PLC 安全規則", ts, fc, s, pipe.params)
                st.rerun()
            nine = {k: d[k] for k in ["設備", "動作", "時間", "幅度", "理由", "預期效果", "風險", "人工確認", "Fallback"]}
            st.dataframe(pd.DataFrame([nine]), hide_index=True, width="stretch")
    st.markdown("#### 管理優先：工單、派工、備品與能耗")
    if out["work_orders"]:
        wo = pd.DataFrame(out["work_orders"]).drop(columns=["說明"])
        st.dataframe(wo, hide_index=True, width="stretch")
        with st.expander("工單說明"):
            for w in out["work_orders"]:
                st.markdown(f"- **{w['工單編號']}** {w['說明']}")
    else:
        st.info("目前沒有需要人工處理的工單。")

# ---------------- 狀態辨識 ----------------
with tab[1]:
    a, b, c, d_ = st.columns(4)
    a.markdown(f"<div style='font-size:2.2em;color:{LIGHT_COLOR[s['light']]}'>● {s['light_text']}</div>",
               unsafe_allow_html=True)
    b.metric("WQI 水質指數", s["wqi"])
    c.metric("融合 DO（mg/L）", s["values"]["DO"])
    d_.metric("增氧機", "運轉" if s["aerator_on"] else "停機", f"{s['power_w']} W" if s["power_w"] else None,
              delta_color="off")
    st.caption("融合值＝可信度 ≥ 50 的探頭取中位數；WQI＝DO 50%、pH 20%、水溫 15%、ORP 15% 子指標加權。"
               "流程圖的 GI 意義待企業確認（Q2），暫以「設備健康度」＝探頭平均可信度呈現。")
    v = s["values"]
    st.dataframe(pd.DataFrame([{"pH": v["pH"], "ORP（mV）": v["ORP"], "SC": v["SC"], "水溫（°C）": v["temp"],
                                "設備健康度": s["device_health"]}]), hide_index=True)
    env = s.get("environment") or {}
    st.markdown("#### 環境（OA4 氣象站）")
    st.dataframe(pd.DataFrame([{"氣溫（°C）": env.get("氣溫"), "濕度（%）": env.get("濕度"),
                                "氣壓（hPa）": env.get("氣壓"), "熱指數": env.get("熱指數")}]), hide_index=True)
    st.caption("氣象站凍結或讀到 0 時顯示空白，也不會進入預測（9/14 起氣象站凍結）。氣溫與水溫差、氣壓變化、濕度是溶氧預測的特徵。")
    st.markdown("#### 感測器可信度（0–100）")
    tr = pd.Series(s["sensor_trust"]).dropna()
    fig = go.Figure(go.Bar(x=tr.values, y=[k.replace(" 即時值", "") for k in tr.index], orientation="h",
                           marker_color=["#1f9d6b" if x >= 80 else "#e0a800" if x >= 50 else "#d64545" for x in tr.values]))
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), xaxis_range=[0, 100])
    st.plotly_chart(fig, width="stretch")

# ---------------- 異常診斷 ----------------
with tab[2]:
    diags = out["diagnoses"]
    if not diags:
        st.success("這一小時沒有異常。")
    for d in sorted(diags, key=lambda d: -d["confidence"]):
        lvl = "error" if d["confidence"] >= 0.8 else "warning" if d["confidence"] >= C.ALARM_MIN_CONF else "info"
        getattr(st, lvl)(f"**{d['target']}｜{d['type']}**（診斷可信度 {d['confidence']:.2f}，已持續 {d['duration_h']} 小時）\n\n"
                         f"可能原因：{d['cause']}\n\n判斷證據：{'；'.join(d['evidence'])}")
    st.caption(f"可信度 < {C.ALARM_MIN_CONF} 只當資料品質提示、不派工。")

# ---------------- 趨勢預測 ----------------
with tab[3]:
    a, b, c = st.columns(3)
    a.metric("6 小時內低溶氧機率", f"{fc['p_low']:.0%}" if fc["p_low"] is not None else "—")
    b.metric("預計超標時間", "已低於門檻" if fc["hours_to_threshold"] == 0 else
             (f"{fc['hours_to_threshold']} 小時後" if fc["hours_to_threshold"] else "6 小時內不會"))
    worst = fc.get("fail_target")
    c.metric("探頭故障機率（最高）", f"{fc['fail_prob']:.0%}" if fc.get("fail_prob") is not None else "—",
             worst.replace(" 即時值", "") if worst else None, delta_color="off")
    aer, risk = fc.get("aerator") or {}, fc.get("ops_risk") or {}
    d1, d2, d3 = st.columns(3)
    d1.metric("增氧機 48 h 內故障機率", f"{aer['fail_prob']:.0%}" if aer.get("fail_prob") is not None else "—",
              f"{aer['slope_w_per_day']:+.1f} W／天" if aer.get("slope_w_per_day") is not None else None,
              delta_color="off")
    has_loss = bool(risk) and risk.get("expected_loss") is not None
    d2.metric("營運風險（6 h）", risk.get("level", "—"),
              f"預期損失約 {risk['expected_loss']} 元" if has_loss else risk.get("note"), delta_color="off")
    d3.metric("期望低溶氧／危急時數（6 h）",
              f"{risk['expected_low_h']}／{risk['expected_crit_h']} h" if has_loss else "—")
    if aer.get("evidence"):
        st.caption("增氧機：" + aer["evidence"] + "。營運風險＝" + "＋".join(f"{k} {v} 元" for k, v in risk.get("breakdown", {}).items())
                   + "（單價為估計值，見 common/config.py）")
    hist = view.frame["DO"].loc[ts - pd.Timedelta(hours=48):ts]
    fut_t = [ts + pd.Timedelta(hours=h) for h in range(0, 7)]
    fut = [fc["now"]] + fc["path"]
    actual = view.frame["DO"].loc[ts:ts + pd.Timedelta(hours=6)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist.values, name="融合 DO（過去 48 h）", line=dict(color="#333")))
    fig.add_trace(go.Scatter(x=fut_t, y=fut, name="AI 預測 1–6 h", line=dict(color="#1f9d6b", dash="dash")))
    fig.add_trace(go.Scatter(x=actual.index, y=actual.values, name="實際（回放答案）",
                             line=dict(color="#bbb", dash="dot")))
    for col in C.PROBES["DO"]:
        raw = view.df[col].loc[ts - pd.Timedelta(hours=48):ts]
        fig.add_trace(go.Scatter(x=raw.index, y=raw.values, name=col.replace(" 即時值", "") + " 原始",
                                 line=dict(width=0.8), opacity=0.35, visible="legendonly"))
    fig.add_hline(y=C.DO_LOW, line=dict(color="#d64545", dash="dot"), annotation_text="低溶氧門檻 3.0")
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="DO（mg/L）",
                      legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    rul = pd.DataFrame(fc["probe_rul"]).T
    rul.index = [i.replace(" 即時值", "") for i in rul.index]
    st.markdown("#### 預測維護：探頭剩餘可用時間")
    st.dataframe(rul.rename(columns={"rul_h": "剩餘可用時間（h）", "slope_per_day": "偏離速度（每天）",
                                     "fail_prob": "48 h 內故障機率"}), width="stretch")

# ---------------- 執行回饋 ----------------
with tab[4]:
    st.markdown("AI 提出決策 → SCADA 呈現、告警與管理流程 → PLC 保留安全連鎖與緊急控制 → **結果回傳、驗證、再學習**。"
                "低風險且已驗證：自動執行；中高風險：人工確認；系統失效：Fallback 安全規則。")
    if len(fb_log):
        v = FB.verify(fb_log, pipe.frame, ts)
        sm = FB.summary(v)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("執行紀錄", sm["紀錄"])
        m2.metric("預警已驗證", sm["預警已驗證"], help="決策後 6 小時，看 DO 是否真的低於 3.0（歷史資料，真實結果）")
        m3.metric("預警成真率", f"{sm['預警成真率']:.0%}" if sm["預警成真率"] is not None else "—")
        m4.metric("增氧決策駁回率", f"{sm['駁回率']:.0%}" if sm["駁回率"] is not None else "—")
        show = v.drop(columns=["紀錄時間", "類別"]).copy()
        show["決策時間"] = pd.to_datetime(show["決策時間"]).dt.strftime("%m/%d %H:00")
        st.dataframe(show, hide_index=True, width="stretch")
        st.caption("驗證以目前回放時間為準：回放超過決策後 6 小時才驗證。「模擬執行」＝歷史實際＋增氧機效果"
                   f"（{pipe.params['aerator_effect']} mg/L/h，衰減 {pipe.params['effect_decay']}），"
                   "因為回放資料裡 AI 的行動沒有真的發生；預警成真率與駁回率是真實回饋。")
    else:
        st.info("在「決策與工單」核准、駁回或送出決策後，紀錄會存到 backtest/feedback.csv，並在回放時間經過後自動驗證。")

    st.markdown("#### 依執行結果重新學習")
    st.caption("只用目前回放時間以前的資料：前 2 週調 α、β，最後 1 週驗證；再依預警成真率與駁回率修正 α，寫回 decide/params.json。")
    c1, c2 = st.columns([1, 3])
    if c1.button("重新學習", type="primary"):
        with st.spinner("重新學習中…"):
            r = FB.relearn(pipe, ts, fb_log)
        pipe.params.clear()
        pipe.params.update(r["after"])
        ss.relearn = r
        st.rerun()
    if c2.button("清除執行紀錄"):
        FB.clear()
        ss.pop("relearn", None)
        st.rerun()
    if ss.get("relearn"):
        r = ss.relearn
        b, a = r["before"], r["after"]
        st.success(f"已更新 decide/params.json：α {b['alpha']} → {a['alpha']}、β {b['beta']} → {a['beta']}、"
                   f"{'已驗證' if a['validated'] else '未驗證'}（之後的決策立即套用）")
        for n in r["notes"]:
            st.markdown(f"- {n}")
        if r["validation"] is not None:
            st.markdown("驗證期各策略（工程估計效果）：")
            st.dataframe(r["validation"], width="stretch")
    if FB.RELEARN_LOG.exists():
        with st.expander("再學習紀錄"):
            st.dataframe(pd.read_csv(FB.RELEARN_LOG), hide_index=True, width="stretch")

# ---------------- 成效驗證 ----------------
with tab[5]:
    rep = ROOT / "backtest" / "report.md"
    if rep.exists():
        text = rep.read_text(encoding="utf-8")
        head = text.split("## 1.")[0]
        st.markdown(head)
        for name, cap in [("tradeoff.png", "用電與低溶氧的取捨"), ("closed_loop_example.png", "閉環範例"),
                          ("sensor_trust.png", "探頭可信度")]:
            img = ROOT / "backtest" / "figures" / name
            if img.exists():
                st.image(str(img), caption=cap)
        st.caption("完整報告：backtest/report.md（由 scripts/run_backtest.py 產生）")
    else:
        st.warning("尚未產生報告：請執行 .venv/bin/python scripts/run_backtest.py")

if auto and ss.i < len(idx) - 1:
    time.sleep(1.0)
    ss.i += 1
    st.rerun()
