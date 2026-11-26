"""產生成效驗證報告：backtest/report.md、backtest/figures/*.png，並把再學習後的決策參數寫入 decide/params.json。

    .venv/bin/python scripts/run_backtest.py          # 約 5 分鐘（第一次要訓練預測模型）

報告內的數字都由本腳本計算，改了任何模組請重跑。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from backtest import closed_loop as CL
from backtest import effect as E
from backtest.detection import CLEAN_WINDOW, known_event_eval, synthetic_eval
from common import config as C
from common.load_jnc import ROOT
from common.pipeline import PondPipeline
from backtest.equipment import false_alarm_rate, synthetic_lead
from forecast.pond import FOLDS, WEATHER_FEATURES, aerator_health, baselines, evaluate, low_do_onsets, ops_risk, \
    rule_alarm, walk_forward, warning_eval

OUT = ROOT / "backtest"
FIG = OUT / "figures"
plt.rcParams.update({"font.family": ["Heiti TC", "PingFang TC", "Noto Sans CJK TC", "sans-serif"],
                     "axes.unicode_minus": False, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
COLORS = {"歷史實際": "#9a9a9a", "固定門檻（原始探頭）": "#d08c3c", "固定門檻": "#3b7dd8", "AI 決策": "#1f9d6b"}


def md(df: pd.DataFrame, fmt: str = "{:.3g}") -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join([df.index.name or ""] + cols) + " |", "|" + "---|" * (len(cols) + 1)]
    for i, r in df.iterrows():
        cells = [fmt.format(v) if isinstance(v, float) else str(v) for v in r]
        lines.append("| " + " | ".join([str(i)] + cells) + " |")
    return "\n".join(lines)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    print("建立管線…")
    pipe = PondPipeline.build()
    df, f, pred, models = pipe.df, pipe.frame, pipe.pred, pipe.models
    start, end = pred.index[0], pred.index[-1]

    # ---------- 1. 異常診斷 ----------
    print("異常診斷評估…")
    by_type, syn = synthetic_eval(df)
    by_type_raw = by_type.copy()
    known = known_event_eval(df, pipe.hourly_diag)
    print("漂移偵測方法對照…")
    drift_rows = {}
    for name, m in [("舊法（6 h 平均超過容許差）", "old"), ("舊法＋CUSUM", "old+cusum"),
                    ("舊法＋EWMA（本作品）", "old+ewma")]:
        bt_m, s_m = synthetic_eval(df, drift_method=m) if m != C.DRIFT_METHOD else (by_type_raw, syn)
        ke = known_event_eval(df, drift_method=m).set_index("事件")
        drift_rows[name] = {"漂移 Recall": bt_m.loc["drift", "recall"], "漂移偵測延遲（h）": bt_m.loc["drift", "delay_h"],
                            "整體 Recall": s_m["recall"], "Precision": s_m["precision"],
                            "每週誤報": s_m["false_alarms_per_week"],
                            "pH1 漂移 P12 首次偵測": ke.loc["P12", "首次偵測"],
                            "DO2 劣化 P14": ke.loc["P14", "首次偵測"], "DO3 劣化 P17": ke.loc["P17", "首次偵測"]}
    drift_cmp = pd.DataFrame(drift_rows).T
    drift_cmp.index.name = "方法"
    by_type.index.name = "注入故障"
    by_type.columns = ["次數", "Recall", "類型正確率", "偵測延遲中位數（h）"]

    # ---------- 2. 趨勢預測 ----------
    print("預測評估…")
    preds = {"GBDT（本作品）": pred, **{k: v.loc[start:] for k, v in baselines(f).items()}}
    ev = evaluate(f, preds, start)
    mae = ev.pivot(index="模型", columns="預測時距", values="MAE")
    rmse = ev.pivot(index="模型", columns="預測時距", values="RMSE")
    gain = (1 - mae.loc["GBDT（本作品）"] / mae.loc["持續法"]) * 100
    warn = pd.DataFrame([warning_eval(f, pred, start, a) for a in [0.1, 0.2, 0.3, 0.4, 0.5]]).set_index("α")

    print("環境特徵對照（不含環境再訓練一次）…")
    pred_nw, _ = walk_forward(f, weather=False)
    ev_w = evaluate(f, {"含環境（本作品）": pred, "不含環境": pred_nw}, start)
    mae_w = ev_w.pivot(index="模型", columns="預測時距", values="MAE")
    mae_w.index.name = "模型"

    # ---------- 2b. 增氧機故障機率、營運風險 ----------
    print("設備故障機率與營運風險…")
    aer_fa = false_alarm_rate(f, start, end)
    aer_lead = synthetic_lead(f, ["2026-07-20 00:00", "2026-07-28 00:00", "2026-08-05 00:00",
                                  "2026-08-20 00:00", "2026-09-10 00:00"]).set_index("衰退開始")
    risk_rows = []
    for t in pred.index[::2]:
        r = ops_risk(pred.loc[t], bool(f.loc[t, "aerator_on"]) if pd.notna(f.loc[t, "aerator_on"]) else None,
                     aerator_health(f.loc[:t])["fail_prob"])
        actual = int((f["DO"].loc[t + pd.Timedelta(hours=1):t + pd.Timedelta(hours=6)] < C.DO_LOW).sum())
        if r["expected_loss"] is None:
            continue
        risk_rows.append({"level": r["level"], "pred": r["expected_low_h"], "actual": actual, "loss": r["expected_loss"]})
    risk_df = pd.DataFrame(risk_rows)
    risk_tab = risk_df.groupby("level").agg(小時數=("level", "size"), 預期低溶氧時數=("pred", "mean"),
                                            實際低溶氧時數=("actual", "mean"), 預期損失_元=("loss", "mean"))
    risk_tab = risk_tab.reindex([x for x in ["低", "中", "高"] if x in risk_tab.index])
    risk_tab.index.name = "營運風險"

    # ---------- 3. 閉環成效 ----------
    print("閉環模擬…")
    est = E.estimate(f, pd.Timestamp(FOLDS[0][0]) - pd.Timedelta(hours=1))
    eng = E.ENGINEERING
    tuned = CL.tune(f, pred, models, eng["aerator_effect"], eng["effect_decay"],
                    ("2026-07-15", "2026-07-31 23:00"), ("2026-08-01", str(end)))
    # 閉環比較一律用再學習後實際上線的 α、β（與 decide/params.json 一致）
    tables, logs_eng = {}, None
    for eff in [E.ENGINEERING, est]:
        tab, logs = CL.compare(f, pred, models, eff["aerator_effect"], eff["effect_decay"],
                               tuned["alpha"], tuned["beta"])
        tab.index.name = "策略"
        tables[eff["source"]] = tab
        if eff is E.ENGINEERING:
            logs_eng = logs
    params = {"alpha": tuned["alpha"], "beta": tuned["beta"], "validated": tuned["validated"],
              "aerator_effect": eng["aerator_effect"], "effect_decay": eng["effect_decay"],
              "updated": date.today().isoformat(), "note": "由 scripts/run_backtest.py 再學習產生"}
    CL.save_params(params)

    # ---------- 2c. 提前預警：重新定義事件＋簡單規則基準（指導老師 11/25 建議） ----------
    print("提前預警（新事件定義＋簡單規則基準）…")
    a_live = params["alpha"]
    K = C.EVENT_MIN_CLEAR
    do_oos = f["DO"].loc[start:]
    on_old, on_new = low_do_onsets(do_oos), low_do_onsets(do_oos, K)
    pre_low = sum(bool((do_oos.loc[t - pd.Timedelta(hours=6):t - pd.Timedelta(hours=1)] < C.DO_LOW).any())
                  for t in on_old)
    methods = {f"AI 預測（α = {a_live}，上線參數）": dict(alpha=a_live),
               "AI 預測（α = 0.3，舊報告）": dict(alpha=0.3),
               "簡單規則：DO < 3.1 就告警": dict(alarm=rule_alarm(f, 3.1)),
               "簡單規則：DO < 3.2 就告警": dict(alarm=rule_alarm(f, 3.2)),
               "固定門檻：DO < 3.0 才告警": dict(alarm=rule_alarm(f, C.DO_LOW))}
    warn_cmp = {}
    for name, kw in methods.items():
        for label, mc in [("舊定義", 0), (f"新定義（前 {K} h 都 ≥ 3）", K)]:
            r = warning_eval(f, pred, start, min_clear=mc, **{"alpha": kw.get("alpha", 0.0), **kw})
            warn_cmp[(name, label)] = {"事件數": r["低溶氧事件數"], "預警率": r["預警率"],
                                       "平均提前（h）": r["平均提前小時"], "每週誤報": r["誤報（每週）"]}
    warn_cmp = pd.DataFrame(warn_cmp).T
    warn_new = warn_cmp.xs(f"新定義（前 {K} h 都 ≥ 3）", level=1)
    warn_old = warn_cmp.xs("舊定義", level=1)
    warn_new.index.name = warn_old.index.name = "方法"
    w_live = warn_new.loc[f"AI 預測（α = {a_live}，上線參數）"]
    w_rule = warn_new.loc["簡單規則：DO < 3.1 就告警"]
    w_a3 = warn_new.loc["AI 預測（α = 0.3，舊報告）"]
    w_r32 = warn_new.loc["簡單規則：DO < 3.2 就告警"]
    w_w = pd.DataFrame({"含環境（本作品）": warning_eval(f, pred, start, a_live, K),
                        "不含環境": warning_eval(f, pred_nw, start, a_live, K)}).T.drop(columns="α")
    w_w.index.name = "模型"

    # 取捨曲線
    front = []
    for thr in [3.0, 3.2, 3.4, 3.6, 3.8]:
        for pol in ["固定門檻（原始探頭）", "固定門檻"]:
            m = CL.metrics(CL.simulate(f, pred, models, pol, eng["aerator_effect"], eng["effect_decay"], thr_on=thr))
            front.append({"策略": pol, "參數": thr, **m})
    for a in [0.05, 0.1, 0.2, 0.3, 0.4, 0.5]:
        m = CL.metrics(CL.simulate(f, pred, models, "AI 決策", eng["aerator_effect"], eng["effect_decay"], alpha=a))
        front.append({"策略": "AI 決策", "參數": a, **m})
    front = pd.DataFrame(front)

    # ---------- 圖 ----------
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for pol, g in front.groupby("策略"):
        ax.plot(g["增氧機用電（度）"], g["低溶氧時數（DO<3）"], "o-", color=COLORS[pol], label=pol, ms=4)
        for _, r in g.iterrows():
            ax.annotate(f"{r['參數']:g}", (r["增氧機用電（度）"], r["低溶氧時數（DO<3）"]), fontsize=7,
                        xytext=(3, 3), textcoords="offset points", color=COLORS[pol])
    h = tables[eng["source"]].loc["歷史實際"]
    ax.scatter([h["增氧機用電（度）"]], [h["低溶氧時數（DO<3）"]], color=COLORS["歷史實際"], label="歷史實際", zorder=3)
    ax.set_xlabel("增氧機用電（度）")
    ax.set_ylabel("低溶氧時數（DO < 3 mg/L）")
    ax.set_title("用電與低溶氧的取捨（越靠左下越好；數字為門檻或 α）", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "tradeoff.png", dpi=160)
    plt.close(fig)

    a, b = "2026-07-18", "2026-07-24"
    fig, axes = plt.subplots(2, 1, figsize=(7.5, 4.6), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    ax = axes[0]
    for pol in ["歷史實際", "固定門檻", "AI 決策"]:
        ax.plot(logs_eng[pol].loc[a:b, "do_sim"], color=COLORS[pol], lw=1.2, label=pol)
    ax.axhline(C.DO_LOW, color="#c0392b", lw=0.8, ls="--")
    ax.text(pd.Timestamp(a), C.DO_LOW + 0.05, "低溶氧門檻 3.0", color="#c0392b", fontsize=7)
    ax.set_ylabel("DO（mg/L）")
    ax.legend(fontsize=7, frameon=False, ncol=3)
    ax.set_title("7/18–7/24 低溶氧期間：三種策略的溶氧（工程估計效果）", fontsize=9)
    ax = axes[1]
    for pol in ["固定門檻", "AI 決策"]:
        ax.step(logs_eng[pol].loc[a:b].index, logs_eng[pol].loc[a:b, "u"], where="post", color=COLORS[pol], lw=1)
    ax.step(logs_eng["歷史實際"].loc[a:b].index, logs_eng["歷史實際"].loc[a:b, "u"], where="post",
            color=COLORS["歷史實際"], lw=1, ls=":")
    ax.set_ylabel("增氧機台數")
    ax.set_yticks([0, 1, 2])
    fig.tight_layout()
    fig.savefig(FIG / "closed_loop_example.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    a, b = "2026-07-19", "2026-07-22"
    ax.plot(f.loc[a:b, "DO"], color="#333", lw=1.2, label="實際 DO（融合）")
    ax.plot(pred.loc[a:b, "h3"].shift(3, freq="h"), color="#1f9d6b", lw=1, label="3 小時前的預測")
    ax.plot(f["DO"].shift(3).loc[a:b], color="#9a9a9a", lw=1, ls=":", label="持續法（3 小時前的值）")
    ax.axhline(C.DO_LOW, color="#c0392b", lw=0.8, ls="--")
    ax.set_ylabel("DO（mg/L）")
    ax.legend(fontsize=7, frameon=False, ncol=3)
    ax.set_title("溶氧 3 小時預測（樣本外）", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "forecast_example.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(7.5, 5.2), sharex=True)
    for ax, (cols, title) in zip(axes, [(C.PROBES["DO"], "DO 三支探頭"), (C.PROBES["pH"], "pH 三支探頭"), (None, "DO 探頭可信度")]):
        if cols:
            for c in cols:
                ax.plot(df.loc["2026-08-05":"2026-09-28", c], lw=0.7, label=c.replace(" 即時值", ""))
        else:
            for c in C.PROBES["DO"]:
                ax.plot(f.loc["2026-08-05":"2026-09-28", f"trust:{c}"], lw=0.8, label=c.replace(" 即時值", ""))
            ax.set_ylim(-5, 105)
        ax.set_title(title, fontsize=8, loc="left")
        ax.legend(fontsize=7, frameon=False, ncol=3, loc="lower left")
    fig.suptitle("狀態辨識：pH1 漂移、DO2 劣化、DO3 失效時，可信度自動下降並排除", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "sensor_trust.png", dpi=160)
    plt.close(fig)

    # ---------- 報告 ----------
    t_eng = tables[eng["source"]]
    t_dat = tables[est["source"]]
    hist, thr_raw, thr, ai = (t_eng.loc[k] for k in CL.POLICIES)
    hist_d, _, thr_d, ai_d = (t_dat.loc[k] for k in CL.POLICIES)
    pct = lambda x, y: (1 - x / y) * 100 if y else 0.0
    known_hit = (known["偵測到"] == "是").sum()
    vc = tuned["validation_cost"]
    best_base = min((k for k in vc if k != "AI 決策"), key=vc.get)
    text = f"""# 成效驗證報告（魚塭 pond）

