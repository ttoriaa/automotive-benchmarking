from __future__ import annotations

import argparse
import csv
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


def _report_dir_for_date(date_text: str) -> Path:
  report_dir = REPORT_ROOT / date_text
  if not report_dir.exists() or not report_dir.is_dir():
    raise FileNotFoundError(f"Report date folder not found: {report_dir}")
  if not (report_dir / "filtered.csv").exists():
    raise FileNotFoundError(f"filtered.csv not found under report date: {report_dir}")
  return report_dir


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


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict((k, str(v).strip()) for k, v in row.items()) for row in csv.DictReader(f)]


def _num(value: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)", str(value or ""))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    mid = n // 2
    if n % 2 == 1:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def _top_brands(rows: list[dict[str, str]], top_n: int = 8) -> list[tuple[str, int]]:
    cnt: dict[str, int] = {}
    for r in rows:
        brand = (r.get("品牌") or "未明确").strip()
        cnt[brand] = cnt.get(brand, 0) + 1
    return sorted(cnt.items(), key=lambda x: (-x[1], x[0]))[:top_n]


def _is_missing_badge_value(value: str) -> bool:
  text = (value or "").strip()
  return text in {"未明确显示", "未完全显示"}


def _render_table_cell(value: str) -> str:
  text = str(value or "")
  if _is_missing_badge_value(text):
    return f'<span class="missing-badge">{html.escape(text)}</span>'
  return html.escape(text)


def _base_style() -> str:
    return """
  <style>
    :root {
      --bg1: #fff6eb;
      --bg2: #edf5ff;
      --ink: #12202b;
      --muted: #5d6874;
      --line: rgba(18, 32, 43, 0.14);
      --card: rgba(255, 255, 255, 0.88);
      --accent: #c55300;
      --accent-2: #ff8a00;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 480px at 0% 0%, #ffd9b7 0%, transparent 55%),
        radial-gradient(1000px 520px at 100% 10%, #c4e0ff 0%, transparent 55%),
        linear-gradient(145deg, var(--bg1), var(--bg2));
      min-height: 100vh;
      padding: 20px;
    }
    .shell { max-width: 1280px; margin: 0 auto; }
    .nav {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 14px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 10px;
      box-shadow: 0 12px 30px rgba(0,0,0,.06);
    }
    .nav a {
      text-decoration: none;
      color: var(--ink);
      padding: 8px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #fff;
      font-weight: 600;
      font-size: 14px;
    }
    .nav a.active {
      color: #fff;
      border-color: transparent;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
    }
    .nav-spacer {
      flex: 1;
    }
    .lang-switch {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .lang-btn {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      padding: 7px 11px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }
    .lang-btn.active {
      color: #fff;
      border-color: transparent;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
    }
    .panel {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      box-shadow: 0 16px 42px rgba(0,0,0,.08);
    }
    h1 { margin: 0 0 8px; font-size: 34px; }
    h2 { margin: 0 0 8px; font-size: 22px; }
    .sub { color: var(--muted); line-height: 1.7; margin: 6px 0 0; }
    .meta { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
    .pill {
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 13px;
      color: var(--muted);
    }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-top: 14px; }
    .card {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      padding: 14px;
    }
    .table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      margin-top: 14px;
    }
    table { border-collapse: collapse; width: 100%; font-size: 13px; }
    th, td { border-bottom: 1px solid #edf0f3; padding: 8px 10px; text-align: left; white-space: nowrap; }
    th { position: sticky; top: 0; background: #f8fafc; z-index: 1; }
    .frame {
      width: 100%;
      height: min(78vh, 920px);
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      margin-top: 12px;
    }
    .missing-badge {
      display: inline-flex;
      align-items: center;
      padding: 3px 8px;
      border-radius: 999px;
      border: 1px solid rgba(93, 104, 116, 0.18);
      background: #eef2f6;
      color: #6b7683;
      font-size: 12px;
      font-weight: 600;
      line-height: 1.2;
    }
    .filter-shell {
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      padding: 14px;
    }
    .filter-title {
      margin: 0 0 10px;
      font-size: 16px;
      font-weight: 700;
    }
    .filter-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      padding: 6px 10px;
      font-size: 13px;
      color: var(--muted);
    }
    .chip select,
    .chip input {
      border: none;
      outline: none;
      background: transparent;
      color: var(--ink);
      font-size: 13px;
      min-width: 110px;
    }
    .chip.search input {
      min-width: 180px;
    }
    .chip-btn {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--ink);
      padding: 7px 12px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }
    .chip-btn:hover {
      background: #f8fafc;
    }
    .foot { margin-top: 12px; color: var(--muted); font-size: 12px; }
    @media (max-width: 700px) {
      body { padding: 10px; }
      h1 { font-size: 26px; }
      .frame { height: min(68vh, 680px); }
    }
  </style>
"""


def _nav(active: str) -> str:
    tabs = [
        ("index.html", "首页简介", "intro", "nav_intro"),
        ("data.html", "数据表", "data", "nav_data"),
        ("dashboard.html", "可视化", "dash", "nav_dash"),
        ("insights.html", "趋势总结", "insights", "nav_insights"),
    ]
    links: list[str] = []
    for href, label, key, i18n_key in tabs:
        cls = "active" if key == active else ""
        links.append(f"<a class=\"{cls}\" href=\"{href}\" data-i18n=\"{i18n_key}\">{html.escape(label)}</a>")
    return (
        f"<nav class=\"nav\">"
        f"{''.join(links)}"
        f"<span class=\"nav-spacer\"></span>"
        f"<div class=\"lang-switch\">"
        f"<button id=\"langZhBtn\" class=\"lang-btn\" type=\"button\" data-lang=\"zh\">中文</button>"
        f"<button id=\"langEnBtn\" class=\"lang-btn\" type=\"button\" data-lang=\"en\">English</button>"
        f"</div>"
        f"</nav>"
    )


