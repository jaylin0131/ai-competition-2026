"""把網站上的勾選（Supabase task_status 表）寫回兩個專案的 schedule/tasks.csv，再重產各自的甘特圖。

由 GitHub Actions 每天執行（.github/workflows/sync-status.yml），也可以手動：
    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python3 site/sync_status.py

規則：
- 勾選完成 → status 改為 done
- 取消勾選，而 tasks.csv 原本是 done → 改回 doing
- 其他欄位（日期、負責人、任務名稱）不動；網站沒有勾選紀錄的任務也不動
SUPABASE_SERVICE_KEY 是私密金鑰，只放在 GitHub Secrets，不可寫進網頁或程式碼。
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = {"jnc": "JNC-AIoT", "qkd": "QKD-Eavesdrop-AI"}


def fetch_status(url: str, key: str) -> dict[str, bool]:
    req = urllib.request.Request(
        f"{url.rstrip('/')}/rest/v1/task_status?select=key,done",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        rows = json.load(r)
    return {row["key"]: bool(row["done"]) for row in rows}


def apply(project: str, folder: str, status: dict[str, bool]) -> list[str]:
    path = ROOT / folder / "schedule" / "tasks.csv"
    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames or []
    rows = list(reader)
    changes = []
    for row in rows:
        done = status.get(f"{project}_{row['id']}")
        if done is None:
            continue
        new = "done" if done else ("doing" if row["status"] == "done" else row["status"])
        if new != row["status"]:
            changes.append(f"{folder} {row['id']}：{row['status']} → {new}")
            row["status"] = new
    if changes:
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        path.write_text(out.getvalue(), encoding="utf-8")
        subprocess.run([sys.executable, "scripts/build_gantt.py"], cwd=ROOT / folder, check=True)
    return changes


def main() -> None:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    if not (url and key):
        raise SystemExit("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_KEY（請在 GitHub 儲存庫的 Settings → Secrets 設定）")
    status = fetch_status(url, key)
    print(f"網站上有 {len(status)} 筆勾選紀錄")
    changes = [c for p, f in PROJECTS.items() for c in apply(p, f, status)]
    print("\n".join(changes) if changes else "tasks.csv 已是最新，沒有變更")


if __name__ == "__main__":
    main()