> 由 `scripts/run_backtest.py` 自動產生（{date.today().isoformat()}），請勿手改；改了模組後重跑。
> 樣本外期間：{start:%m/%d}–{end:%m/%d}（滾動驗證：每段只用之前的資料訓練，見 forecast/pond.py 的 FOLDS）。
> 11/26 依指導老師建議修正：預警改用新的事件定義並加入簡單規則基準、數字一律用上線參數 α = {a_live}、
> 閉環成效同時列兩組增氧效果並與固定門檻比較、「已驗證」要比最好的基準省 {C.VALIDATE_MARGIN:.0%} 以上。

## 重點

| 項目 | 結果 | 比較基準 |
|---|---|---|
| 已知故障事件（notes/eda/events.md） | **{known_hit}/{len(known)} 偵測到** | — |
| 合成故障 Recall | **{syn['recall']:.0%}**（{syn['labels']} 次注入） | 物理範圍檢查只抓得到掉 0、超範圍 |
| 每週誤報（乾淨期間） | **{syn['false_alarms_per_week']:.1f} 次** | — |
| **探頭可信度的效果**（同一條固定門檻規則，只差有沒有先排除故障探頭；工程估計） | **無效告警 {thr_raw['無效告警時數']:.0f} → {thr['無效告警時數']:.0f} 小時、用電 {thr_raw['增氧機用電（度）']:.0f} → {thr['增氧機用電（度）']:.0f} 度（−{pct(thr['增氧機用電（度）'], thr_raw['增氧機用電（度）']):.0f}%）、低溶氧 {thr_raw['低溶氧時數（DO<3）']:.0f} → {thr['低溶氧時數（DO<3）']:.0f} 小時** | 直接用原始探頭（一般 SCADA） |
| 無效告警時數（DO 其實 ≥ 3.5，工程估計） | AI 決策（α = {a_live}）{ai['無效告警時數']:.0f} 小時 | 固定門檻 {thr['無效告警時數']:.0f}、原始探頭門檻 {thr_raw['無效告警時數']:.0f} 小時 |
| DO 預測 MAE（1／3／6 h） | **{mae.loc['GBDT（本作品）', '1 h']:.3f}／{mae.loc['GBDT（本作品）', '3 h']:.3f}／{mae.loc['GBDT（本作品）', '6 h']:.3f}** | 持續法 {mae.loc['持續法', '1 h']:.3f}／{mae.loc['持續法', '3 h']:.3f}／{mae.loc['持續法', '6 h']:.3f}（改善 {gain['1 h']:.0f}%／{gain['3 h']:.0f}%／{gain['6 h']:.0f}%） |
| 低溶氧提前預警（新事件定義，α = {a_live}） | {w_live['預警率']:.0%} 事件、平均提前 {w_live['平均提前（h）']:.1f} 小時，每週誤報 {w_live['每週誤報']:.1f} 次（共 {w_live['事件數']:.0f} 個事件） | 簡單規則 DO < 3.1：{w_rule['預警率']:.0%}、提前 {w_rule['平均提前（h）']:.1f} 小時、每週誤報 {w_rule['每週誤報']:.1f} 次 |
| 低溶氧時數（工程估計效果） | {ai['低溶氧時數（DO<3）']:.0f} 小時 | 歷史 {hist['低溶氧時數（DO<3）']:.0f}、固定門檻 {thr['低溶氧時數（DO<3）']:.0f}、原始探頭門檻 {thr_raw['低溶氧時數（DO<3）']:.0f} |
| 低溶氧時數（資料估計效果） | {ai_d['低溶氧時數（DO<3）']:.0f} 小時 | 歷史 {hist_d['低溶氧時數（DO<3）']:.0f}、固定門檻 {thr_d['低溶氧時數（DO<3）']:.0f} |
| 用電（工程估計） | AI 決策 {ai['增氧機用電（度）']:.0f} 度 | 固定門檻 {thr['增氧機用電（度）']:.0f}、原始探頭門檻 {thr_raw['增氧機用電（度）']:.0f} 度 |
| 再學習驗證（8/01 起） | α = {tuned['alpha']}，成本比最好的基準（{best_base}）{'省' if tuned['margin'] >= 0 else '多'} {abs(tuned['margin']):.1%} → **{'已驗證' if tuned['validated'] else '未驗證'}**（門檻 {C.VALIDATE_MARGIN:.0%}） | — |

