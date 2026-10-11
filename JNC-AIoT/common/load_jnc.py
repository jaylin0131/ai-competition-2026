"""讀取銘祥科技提供的 7 個場域 CSV。全隊共用，請勿各自另寫讀檔程式。

原始檔（data/raw/）的格式：Excel 匯出、UTF-16 LE、Tab 分隔、CRLF、每小時一筆。
欄名帶有設備前綴，例如「專家系統【C22】感測器主機 - pH1 即時值」，這裡只保留「 - 」後面的部分。

用法：
    from common.load_jnc import load, load_raw, SITES
    df = load("pond")          # 讀整理後的 data/processed/pond.csv（index 為時間）
    raw = load_raw("pond")     # 直接讀原始檔，結果與 load() 相同
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


@dataclass(frozen=True)
class Site:
    key: str          # 程式裡用的代號，也是 data/processed/ 的檔名
    name: str         # 中文名稱
    raw_file: str     # data/raw/ 裡的原始檔名
    skiprows: int     # 標題列前要跳過的列數
    role: str         # 在作品中的定位：核心／擴充／加分
    summary: str      # 資料內容


SITES: dict[str, Site] = {s.key: s for s in [
    Site("pond", "專家系統（魚塭）", "Data2026-06-01專家系統.csv", 0, "核心",
         "三組 pH／ORP／SC／DO 探頭、水溫、微氣候、水位、設備用電"),
    Site("river", "三爺宮溪（河川站）", "Data2026-01-01-三爺宮溪.csv", 0, "擴充",
         "河川水質（pH、EC、DO）與太陽能供電站（電池電量、電壓）"),
    Site("goat", "羊舍", "Data2026-06-01-羊舍.csv", 0, "擴充",
         "畜舍環境（溫濕度、CO2、NH3、CH4、THI）與帆布、遮陽、風扇的操作狀態"),
    Site("yucheng_north", "育成北側", "Data2026-06-01-育成北側.csv", 0, "加分",
         "空品與設備健康（訊號強度、開機次數、電池電壓、4G CSQ）"),
    Site("yucheng1", "育成一廠", "Data2026-06-01-育成一廠.csv", 0, "加分",
         "空品（PM2.5、PM10、HCHO、CO、TVOC）與溫濕度、風"),
    Site("northeast", "東北角", "Data2026-06-01-東北角.csv", 0, "加分",
         "空品（PM2.5、PM10、HCHO、CO、TVOC）與溫濕度、風"),
    Site("construction", "工地微氣候", "Data2026-01-01-工地微氣候.csv", 2, "加分",
         "工地微氣候（溫濕度、熱指數、危害等級、PM2.5、PM10、噪音）"),
]}


def _short(col: str) -> str:
    return col.split(" - ", 1)[-1].strip()


def load_raw(site: str) -> pd.DataFrame:
    """讀原始檔，回傳以小時為 index、數值欄位的 DataFrame（不改任何數值）。"""
    s = SITES[site]
    df = pd.read_csv(RAW_DIR / s.raw_file, sep="\t", encoding="utf-16", skiprows=s.skiprows, dtype=str)
    df = df.dropna(axis=1, how="all")
    df.columns = [_short(c) for c in df.columns]
    time = pd.to_datetime(df["日期"], format="%Y/%m/%d") + pd.to_timedelta(df["小時"].astype(int), unit="h")
    df = df.drop(columns=["日期", "小時"]).apply(pd.to_numeric, errors="coerce")
    df.index = pd.DatetimeIndex(time, name="time")
    return df.sort_index()


def load(site: str) -> pd.DataFrame:
    """讀 data/processed/<site>.csv；尚未產生時改讀原始檔。"""
    path = PROCESSED_DIR / f"{site}.csv"
    if not path.exists():
        return load_raw(site)
    return pd.read_csv(path, index_col="time", parse_dates=["time"])


def hourly(df: pd.DataFrame) -> pd.DataFrame:
    """補齊每小時的時間軸，缺漏的小時填 NaN（缺漏可能代表斷線）。重複時間只保留第一筆。"""
    return df[~df.index.duplicated()].asfreq("h")
