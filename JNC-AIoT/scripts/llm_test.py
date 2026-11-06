"""D6／S11 本地語言模型實測：抽 10 張回放工單，比較數字守門員擋下次數、中文品質、速度。

    ollama serve &                                   # 另開終端機
    .venv/bin/python scripts/llm_test.py gemma4:e4b  # 可一次給多個模型

結果寫到 notes/llm-test.md（中文品質欄由人填 1–5 分），原始輸出在 notes/llm-test/。
禁用中資模型（docs/architecture.md 第 7 節）。
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.load_jnc import ROOT
from common.pipeline import PondPipeline
from decide.workorder import NUM, number_guard, ollama_generate

OUT = ROOT / "notes" / "llm-test.md"
RAW = ROOT / "notes" / "llm-test"
# 中文數字可以繞過數字守門員（例如把「3 小時」寫成「五小時」），另外標出來給人看
CN_NUM = re.compile(r"[一二兩三四五六七八九十百千]+\s*(?:小時|天|台|度|次|分鐘|元|%)")
# 涵蓋不同決策類型的時間點（含注入故障），依序收集到 10 張不重複的工單
SAMPLES = [
    ("2026-07-19 18:00", None), ("2026-07-20 03:00", None), ("2026-08-30 14:00", None),
    ("2026-09-20 06:00", None), ("2026-09-10 13:00", None), ("2026-08-11 14:00", None),
    ("2026-07-25 12:00", ("dropout", "DO2 即時值", 6)), ("2026-07-25 12:00", ("stuck", "pH3 即時值", 14)),
    ("2026-08-05 09:00", ("offline", "ALL", 3)), ("2026-08-05 09:00", ("drift", "ORP2 即時值", 48)),
    ("2026-07-28 15:00", None), ("2026-09-14 20:00", None),
]


def collect(n: int = 10) -> list[dict]:
    pipe = PondPipeline.build()
    seen, out = set(), []
    for ts, fault in SAMPLES:
        p = pipe.with_fault(*fault[:2], ts, fault[2]) if fault else pipe
        for w in p.step(ts)["work_orders"]:
            key = (w["對象"], w["工作"])
            if key in seen:
                continue
            seen.add(key)
            out.append({"ts": ts, "fault": fault[0] if fault else "", **w})
            if len(out) == n:
                return out
    return out


def run(model: str, orders: list[dict]) -> list[dict]:
    ollama_generate(model, "測試")  # 暖機：第一次要載入模型
    rows = []
    for w in orders:
        t0 = time.time()
        try:
            r = ollama_generate(model, w["說明"])
            text, err = r["response"].strip(), ""
        except Exception as e:  # 逾時或服務沒開
            r, text, err = {}, "", str(e)
        sec = time.time() - t0
        tok = r.get("eval_count", 0)
        rate = tok / (r["eval_duration"] / 1e9) if r.get("eval_duration") else 0.0
        src = {abs(float(n)) for n in NUM.findall(w["說明"])}
        bad = sorted({n for n in NUM.findall(text) if abs(float(n)) not in src})
        rows.append({"工單": w["工單編號"], "source": w["說明"], "output": text, "error": err,
                     "guard_ok": bool(text) and number_guard(text, w["說明"]), "bad_numbers": bad,
                     "cn_numbers": CN_NUM.findall(text), "seconds": round(sec, 1), "tokens": tok,
                     "tok_per_s": round(rate, 1)})
        print(f"  {w['工單編號']}  {sec:5.1f}s  守門員{'通過' if rows[-1]['guard_ok'] else '擋下'}")
    return rows


def machine() -> str:
    try:
        cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
        mem = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout) / 2 ** 30
        ver = subprocess.run(["ollama", "--version"], capture_output=True, text=True).stdout.strip()
    except Exception:
        cpu, mem, ver = platform.processor(), 0, "?"
    return f"{cpu}，{mem:.0f} GB RAM，{platform.system()} {platform.mac_ver()[0]}，{ver}"


def write(results: dict[str, list[dict]], orders: list[dict]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for m, rows in results.items():
        (RAW / f"{m.replace(':', '_').replace('/', '_')}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# 本地語言模型實測（D6／S11）", "",
             f"> 由 `scripts/llm_test.py` 產生（{date.today().isoformat()}）。機器：{machine()}。",
             "> 語言模型只把決策改寫成工單白話說明；數字守門員：輸出中的阿拉伯數字都必須出現在原始決策，否則退回範本。",
             "> 「中文數字」欄列出可能繞過守門員的寫法（例如「五小時」），要人工確認是否正確。", "",
             "## 結果", "",
             "| 模型 | 成功回應 | 守門員擋下 | 含中文數字 | 平均秒數／張 | 生成速度（token/s） | 中文品質（人工 1–5） |",
             "|---|---|---|---|---|---|---|"]
    for m, rows in results.items():
        ok = [r for r in rows if r["output"]]
        lines.append(f"| {m} | {len(ok)}/{len(rows)} | {sum(not r['guard_ok'] for r in ok)} | "
                     f"{sum(bool(r['cn_numbers']) for r in ok)} | "
                     f"{sum(r['seconds'] for r in ok) / max(len(ok), 1):.1f} | "
                     f"{sum(r['tok_per_s'] for r in ok) / max(len(ok), 1):.1f} | （待填） |")
    lines += ["", "## 測試工單（範本原文）", ""]
    for w in orders:
        tag = f"（注入 {w['fault']}）" if w["fault"] else ""
        lines.append(f"- **{w['工單編號']}** {w['ts']}{tag}：{w['說明']}")
    for m, rows in results.items():
        lines += ["", f"## {m} 輸出", ""]
        for r in rows:
            flag = "通過" if r["guard_ok"] else (f"擋下（多出數字 {', '.join(r['bad_numbers'])}）" if r["output"] else f"失敗：{r['error']}")
            cn = f"；中文數字：{'、'.join(r['cn_numbers'])}" if r["cn_numbers"] else ""
            lines.append(f"- **{r['工單']}**（{r['seconds']} 秒，守門員{flag}{cn}）：{r['output'] or '—'}")
    lines += ["", "## 結論", "", "（測完由負責人填寫：選哪個模型、是否預設開啟 LLM 改寫、決賽離線方案）", ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    models = sys.argv[1:] or ["gemma4:e4b"]
    orders = collect()
    print(f"收集到 {len(orders)} 張工單")
    results = {}
    for m in models:
        print(f"測試 {m}…")
        results[m] = run(m, orders)
    write(results, orders)
    print(f"完成：{OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