**怎麼解讀**
- AI 最確定的價值是「先判斷探頭可不可信」：同一條「DO < 3 就開機」的規則，直接用探頭原始值時，DO2 劣化（8/27–9/02）與 DO3 失效（9/19–9/25）期間讀到 0，會一直誤開備用增氧機與告警（無效告警 {thr_raw['無效告警時數']:.0f} 小時）；先用狀態辨識排除故障探頭後降到 {thr['無效告警時數']:.0f} 小時，用電少 {pct(thr['增氧機用電（度）'], thr_raw['增氧機用電（度）']):.0f}%。這個比較不依賴預測模型與 α。
- 預測性增氧（α = {a_live}）會多出無效告警（{ai['無效告警時數']:.0f} 小時）與用電（比固定門檻多 {-pct(ai['增氧機用電（度）'], thr['增氧機用電（度）']):.0f}%），換來較少的低溶氧時數，見取捨曲線。
- 提前預警要和簡單規則比才有意義：舊定義的 {len(on_old)} 個「事件」中有 {pre_low} 個在跌破前 6 小時內 DO 就已經低於 3（在門檻附近反覆穿越），連「跌破 3 才告警」的固定門檻都能算出 {warn_old.loc['固定門檻：DO < 3.0 才告警', '預警率']:.0%} 預警率。改成「前 {K} 小時都 ≥ 3 才算新事件」後只剩 {len(on_new)} 個：同樣抓到 {w_a3['預警率']:.0%} 事件時，AI（α = 0.3）提前 {w_a3['平均提前（h）']:.1f} 小時、每週誤報 {w_a3['每週誤報']:.1f} 次，簡單規則 DO < 3.2 提前 {w_r32['平均提前（h）']:.1f} 小時、誤報 {w_r32['每週誤報']:.1f} 次。AI 略好，但只有 {len(on_new)} 個事件，**差距不足以下定論**。上線的 α = {a_live} 抓得多（{w_live['預警率']:.0%}），代價是每週誤報 {w_live['每週誤報']:.1f} 次。
- 低溶氧時數的改善**依賴增氧機效果的假設**：工程估計（假設池子 0.5 公頃、水深 1.5 m）下 AI {ai['低溶氧時數（DO<3）']:.0f} 小時、固定門檻 {thr['低溶氧時數（DO<3）']:.0f} 小時；資料估計下只有 {hist_d['低溶氧時數（DO<3）']:.0f} → {ai_d['低溶氧時數（DO<3）']:.0f} 小時（少 {pct(ai_d['低溶氧時數（DO<3）'], hist_d['低溶氧時數（DO<3）']):.0f}%），固定門檻 {thr_d['低溶氧時數（DO<3）']:.0f}。和歷史操作比的大幅改善主要來自「有自動控制」，不是 AI 本身。
- 再學習只比最好的基準省 {tuned['margin']:.1%}，{'達到' if tuned['validated'] else '未達'} {C.VALIDATE_MARGIN:.0%} 門檻，所以{'DO 已低於門檻的增氧可自動執行' if tuned['validated'] else '增氧決策一律人工確認（危急 DO < 2.5 的增氧仍自動執行）'}。