def _language_script(page: str, total_rows: int = 0) -> str:
    i18n = {
        "zh": {
            "nav_intro": "首页简介",
            "nav_data": "数据表",
            "nav_dash": "可视化",
            "nav_insights": "趋势总结",
            "intro_title": "EV Charging Benchmarking",
            "intro_sub": "这是一个电动车充电与电池性能 benchmarking 网站，用于持续对比不同车型在快充速度、续航、电池指标上的表现，支持定期更新与趋势追踪。",
            "intro_meta_latest": "最新数据日期:",
            "intro_meta_source": "数据源: 懂车帝参数页 + 日报处理结果",
            "intro_meta_purpose": "Purpose: 性能对比、选型参考、趋势监控",
            "intro_card_source_title": "数据源",
            "intro_card_source_sub": "来自懂车帝车型参数页抓取与日报筛选（纯电、价格阈值）。",
            "intro_card_bench_title": "Benchmark 维度",
            "intro_card_bench_sub": "快充时间、充电窗口、高压平台、电池容量、电池能量密度、CLTC续航等。",
            "intro_card_usage_title": "使用方式",
            "intro_card_usage_sub": "先看数据表，再看可视化，最后在趋势页查看关键 takeaway。",
            "intro_foot": "注: 本站采用最新一期数据覆盖发布（适合按月更新），页面 2/3/4 均基于同一期数据构建。",
            "data_title": "Charging & Battery 参数数据表",
            "data_sub": "此页展示最新抓取与处理后的 benchmarking 表格，供横向对比和二次分析。该页会随日报定期更新。",
            "data_meta_date": "数据日期:",
            "data_meta_rows": "记录数:",
            "data_meta_file": "数据文件:",
            "data_filter_title": "筛选",
            "data_filter_brand": "品牌",
            "data_filter_power": "动力形式",
            "data_filter_hv": "高压平台",
            "data_filter_battery": "电池类型",
            "data_filter_cell_brand": "电芯品牌",
            "data_filter_keyword": "模糊搜索",
            "data_filter_placeholder": "车型/品牌/电池关键字",
            "data_filter_all": "全部",
            "data_filter_unknown": "未知",
            "data_filter_clear": "清空筛选",
            "data_stat_all": "显示全部 {count} 条记录",
            "data_stat_filtered": "筛选后显示 {count} 条记录",
            "dash_title": "可视化 Dashboard",
            "dash_sub": "该可视化由数据表页同源数据自动生成，用于快速观察车型分布、充电效率与关键指标差异。",
            "dash_meta_date": "数据日期:",
            "dash_meta_source": "来源: data.html 同批数据",
            "ins_title": "趋势总结与 Takeaways",
            "ins_sub": "基于数据表页与 Dashboard 同批数据，提炼关键趋势与可执行结论，帮助你快速做车型性能 benchmarking 决策。",
            "ins_meta_date": "数据日期:",
            "ins_meta_samples": "样本数:",
            "ins_meta_hv": "800V及以上占比:",
            "ins_meta_avg_fast": "平均快充时间:",
            "ins_meta_avg_fast_na": "未明确",
            "ins_meta_avg_fast_unit": "分钟",
            "ins_sync_title": "同步结论（来自数据表与 Dashboard 同批数据）",
            "ins_bubble_title": "品牌分布 Bubble",
            "ins_fast_title": "最快快充车型（Top 5）",
            "ins_slow_title": "最慢快充车型（Bottom 5）",
            "ins_takeaways_title": "Takeaways",
            "ins_line_1": "样本 {total} 款车型中，800V及以上占比 {highRatio}% ，说明高压平台在当前样本中已形成明显渗透。",
            "ins_line_2": "快充时间均值 {avgFast} 分钟，中位数 {medianFast} 分钟。",
            "ins_line_3": "CLTC 续航均值 {avgCltc} km，可与 Dashboard 的分布图交叉验证。",
            "ins_rank_brand_label": "品牌:",
            "ins_rank_fast_label": "快充时间:",
            "ins_rank_hv_label": "高压平台:",
            "ins_rank_minutes": "分钟",
            "ins_rank_unknown": "未明确",
            "ins_t1_title": "1. 高压平台渗透",
            "ins_t1_sub": "高压平台占比可用于判断高功率快充基础能力，适合持续按周追踪其变化。",
            "ins_t2_title": "2. 充电效率分化",
            "ins_t2_sub": "同价位车型快充时间差异明显，建议结合充电窗口与电池容量做综合比较。",
            "ins_t3_title": "3. 品牌策略差异",
            "ins_t3_sub": "品牌在电池容量和快充时间上的取舍不同，可用于产品定位和竞品研究。",
        },
        "en": {
            "nav_intro": "Overview",
            "nav_data": "Data Table",
            "nav_dash": "Visualization",
            "nav_insights": "Insights",
            "intro_title": "EV Charging Benchmarking",
            "intro_sub": "This site benchmarks EV charging and battery performance, with continuous comparison across models on fast-charging speed, range, and battery metrics.",
            "intro_meta_latest": "Latest data date:",
            "intro_meta_source": "Source: Dongchedi spec pages + daily pipeline outputs",
            "intro_meta_purpose": "Purpose: performance comparison, model selection, trend tracking",
            "intro_card_source_title": "Data Source",
            "intro_card_source_sub": "Built from Dongchedi model spec scraping and daily report filtering (BEV + price thresholds).",
            "intro_card_bench_title": "Benchmark Dimensions",
            "intro_card_bench_sub": "Fast-charging time, charging window, high-voltage platform, battery capacity, energy density, CLTC range, and more.",
            "intro_card_usage_title": "How To Use",
            "intro_card_usage_sub": "Start from the data table, explore charts, then review key takeaways in the insights page.",
            "intro_foot": "Note: The site publishes the latest snapshot only; pages 2/3/4 are generated from the same report batch.",
            "data_title": "Charging & Battery Data Table",
            "data_sub": "This page shows the latest processed benchmarking table for side-by-side comparison and downstream analysis.",
            "data_meta_date": "Data date:",
            "data_meta_rows": "Rows:",
            "data_meta_file": "Data file:",
            "data_filter_title": "Filters",
            "data_filter_brand": "Brand",
            "data_filter_power": "Power Type",
            "data_filter_hv": "HV Platform",
            "data_filter_battery": "Battery Type",
            "data_filter_cell_brand": "Cell Brand",
            "data_filter_keyword": "Keyword Search",
            "data_filter_placeholder": "Model/brand/battery keyword",
            "data_filter_all": "All",
            "data_filter_unknown": "Unknown",
            "data_filter_clear": "Clear Filters",
            "data_stat_all": "Showing all {count} rows",
            "data_stat_filtered": "Showing {count} filtered rows",
            "dash_title": "Visualization Dashboard",
            "dash_sub": "This dashboard is generated from the same dataset as the data table, for quick comparison of distribution and charging metrics.",
            "dash_meta_date": "Data date:",
            "dash_meta_source": "Source: same batch as data.html",
            "ins_title": "Insights & Takeaways",
            "ins_sub": "Based on the same data batch as the table and dashboard, this page highlights actionable trends for EV benchmarking decisions.",
            "ins_meta_date": "Data date:",
            "ins_meta_samples": "Samples:",
            "ins_meta_hv": "800V+ share:",
            "ins_meta_avg_fast": "Avg fast charge time:",
            "ins_meta_avg_fast_na": "N/A",
            "ins_meta_avg_fast_unit": "min",
            "ins_sync_title": "Aligned Findings (same data batch)",
            "ins_bubble_title": "Brand Bubble Distribution",
            "ins_fast_title": "Fastest Charging Models (Top 5)",
            "ins_slow_title": "Slowest Charging Models (Bottom 5)",
            "ins_takeaways_title": "Takeaways",
            "ins_line_1": "Across {total} models, the 800V+ share is {highRatio}%, indicating clear high-voltage platform penetration in this sample.",
            "ins_line_2": "Average fast-charging time is {avgFast} min, with a median of {medianFast} min.",
            "ins_line_3": "Average CLTC range is {avgCltc} km, which can be cross-validated with the dashboard distribution.",
            "ins_rank_brand_label": "Brand:",
            "ins_rank_fast_label": "Fast charge:",
            "ins_rank_hv_label": "HV platform:",
            "ins_rank_minutes": "min",
            "ins_rank_unknown": "Unknown",
            "ins_t1_title": "1. High-Voltage Penetration",
            "ins_t1_sub": "The share of high-voltage platforms is a practical proxy for high-power charging readiness.",
            "ins_t2_title": "2. Charging Efficiency Gap",
            "ins_t2_sub": "Large fast-charging differences exist even in similar price ranges; compare with charging window and battery capacity.",
            "ins_t3_title": "3. Brand Strategy Differences",
            "ins_t3_sub": "Brands show different trade-offs between battery capacity and charging speed, useful for positioning and competitor analysis.",
        },
    }
    payload = json.dumps(i18n, ensure_ascii=False)
    return f"""
  <script>
    (function () {{
      const page = {json.dumps(page)};
      const totalRows = {int(total_rows)};
      const I18N = {payload};

      function currentLang() {{
        const saved = localStorage.getItem('site_lang');
        if (saved === 'zh' || saved === 'en') {{
          return saved;
        }}
        return document.documentElement.lang && document.documentElement.lang.toLowerCase().startsWith('en') ? 'en' : 'zh';
      }}

      function t(lang, key) {{
        return (I18N[lang] && I18N[lang][key]) || (I18N.zh && I18N.zh[key]) || '';
      }}

      function format(template, data) {{
        return String(template || '').replace(/\\{{(\\w+)\\}}/g, function (_, k) {{
          return data[k] !== undefined ? String(data[k]) : '';
        }});
      }}

      function applyDataStat(lang) {{
        const stat = document.getElementById('filterStat');
        if (!stat || page !== 'data') {{
          return;
        }}
        const filteredRows = Number(stat.dataset.filteredRows || totalRows);
        const key = filteredRows === totalRows ? 'data_stat_all' : 'data_stat_filtered';
        stat.textContent = format(t(lang, key), {{ count: filteredRows }});
      }}

      function applyInsightTemplates(lang) {{
        if (page !== 'insights') {{
          return;
        }}
        document.querySelectorAll('[data-i18n-template]').forEach(function (el) {{
          const key = el.getAttribute('data-i18n-template');
          el.textContent = format(t(lang, key), el.dataset || {{}});
        }});

        const avgFastEl = document.getElementById('insMetaAvgFastValue');
        if (avgFastEl) {{
          const val = avgFastEl.dataset.value || '';
          const hasNumber = /^\\d+(\\.\\d+)?$/.test(val);
          avgFastEl.textContent = hasNumber
            ? `${{val}} ${{t(lang, 'ins_meta_avg_fast_unit')}}`
            : t(lang, 'ins_meta_avg_fast_na');
        }}
      }}

      function syncDashboardFrame(lang) {{
        if (page !== 'dash') {{
          return;
        }}
        const frame = document.querySelector('iframe.frame');
        if (!frame) {{
          return;
        }}
        try {{
          const url = new URL(frame.getAttribute('src') || '', window.location.href);
          url.searchParams.set('lang', lang);
          frame.setAttribute('src', url.toString());
        }} catch (_err) {{
          // Ignore malformed src values.
        }}
      }}

      function setLang(lang) {{
        const zhBtn = document.getElementById('langZhBtn');
        const enBtn = document.getElementById('langEnBtn');
        if (zhBtn) {{
          zhBtn.classList.toggle('active', lang === 'zh');
        }}
        if (enBtn) {{
          enBtn.classList.toggle('active', lang === 'en');
        }}

        document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
        document.querySelectorAll('[data-i18n]').forEach(function (el) {{
          const key = el.getAttribute('data-i18n');
          const val = t(lang, key);
          if (val) {{
            el.textContent = val;
          }}
        }});
        document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {{
          const key = el.getAttribute('data-i18n-placeholder');
          const val = t(lang, key);
          if (val) {{
            el.setAttribute('placeholder', val);
          }}
        }});

        applyDataStat(lang);
        applyInsightTemplates(lang);
        localStorage.setItem('site_lang', lang);
        syncDashboardFrame(lang);
        window.dispatchEvent(new CustomEvent('site-lang-changed', {{ detail: {{ lang }} }}));
      }}

      window.updateDataStatText = function (visibleRows) {{
        const stat = document.getElementById('filterStat');
        if (!stat) {{
          return;
        }}
        stat.dataset.filteredRows = String(visibleRows);
        applyDataStat(currentLang());
      }};

      const zhBtn = document.getElementById('langZhBtn');
      const enBtn = document.getElementById('langEnBtn');
      if (zhBtn) {{
        zhBtn.addEventListener('click', function () {{ setLang('zh'); }});
      }}
      if (enBtn) {{
        enBtn.addEventListener('click', function () {{ setLang('en'); }});
      }}

      window.addEventListener('storage', function (e) {{
        if (e.key === 'site_lang') {{
          setLang(currentLang());
        }}
      }});

      setLang(currentLang());
    }})();
  </script>
"""


