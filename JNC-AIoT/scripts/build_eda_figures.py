"""產生 notes/eda/<site>/ 的資料初探圖（S09）。

用法：python scripts/build_eda_figures.py
每個場域畫兩張圖：
  timeseries.png  重點欄位的時間序列（小倍數，每欄一格），灰底標出已知的異常或斷線期間
  diurnal.png     各欄位的 24 小時中位數曲線（看日夜週期）
異常期間是讀資料後人工判讀的結果，說明寫在 notes/eda/<site>.md。
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common.load_jnc import hourly, load  # noqa: E402

OUT = ROOT / "notes" / "eda"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # 類別色固定順序：探頭 1、2、3
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": ["Heiti TC", "PingFang TC", "Noto Sans CJK TC", "sans-serif"],
    "axes.unicode_minus": False, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "font.size": 9,
})

# 每格：(標題, [欄位...])；一格多欄時代表同一物理量的多個探頭
# spans：(開始, 結束, 標籤)，灰底標示
CONFIG: dict[str, dict] = {
    "pond": {
        "panels": [
            ("溶氧 DO（mg/L）", ["DO1 即時值", "DO2 即時值", "DO3 即時值"]),
            ("pH", ["pH1 即時值", "pH2 即時值", "pH3 即時值"]),
            ("導電度 SC", ["SC1 即時值", "SC2 即時值", "SC3 即時值"]),
            ("ORP（mV）", ["ORP1 即時值", "ORP2 即時值", "ORP3 即時值"]),
            ("水溫（°C）", ["DO1水溫"]),
            ("系統總和功率（W）", ["CPM 系統總和功率"]),
            ("微氣候溫度 OA4（°C）", ["OA4 溫度"]),
            ("水位高度", ["水位高度"]),
        ],
        "spans": [
            ("2026-06-01", "2026-06-06 11:00", "微氣候／水位未啟用"),
            ("2026-06-23 09:00", "2026-07-01 15:00", "主機斷線"),
            ("2026-08-17 12:00", "2026-09-02 11:00", "pH1 漂移"),
            ("2026-09-14 01:00", "2026-09-28 21:00", "OA4 凍結"),
            ("2026-09-19 12:00", "2026-09-25 11:00", "DO3 歸零"),
        ],
        "diurnal": ["DO1 即時值", "DO2 即時值", "DO3 即時值", "DO1水溫", "CPM 系統總和功率", "OA4 溫度"],
    },
    "river": {
        "panels": [
            ("溶氧 DO（mg/L）", ["DO"]), ("DO 飽和度（%）", ["DO飽和度"]), ("pH", ["pH"]),
            ("導電度 EC", ["EC"]), ("水溫（°C）", ["水溫"]), ("電池電量（%）", ["電池電量"]),
            ("DO 斜率（校正係數）", ["DO斜率"]),
        ],
        "spans": [
            ("2026-01-22 16:00", "2026-01-22 17:00", "斜率重設"),
            ("2026-02-11", "2026-03-23 19:00", "DO 斜率反覆切換"),
            ("2026-04-17 12:00", "2026-05-01", "EC 平線／電池下滑"),
        ],
        "diurnal": ["DO", "pH", "EC", "水溫", "太陽能電壓", "電池電量"],
    },
    "goat": {
        "panels": [
            ("成羊區 THI", ["成羊區THI"]), ("仔羊區 THI", ["仔羊區THI"]),
            ("成羊區平均溫度（°C）", ["成羊區平均溫度"]), ("成羊區平均濕度（%）", ["成羊區平均濕度"]),
            ("成羊區平均 CO2（ppm）", ["成羊區平均CO2"]), ("南右帆布張（狀態碼）", ["南右帆布張 23/24"]),
            ("風扇-07（狀態碼）", ["風扇-07"]), ("1 小時雨量（mm）", ["1小時雨量"]),
        ],
        "spans": [("2026-07-30 11:00", "2026-07-31 15:00", "狀態碼 2／4")],
        "diurnal": ["成羊區THI", "仔羊區THI", "成羊區平均溫度", "成羊區平均濕度", "成羊區平均CO2", "ID4-CO2"],
        "thi": True,
    },
    "yucheng_north": {
        "panels": [
            ("溫度（°C）", ["溫度"]), ("PM2.5（μg/m³）", ["PM2.5"]), ("CO", ["CO"]),
            ("4G 訊號 CSQ", ["4G訊號(CSQ)"]), ("開機次數", ["開機次數(次)"]),
            ("運轉時間（小時）", ["運轉時間(秒)"]), ("電池電壓（V）", ["電池電壓(V)"]),
        ],
        "spans": [
            ("2026-06-13 09:00", "2026-06-22 08:00", "斷線 9 天"),
            ("2026-06-25 19:00", "2026-08-31 08:00", "斷線 67 天"),
        ],
        "diurnal": ["溫度", "濕度", "PM2.5", "PM10", "TVOC PID", "風速"],
        "range": ("2026-06-01", "2026-06-26"),
    },
    "yucheng1": {
        "panels": [
            ("PM2.5（μg/m³）", ["PM2.5"]), ("PM10（μg/m³）", ["PM10"]), ("CO", ["CO"]),
            ("TVOC(PID)", ["TVOC(PID)"]), ("溫度（°C）", ["TEMP"]), ("濕度（%）", ["RH"]),
        ],
        "spans": [("2026-06-26 15:00", "2026-07-02", "CO 長時間偏高")],
        "diurnal": ["PM2.5", "PM10", "CO", "TEMP", "RH", "風速"],
    },
    "northeast": {
        "panels": [
            ("PM2.5（μg/m³）", ["PM2.5"]), ("PM10（μg/m³）", ["PM10"]), ("TVOC", ["TVOC"]),
            ("CO", ["CO"]), ("溫度（°C）", ["TEMP"]), ("濕度（%）", ["RH"]),
        ],
        "spans": [
            ("2026-06-26 01:00", "2026-06-29 15:00", "溫濕度凍結"),
            ("2026-08-21 11:00", "2026-08-24 09:00", "TVOC 上升→全面失常"),
        ],
        "diurnal": ["PM2.5", "PM10", "TEMP", "RH", "風速"],
    },
    "construction": {
        "panels": [
            ("PM2.5（μg/m³，上限截 150）", ["PM2.5"]), ("PM10（μg/m³，上限截 250）", ["PM10"]),
            ("噪音（dB）", ["噪音"]), ("溫度（°C）", ["溫度"]), ("熱指數（°C）", ["熱指數"]),
            ("濕度（%）", ["濕度"]),
        ],
        "spans": [("2026-03-01 02:00", "2026-03-02 08:00", "斷線 30 h")],
        "diurnal": ["噪音", "PM2.5", "PM10", "溫度", "濕度", "風速"],
        "clip": {"PM2.5": 150, "PM10": 250},
    },
}


def _shade(ax, spans, label: bool):
    for k, (start, end, text) in enumerate(spans):
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color="#d9d8d2", alpha=0.55, lw=0, zorder=0)
        if label:
            ax.annotate(text, (pd.Timestamp(start), 1.0), xycoords=("data", "axes fraction"),
                        xytext=(2, 2 + 11 * (k % 2)), textcoords="offset points", fontsize=7.5, color=INK2, va="bottom")


def timeseries(site: str, cfg: dict) -> None:
    df = load(site)
    df = hourly(df[~(df.fillna(0) == 0).all(axis=1)])  # 全 0 列是斷線，不畫
    if "range" in cfg:
        df = df.loc[cfg["range"][0]:cfg["range"][1]]
    df = df.copy()
    if "運轉時間(秒)" in df:
        df["運轉時間(秒)"] = df["運轉時間(秒)"] / 3600
    for col, cap in cfg.get("clip", {}).items():
        df[col] = df[col].clip(upper=cap)
    panels = cfg["panels"]
    fig, axes = plt.subplots(len(panels), 1, figsize=(11, 1.55 * len(panels) + 0.6), sharex=True)
    for i, (ax, (title, cols)) in enumerate(zip(axes, panels)):
        _shade(ax, cfg["spans"], label=(i == 0))
        for j, col in enumerate(cols):
            ax.plot(df.index, df[col], lw=0.9 if len(cols) > 1 else 1.0,
                    color=SERIES[j], label=col.replace(" 即時值", ""))
        if cfg.get("thi") and "THI" in title:
            for y, t in [(79, "79 警戒"), (84, "84 危險")]:
                ax.axhline(y, color=INK2, lw=0.8, ls="--")
                ax.text(df.index[-1], y, f" {t}", fontsize=7.5, color=INK2, va="center")
        ax.set_title(title, loc="left", fontsize=9.5, color=INK, pad=26 if i == 0 else 3)
        if len(cols) > 1:
            ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7.5, frameon=False)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    fig.tight_layout(h_pad=0.6)
    fig.savefig(OUT / site / "timeseries.png", dpi=130)
    plt.close(fig)


def diurnal(site: str, cols: list[str]) -> None:
    df = load(site)
    df = df[~(df.fillna(0) == 0).all(axis=1)]
    prof = df.groupby(df.index.hour)[cols].median()  # 用中位數，避免單一極端值拉歪
    n = len(cols)
    ncols = 3
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 2.3 * nrows + 0.4), squeeze=False)
    for ax, col in zip(axes.flat, cols):
        ax.plot(prof.index, prof[col], color=SERIES[0], lw=2, marker="o", ms=3)
        ax.set_title(col, loc="left", fontsize=9.5, color=INK)
        ax.set_xticks(range(0, 24, 3))
        ax.set_xlabel("時", fontsize=8)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle("24 小時曲線（全期間各小時的中位數）", x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / site / "diurnal.png", dpi=130)
    plt.close(fig)


def main() -> None:
    for site, cfg in CONFIG.items():
        (OUT / site).mkdir(parents=True, exist_ok=True)
        timeseries(site, cfg)
        diurnal(site, cfg["diurnal"])
        print("OK", site)


if __name__ == "__main__":
    main()