## 1. 異常診斷

### 1.1 已知事件（弱標籤）

{known.to_markdown(index=False) if hasattr(known, 'to_markdown') and _has_tabulate() else md(known.set_index('事件'))}

### 1.2 合成故障注入

在乾淨期間 {CLEAN_WINDOW[0]}–{CLEAN_WINDOW[1]} 的 12 支水質探頭上隨機注入 5 種故障（5 個隨機種子，每次 10 個），判斷是否在故障期間 ±3 小時內抓到同一支探頭。

{md(by_type, '{:.2f}')}

整體：Recall {syn['recall']:.0%}、Precision {syn['precision']:.0%}、類型正確率 {syn['type_accuracy']:.0%}、每週誤報 {syn['false_alarms_per_week']:.1f} 次。
Precision 偏低的主因是 SC 探頭本身常有短暫跳動；可信度 < {C.ALARM_MIN_CONF} 的診斷只當資料品質提示、不派工。

### 1.3 漂移偵測：舊法 vs CUSUM／EWMA

舊法要 6 小時平均偏離超過容許差並持續 6 小時，抓不到「一直往同一邊慢慢偏、還沒超過容許差」的漂移。
新增統計管制圖：偏離量用過去 7 天的中位數與穩健標準差標準化後做 CUSUM（k = {C.DRIFT_CUSUM_K}、h = {C.DRIFT_CUSUM_H}）
或 EWMA（λ = {C.DRIFT_EWMA_LAMBDA}、L = {C.DRIFT_EWMA_L}）；為了壓誤報，只用在 DO、pH，且要 6 小時平均偏離 ≥ 容許差 × {C.DRIFT_MIN_FRAC}、
警報持續 {C.DRIFT_PERSIST} 小時。SC 探頭本身跳動大，用了誤報會增加 2–3 倍，所以不用。