def _build_intro_html(latest_date: str) -> str:
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>EV Charging Benchmarking</title>
{_base_style()}
</head>
<body>
  <div class=\"shell\">
    {_nav('intro')}
    <section class=\"panel\">
      <h1 data-i18n=\"intro_title\">EV Charging Benchmarking</h1>
      <p class=\"sub\" data-i18n=\"intro_sub\">这是一个电动车充电与电池性能 benchmarking 网站，用于持续对比不同车型在快充速度、续航、电池指标上的表现，支持定期更新与趋势追踪。</p>
      <div class=\"meta\">
        <span class=\"pill\"><span data-i18n=\"intro_meta_latest\">最新数据日期:</span> {latest_date}</span>
        <span class=\"pill\" data-i18n=\"intro_meta_source\">数据源: 懂车帝参数页 + 日报处理结果</span>
        <span class=\"pill\" data-i18n=\"intro_meta_purpose\">Purpose: 性能对比、选型参考、趋势监控</span>
      </div>
      <div class=\"grid\">
        <article class=\"card\"><h3 data-i18n=\"intro_card_source_title\">数据源</h3><p class=\"sub\" data-i18n=\"intro_card_source_sub\">来自懂车帝车型参数页抓取与日报筛选（纯电、价格阈值）。</p></article>
        <article class=\"card\"><h3 data-i18n=\"intro_card_bench_title\">Benchmark 维度</h3><p class=\"sub\" data-i18n=\"intro_card_bench_sub\">快充时间、充电窗口、高压平台、电池容量、电池能量密度、CLTC续航等。</p></article>
        <article class=\"card\"><h3 data-i18n=\"intro_card_usage_title\">使用方式</h3><p class=\"sub\" data-i18n=\"intro_card_usage_sub\">先看数据表，再看可视化，最后在趋势页查看关键 takeaway。</p></article>
      </div>
      <p class=\"foot\" data-i18n=\"intro_foot\">注: 本站采用最新一期数据覆盖发布（适合按月更新），页面 2/3/4 均基于同一期数据构建。</p>
    </section>
  </div>
{_language_script('intro')}
</body>
</html>
"""


def _pick_column(headers: list[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in headers:
            return c
    return None


def _high_voltage_tag(row: dict[str, str]) -> str:
    v = _num(row.get("高压平台电压(V)", ""))
    if v is None:
        return "未知"
    if v >= 800:
        return "800V及以上"
    return "800V以下"


def _build_data_html(latest_date: str, rows: list[dict[str, str]]) -> str:
    if not rows:
        table_html = "<p class=\"sub\">暂无数据。</p>"
        filter_html = ""
        script_html = ""
    else:
        headers = list(rows[0].keys())
        brand_col = _pick_column(headers, ["品牌"])
        power_col = _pick_column(headers, ["动力形式", "能源类型", "驱动形式"])
        battery_col = _pick_column(headers, ["电池类型", "电池种类", "电池材质"])
        cell_brand_col = _pick_column(headers, ["电芯品牌", "电芯厂商", "电池品牌", "电信品牌"])

        brands = sorted({(r.get(brand_col, "") if brand_col else "").strip() for r in rows if (r.get(brand_col, "") if brand_col else "").strip()})
        powers = sorted({(r.get(power_col, "") if power_col else "").strip() for r in rows if (r.get(power_col, "") if power_col else "").strip()})
        batteries = sorted({(r.get(battery_col, "") if battery_col else "").strip() for r in rows if (r.get(battery_col, "") if battery_col else "").strip()})
        cell_brands = sorted({(r.get(cell_brand_col, "") if cell_brand_col else "").strip() for r in rows if (r.get(cell_brand_col, "") if cell_brand_col else "").strip()})

        filter_html = f"""
      <div class=\"filter-shell\">
        <h3 class=\"filter-title\" data-i18n=\"data_filter_title\">筛选</h3>
        <div class=\"filter-row\">
          <label class=\"chip\"><span data-i18n=\"data_filter_brand\">品牌</span>
            <select id=\"brandFilter\"> 
              <option value=\"\" data-i18n=\"data_filter_all\">全部</option>
              {''.join(f'<option value="{html.escape(x)}">{html.escape(x)}</option>' for x in brands)}
            </select>
          </label>
          <label class=\"chip\"><span data-i18n=\"data_filter_power\">动力形式</span>
            <select id=\"powerFilter\">
              <option value=\"\" data-i18n=\"data_filter_all\">全部</option>
              {''.join(f'<option value="{html.escape(x)}">{html.escape(x)}</option>' for x in powers)}
            </select>
          </label>
          <label class=\"chip\"><span data-i18n=\"data_filter_hv\">高压平台</span>
            <select id=\"hvFilter\">
              <option value=\"\" data-i18n=\"data_filter_all\">全部</option>
              <option value=\"800V及以上\">800V及以上</option>
              <option value=\"800V以下\">800V以下</option>
              <option value=\"未知\" data-i18n=\"data_filter_unknown\">未知</option>
            </select>
          </label>
          <label class=\"chip\"><span data-i18n=\"data_filter_battery\">电池类型</span>
            <select id=\"batteryFilter\">
              <option value=\"\" data-i18n=\"data_filter_all\">全部</option>
              {''.join(f'<option value="{html.escape(x)}">{html.escape(x)}</option>' for x in batteries)}
            </select>
          </label>
          <label class=\"chip\"><span data-i18n=\"data_filter_cell_brand\">电芯品牌</span>
            <select id=\"cellBrandFilter\">
              <option value=\"\" data-i18n=\"data_filter_all\">全部</option>
              {''.join(f'<option value="{html.escape(x)}">{html.escape(x)}</option>' for x in cell_brands)}
            </select>
          </label>
          <label class=\"chip search\"><span data-i18n=\"data_filter_keyword\">模糊搜索</span>
            <input id=\"keywordFilter\" type=\"text\" placeholder=\"车型/品牌/电池关键字\" data-i18n-placeholder=\"data_filter_placeholder\" />
          </label>
          <button id=\"clearFilters\" class=\"chip-btn\" type=\"button\" data-i18n=\"data_filter_clear\">清空筛选</button>
        </div>
        <p class=\"sub\" id=\"filterStat\" data-filtered-rows=\"{len(rows)}\" style=\"margin-top:10px\" data-i18n=\"data_stat_all\">显示全部 {len(rows)} 条记录</p>
      </div>
