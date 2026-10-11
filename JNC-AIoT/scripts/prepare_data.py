"""把 data/raw/ 的 7 個原始 CSV 整理成 data/processed/，並產生資料字典。

做的事（只處理格式，不改數值；不合理值的判斷交給 P3 的物理規則）：
- UTF-16／Tab → UTF-8／逗號；欄名去掉設備前綴；日期＋小時合併成 time 欄
- 依時間排序；重複時間只保留第一筆
- 統計每個場域的期間、筆數、缺漏小時、每個欄位的範圍、0 值與負值比例

輸出：
- data/processed/<site>.csv
- data/processed/sites.json（每個場域的摘要，給程式用）
- docs/data-dictionary.md（給人看的資料字典）

用法（在專案根目錄執行）：
    python3 scripts/prepare_data.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from common.load_jnc import PROCESSED_DIR, SITES, load_raw  # noqa: E402

DICT_MD = ROOT / "docs" / "data-dictionary.md"

# 欄位意義與單位：依欄名與數值範圍推測，標「?」的請向企業確認；由上往下比對，較具體的放前面
UNITS = [
    ("DO1水溫", "°C"), ("DO飽和度", "%"), ("斜率", "探頭斜率 %（校正狀態）"), ("DO", "溶氧 mg/L"), ("pH", "酸鹼值"),
    ("ORP", "氧化還原電位 mV"), ("SC", "導電度（單位?）"), ("EC", "導電度 µS/cm?"), ("水溫", "°C"), ("溫度", "°C"),
    ("TEMP", "°C"), ("濕度", "%RH"), ("RH", "%RH"), ("大氣壓力", "hPa"), ("熱指數", "°C"), ("危害等級", "等級"),
    ("風速", "m/s"), ("風向", "度"), ("水位", "水位高度（單位?）"), ("功率因數", "無單位 0–1"), ("無功功率", "var?（正負號代表電感性／電容性）"),
    ("視在功率", "VA?"), ("功率", "W?"), ("相電壓", "V"), ("電壓", "V"), ("電流", "A"), ("頻率", "Hz"),
    ("度數", "kWh"), ("電度", "kWh?"), ("電池電量", "%"), ("PM2.5", "µg/m³"), ("PM10", "µg/m³"), ("HCHO", "甲醛 ppm?"),
    ("CO2", "ppm"), ("CO", "一氧化碳 ppm?"), ("TVOC", "ppm?"), ("NH3", "氨 ppm?"), ("CH4", "甲烷 ppm?"), ("噪音", "dB"),
    ("雨量", "mm"), ("THI", "溫濕度指數"), ("帆布", "致動器狀態碼 0–4（意義?）"), ("遮陽", "致動器狀態碼 0–4（意義?）"),
    ("風扇", "致動器狀態碼 0–4（意義?）"), ("加開", "控制旗標?"), ("減開", "控制旗標?"), ("訊號強度", "?"),
    ("CSQ", "4G 訊號品質 0–31"), ("運轉時間", "秒"), ("送電時間", "秒"), ("開機次數", "次（累計）"),
]


def unit_of(col: str) -> str:
    return next((unit for key, unit in UNITS if key in col), "")


def profile(site: str) -> tuple[pd.DataFrame, dict, list[dict]]:
    df = load_raw(site)
    dup = int(df.index.duplicated().sum())
    df = df[~df.index.duplicated()]
    full = pd.date_range(df.index.min(), df.index.max(), freq="h")
    missing = full.difference(df.index)
    info = {
        "key": site,
        "name": SITES[site].name,
        "role": SITES[site].role,
        "raw_file": SITES[site].raw_file,
        "start": df.index.min().isoformat(),
        "end": df.index.max().isoformat(),
        "rows": len(df),
        "expected_hours": len(full),
        "missing_hours": len(missing),
        "duplicate_rows_dropped": dup,
        "columns": list(df.columns),
    }
    cols = []
    for c in df.columns:
        x = df[c]
        n = int(x.notna().sum())
        cols.append({
            "col": c, "unit": unit_of(c), "non_null": n,
            "min": x.min(), "median": x.median(), "max": x.max(),
            "zero_pct": round(100 * float((x == 0).sum()) / n, 1) if n else None,
            "neg": int((x < 0).sum()),
        })
    return df, info, cols


def fmt(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    v = float(v)
    return f"{v:.0f}" if v.is_integer() else f"{v:.3g}"


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    infos, md = [], [
        "# 資料字典",
        "",
        f"> 由 `scripts/prepare_data.py` 從 `data/raw/` 自動產生（{date.today():%Y-%m-%d}），請勿手動修改。",
        "> 單位是依欄名與數值範圍推測的，標「?」的要向企業確認。",
        "> 「0 值 %」高的欄位可能是感測器未啟用或斷線，不一定是真的 0。",
        "",
        "## 場域總覽",
        "",
        "| 代號 | 場域 | 定位 | 期間 | 筆數 | 缺漏小時 | 欄位數 |",
        "|---|---|---|---|---|---|---|",
    ]
    details = []
    for key in SITES:
        df, info, cols = profile(key)
        df.to_csv(PROCESSED_DIR / f"{key}.csv", encoding="utf-8")
        infos.append(info)
        md.append(f"| `{key}` | {info['name']} | {info['role']} | {info['start'][:10]} – {info['end'][:10]} | "
                  f"{info['rows']:,} | {info['missing_hours']:,} / {info['expected_hours']:,} | {len(cols)} |")
        details += [
            "", f"## {info['name']}（`{key}`）", "",
            f"- 原始檔：`data/raw/{info['raw_file']}`",
            f"- 整理後：`data/processed/{key}.csv`",
            f"- 內容：{SITES[key].summary}",
            f"- 期間：{info['start'][:16].replace('T', ' ')} – {info['end'][:16].replace('T', ' ')}，"
            f"{info['rows']:,} 筆；缺漏 {info['missing_hours']:,} 小時；重複時間 {info['duplicate_rows_dropped']} 筆已移除",
            "",
            "| 欄位 | 推測意義／單位 | 有值筆數 | 最小 | 中位數 | 最大 | 0 值 % | 負值筆數 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for c in cols:
            neg = f"**{c['neg']}**" if c["neg"] else "0"
            details.append(f"| {c['col']} | {c['unit'] or '—'} | {c['non_null']:,} | {fmt(c['min'])} | "
                           f"{fmt(c['median'])} | {fmt(c['max'])} | {fmt(c['zero_pct'])} | {neg} |")
        print(f"{key:14s} {info['rows']:5d} 筆  缺漏 {info['missing_hours']:4d} 小時  → data/processed/{key}.csv")
    (PROCESSED_DIR / "sites.json").write_text(json.dumps(infos, ensure_ascii=False, indent=2), encoding="utf-8")
    DICT_MD.write_text("\n".join(md + details) + "\n", encoding="utf-8")
    print(f"已產生 {DICT_MD.relative_to(ROOT)} 與 data/processed/sites.json")


if __name__ == "__main__":
    main()