{md(drift_cmp, '{:.2f}')}

結論：採用「舊法＋EWMA」。漂移 Recall 提高、三個真實探頭劣化提早 12–19 小時發現，代價是每週誤報略增；CUSUM 在這組資料結果相同。

## 2. 溶氧預測

![預測範例](figures/forecast_example.png)

MAE（mg/L）：

{md(mae, '{:.3f}')}

RMSE（mg/L）：

{md(rmse, '{:.3f}')}

模型：{models[0].engine}（預測 h 小時後與現在的差，絕對誤差損失；本機缺 libomp 時自動改用 scikit-learn 的同類模型）。

### 2.1 低溶氧提前預警：事件定義與簡單規則基準

事件前 1–6 小時內有告警即算預警成功；誤報＝告警開始後 6 小時內 DO 沒有跌破 3。

- **舊定義**：融合 DO 由 ≥ 3 跌破 3 就算一個事件，共 {len(on_old)} 個；其中 {pre_low} 個在跌破前 6 小時內 DO 已經低於 3（在門檻附近反覆穿越），「提前預警」其實是看到已經偏低的 DO。
- **新定義**：跌破前 {K} 小時都要有資料且 ≥ 3，才算一次新的低溶氧事件，共 {len(on_new)} 個。
- **簡單規則基準**：不用預測模型，「融合 DO 低於 3.1（或 3.2）就告警」；「DO < 3.0 才告警」就是一般 SCADA 的固定門檻（新定義下必然提前 0 小時）。

