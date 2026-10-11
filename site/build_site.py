"""把兩個專案的 schedule/tasks.csv 合併成團隊時程網站（site/index.html）。

用法（在儲存庫根目錄執行）：
    python3 site/build_site.py                                   # Claude Artifact 版 → site/index.html
    python3 site/build_site.py --mode supabase --out site/dist/index.html   # Cloudflare Pages 版

Supabase 版從環境變數讀 SUPABASE_URL、SUPABASE_ANON_KEY（公開金鑰，本來就會出現在網頁裡）；
沒設定時網站仍可建置，但只顯示 tasks.csv 的狀態、不能勾選。

資料來源（唯一來源，網站不手改）：
- JNC-AIoT/schedule/tasks.csv
- QKD-Eavesdrop-AI/schedule/tasks.csv
- QKD-Eavesdrop-AI/schedule/team.csv（名冊）

Artifact 版：產生後把 site/index.html 重新發布到同一個 Artifact 網址。
Cloudflare 版：push 到 GitHub 後由 Cloudflare Pages 自動建置部署。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = Path(__file__).resolve().parent
TEMPLATE = SITE / "template.html"
OUT = SITE / "index.html"
SUPABASE_JS = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js"

PROJECTS = [
    {"key": "jnc", "name": "企業組｜銘祥科技 AIoT", "short": "企業組", "dir": "JNC-AIoT",
     "deadline": "M8"},
    {"key": "qkd", "name": "資電組｜QKD 鏈路健康診斷", "short": "資電組", "dir": "QKD-Eavesdrop-AI",
     "deadline": "M7"},
]
# 身分選單除了 team.csv 的成員之外，額外列出的身分（不負責任務，不出現在成員篩選）
EXTRA_IDENTITIES = ["黃秋杰老師"]
FIELDS = ["id", "phase", "group", "owner", "task", "start", "end", "depends", "status", "deliverable"]
STATUSES = {"done", "doing", "todo", "optional"}


def load_tasks(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    tasks = []
    for r in rows:
        if r["status"] not in STATUSES:
            raise SystemExit(f"{path}：{r['id']} 的 status 不正確：{r['status']}")
        if r["end"] < r["start"]:
            raise SystemExit(f"{path}：{r['id']} 的結束日早於開始日")
        t = {k: (r.get(k) or "").strip() for k in FIELDS}
        t["owners"] = [o for o in t.pop("owner").split("、") if o]
        t["depends"] = [d for d in t["depends"].split(";") if d]
        tasks.append(t)
    return tasks


def last_change(fallback_mtime: float) -> str:
    """tasks.csv 最後一次 commit 的時間；不在 git 裡（或淺層 clone 失敗）就用檔案修改時間。"""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M", "--",
             *(f"{p['dir']}/schedule/tasks.csv" for p in PROJECTS)],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if out:
            return out
    except (OSError, subprocess.SubprocessError):
        pass
    return datetime.fromtimestamp(fallback_mtime).strftime("%Y-%m-%d %H:%M")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("artifact", "supabase"), default="artifact")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    projects = []
    newest = 0.0
    for p in PROJECTS:
        path = ROOT / p["dir"] / "schedule" / "tasks.csv"
        newest = max(newest, path.stat().st_mtime)
        projects.append({k: v for k, v in p.items() if k != "dir"} | {"tasks": load_tasks(path)})

    team_path = ROOT / "QKD-Eavesdrop-AI" / "schedule" / "team.csv"
    with team_path.open(encoding="utf-8") as f:
        team = [{"name": r["name"], "dept": r["dept"], "role": r["role"]} for r in csv.DictReader(f)]

    backend = {"mode": args.mode}
    if args.mode == "supabase":
        backend |= {"url": os.environ.get("SUPABASE_URL", "").strip(), "anonKey": os.environ.get("SUPABASE_ANON_KEY", "").strip()}
        if not (backend["url"] and backend["anonKey"]):
            print("提示：建置時沒有 SUPABASE_URL／SUPABASE_ANON_KEY，網頁會在執行時改讀 /config.js（Workers 版）")

    data = {
        "backend": backend,
        "updated": last_change(newest),
        "projects": projects,
        "team": team,
        "extraIdentities": EXTRA_IDENTITIES,
        "keyDates": [
            {"date": "2026-11-28", "label": "隊內送件"},
            {"date": "2026-12-01", "label": "報名截止"},
            {"date": "2026-12-11", "label": "初賽"},
            {"date": "2026-12-19", "label": "決賽"},
        ],
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    # Workers 版：/config.js 由 worker/index.js 在執行時提供連線資訊（Pages 版沒有這支檔案，會改用建置時嵌入的值）
    head = f'<script src="/config.js"></script><script src="{SUPABASE_JS}"></script>' if args.mode == "supabase" else ""
    html = TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", payload).replace("<!--__HEAD__-->", head)
    if args.mode == "supabase":
        # 獨立網站需要完整文件；Artifact 版由發布工具包上外框
        html = ('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta name="robots" content="noindex">'
                f'</head><body>{html}</body></html>')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    n = sum(len(p["tasks"]) for p in projects)
    print(f"已產生 {args.out}（{args.mode}）：{len(projects)} 個專案、{n} 項任務、{len(team)} 位成員（資料時間 {data['updated']}）")


if __name__ == "__main__":
    main()
