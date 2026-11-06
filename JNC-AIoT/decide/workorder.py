"""管理優先：工單、派工、備品與能耗。

工單先用範本產生（離線、可重現）。若設定環境變數 JNC_LLM_MODEL（例：gemma4:e4b，經 Ollama 本機執行），
會請 LLM 改寫成白話，但「數字守門員」會檢查：LLM 輸出的每個數字都必須出現在決策資料裡，否則退回範本。
禁用中資模型（architecture.md 第 7 節）。
"""

from __future__ import annotations

import json
import os
import re
import urllib.request

from common import config as C

NUM = re.compile(r"-?\d+(?:\.\d+)?")


def work_orders(decisions: list[dict]) -> list[dict]:
    """把需要人處理的決策轉成工單。"""
    out = []
    for d in decisions:
        if d["執行模式"] == "自動執行" and d["類別"] == "行動控制":
            continue
        out.append({
            "工單編號": "WO-" + d["編號"], "優先級": f"P{d['優先級']}", "對象": d["設備"], "工作": d["動作"],
            "期限": d["時間"], "派工": d.get("派工", "值班人員"), "備品": d.get("備品", "—"),
            "能耗_kWh": d.get("能耗_kWh", 0.0),
            "電費_元": round(d.get("能耗_kWh", 0.0) * C.ELECTRICITY_PRICE, 1),
            "說明": render(d), "執行模式": d["執行模式"],
        })
    return out


def render(d: dict) -> str:
    text = (f"【{d['執行模式']}｜P{d['優先級']}】{d['設備']} {d['動作']}（{d['時間']}，{d['幅度']}）。"
            f"原因：{d['理由']}。預期：{d['預期效果']}。風險：{d['風險']}。Fallback：{d['Fallback']}。")
    model = os.environ.get("JNC_LLM_MODEL")
    if not model:
        return text
    try:
        polished = _ollama(model, text)
    except Exception:
        return text
    return polished if number_guard(polished, text) else text


def _values(text: str) -> set[float]:
    return {abs(float(n)) for n in NUM.findall(text)}


def number_guard(output: str, source: str) -> bool:
    """LLM 輸出的數字都必須出現在來源文字中（比數值，不比寫法：-2.07 與 2.07、1.0 與 1 視為相同）。"""
    return _values(output) <= _values(source)


PROMPT = ("把下面的養殖場決策改寫成給現場人員看的一段繁體中文工單說明，"
          "不要新增任何數字，不要改變動作與時間：\n")


def ollama_generate(model: str, text: str, timeout: float | None = None) -> dict:
    """呼叫本機 Ollama。回傳 Ollama 的完整回應（response、eval_count、eval_duration 等，測速用）。"""
    timeout = timeout or float(os.environ.get("JNC_LLM_TIMEOUT", "180"))
    body = {"model": model, "prompt": PROMPT + text, "stream": False, "options": {"temperature": 0.2}}
    req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _ollama(model: str, text: str) -> str:
    return ollama_generate(model, text)["response"].strip()