"""

        thead = "<tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in headers) + "</tr>"
        body = []
        for r in rows:
            brand_val = (r.get(brand_col, "") if brand_col else "").strip()
            power_val = (r.get(power_col, "") if power_col else "").strip()
            battery_val = (r.get(battery_col, "") if battery_col else "").strip()
            cell_brand_val = (r.get(cell_brand_col, "") if cell_brand_col else "").strip()
            search_text = " ".join(str(r.get(h, "")) for h in headers).lower()
            hv_val = _high_voltage_tag(r)
            row_attrs = (
                f'data-brand="{html.escape(brand_val)}" '
                f'data-power="{html.escape(power_val)}" '
              f'data-hv="{html.escape(hv_val)}" '
              f'data-battery="{html.escape(battery_val)}" '
              f'data-cell-brand="{html.escape(cell_brand_val)}" '
              f'data-search="{html.escape(search_text)}"'
            )
            body.append(
                f"<tr {row_attrs}>"
              + "".join(f"<td>{_render_table_cell(str(r.get(h, '')))}</td>" for h in headers)
                + "</tr>"
            )
        table_html = f"<div class=\"table-wrap\"><table><thead>{thead}</thead><tbody>{''.join(body)}</tbody></table></div>"

        script_html = """
  <script>
    (function () {
      const brand = document.getElementById('brandFilter');
      const power = document.getElementById('powerFilter');
      const hv = document.getElementById('hvFilter');
      const battery = document.getElementById('batteryFilter');
      const cellBrand = document.getElementById('cellBrandFilter');
      const keyword = document.getElementById('keywordFilter');
      const clearBtn = document.getElementById('clearFilters');
      const stat = document.getElementById('filterStat');
      const rows = Array.from(document.querySelectorAll('tbody tr'));

      function applyFilters() {
        const b = brand.value;
        const p = power.value;
        const h = hv.value;
        const bt = battery.value;
        const cb = cellBrand.value;
        const kw = keyword.value.trim().toLowerCase();
        let visible = 0;

        rows.forEach((row) => {
          const okBrand = !b || row.dataset.brand === b;
          const okPower = !p || row.dataset.power === p;
          const okHv = !h || row.dataset.hv === h;
          const okBattery = !bt || row.dataset.battery === bt;
          const okCellBrand = !cb || row.dataset.cellBrand === cb;
          const okKeyword = !kw || row.dataset.search.includes(kw);
          const show = okBrand && okPower && okHv && okBattery && okCellBrand && okKeyword;
          row.style.display = show ? '' : 'none';
          if (show) {
            visible += 1;
          }
        });

        stat.dataset.filteredRows = String(visible);
        if (typeof window.updateDataStatText === 'function') {
          window.updateDataStatText(visible);
        } else {
          stat.textContent = `筛选后显示 ${visible} 条记录`;
        }
      }

      brand.addEventListener('change', applyFilters);
      power.addEventListener('change', applyFilters);
      hv.addEventListener('change', applyFilters);
      battery.addEventListener('change', applyFilters);
      cellBrand.addEventListener('change', applyFilters);
      keyword.addEventListener('input', applyFilters);
      clearBtn.addEventListener('click', () => {
        brand.value = '';
        power.value = '';
        hv.value = '';
        battery.value = '';
        cellBrand.value = '';
        keyword.value = '';
        applyFilters();
      });
    })();
  </script>