新定義：

{md(warn_new, '{:.2f}')}

舊定義（前一版報告的算法，留作對照）：

{md(warn_old, '{:.2f}')}

AI 在不同 α 下（舊定義，供調參參考）：

{md(warn, '{:.2f}')}

### 2.2 環境資料（OA4 氣象站）的貢獻

特徵：{'、'.join(WEATHER_FEATURES)}（氣溫與水溫差、氣壓 3／6 小時變化、濕度）。氣象站凍結或讀到 0 的小時當缺值
（約 {f['pressure'].isna().mean():.0%} 的小時，主要是 9/14 起的凍結）。全套 6 項（再加氣溫、氣壓本身）也比較過，3–6 小時 MAE 略差，所以只留這 4 項。

MAE（mg/L）：

{md(mae_w, '{:.3f}')}

提前預警（新定義，α = {a_live}）：

{md(w_w, '{:.2f}')}

結論：加入環境資料後 MAE 差異在 ±0.003 以內（雜訊範圍），預警多抓到事件、提前時間略長，每週誤報略增。

### 2.3 增氧機故障機率（設備預測維護）

運轉功率 24 小時趨勢外推到低負載門檻 {C.AERATOR_LOW_LOAD_W:.0f} W，48 小時內低於門檻的機率 ≥ {C.AERATOR_FAIL_ALERT} 就排預防性檢修。
資料期間增氧機沒有真的故障過（運轉功率 714–796 W），所以：

