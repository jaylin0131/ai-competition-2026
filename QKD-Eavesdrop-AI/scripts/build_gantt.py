"""從 schedule/tasks.csv 產生甘特圖。

輸出：
- schedule/gantt.html：可直接用瀏覽器開啟的甘特圖（含今日線、期中考週、進度統計）
- schedule/gantt.md：Mermaid 版甘特圖，GitHub 上會直接渲染

用法（在專案根目錄執行）：
    python3 scripts/build_gantt.py
    python3 scripts/build_gantt.py --today 2026-10-20 --exam 2026-11-02:2026-11-13

更新進度的方式：只改 tasks.csv 的 status 欄（todo / doing / done / optional），再重新執行本程式。
owner 欄填 schedule/team.csv 裡的姓名，多人用「、」分隔、第一位是主責；「全員」代表所有人。
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
TEAM_CSV = ROOT / "schedule" / "team.csv"
ALL_MEMBERS = "全員"
UPCOMING_DAYS = 14

STATUS_LABEL = {"done": "完成", "doing": "進行中", "todo": "未開始", "optional": "進階選做"}
GROUP_ORDER = ["A", "B", "A+B", "C", "全員"]
GROUP_LABEL = {"A": "A 組 通訊", "B": "B 組 機器學習", "A+B": "A＋B 組", "C": "C 組 PM", "全員": "全員"}
DEADLINE_ID = "M7"


@dataclass
class Task:
    id: str
    phase: str
    group: str
    owners: list[str]
    task: str
    start: date
    end: date
    depends: list[str]
    status: str
    deliverable: str

    @property
    def is_milestone(self) -> bool:
        return self.id.startswith("M")

    @property
    def lead(self) -> str:
        return self.owners[0] if self.owners else ""


@dataclass
class Member:
    name: str
    dept: str
    group: str
    role: str


def load_team(path: Path) -> list[Member]:
    with path.open(encoding="utf-8") as f:
        return [Member(**row) for row in csv.DictReader(f)]


def load_tasks(path: Path, team: list[Member]) -> list[Task]:
    tasks = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tasks.append(
                Task(
                    id=row["id"],
                    phase=row["phase"],
                    group=row["group"],
                    owners=[o for o in row["owner"].split("、") if o],
                    task=row["task"],
                    start=date.fromisoformat(row["start"]),
                    end=date.fromisoformat(row["end"]),
                    depends=[d for d in row["depends"].split(";") if d],
                    status=row["status"],
                    deliverable=row["deliverable"],
                )
            )
    ids = {t.id for t in tasks}
    names = {m.name for m in team} | {ALL_MEMBERS}
    for t in tasks:
        missing = [d for d in t.depends if d not in ids]
        if missing:
            raise SystemExit(f"{t.id} 的相依任務不存在：{missing}")
        if t.end < t.start:
            raise SystemExit(f"{t.id} 的結束日早於開始日")
        if t.status not in STATUS_LABEL:
            raise SystemExit(f"{t.id} 的 status 不正確：{t.status}")
        unknown = [o for o in t.owners if o not in names]
        if unknown:
            raise SystemExit(f"{t.id} 的負責人不在 team.csv：{unknown}")
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
LABEL_W = 370
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
        g = "g-" + {"A": "a", "B": "b", "A+B": "ab", "C": "c", "全員": "all"}[t.group]
        tip = f"{t.id} {t.task}｜{'、'.join(t.owners) or GROUP_LABEL[t.group]}｜{t.start:%m/%d}–{t.end:%m/%d}｜{STATUS_LABEL[t.status]}"
        late = t in late_tasks([t], today)
        label_cls = "label late" if late else "label"
        out.append(f'<g class="row {g} s-{t.status}"><title>{html.escape(tip)}</title>')
        out.append(f'<text x="8" y="{cy + 4}" class="tid">{t.id}</text>')
        out.append(f'<text x="44" y="{cy + 4}" class="{label_cls}">{html.escape(t.task[:18] + ("…" if len(t.task) > 18 else ""))}</text>')
        if t.lead:
            out.append(f'<text x="{LABEL_W - 10}" y="{cy + 4}" class="owner">{html.escape(t.lead)}</text>')
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


def owners_html(t: Task) -> str:
    if not t.owners:
        return "—"
    first, *rest = t.owners
    return "<b>" + html.escape(first) + "</b>" + "".join("、" + html.escape(o) for o in rest)


def build_people(tasks: list[Task], team: list[Member], today: date) -> str:
    """每位成員的任務清單：主責／協助、兩週內要做的任務標示出來。"""
    soon = today + timedelta(days=UPCOMING_DAYS)
    shared = [t for t in tasks if ALL_MEMBERS in t.owners and t.status != "done"]
    cards = []
    for m in team:
        mine = [t for t in tasks if m.name in t.owners and not t.is_milestone]
        open_ = [t for t in mine if t.status != "done"]
        lead_n = sum(t.lead == m.name for t in open_)
        items = "".join(
            f'<li class="{"soon" if t.start <= soon else ""}"><b>{t.id}</b> {html.escape(t.task)}'
            f'<span class="when">{t.start.month}/{t.start.day}–{t.end.month}/{t.end.day}'
            f'{"・主責" if t.lead == m.name else "・協助"}</span></li>'
            for t in sorted(open_, key=lambda t: t.start)
        ) or "<li>—</li>"
        g = {"A": "a", "B": "b", "C": "c"}.get(m.group, "all")
        cards.append(
            f'<div class="card person g-{g}"><div class="pname"><i class="sw"></i>{html.escape(m.name)}</div>'
            f'<div class="k">{html.escape(m.dept)}｜{html.escape(m.role)}</div>'
            f'<div class="k">未完成 {len(open_)} 項（主責 {lead_n}）＋全員任務 {len(shared)} 項</div>'
            f'<ul class="tasks">{items}</ul></div>'
        )
    return "".join(cards)


def build_html(tasks: list[Task], team: list[Member], today: date, exam: tuple[date, date] | None) -> str:
    s = summary(tasks, today)
    nm = s["next_milestone"]
    nm_text = f"{nm.task.replace('里程碑：', '')}（{nm.start.month}/{nm.start.day}）" if nm else "—"
    late_html = (
        "".join(f"<li><b>{t.id}</b> {html.escape(t.task)}（應於 {t.end.month}/{t.end.day} 完成）</li>" for t in s["late"])
        or "<li>沒有落後的任務</li>"
    )
    doing_html = "".join(f"<li><b>{t.id}</b> {html.escape(t.task)}</li>" for t in s["doing"]) or "<li>—</li>"

    rows = "".join(
        f'<tr class="s-{t.status}"><td>{t.id}</td><td>{html.escape(t.task)}</td><td>{GROUP_LABEL[t.group]}</td><td>{owners_html(t)}</td>'
        f"<td>{t.start.month}/{t.start.day}–{t.end.month}/{t.end.day}</td>"
        f"<td>{'、'.join(t.depends) or '—'}</td><td><span class=\"pill p-{t.status}\">{STATUS_LABEL[t.status]}</span></td>"
        f"<td>{html.escape(t.deliverable) or '—'}</td></tr>"
        for t in tasks
    )
    legend = "".join(
        f'<span class="lg"><i class="sw g-{k}"></i>{GROUP_LABEL[g]}</span>'
        for g, k in zip(GROUP_ORDER, ["a", "b", "ab", "c", "all"])
    )

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QKD 專案甘特圖</title>
<style>
:root {{
  --bg:#f7f7f5; --card:#fff; --ink:#1d1d1b; --muted:#6b6b66; --line:#e3e2dc; --phase:#efeee8;
  --a:#2f6fd6; --b:#8a4fd1; --ab:#4f5fd1; --c:#13896f; --all:#7a7a72;
  --today:#d13b3b; --exam:rgba(230,160,40,.12); --late:#c0392b; --deadline:#d13b3b;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg:#161615; --card:#1f1f1d; --ink:#ecebe6; --muted:#a3a29b; --line:#34332f; --phase:#2a2a27;
    --a:#6b9ef0; --b:#b58cf0; --ab:#8a96f0; --c:#3fc4a2; --all:#a8a8a0;
    --today:#f06b6b; --exam:rgba(230,160,40,.14); --late:#f07a6b; --deadline:#f06b6b;
  }}
}}
:root[data-theme="dark"] {{
  --bg:#161615; --card:#1f1f1d; --ink:#ecebe6; --muted:#a3a29b; --line:#34332f; --phase:#2a2a27;
  --a:#6b9ef0; --b:#b58cf0; --ab:#8a96f0; --c:#3fc4a2; --all:#a8a8a0;
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
.meter i {{ display:block; height:100%; background:var(--c); }}
.legend {{ display:flex; flex-wrap:wrap; gap:14px; margin:8px 0 10px; color:var(--muted); font-size:12.5px; }}
.lg {{ display:inline-flex; align-items:center; gap:6px; }}
.sw {{ width:14px; height:10px; border-radius:3px; display:inline-block; background:var(--g); }}
.scroll {{ overflow-x:auto; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:8px 0; }}
svg.gantt {{ display:block; font-size:12.5px; }}
.g-a {{ --g:var(--a); }} .g-b {{ --g:var(--b); }} .g-ab {{ --g:var(--ab); }} .g-c {{ --g:var(--c); }} .g-all {{ --g:var(--all); }}
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
.p-done {{ background:color-mix(in srgb,var(--c) 18%,transparent); }}
.p-doing {{ background:color-mix(in srgb,var(--a) 18%,transparent); }}
.p-optional {{ border-style:dashed; }}
.tablewrap {{ overflow-x:auto; }}
h2 {{ font-size:17px; margin:28px 0 2px; }}
.owner {{ fill:var(--muted); font-size:11.5px; text-anchor:end; }}
.people {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:12px; }}
.pname {{ font-weight:650; font-size:16px; display:flex; align-items:center; gap:8px; }}
.person .sw {{ background:var(--g); }}
.tasks {{ list-style:none; padding:0; margin:8px 0 0; font-size:13px; }}
.tasks li {{ padding:4px 0; border-top:1px solid var(--line); color:var(--muted); }}
.tasks li.soon {{ color:var(--ink); font-weight:600; }}
.when {{ display:block; font-size:11.5px; font-weight:400; color:var(--muted); }}
footer {{ color:var(--muted); font-size:12px; margin-top:16px; }}
</style>
</head>
<body>
<main>
<h1>QKD 鏈路 AI 健康診斷：執行甘特圖</h1>
<p class="sub">2026 全國 AI 專題創意競賽・大會專題類資電領域組｜資料日期 {today.year}/{today.month}/{today.day}</p>

<section class="stats">
  <div class="card"><div class="k">整體進度（不含里程碑與選做）</div><div class="v">{s['done']} / {s['total']}（{s['pct']}%）</div><div class="meter"><i style="width:{s['pct']}%"></i></div></div>
  <div class="card"><div class="k">距報名繳件截止 12/1</div><div class="v">{s['days_to_deadline']} 天</div></div>
  <div class="card"><div class="k">下一個里程碑</div><div class="v" style="font-size:16px">{html.escape(nm_text)}</div></div>
  <div class="card"><div class="k">進行中</div><ul>{doing_html}</ul></div>
  <div class="card"><div class="k">落後任務</div><ul>{late_html}</ul></div>
</section>

<div class="legend">{legend}<span class="lg">實心＝完成、半滿＝進行中、虛線＝選做、◆＝里程碑、紅色虛線＝今天、橘色區＝期中考週</span></div>
<div class="scroll">{build_svg(tasks, today, exam)}</div>

<h2>人員分工</h2>
<p class="sub">粗體＝兩週內開始的任務。主責負責交付，協助者分擔實作。</p>
<section class="people">{build_people(tasks, team, today)}</section>

<div class="tablewrap"><table>
<thead><tr><th>ID</th><th>任務</th><th>組別</th><th>負責人</th><th>期間</th><th>前置</th><th>狀態</th><th>交付物</th></tr></thead>
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
        "    title QKD 鏈路 AI 健康診斷",
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
                who = t.lead or t.group
                lines.append(f"    [{who}] {name} :{tag[t.status]}{t.id}, {t.start}, {dur}d")
    lines += ["```", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    ap.add_argument("--exam", default="2026-11-02:2026-11-13", help="期中考週 起:迄，空字串表示不顯示")
    args = ap.parse_args()
    exam = tuple(date.fromisoformat(p) for p in args.exam.split(":")) if args.exam else None

    team = load_team(TEAM_CSV)
    tasks = load_tasks(TASKS_CSV, team)
    OUT_HTML.write_text(build_html(tasks, team, args.today, exam), encoding="utf-8")
    OUT_MD.write_text(build_md(tasks, args.today), encoding="utf-8")
    s = summary(tasks, args.today)
    print(f"已產生 {OUT_HTML.relative_to(ROOT)} 與 {OUT_MD.relative_to(ROOT)}")
    print(f"進度 {s['done']}/{s['total']}（{s['pct']}%），落後 {len(s['late'])} 項，距截止 {s['days_to_deadline']} 天")


if __name__ == "__main__":
    main()