"""

    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Charging & Battery Data</title>
{_base_style()}
</head>
<body>
  <div class=\"shell\">
    {_nav('data')}
    <section class=\"panel\">
      <h1 data-i18n=\"data_title\">Charging & Battery 参数数据表</h1>
      <p class=\"sub\" data-i18n=\"data_sub\">此页展示最新抓取与处理后的 benchmarking 表格，供横向对比和二次分析。该页会随日报定期更新。</p>
      <div class=\"meta\">
        <span class=\"pill\"><span data-i18n=\"data_meta_date\">数据日期:</span> {latest_date}</span>
        <span class=\"pill\"><span data-i18n=\"data_meta_rows\">记录数:</span> {len(rows)}</span>
        <span class=\"pill\"><span data-i18n=\"data_meta_file\">数据文件:</span> reports/{latest_date}/filtered.csv</span>
      </div>
      {filter_html}
      {table_html}
    </section>
  </div>
{_language_script('data', len(rows))}
{script_html}
</body>
</html>
"""


def _build_dashboard_html(latest_date: str) -> str:
    dashboard = f"reports/{latest_date}/charging_visualization_dashboard.html"
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Charging Dashboard</title>
{_base_style()}
</head>
<body>
  <div class=\"shell\">
    {_nav('dash')}
    <section class=\"panel\">
      <h1 data-i18n=\"dash_title\">可视化 Dashboard</h1>
      <p class=\"sub\" data-i18n=\"dash_sub\">该可视化由数据表页同源数据自动生成，用于快速观察车型分布、充电效率与关键指标差异。</p>
      <div class=\"meta\">
        <span class=\"pill\"><span data-i18n=\"dash_meta_date\">数据日期:</span> {latest_date}</span>
        <span class=\"pill\" data-i18n=\"dash_meta_source\">来源: data.html 同批数据</span>
      </div>
      <iframe class=\"frame\" src=\"{dashboard}\" title=\"Charging Dashboard\"></iframe>
    </section>
  </div>
{_language_script('dash')}
</body>
</html>
"""


def _build_insights_html(latest_date: str, rows: list[dict[str, str]]) -> str:
    total = len(rows)
    fast_values = [x for x in (_num(r.get("快充时间(分钟)", "")) for r in rows) if x is not None]
    avg_fast = (sum(fast_values) / len(fast_values)) if fast_values else None
    median_fast = _median(fast_values)
    cltc_values = [x for x in (_num(r.get("纯电续航里程(km)CLTC", "")) for r in rows) if x is not None]
    avg_cltc = (sum(cltc_values) / len(cltc_values)) if cltc_values else None
    high_voltage = sum(1 for r in rows if (_num(r.get("高压平台电压(V)", "")) or 0) >= 800)
    high_ratio = (high_voltage / total * 100) if total else 0

    by_fast = []
    for r in rows:
        t = _num(r.get("快充时间(分钟)", ""))
        if t is not None:
            by_fast.append((t, r))
    by_fast.sort(key=lambda x: x[0])
    fastest = by_fast[:5]
    slowest = by_fast[-5:]

    def _render_rank_row(items: list[tuple[float, dict[str, str]]], tone: str) -> str:
      if not items:
        return "<p class=\"sub\">暂无可用数据</p>"
      cards = []
      for val, row in items:
        voltage = _num(row.get("高压平台电压(V)", ""))
        hv_value = f"{voltage:.0f}V" if voltage is not None else '<span data-i18n="ins_rank_unknown">未明确</span>'
        cards.append(
          f"<article class=\"rank-card {tone}\">"
          f"<h3>{html.escape(row.get('车型', '未命名车型'))}</h3>"
          f"<p class=\"sub\"><span data-i18n=\"ins_rank_brand_label\">品牌:</span> {html.escape(row.get('品牌', '未明确'))}</p>"
          f"<p class=\"sub\"><span data-i18n=\"ins_rank_fast_label\">快充时间:</span> {val:.1f} <span data-i18n=\"ins_rank_minutes\">分钟</span></p>"
          f"<p class=\"sub\"><span data-i18n=\"ins_rank_hv_label\">高压平台:</span> {hv_value}</p>"
          "</article>"
        )
      return "<div class=\"rank-row\">" + "".join(cards) + "</div>"

    brand_bucket: dict[str, dict[str, float | int]] = {}
    for r in rows:
        b = (r.get("品牌") or "未明确").strip()
        x = brand_bucket.setdefault(b, {"count": 0, "fast_sum": 0.0, "fast_n": 0})
        x["count"] = int(x["count"]) + 1
        fv = _num(r.get("快充时间(分钟)", ""))
        if fv is not None:
            x["fast_sum"] = float(x["fast_sum"]) + fv
            x["fast_n"] = int(x["fast_n"]) + 1

    bubble_rows: list[dict[str, float | str | int]] = []
    for b, stat in sorted(brand_bucket.items(), key=lambda kv: (-int(kv[1]["count"]), kv[0]))[:20]:
        fast_n = int(stat["fast_n"])
        fast_avg = (float(stat["fast_sum"]) / fast_n) if fast_n else None
        bubble_rows.append(
            {
                "brand": b,
                "count": int(stat["count"]),
                "fastAvg": round(fast_avg, 2) if fast_avg is not None else None,
            }
        )

    bubble_payload = json.dumps(bubble_rows, ensure_ascii=False)

    avg_fast_text = f"{avg_fast:.1f}" if avg_fast is not None else "未明确"
    median_fast_text = f"{median_fast:.1f}" if median_fast is not None else "未明确"
    avg_cltc_text = f"{avg_cltc:.0f}" if avg_cltc is not None else "未明确"

    bubble_script = """
  <script>
    (function () {
      const rows = __BUBBLE_PAYLOAD__;
      function renderBubble() {
        const chart = document.getElementById('brandBubble');
        const lang = localStorage.getItem('site_lang') === 'en' ? 'en' : 'zh';
        const label = function (zh, en) { return lang === 'en' ? en : zh; };

        if (!rows || rows.length === 0) {
          chart.innerHTML = '<p class="sub" style="padding:12px">' + label('暂无品牌分布数据', 'No brand distribution data available') + '</p>';
          return;
        }

        const x = rows.map(r => r.brand);
        const y = rows.map(r => r.fastAvg === null ? 0 : r.fastAvg);
        const size = rows.map(r => Math.max(14, Math.sqrt(r.count) * 9));
        const text = rows.map(r => {
          const avgFast = r.fastAvg === null ? label('未明确', 'N/A') : r.fastAvg;
          return lang === 'en'
            ? `${r.brand}<br>Models: ${r.count}<br>Avg Fast Charge: ${avgFast} min`
            : `${r.brand}<br>车型数: ${r.count}<br>平均快充: ${avgFast} 分钟`;
        });

        Plotly.newPlot('brandBubble', [{
          type: 'scatter',
          mode: 'markers',
          x,
          y,
          text,
          hovertemplate: '%{text}<extra></extra>',
          marker: {
            size,
            color: y,
            colorscale: 'YlOrRd',
            showscale: true,
            opacity: 0.78,
            line: { width: 1, color: 'rgba(20,32,43,0.35)' }
          }
        }], {
          margin: { l: 60, r: 20, t: 10, b: 90 },
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(255,255,255,0.35)',
          xaxis: { title: label('品牌', 'Brand'), tickangle: -25 },
          yaxis: { title: label('平均快充时间(分钟)', 'Avg Fast Charge Time (min)') },
          font: { family: 'Segoe UI, PingFang SC, Microsoft YaHei, sans-serif', color: '#14202b' }
        }, { responsive: true, displaylogo: false });

        }

        renderBubble();
        window.addEventListener('site-lang-changed', renderBubble);
    })();
  </script>