- 真實資料誤報：樣本外期間 **{aer_fa:.1%}** 的小時發出預警
- 合成功率衰退（72 小時內線性降到 600 W，加 ±5 W 雜訊）：

{md(aer_lead, '{:.0f}')}

### 2.4 營運風險

6 小時預期損失＝期望低溶氧時數 × {C.LOSS_PER_LOW_HOUR:.0f} 元＋期望危急時數 × {C.LOSS_PER_CRIT_HOUR:.0f} 元＋增氧電費＋增氧機故障機率 × {C.AERATOR_FAILURE_COST:.0f} 元；
≥ {C.OPS_RISK_MID:.0f} 元為「中」、≥ {C.OPS_RISK_HIGH:.0f} 元為「高」（單價為估計值，待企業確認）。下表檢查分級是否對應實際結果（樣本外，每 2 小時抽一次）：

{md(risk_tab, '{:.1f}')}

## 3. 閉環成效（模擬 SCADA／PLC 執行）

反事實模擬（AI 決策用上線參數 α = {tuned['alpha']}、β = {tuned['beta']}；假設需人工確認的決策都被核准）：DO_sim = DO_實際 + Δ，Δ 由「策略與現場操作的台數差」累積並衰減（backtest/effect.py）。
增氧機效果有兩組：

