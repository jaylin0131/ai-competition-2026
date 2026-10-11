"""從 schedule/tasks.csv 產生甘特圖。

輸出：
- schedule/gantt.html：可直接用瀏覽器開啟的甘特圖（含今日線、期中考週、進度統計）
- schedule/gantt.md：Mermaid 版甘特圖，GitHub 上會直接渲染

用法（在專案根目錄執行）：
    python3 scripts/build_gantt.py
    python3 scripts/build_gantt.py --today 2026-10-20 --exam 2026-11-02:2026-11-13

更新進度的方式：只改 tasks.csv 的 status 欄（todo / doing / done / optional），再重新執行本程式。
"""

from __future__ import annotations

import argparse
import csv
import html
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_CSV = ROOT / "schedule" / "tasks.csv"
OUT_HTML = ROOT / "schedule" / "gantt.html"
OUT_MD = ROOT / "schedule" / "gantt.md"

STATUS_LABEL = {"done": "完成", "doing": "進行中", "todo": "未開始", "optional": "進階選做"}
GROUP_ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "全員"]
GROUP_LABEL = {
    "P1": "P1 隊長／文件（周冠辰）", "P2": "P2 資料平台（許程景、林子桀）", "P3": "P3 狀態辨識（何名綸）",
    "P4": "P4 異常診斷（王端宏）", "P5": "P5 趨勢預測（林子桀，暫定）", "P6": "P6 決策引擎（許程景，暫定）", "全員": "全員",
}
GROUP_CLASS = {"P1": "p1", "P2": "p2", "P3": "p3", "P4": "p4", "P5": "p5", "P6": "p6", "全員": "all"}
DEADLINE_ID = "M8"


@dataclass
class Task:
    id: str
    phase: str
    group: str
    task: str
    start: date
    end: date
    depends: list[str]
    status: str
    deliverable: str
    owner: str = ""

    @property
    def is_milestone(self) -> bool:
        return self.id.startswith("M")


def load_tasks(path: Path) -> list[Task]:
    tasks = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tasks.append(
                Task(
                    id=row["id"],
                    phase=row["phase"],
                    group=row["group"],
                    task=row["task"],
                    start=date.fromisoformat(row["start"]),
                    end=date.fromisoformat(row["end"]),
                    depends=[d for d in row["depends"].split(";") if d],
                    status=row["status"],
                    deliverable=row["deliverable"],
                    owner=row.get("owner") or "",
                )
            )
    ids = {t.id for t in tasks}
    for t in tasks:
        missing = [d for d in t.depends if d not in ids]
        if missing:
            raise SystemExit(f"{t.id} 的相依任務不存在：{missing}")
        if t.end < t.start:
            raise SystemExit(f"{t.id} 的結束日早於開始日")
        if t.status not in STATUS_LABEL:
            raise SystemExit(f"{t.id} 的 status 不正確：{t.status}")
    return tasks


def late_tasks(tasks: list[Task], today: date) -> list[Task]:
    return [t for t in tasks if t.status in ("todo", "doing") and t.end < today]


def summary(tasks: list[Task], today: date) -> dict:
    work = [t for t in tasks if not t.is_milestone and t.status != "optional"]
    done = sum(t.status == "done" for t in work)
    upcoming = [t for t in tasks if t.is_milestone and t.start >= today]
    deadline = next(t for t in tasks if t.id == DEADLINE_ID).start
    return {
        "done": done,
        "total": len(work),
        "pct": round(100 * done / len(work)) if work else 0,
        "doing": [t for t in tasks if t.status == "doing"],
        "late": late_tasks(tasks, today),
        "next_milestone": upcoming[0] if upcoming else None,
        "days_to_deadline": (deadline - today).days,
    }


# ---------- HTML ----------

DAY_W = 11
LABEL_W = 340
ROW_H = 26
PHASE_H = 30
AXIS_H = 60


