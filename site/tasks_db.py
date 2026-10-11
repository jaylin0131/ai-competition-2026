"""網站資料庫（Supabase tasks 表）與兩個專案 schedule/tasks.csv 之間的匯入、匯出。

網站上的規劃是唯一來源；tasks.csv 是每天自動匯出的副本，不要手改（會被覆蓋）。

    python3 site/tasks_db.py import            # 第一次：把 tasks.csv 匯入網站（資料庫已有任務時會拒絕）
    python3 site/tasks_db.py import --replace  # 用 tasks.csv 整份覆蓋網站上的規劃（會丟掉網站上的修改）
    python3 site/tasks_db.py export            # 把網站上的規劃寫回 tasks.csv，並重產兩個專案的甘特圖

都由 GitHub Actions 執行（.github/workflows/），需要環境變數 SUPABASE_URL、SUPABASE_SERVICE_KEY。
SUPABASE_SERVICE_KEY 是私密金鑰，只放在 GitHub Secrets，不可寫進網頁或程式碼。
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = {"jnc": "JNC-AIoT", "qkd": "QKD-Eavesdrop-AI"}
FIELDS = ["id", "phase", "group", "owner", "task", "start", "end", "depends", "status", "deliverable"]


class Rest:
    def __init__(self) -> None:
        url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
        if not (url and key):
            raise SystemExit("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_KEY（請在 GitHub 儲存庫的 Settings → Secrets 設定）")
        self.base = f"{url}/rest/v1"
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def call(self, method: str, path: str, body=None, prefer: str = "") -> list:
        headers = dict(self.headers, **({"Prefer": prefer} if prefer else {}))
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{self.base}/{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode()
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Supabase 錯誤 {e.code}：{e.read().decode()[:300]}")
        return json.loads(text) if text else []


def read_csv(folder: str) -> tuple[list[str], list[dict]]:
    path = ROOT / folder / "schedule" / "tasks.csv"
    reader = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
    return list(reader.fieldnames or FIELDS), list(reader)


def do_import(api: Rest, replace: bool) -> None:
    existing = api.call("GET", "tasks?select=key&limit=1")
    if existing and not replace:
        raise SystemExit("網站資料庫已經有任務，為避免蓋掉網站上的修改，已停止。確定要用 tasks.csv 覆蓋時請加 --replace。")

    # 早期只有勾選功能時的紀錄（task_status 表），一併套用
    try:
        ticks = {r["key"]: r["done"] for r in api.call("GET", "task_status?select=key,done")}
    except SystemExit:
        ticks = {}

    rows = []
    for project, folder in PROJECTS.items():
        _, tasks = read_csv(folder)
        for i, t in enumerate(tasks):
            key = f"{project}_{t['id']}"
            status = t["status"]
            if key in ticks:
                status = "done" if ticks[key] else ("doing" if status == "done" else status)
            rows.append({
                "key": key, "project": project, "id": t["id"], "phase": t["phase"], "grp": t["group"],
                "owners": t.get("owner", ""), "task": t["task"], "start_date": t["start"], "end_date": t["end"],
                "depends": t["depends"], "status": status, "deliverable": t["deliverable"],
                "sort": (i + 1) * 10, "updated_by_name": "tasks.csv 匯入",
            })
    if replace:
        api.call("DELETE", "tasks?key=not.is.null", prefer="return=minimal")
    api.call("POST", "tasks?on_conflict=key", rows, prefer="resolution=merge-duplicates,return=minimal")
    print(f"已匯入 {len(rows)} 項任務（套用舊勾選 {len(ticks)} 筆）")


def do_export(api: Rest) -> None:
    rows = api.call("GET", "tasks?select=*&order=project.asc,sort.asc,id.asc")
    if not rows:
        raise SystemExit("網站資料庫沒有任務，請先執行匯入（import）。為避免清空 tasks.csv，已停止。")
    for project, folder in PROJECTS.items():
        fields, _ = read_csv(folder)
        mine = [r for r in rows if r["project"] == project]
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in mine:
            w.writerow({
                "id": r["id"], "phase": r["phase"], "group": r["grp"], "owner": r["owners"], "task": r["task"],
                "start": r["start_date"], "end": r["end_date"], "depends": r["depends"], "status": r["status"],
                "deliverable": r["deliverable"],
            })
        path = ROOT / folder / "schedule" / "tasks.csv"
        changed = path.read_text(encoding="utf-8") != out.getvalue()
        path.write_text(out.getvalue(), encoding="utf-8")
        subprocess.run([sys.executable, "scripts/build_gantt.py"], cwd=ROOT / folder, check=True)
        print(f"{folder}：{len(mine)} 項任務{'（有變更）' if changed else '（沒有變更）'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import")
    imp.add_argument("--replace", action="store_true")
    sub.add_parser("export")
    args = ap.parse_args()
    api = Rest()
    if args.cmd == "import":
        do_import(api, args.replace)
    else:
        do_export(api)


if __name__ == "__main__":
    main()