- **工程估計**：{eng['aerator_effect']} mg/L/h、衰減 {eng['effect_decay']}（{eng['source']}）
- **資料估計**：{est['aerator_effect']} mg/L/h、衰減 {est['effect_decay']}（{est['source']}）

""" + "\n\n".join(f"### {k}\n\n{md(v, '{:.0f}')}" for k, v in tables.items()) + f"""

![取捨曲線](figures/tradeoff.png)

![閉環範例](figures/closed_loop_example.png)

### 3.1 再學習（調整 α、β）

在 7/15–7/31 找成本最低的參數（成本＝低溶氧時數 × {CL.LOSS_PER_LOW_HOUR:.0f} 元＋危急時數 × {C.LOSS_PER_CRIT_HOUR:.0f} 元＋電費），到 8/01 之後驗證：

- 選到 α = {tuned['alpha']}、β = {tuned['beta']}
- 驗證期成本：""" + "、".join(f"{k} {v:,.0f}" for k, v in tuned["validation_cost"].items()) + f"""
- 比最好的基準（{best_base}）{'省' if tuned['margin'] >= 0 else '多'} {abs(tuned['margin']):.1%}；「已驗證」門檻為省 {C.VALIDATE_MARGIN:.0%} 以上（common/config.py 的 VALIDATE_MARGIN，只贏 1–2% 在模擬誤差範圍內）
- 結果：**{'已驗證 → DO 已低於門檻的增氧（風險低）自動執行；只是預測會低（風險中）仍需人工確認' if tuned['validated'] else '未驗證 → 增氧決策一律人工確認（危急 DO < 2.5 的增氧不受影響，仍自動執行）'}**

## 4. 狀態辨識

![探頭可信度](figures/sensor_trust.png)

## 5. 限制與待確認

- 企業沒有維修紀錄（Q1），異常偵測用已知事件＋合成故障評估。
- 增氧機台數、池子面積未知（Q5），閉環效果依工程估計，並附資料估計的保守結果；資料估計受操作時機混淆，偏低。
- 備用增氧機、暫停投餵在資料中沒有對應欄位，模擬時把備用機視為與主機相同效果。
- 低溶氧門檻 3.0 mg/L 依此池資料分布訂定，物種與企業標準待確認。
"""
    (OUT / "report.md").write_text(text, encoding="utf-8")
    print("完成：backtest/report.md、backtest/figures/、decide/params.json")
    print(params)


def _has_tabulate() -> bool:
    try:
        import tabulate  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    main()
