from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "reports" / "dongchedi_daily"
SITE_ROOT = ROOT / "site"


def _report_dirs() -> list[Path]:
    if not REPORT_ROOT.exists():
        return []

    dirs: list[Path] = []
    for path in REPORT_ROOT.iterdir():
        if not path.is_dir():
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.name):
            continue
        if (path / "filtered.csv").exists() and (path / "charging_visualization_dashboard.html").exists():
            dirs.append(path)
    return sorted(dirs)


def _latest_report_dir() -> Path:
    dirs = _report_dirs()
    if not dirs:
        raise FileNotFoundError("No generated Dongchedi report found under reports/dongchedi_daily")
    return dirs[-1]


def _copy_report_dir(report_dir: Path) -> None:
    target = SITE_ROOT / "reports" / report_dir.name
    target.mkdir(parents=True, exist_ok=True)

    for item in report_dir.iterdir():
        if item.is_file() and item.suffix.lower() in {".html", ".csv", ".json", ".md"}:
            shutil.copy2(item, target / item.name)

    summary_md = report_dir / "summary.md"
    if summary_md.exists():
      summary_html = "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>摘要</title><style>body{font-family:Segoe UI,PingFang SC,Microsoft YaHei,sans-serif;line-height:1.7;margin:24px;background:#faf7f2;color:#12202b}pre{white-space:pre-wrap;word-break:break-word;background:#fff;border:1px solid rgba(18,32,43,.14);border-radius:16px;padding:20px;box-shadow:0 10px 28px rgba(0,0,0,.05)}</style></head><body><pre>"
      summary_html += html.escape(summary_md.read_text(encoding="utf-8"))
      summary_html += "</pre></body></html>"
      (target / "summary.html").write_text(summary_html, encoding="utf-8")


def _write_latest_alias(report_dir: Path) -> None:
    latest_dir = SITE_ROOT / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)

    dashboard_src = report_dir / "charging_visualization_dashboard.html"
    shutil.copy2(dashboard_src, latest_dir / "charging_visualization_dashboard.html")

    index_html = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta http-equiv="refresh" content="0; url=charging_visualization_dashboard.html" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>最新懂车帝充电数据可视化</title>
</head>
<body>
  <p>正在跳转到最新可视化页面。若未自动跳转，请打开 <a href="charging_visualization_dashboard.html">charging_visualization_dashboard.html</a>。</p>
</body>
</html>
"""
    (latest_dir / "index.html").write_text(index_html, encoding="utf-8")


def _build_index_html(report_dirs: list[Path], latest_report: Path) -> str:
    latest_date = latest_report.name
    cards = []
    for report_dir in reversed(report_dirs):
        dashboard = f"reports/{report_dir.name}/charging_visualization_dashboard.html"
    summary = f"reports/{report_dir.name}/summary.html"
    confluence = f"reports/{report_dir.name}/confluence_section.html"
    cards.append(
      "<article class=\"card\">"
      f"<div class=\"date\">{html.escape(report_dir.name)}</div>"
      f"<a class=\"primary\" href=\"{dashboard}\">打开可视化仪表盘</a>"
      f"<div class=\"links\"><a href=\"{summary}\">summary.html</a><a href=\"{confluence}\">confluence_section.html</a></div>"
      "</article>"
    )

    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>懂车帝充电数据网站</title>
  <style>
    :root {{
      --bg1: #fff6eb;
      --bg2: #edf5ff;
      --ink: #12202b;
      --muted: #5d6874;
      --line: rgba(18, 32, 43, 0.14);
      --card: rgba(255, 255, 255, 0.86);
      --accent: #c55300;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 480px at 0% 0%, #ffd9b7 0%, transparent 55%),
        radial-gradient(1000px 520px at 100% 10%, #c4e0ff 0%, transparent 55%),
        linear-gradient(145deg, var(--bg1), var(--bg2));
      min-height: 100vh;
      padding: 24px;
    }}
    .shell {{ max-width: 1240px; margin: 0 auto; }}
    .hero {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 24px;
      box-shadow: 0 18px 50px rgba(0, 0, 0, 0.08);
      backdrop-filter: blur(8px);
    }}
    h1 {{ margin: 0; font-size: 34px; }}
    .sub {{ color: var(--muted); margin: 10px 0 0; line-height: 1.7; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 18px; }}
    .button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px 16px;
      border-radius: 999px;
      text-decoration: none;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.92);
      color: var(--ink);
      font-weight: 600;
    }}
    .button.primary {{
      background: linear-gradient(135deg, #d45b00, #ff8a00);
      border-color: transparent;
      color: white;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
      color: var(--muted);
      font-size: 13px;
    }}
    .pill {{
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.74);
      border: 1px solid var(--line);
    }}
    .section-title {{ margin: 26px 4px 12px; font-size: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 28px rgba(0, 0, 0, 0.05);
    }}
    .date {{ font-size: 20px; font-weight: 700; margin-bottom: 12px; }}
    .primary {{
      display: inline-block;
      margin-bottom: 12px;
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }}
    .links {{ display: flex; flex-wrap: wrap; gap: 12px; font-size: 13px; }}
    .links a {{ color: var(--muted); text-decoration: none; }}
    .foot {{ margin: 18px 4px 0; color: var(--muted); font-size: 12px; line-height: 1.6; }}
    @media (max-width: 700px) {{ body {{ padding: 12px; }} h1 {{ font-size: 28px; }} }}
  </style>
</head>
<body>
  <div class=\"shell\">
    <section class=\"hero\">
      <h1>懂车帝充电数据网站</h1>
      <p class=\"sub\">站点内容来自懂车帝充电数据日报和自动生成的可视化图表。最新页面会同步到固定入口，历史日报保留在归档目录中。</p>
      <div class=\"actions\">
        <a class=\"button primary\" href=\"latest/charging_visualization_dashboard.html\">打开最新可视化</a>
        <a class=\"button\" href=\"reports/{latest_date}/summary.md\">查看最新摘要</a>
      </div>
      <div class=\"meta\">
        <span class=\"pill\">最新日期: {latest_date}</span>
        <span class=\"pill\">日报数量: {len(report_dirs)}</span>
        <span class=\"pill\">更新方式: GitHub Actions 定时发布</span>
      </div>
    </section>

    <h2 class=\"section-title\">历史归档</h2>
    <section class=\"grid\">
      {''.join(cards)}
    </section>

    <div class=\"foot\">提示：如果你希望站点真正“每天有新数据”，还需要让上游懂车帝源文件每天刷新或接入自动抓取步骤。Pages 这一层负责把最新结果公开发布出来。</div>
  </div>
</body>
</html>
"""


def main() -> None:
    latest_report = _latest_report_dir()
    report_dirs = _report_dirs()

    SITE_ROOT.mkdir(parents=True, exist_ok=True)

    for report_dir in report_dirs:
        _copy_report_dir(report_dir)

    _write_latest_alias(latest_report)
    (SITE_ROOT / "index.html").write_text(_build_index_html(report_dirs, latest_report), encoding="utf-8")

    print(json.dumps({"status": "ok", "latest_report": latest_report.name, "reports": len(report_dirs)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()