""".replace("__BUBBLE_PAYLOAD__", bubble_payload)

    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Insights & Takeaways</title>
{_base_style()}
  <script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>
  <style>
    .rank-row {{
      display: flex;
      gap: 12px;
      overflow-x: auto;
      padding-bottom: 8px;
      margin-top: 10px;
    }}
    .rank-card {{
      min-width: 270px;
      max-width: 320px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      padding: 12px;
      box-shadow: 0 10px 24px rgba(0,0,0,.06);
    }}
    .rank-card.fast {{ border-left: 5px solid #2a9d8f; }}
    .rank-card.slow {{ border-left: 5px solid #e76f51; }}
    .bubble-wrap {{
      margin-top: 12px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255,255,255,.8);
      padding: 6px;
    }}
    .bubble-chart {{ height: 420px; }}
  </style>
</head>
<body>
  <div class=\"shell\">
    {_nav('insights')}
    <section class=\"panel\">
      <h1 data-i18n=\"ins_title\">趋势总结与 Takeaways</h1>
      <p class=\"sub\" data-i18n=\"ins_sub\">基于数据表页与 Dashboard 同批数据，提炼关键趋势与可执行结论，帮助你快速做车型性能 benchmarking 决策。</p>
      <div class=\"meta\">
        <span class=\"pill\"><span data-i18n=\"ins_meta_date\">数据日期:</span> {latest_date}</span>
        <span class=\"pill\"><span data-i18n=\"ins_meta_samples\">样本数:</span> {total}</span>
        <span class=\"pill\"><span data-i18n=\"ins_meta_hv\">800V及以上占比:</span> {high_ratio:.1f}%</span>
        <span class=\"pill\"><span data-i18n=\"ins_meta_avg_fast\">平均快充时间:</span> <span id=\"insMetaAvgFastValue\" data-value=\"{f'{avg_fast:.1f}' if avg_fast is not None else ''}\">{f'{avg_fast:.1f} 分钟' if avg_fast is not None else '未明确'}</span></span>
      </div>

      <h2 style=\"margin-top:16px\" data-i18n=\"ins_sync_title\">同步结论（来自数据表与 Dashboard 同批数据）</h2>
      <div class=\"grid\">
        <article class=\"card\"><p class=\"sub\" data-i18n-template=\"ins_line_1\" data-total=\"{total}\" data-high-ratio=\"{high_ratio:.1f}\">样本 {total} 款车型中，800V及以上占比 {high_ratio:.1f}% ，说明高压平台在当前样本中已形成明显渗透。</p></article>
        <article class=\"card\"><p class=\"sub\" data-i18n-template=\"ins_line_2\" data-avg-fast=\"{avg_fast_text}\" data-median-fast=\"{median_fast_text}\">快充时间均值 {avg_fast_text} 分钟，中位数 {median_fast_text} 分钟。</p></article>
        <article class=\"card\"><p class=\"sub\" data-i18n-template=\"ins_line_3\" data-avg-cltc=\"{avg_cltc_text}\">CLTC 续航均值 {avg_cltc_text} km，可与 Dashboard 的分布图交叉验证。</p></article>
      </div>

      <h2 style=\"margin-top:16px\" data-i18n=\"ins_bubble_title\">品牌分布 Bubble</h2>
      <div class=\"bubble-wrap\"><div id=\"brandBubble\" class=\"bubble-chart\"></div></div>

      <h2 style=\"margin-top:16px\" data-i18n=\"ins_fast_title\">最快快充车型（Top 5）</h2>
      {_render_rank_row(fastest, 'fast')}

      <h2 style=\"margin-top:16px\" data-i18n=\"ins_slow_title\">最慢快充车型（Bottom 5）</h2>
      {_render_rank_row(slowest, 'slow')}

      <h2 style=\"margin-top:16px\" data-i18n=\"ins_takeaways_title\">Takeaways</h2>
      <div class=\"grid\">
        <article class=\"card\"><h3 data-i18n=\"ins_t1_title\">1. 高压平台渗透</h3><p class=\"sub\" data-i18n=\"ins_t1_sub\">高压平台占比可用于判断高功率快充基础能力，适合持续按周追踪其变化。</p></article>
        <article class=\"card\"><h3 data-i18n=\"ins_t2_title\">2. 充电效率分化</h3><p class=\"sub\" data-i18n=\"ins_t2_sub\">同价位车型快充时间差异明显，建议结合充电窗口与电池容量做综合比较。</p></article>
        <article class=\"card\"><h3 data-i18n=\"ins_t3_title\">3. 品牌策略差异</h3><p class=\"sub\" data-i18n=\"ins_t3_sub\">品牌在电池容量和快充时间上的取舍不同，可用于产品定位和竞品研究。</p></article>
      </div>
    </section>
  </div>
  {_language_script('insights')}
  {bubble_script}
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the static Dongchedi Pages site.")
    parser.add_argument("--date", default="", help="Publish a specific report date in YYYY-MM-DD. Defaults to latest available report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    latest_report = _report_dir_for_date(args.date) if args.date else _latest_report_dir()
    latest_date = latest_report.name
    latest_csv = latest_report / "filtered.csv"
    latest_rows = _load_rows(latest_csv) if latest_csv.exists() else []

    # Always publish a single latest snapshot so new runs overwrite prior data.
    if SITE_ROOT.exists():
        shutil.rmtree(SITE_ROOT)
    SITE_ROOT.mkdir(parents=True, exist_ok=True)

    _copy_report_dir(latest_report)
    _write_latest_alias(latest_report)
    (SITE_ROOT / "index.html").write_text(_build_intro_html(latest_date), encoding="utf-8")
    (SITE_ROOT / "data.html").write_text(_build_data_html(latest_date, latest_rows), encoding="utf-8")
    (SITE_ROOT / "dashboard.html").write_text(_build_dashboard_html(latest_date), encoding="utf-8")
    (SITE_ROOT / "insights.html").write_text(_build_insights_html(latest_date, latest_rows), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "latest_report": latest_report.name,
                "reports": 1,
                "publish_mode": "latest-only-overwrite",
                "pages": ["index.html", "data.html", "dashboard.html", "insights.html"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