def build_svg(tasks: list[Task], today: date, exam: tuple[date, date] | None) -> str:
    lo = min(t.start for t in tasks) - timedelta(days=1)
    hi = max(t.end for t in tasks) + timedelta(days=2)
    days = (hi - lo).days
    width = LABEL_W + days * DAY_W + 24

    def x(d: date) -> float:
        return LABEL_W + (d - lo).days * DAY_W

    rows: list[tuple[str, object]] = []
    for phase in dict.fromkeys(t.phase for t in tasks):
        rows.append(("phase", phase))
        rows.extend(("task", t) for t in tasks if t.phase == phase)
    height = AXIS_H + sum(PHASE_H if kind == "phase" else ROW_H for kind, _ in rows) + 16

    out = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" '
        f'aria-label="專案執行甘特圖" class="gantt">'
    ]
    # 期中考週
    if exam:
        out.append(
            f'<rect x="{x(exam[0])}" y="{AXIS_H - 6}" width="{(exam[1] - exam[0]).days * DAY_W + DAY_W}" '
            f'height="{height - AXIS_H}" class="exam"/>'
            f'<text x="{x(exam[0]) + 4}" y="{height - 6}" class="exam-label">期中考週（各自確認）</text>'
        )
    # 週刻度（每週一）
    d = lo + timedelta(days=(7 - lo.weekday()) % 7)
    while d <= hi:
        out.append(
            f'<line x1="{x(d)}" x2="{x(d)}" y1="{AXIS_H - 6}" y2="{height}" class="grid"/>'
            f'<text x="{x(d)}" y="{AXIS_H - 14}" class="tick">{d.month}/{d.day}</text>'
        )
        d += timedelta(days=7)
    # 月份
    m = date(lo.year, lo.month, 1)
    while m <= hi:
        mx = max(x(m), LABEL_W)
        out.append(f'<text x="{mx + 2}" y="14" class="month">{m.year} 年 {m.month} 月</text>')
        m = date(m.year + (m.month // 12), m.month % 12 + 1, 1)

    y = AXIS_H
    for kind, item in rows:
        if kind == "phase":
            out.append(
                f'<rect x="0" y="{y + 4}" width="{width}" height="{PHASE_H - 8}" class="phase-bg"/>'
                f'<text x="8" y="{y + PHASE_H / 2 + 5}" class="phase">{html.escape(item)}</text>'
            )
            y += PHASE_H
            continue
        t: Task = item
        cy = y + ROW_H / 2
        g = "g-" + GROUP_CLASS[t.group]
        tip = f"{t.id} {t.task}｜{GROUP_LABEL[t.group]}｜{t.owner}｜{t.start:%m/%d}–{t.end:%m/%d}｜{STATUS_LABEL[t.status]}"
        late = t in late_tasks([t], today)
        label_cls = "label late" if late else "label"
        out.append(f'<g class="row {g} s-{t.status}"><title>{html.escape(tip)}</title>')
        out.append(f'<text x="8" y="{cy + 4}" class="tid">{t.id}</text>')
        out.append(f'<text x="44" y="{cy + 4}" class="{label_cls}">{html.escape(t.task[:24] + ("…" if len(t.task) > 24 else ""))}</text>')
        if t.is_milestone:
            mx = x(t.start) + DAY_W / 2
            cls = "ms deadline" if t.id == DEADLINE_ID else "ms"
            out.append(f'<path d="M{mx} {cy - 8}l8 8l-8 8l-8 -8z" class="{cls}"/>')
            out.append(f'<text x="{mx + 12}" y="{cy + 4}" class="date">{t.start.month}/{t.start.day}</text>')
        else:
            bx, bw = x(t.start) + 1, (t.end - t.start).days * DAY_W + DAY_W - 2
            out.append(f'<rect x="{bx}" y="{cy - 8}" width="{bw}" height="16" rx="4" class="bar"/>')
            if t.status == "doing":
                out.append(f'<rect x="{bx}" y="{cy - 8}" width="{bw / 2}" height="16" rx="4" class="bar-fill"/>')
            if t.status == "done":
                out.append(f'<text x="{bx + bw + 6}" y="{cy + 4}" class="date">✓</text>')
        out.append("</g>")
        y += ROW_H

    # 今日線
    if lo <= today <= hi:
        tx = x(today) + DAY_W / 2
        out.append(
            f'<line x1="{tx}" x2="{tx}" y1="{AXIS_H - 6}" y2="{height}" class="today"/>'
            f'<text x="{tx + 4}" y="32" class="today-label">今天 {today.month}/{today.day}</text>'
        )
    out.append("</svg>")
    return "\n".join(out)


def build_html(tasks: list[Task], today: date, exam: tuple[date, date] | None) -> str:
    s = summary(tasks, today)
    nm = s["next_milestone"]
    nm_text = f"{nm.task.replace('里程碑：', '')}（{nm.start.month}/{nm.start.day}）" if nm else "—"
    late_html = (
        "".join(f"<li><b>{t.id}</b> {html.escape(t.task)}（應於 {t.end.month}/{t.end.day} 完成）</li>" for t in s["late"])
        or "<li>沒有落後的任務</li>"
    )
    doing_html = "".join(f"<li><b>{t.id}</b> {html.escape(t.task)}</li>" for t in s["doing"]) or "<li>—</li>"

    rows = "".join(
        f'<tr class="s-{t.status}"><td>{t.id}</td><td>{html.escape(t.task)}</td><td>{GROUP_LABEL[t.group].split("（")[0]}</td><td>{html.escape(t.owner) or "—"}</td>'
        f"<td>{t.start.month}/{t.start.day}–{t.end.month}/{t.end.day}</td>"
        f"<td>{'、'.join(t.depends) or '—'}</td><td><span class=\"pill p-{t.status}\">{STATUS_LABEL[t.status]}</span></td>"
        f"<td>{html.escape(t.deliverable) or '—'}</td></tr>"
        for t in tasks
    )
    legend = "".join(
        f'<span class="lg"><i class="sw g-{k}"></i>{GROUP_LABEL[g]}</span>'
        for g, k in GROUP_CLASS.items()
    )

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JNC-AIoT 甘特圖</title>
<style>
:root {{
  --bg:#f7f7f5; --card:#fff; --ink:#1d1d1b; --muted:#6b6b66; --line:#e3e2dc; --phase:#efeee8;
  --p1:#13896f; --p2:#2f6fd6; --p3:#c07a12; --p4:#c0392b; --p5:#8a4fd1; --p6:#0f8aa8; --all:#7a7a72;
  --today:#d13b3b; --exam:rgba(230,160,40,.12); --late:#c0392b; --deadline:#d13b3b;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg:#161615; --card:#1f1f1d; --ink:#ecebe6; --muted:#a3a29b; --line:#34332f; --phase:#2a2a27;
    --p1:#3fc4a2; --p2:#6b9ef0; --p3:#e9a94a; --p4:#f07a6b; --p5:#b58cf0; --p6:#4cc3dd; --all:#a8a8a0;
    --today:#f06b6b; --exam:rgba(230,160,40,.14); --late:#f07a6b; --deadline:#f06b6b;
  }}
}}
:root[data-theme="dark"] {{
  --bg:#161615; --card:#1f1f1d; --ink:#ecebe6; --muted:#a3a29b; --line:#34332f; --phase:#2a2a27;
  --p1:#3fc4a2; --p2:#6b9ef0; --p3:#e9a94a; --p4:#f07a6b; --p5:#b58cf0; --p6:#4cc3dd; --all:#a8a8a0;
  --today:#f06b6b; --exam:rgba(230,160,40,.14); --late:#f07a6b; --deadline:#f06b6b;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:14px/1.6 -apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif; }}
main {{ max-width:1240px; margin:0 auto; padding:24px 16px 48px; }}
h1 {{ font-size:22px; margin:0 0 4px; }}
.sub {{ color:var(--muted); margin:0 0 20px; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin-bottom:16px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
.card .k {{ color:var(--muted); font-size:12px; }}
.card .v {{ font-size:22px; font-weight:650; }}
.card ul {{ margin:6px 0 0; padding-left:18px; }}
.meter {{ height:6px; background:var(--line); border-radius:3px; margin-top:8px; overflow:hidden; }}
.meter i {{ display:block; height:100%; background:var(--p1); }}
.legend {{ display:flex; flex-wrap:wrap; gap:14px; margin:8px 0 10px; color:var(--muted); font-size:12.5px; }}
.lg {{ display:inline-flex; align-items:center; gap:6px; }}
.sw {{ width:14px; height:10px; border-radius:3px; display:inline-block; background:var(--g); }}
.scroll {{ overflow-x:auto; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:8px 0; }}
svg.gantt {{ display:block; font-size:12.5px; }}
.g-p1 {{ --g:var(--p1); }} .g-p2 {{ --g:var(--p2); }} .g-p3 {{ --g:var(--p3); }} .g-p4 {{ --g:var(--p4); }}
.g-p5 {{ --g:var(--p5); }} .g-p6 {{ --g:var(--p6); }} .g-all {{ --g:var(--all); }}
.grid {{ stroke:var(--line); }}
.tick, .month, .date {{ fill:var(--muted); font-size:11.5px; }}
.tick {{ text-anchor:middle; }}
.month {{ font-weight:600; }}
.phase-bg {{ fill:var(--phase); }}
.phase {{ fill:var(--ink); font-weight:650; }}
.tid {{ fill:var(--muted); font-size:11.5px; }}
.label {{ fill:var(--ink); }}
.label.late {{ fill:var(--late); font-weight:600; }}
.bar {{ fill:var(--g); fill-opacity:.16; stroke:var(--g); stroke-width:1.25; }}
.s-done .bar {{ fill-opacity:.85; }}
.bar-fill {{ fill:var(--g); fill-opacity:.85; }}
.s-optional .bar {{ stroke-dasharray:4 3; fill-opacity:.06; }}
.s-done .label {{ fill:var(--muted); }}
.ms {{ fill:var(--g); }}
.ms.deadline {{ fill:var(--deadline); }}
.exam {{ fill:var(--exam); }}
.exam-label {{ fill:var(--muted); font-size:11px; }}
.today {{ stroke:var(--today); stroke-width:1.5; stroke-dasharray:4 3; }}
.today-label {{ fill:var(--today); font-size:11.5px; font-weight:600; }}
table {{ width:100%; border-collapse:collapse; margin-top:20px; background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden; font-size:13px; }}
th, td {{ text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ color:var(--muted); font-weight:600; font-size:12px; }}
tr.s-done td {{ color:var(--muted); }}
.pill {{ font-size:11.5px; padding:1px 8px; border-radius:999px; border:1px solid var(--line); white-space:nowrap; }}
.p-done {{ background:color-mix(in srgb,var(--p1) 18%,transparent); }}
.p-doing {{ background:color-mix(in srgb,var(--p2) 18%,transparent); }}
.p-optional {{ border-style:dashed; }}
.tablewrap {{ overflow-x:auto; }}
footer {{ color:var(--muted); font-size:12px; margin-top:16px; }}
</style>
</head>
<body>
<main>
<h1>AIoT 預測維護與異常診斷：執行甘特圖</h1>
<p class="sub">2026 全國 AI 專題創意競賽・企業命題類 AI 應用組（銘祥科技）｜資料日期 {today.year}/{today.month}/{today.day}</p>

<section class="stats">
  <div class="card"><div class="k">整體進度（不含里程碑與選做）</div><div class="v">{s['done']} / {s['total']}（{s['pct']}%）</div><div class="meter"><i style="width:{s['pct']}%"></i></div></div>
  <div class="card"><div class="k">距報名繳件截止 12/1</div><div class="v">{s['days_to_deadline']} 天</div></div>
  <div class="card"><div class="k">下一個里程碑</div><div class="v" style="font-size:16px">{html.escape(nm_text)}</div></div>
  <div class="card"><div class="k">進行中</div><ul>{doing_html}</ul></div>
  <div class="card"><div class="k">落後任務</div><ul>{late_html}</ul></div>
</section>

<div class="legend">{legend}<span class="lg">實心＝完成、半滿＝進行中、虛線＝選做、◆＝里程碑、紅色虛線＝今天、橘色區＝期中考週</span></div>
<div class="scroll">{build_svg(tasks, today, exam)}</div>

<div class="tablewrap"><table>
<thead><tr><th>ID</th><th>任務</th><th>角色</th><th>負責人</th><th>期間</th><th>前置</th><th>狀態</th><th>交付物</th></tr></thead>
<tbody>{rows}</tbody>
</table></div>
<footer>由 scripts/build_gantt.py 從 schedule/tasks.csv 產生，請勿手動修改本檔。</footer>
</main>
</body>
</html>
"""


# ---------- Mermaid ----------

def build_md(tasks: list[Task], today: date) -> str:
    s = summary(tasks, today)
    lines = [
        "# 執行甘特圖（Mermaid 版）",
        "",
        f"> 由 `scripts/build_gantt.py` 從 `tasks.csv` 產生，資料日期 {today:%Y-%m-%d}。",
        f"> 進度 {s['done']}/{s['total']}（{s['pct']}%），距 12/1 截止 {s['days_to_deadline']} 天。",
        "> 互動版請開 [gantt.html](gantt.html)。",
        "",
        "```mermaid",
        "gantt",
        "    title 銘祥科技 AIoT 預測維護與異常診斷",
        "    dateFormat YYYY-MM-DD",
        "    axisFormat %m/%d",
        f"    todayMarker stroke-width:2px,stroke:#d13b3b",
    ]
    tag = {"done": "done, ", "doing": "active, ", "todo": "", "optional": ""}
    for phase in dict.fromkeys(t.phase for t in tasks):
        lines.append(f"    section {phase}")
        for t in (t for t in tasks if t.phase == phase):
            name = t.task.replace(":", "：")
            if t.is_milestone:
                crit = "crit, " if t.id == DEADLINE_ID else ""
                lines.append(f"    {name} :{crit}milestone, {t.id}, {t.start}, 0d")
            else:
                dur = (t.end - t.start).days + 1
                lines.append(f"    [{t.owner or t.group}] {name} :{tag[t.status]}{t.id}, {t.start}, {dur}d")
    lines += ["```", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    ap.add_argument("--exam", default="2026-11-02:2026-11-13", help="期中考週 起:迄，空字串表示不顯示")
    args = ap.parse_args()
    exam = tuple(date.fromisoformat(p) for p in args.exam.split(":")) if args.exam else None

    tasks = load_tasks(TASKS_CSV)
    OUT_HTML.write_text(build_html(tasks, args.today, exam), encoding="utf-8")
    OUT_MD.write_text(build_md(tasks, args.today), encoding="utf-8")
    s = summary(tasks, args.today)
    print(f"已產生 {OUT_HTML.relative_to(ROOT)} 與 {OUT_MD.relative_to(ROOT)}")
    print(f"進度 {s['done']}/{s['total']}（{s['pct']}%），落後 {len(s['late'])} 項，距截止 {s['days_to_deadline']} 天")


if __name__ == "__main__":
    main()
