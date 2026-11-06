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
from forecast.pond import FOLDS, baselines, evaluate, warning_eval

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
    known = known_event_eval(df, pipe.hourly_diag)
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

    # ---------- 3. 閉環成效 ----------
    print("閉環模擬…")
    est = E.estimate(f, pd.Timestamp(FOLDS[0][0]) - pd.Timedelta(hours=1))
    tables, logs_eng = {}, None
    for eff in [E.ENGINEERING, est]:
        tab, logs = CL.compare(f, pred, models, eff["aerator_effect"], eff["effect_decay"])
        tab.index.name = "策略"
        tables[eff["source"]] = tab
        if eff is E.ENGINEERING:
            logs_eng = logs
    eng = E.ENGINEERING
    tuned = CL.tune(f, pred, models, eng["aerator_effect"], eng["effect_decay"],
                    ("2026-07-15", "2026-07-31 23:00"), ("2026-08-01", str(end)))
    params = {"alpha": tuned["alpha"], "beta": tuned["beta"], "validated": tuned["validated"],
              "aerator_effect": eng["aerator_effect"], "effect_decay": eng["effect_decay"],
              "updated": date.today().isoformat(), "note": "由 scripts/run_backtest.py 再學習產生"}
    CL.save_params(params)

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
    hist, thr_raw, thr, ai = (t_eng.loc[k] for k in CL.POLICIES)
    pct = lambda x, y: (1 - x / y) * 100 if y else 0.0
    w3 = warn.loc[0.3]
    known_hit = (known["偵測到"] == "是").sum()
    text = f"""# 成效驗證報告（魚塭 pond）

> 由 `scripts/run_backtest.py` 自動產生（{date.today().isoformat()}），請勿手改；改了模組後重跑。
> 樣本外期間：{start:%m/%d}–{end:%m/%d}（滾動驗證：每段只用之前的資料訓練，見 forecast/pond.py 的 FOLDS）。

## 重點

| 項目 | 結果 | 比較基準 |
|---|---|---|
| 已知故障事件（notes/eda/events.md） | **{known_hit}/{len(known)} 偵測到** | — |
| 合成故障 Recall | **{syn['recall']:.0%}**（{syn['labels']} 次注入） | 物理範圍檢查只抓得到掉 0、超範圍 |
| 每週誤報（乾淨期間） | **{syn['false_alarms_per_week']:.1f} 次** | — |
| DO 預測 MAE（1／3／6 h） | **{mae.loc['GBDT（本作品）', '1 h']:.3f}／{mae.loc['GBDT（本作品）', '3 h']:.3f}／{mae.loc['GBDT（本作品）', '6 h']:.3f}** | 持續法 {mae.loc['持續法', '1 h']:.3f}／{mae.loc['持續法', '3 h']:.3f}／{mae.loc['持續法', '6 h']:.3f}（改善 {gain['1 h']:.0f}%／{gain['3 h']:.0f}%／{gain['6 h']:.0f}%） |
| 低溶氧提前預警（α = 0.3） | **{w3['預警率']:.0%} 事件、平均提前 {w3['平均提前小時']:.1f} 小時**，每週誤報 {w3['誤報（每週）']:.1f} 次 | 固定門檻：跌破才告警（提前 0 小時） |
| 低溶氧時數（工程估計效果） | **{ai['低溶氧時數（DO<3）']:.0f} 小時**（比歷史少 {pct(ai['低溶氧時數（DO<3）'], hist['低溶氧時數（DO<3）']):.0f}%） | 歷史 {hist['低溶氧時數（DO<3）']:.0f}、固定門檻 {thr['低溶氧時數（DO<3）']:.0f}、原始探頭門檻 {thr_raw['低溶氧時數（DO<3）']:.0f} |
| 危急時數（DO < 2.5） | **{ai['危急時數（DO<2.5）']:.0f} 小時**（比歷史少 {pct(ai['危急時數（DO<2.5）'], hist['危急時數（DO<2.5）']):.0f}%） | 歷史 {hist['危急時數（DO<2.5）']:.0f} |
| 用電 | **{ai['增氧機用電（度）']:.0f} 度** | 原始探頭門檻 {thr_raw['增氧機用電（度）']:.0f} 度（AI 省 {pct(ai['增氧機用電（度）'], thr_raw['增氧機用電（度）']):.0f}%） |
| 無效告警時數（DO 其實 ≥ 3.5） | **{ai['無效告警時數']:.0f} 小時** | 原始探頭門檻 {thr_raw['無效告警時數']:.0f} 小時 |

**怎麼解讀**
- AI 最大的價值是「先判斷探頭可不可信」：一般 SCADA 直接用探頭原始值，DO2 劣化（8/27–9/02）與 DO3 失效（9/19–9/25）期間讀到 0，會一直誤開備用增氧機與告警；AI 自動排除故障探頭並派工維修。
- 預測讓告警提早約 {w3['平均提前小時']:.0f} 小時，現場有時間調整投餵或準備備用機。
- 在同樣用電量下，AI 比調好的固定門檻只略好（見取捨曲線）：這個池子的低溶氧是長時間緩慢發生，增氧機全開也無法完全避免。**不誇大這一點**。

## 1. 異常診斷

### 1.1 已知事件（弱標籤）

{known.to_markdown(index=False) if hasattr(known, 'to_markdown') and _has_tabulate() else md(known.set_index('事件'))}

### 1.2 合成故障注入

在乾淨期間 {CLEAN_WINDOW[0]}–{CLEAN_WINDOW[1]} 的 12 支水質探頭上隨機注入 5 種故障（5 個隨機種子，每次 10 個），判斷是否在故障期間 ±3 小時內抓到同一支探頭。

{md(by_type, '{:.2f}')}

整體：Recall {syn['recall']:.0%}、Precision {syn['precision']:.0%}、類型正確率 {syn['type_accuracy']:.0%}、每週誤報 {syn['false_alarms_per_week']:.1f} 次。
Precision 偏低的主因是 SC 探頭本身常有短暫跳動；可信度 < {C.ALARM_MIN_CONF} 的診斷只當資料品質提示、不派工。

## 2. 溶氧預測

![預測範例](figures/forecast_example.png)

MAE（mg/L）：

{md(mae, '{:.3f}')}

RMSE（mg/L）：

{md(rmse, '{:.3f}')}

模型：{models[0].engine}（預測 h 小時後與現在的差，絕對誤差損失；本機缺 libomp 時自動改用 scikit-learn 的同類模型）。

低溶氧提前預警（事件＝融合 DO 由 ≥ 3 跌破 3；事件前 1–6 小時內機率 > α 即算預警）：

{md(warn, '{:.2f}')}

## 3. 閉環成效（模擬 SCADA／PLC 執行）

反事實模擬（假設需人工確認的決策都被核准）：DO_sim = DO_實際 + Δ，Δ 由「策略與現場操作的台數差」累積並衰減（backtest/effect.py）。
增氧機效果有兩組：

- **工程估計**：{eng['aerator_effect']} mg/L/h、衰減 {eng['effect_decay']}（{eng['source']}）
- **資料估計**：{est['aerator_effect']} mg/L/h、衰減 {est['effect_decay']}（{est['source']}）

""" + "\n\n".join(f"### {k}\n\n{md(v, '{:.0f}')}" for k, v in tables.items()) + f"""

![取捨曲線](figures/tradeoff.png)

![閉環範例](figures/closed_loop_example.png)

### 3.1 再學習（調整 α、β）

在 7/15–7/31 找成本最低的參數（成本＝低溶氧時數 × {CL.LOSS_PER_LOW_HOUR:.0f} 元＋危急時數 × {3 * CL.LOSS_PER_LOW_HOUR:.0f} 元＋電費），到 8/01 之後驗證：

- 選到 α = {tuned['alpha']}、β = {tuned['beta']}
- 驗證期成本：""" + "、".join(f"{k} {v:,.0f}" for k, v in tuned["validation_cost"].items()) + f"""
- 是否優於所有基準：**{'是 → decide/params.json 設為 validated：DO 已低於門檻的增氧（風險低）自動執行；只是預測會低（風險中）仍需人工確認' if tuned['validated'] else '否 → 增氧決策一律人工確認'}**

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
