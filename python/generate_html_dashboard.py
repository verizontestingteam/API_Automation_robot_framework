import argparse
import base64
import html
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MISSING = "N/A"
UNKNOWN_PIPELINE = "Unknown"
NOT_CLASSIFIED = "Not Classified"
LOGO_PATH = PROJECT_ROOT / "TT_logo" / "ttlogo.png"


def calculate_pass_percentage(passed, total):
    return (passed / total * 100) if total else 0.0


def calculate_summary(results):
    total = len(results)
    passed = sum(result["status"] == "PASS" for result in results)
    failed = sum(result["status"] == "FAIL" for result in results)
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "attention": total - passed,
        "pass_percentage": calculate_pass_percentage(passed, total),
        "failure_percentage": calculate_pass_percentage(failed, total),
        "overall_status": calculate_overall_status(results),
    }


def calculate_pipeline_summary(results, key="pipeline"):
    pipelines = defaultdict(list)
    for result in results:
        pipelines[result[key] or UNKNOWN_PIPELINE].append(result)

    summaries = []
    for pipeline, pipeline_results in sorted(pipelines.items(), key=lambda item: item[0].casefold()):
        passed = sum(result["status"] == "PASS" for result in pipeline_results)
        failed = sum(result["status"] == "FAIL" for result in pipeline_results)
        total = len(pipeline_results)
        summaries.append(
            {
                "pipeline": pipeline,
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_percentage": calculate_pass_percentage(passed, total),
            }
        )
    return summaries


def calculate_completed_pis(results):
    return [result for result in results if result["status"] == "PASS"]


def calculate_failed_pis(results):
    return [result for result in results if result["status"] != "PASS"]


def calculate_overall_status(results):
    failed = sum(result["status"] == "FAIL" for result in results)
    if failed == 0:
        return "STABLE"
    if failed == len(results):
        return "FAILED"
    return "UNSTABLE"


def _normalize_key(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _metadata_for(node):
    metadata = {}
    for item in node.findall("./metadata/item"):
        name = item.get("name")
        if name:
            metadata[_normalize_key(name)] = (item.text or "").strip()
    for key, value in node.attrib.items():
        normalized = _normalize_key(key)
        if normalized in {
            "piid",
            "partyinteractionid",
            "pipeline",
            "actiontype",
            "rca",
            "rootcause",
            "environment",
            "build",
            "buildnumber",
        }:
            metadata[normalized] = value.strip()
    for tag in node.findall("./tags/tag"):
        tag_value = (tag.text or "").strip()
        match = re.match(r"^\s*([^:=]+)\s*[:=]\s*(.*?)\s*$", tag_value)
        if match:
            metadata[_normalize_key(match.group(1))] = match.group(2)
    return metadata


def _first_value(metadata, names, fallback):
    for name in names:
        value = metadata.get(_normalize_key(name))
        if value:
            return value
    return fallback


def _failure_reason(test, status):
    if status is None or status.get("status", "").upper() != "FAIL":
        return MISSING
    reason = (status.text or "").strip()
    if reason:
        return reason
    for message in test.findall(".//msg"):
        if message.get("level", "").upper() == "FAIL" and message.text:
            return message.text.strip()
    return MISSING


def _elapsed_seconds(status_node):
    """Read a status element's duration (Robot Framework 7 `elapsed`, or older start/end times)."""
    if status_node is None:
        return None
    elapsed = status_node.get("elapsed")
    if elapsed:
        try:
            return float(elapsed)
        except ValueError:
            return None
    start, end = status_node.get("starttime"), status_node.get("endtime")
    if start and end and "N/A" not in (start, end):
        try:
            time_format = "%Y%m%d %H:%M:%S.%f"
            return (datetime.strptime(end, time_format) - datetime.strptime(start, time_format)).total_seconds()
        except ValueError:
            return None
    return None


def load_results(output_xml):
    root = ET.parse(output_xml).getroot()
    results = []

    def visit_suite(suite, parent_metadata, parent_path):
        metadata = dict(parent_metadata)
        metadata.update(_metadata_for(suite))
        suite_name = suite.get("name", "").strip()
        suite_path = parent_path + ([suite_name] if suite_name else [])

        for test in suite.findall("./test"):
            test_metadata = dict(metadata)
            test_metadata.update(_metadata_for(test))
            status_node = test.find("./status")
            status = (status_node.get("status", "UNKNOWN") if status_node is not None else "UNKNOWN")
            status = status.strip().upper() or "UNKNOWN"
            suite_label = " / ".join(suite_path) or MISSING
            results.append(
                {
                    "test_name": test.get("name", MISSING).strip() or MISSING,
                    "pi_id": _first_value(
                        test_metadata, ("pi_id", "piid", "party_interaction_id"), MISSING
                    ),
                    "pipeline": _first_value(test_metadata, ("pipeline",), UNKNOWN_PIPELINE),
                    "test_suite": _first_value(
                        test_metadata, ("test_suite", "testsuite"), suite_label
                    ),
                    "suite_name": suite_path[-1] if suite_path else MISSING,
                    "duration": _elapsed_seconds(status_node),
                    "action_type": _first_value(test_metadata, ("action_type",), MISSING),
                    "status": status,
                    "pi_status": (
                        "COMPLETED"
                        if status == "PASS"
                        else "FAILED"
                        if status == "FAIL"
                        else status
                    ),
                    "failure_reason": _failure_reason(test, status_node),
                    "rca": _first_value(
                        test_metadata, ("rca", "root_cause", "rootcause"), NOT_CLASSIFIED
                    ),
                }
            )

        for child_suite in suite.findall("./suite"):
            visit_suite(child_suite, metadata, suite_path)

    for suite in root.findall("./suite"):
        visit_suite(suite, {}, [])
    return root, results


def _escape(value):
    return html.escape(str(value if value not in (None, "") else MISSING), quote=True)


def _format_percentage(value):
    return f"{value:.2f}%"


def _status_class(status):
    if status in {"PASS", "PASSED", "COMPLETED"}:
        return "pass"
    if status in {"FAIL", "FAILED"}:
        return "fail"
    if status in {"STABLE"}:
        return "pass"
    if status in {"UNSTABLE"}:
        return "warn"
    return "warn"


def _render_badge(value, badge_type="status"):
    category_class = _status_class(value) if badge_type == "status" else ""
    return (
        f'<span class="badge {badge_type} {category_class}">{_escape(value)}</span>'
    )


def _render_pipeline_cards(pipeline_summaries):
    if not pipeline_summaries:
        return '<p class="empty-state">No test results are available.</p>'
    cards = []
    for summary in pipeline_summaries:
        percentage = summary["pass_percentage"]
        cards.append(
            f"""
            <article class="pipeline-card">
              <div class="pipeline-heading">
                <h3>{_escape(summary["pipeline"])}</h3>
                <strong>{_format_percentage(percentage)}</strong>
              </div>
              <div class="progress-track" role="progressbar"
                   aria-label="{_escape(summary["pipeline"])} pass rate"
                   aria-valuemin="0" aria-valuemax="100"
                   aria-valuenow="{percentage:.2f}">
                <span class="progress-fill" style="width:{percentage:.2f}%"></span>
              </div>
              <p>{summary["total"]} total <span>|</span> {summary["passed"]} pass
                 <span>|</span> {summary["failed"]} fail</p>
            </article>"""
        )
    return "\n".join(cards)


def _format_duration(seconds):
    if seconds is None:
        return MISSING
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, remainder = divmod(int(round(seconds)), 60)
    return f"{minutes} m {remainder:02d} s"


# Columns that only appear when at least one test provides a value for them
OPTIONAL_COLUMNS = {
    "pi_id": MISSING,
    "pipeline": UNKNOWN_PIPELINE,
    "action_type": MISSING,
    "rca": NOT_CLASSIFIED,
}


def _visible_optional_columns(results):
    return {
        key for key, default in OPTIONAL_COLUMNS.items()
        if any(result[key] != default for result in results)
    }


def _render_table(results, visible, status_of, show_failure, empty_message):
    columns = [("#", lambda index, result: str(index))]
    if "pi_id" in visible:
        columns.append(("PI ID", lambda index, result: _escape(result["pi_id"])))
    if "pipeline" in visible:
        columns.append(("Pipeline", lambda index, result: _escape(result["pipeline"])))
    columns.append((
        "Test Suite",
        lambda index, result: (
            f'{_escape(result["test_suite"])}'
            f'<small class="test-name">Test: {_escape(result["test_name"])}</small>'
        ),
    ))
    if "action_type" in visible:
        columns.append(("Action Type", lambda index, result: _escape(result["action_type"])))
    columns.append(("Duration", lambda index, result: _escape(_format_duration(result["duration"]))))
    columns.append(("Status", lambda index, result: _render_badge(status_of(result))))
    if show_failure:
        columns.append((
            "Failure Reason",
            lambda index, result: f'<span class="reason">{_escape(result["failure_reason"])}</span>',
        ))
        if "rca" in visible:
            columns.append(("RCA", lambda index, result: _render_badge(result["rca"], "rca")))

    head = "".join(f"<th>{_escape(name)}</th>" for name, _ in columns)
    rows = [
        "<tr>" + "".join(f"<td>{render(index, result)}</td>" for _, render in columns) + "</tr>"
        for index, result in enumerate(results, start=1)
    ]
    body = "\n".join(rows) or (
        f'<tr><td colspan="{len(columns)}" class="empty-state">{_escape(empty_message)}</td></tr>'
    )
    return f"<thead><tr>{head}</tr></thead>\n        <tbody>{body}</tbody>"


def _execution_metadata(root, output_xml):
    root_metadata = _metadata_for(root)
    for suite in root.findall("./suite"):
        for key, value in _metadata_for(suite).items():
            root_metadata.setdefault(key, value)
    environment = _first_value(
        root_metadata,
        ("environment", "test_environment"),
        next(
            (
                os.environ[name]
                for name in ("ENVIRONMENT", "TEST_ENVIRONMENT", "ROBOT_ENVIRONMENT", "TARGET_ENV")
                if os.environ.get(name)
            ),
            MISSING,
        ),
    )
    build = _first_value(
        root_metadata,
        ("build", "build_number", "buildnumber"),
        next(
            (
                os.environ[name]
                for name in (
                    "BUILD_NUMBER",
                    "JENKINS_BUILD_NUMBER",
                    "GITHUB_RUN_NUMBER",
                    "CI_PIPELINE_ID",
                )
                if os.environ.get(name)
            ),
            MISSING,
        ),
    )
    try:
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=Path(output_xml).resolve().parent,
            capture_output=True,
            check=True,
            text=True,
            timeout=3,
        )
        branch = branch_result.stdout.strip() or MISSING
    except (OSError, subprocess.SubprocessError):
        branch = MISSING

    generator = root.get("generator", "")
    version_match = re.search(r"(?:Rebot|Robot Framework)\s+([^\s(]+)", generator, re.IGNORECASE)
    version = version_match.group(1) if version_match else MISSING
    # Mention Playwright only when a test actually used the Browser library
    browser_enabled = any(
        (keyword.get("owner") or keyword.get("library")) == "Browser" for keyword in root.iter("kw")
    )
    framework = f"Robot Framework {version}"
    if browser_enabled:
        framework += " + Playwright"

    return {
        "date": datetime.now().astimezone().strftime("%d %B %Y, %H:%M %Z"),
        "environment": environment,
        "branch": branch,
        "framework": framework,
        "build": build,
    }


def generate_report(output_xml, destination=None):
    output_xml = Path(output_xml)
    destination = Path(destination) if destination else output_xml.with_name("execution_dashboard.html")
    root, results = load_results(output_xml)
    summary = calculate_summary(results)
    completed = calculate_completed_pis(results)
    attention = calculate_failed_pis(results)
    metadata = _execution_metadata(root, output_xml)
    status = summary["overall_status"]
    logo_data = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    logo_uri = f"data:image/png;base64,{logo_data}"

    # Show the Party Interaction (PI) layout only when tests provide PI metadata
    visible = _visible_optional_columns(results)
    pi_mode = bool(visible & {"pi_id", "pipeline", "action_type"})
    if "pipeline" in visible:
        group_heading = "Pipeline-wise Execution Summary"
        groups = calculate_pipeline_summary(results)
    else:
        group_heading = "Suite-wise Execution Summary"
        groups = calculate_pipeline_summary(results, key="suite_name")

    if pi_mode:
        title = "DCM Automation - PI &amp; Execution Summary Report"
        completed_heading = f"Party Interaction (PI) - Completed ({len(completed)})"
        attention_heading = f"Party Interaction (PI) - Failed / In-Progress ({len(attention)})"
        completed_status = lambda result: "COMPLETED"  # noqa: E731
        attention_status = lambda result: result["pi_status"]  # noqa: E731
        extra_cards = (
            ("Completed PIs", len(completed), ""),
            ("Failed / Stuck PIs", len(attention), ""),
        )
    else:
        title = "DCM Automation - API Execution Summary Report"
        completed_heading = f"Passed Tests ({len(completed)})"
        attention_heading = f"Failed Tests ({len(attention)})"
        completed_status = lambda result: "PASSED"  # noqa: E731
        attention_status = lambda result: "FAILED" if result["status"] == "FAIL" else result["status"]  # noqa: E731
        suite_count = len({result["test_suite"] for result in results})
        extra_cards = (
            ("Suites", suite_count, ""),
            ("Total Duration", _format_duration(_elapsed_seconds(root.find("./suite/status"))), ""),
        )

    cards = (
        ("Total Tests", summary["total"], ""),
        ("Passed", summary["passed"], _format_percentage(summary["pass_percentage"]) + " pass rate"),
        ("Failed", summary["failed"], _format_percentage(summary["failure_percentage"]) + " failure rate"),
        *extra_cards,
        ("Overall Result", status, ""),
    )
    header_fields = [
        ("Report", metadata["date"]),
        ("Environment", metadata["environment"]),
        ("Branch", metadata["branch"]),
        ("Framework", metadata["framework"]),
        ("Build", metadata["build"]),
    ]
    header_html = "\n            ".join(
        f"<span>{_escape(label)}: {_escape(value)}</span>"
        for label, value in header_fields
        if value != MISSING
    )
    links = [
        (label, filename)
        for label, filename in (("Detailed Robot log", "log.html"), ("Robot report", "report.html"))
        if (destination.parent / filename).exists()
    ]
    links_html = "".join(
        f'<a class="report-link" href="{_escape(filename)}">{_escape(label)} &rarr;</a>'
        for label, filename in links
    )
    footer_environment = (
        f" | Environment: {_escape(metadata['environment'])}" if metadata["environment"] != MISSING else ""
    )
    card_html = "\n".join(
        f"""<article class="kpi-card {_status_class(str(value)) if label == "Overall Result" else ""}">
          <span>{_escape(label)}</span><strong>{_escape(value)}</strong>
          <small>{_escape(detail) if detail else "&nbsp;"}</small>
        </article>"""
        for label, value, detail in cards
    )
    pass_width = summary["pass_percentage"]

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{title}</title>
  <style>
    :root {{
      --pass: #16a34a; --fail: #dc2626; --warn: #d97706; --primary: #1d4ed8;
      --dark: #0f172a; --border: #e2e8f0; --muted: #64748b; --surface: #ffffff;
      --canvas: #f1f5f9; --radius: 14px;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; color: #172033; background: var(--canvas);
      font: 15px/1.6 "Segoe UI", "Helvetica Neue", Arial, sans-serif; }}
    .hero {{ color: white; background: linear-gradient(115deg, #0b1224, #172554 55%, #1d4ed8);
      padding: 30px max(24px, calc((100vw - 1240px) / 2)); }}
    .hero-inner {{ max-width: 1240px; margin: auto; display: flex; gap: 28px;
      justify-content: space-between; align-items: center; }}
    .brand {{ display: flex; align-items: center; gap: 18px; min-width: 0; }}
    .brand-logo {{ flex: 0 0 auto; display: flex; align-items: left; justify-content: left;
      width: 190px; height: 72px; overflow: hidden; border-radius: 12px; background: rgba(255,255,255,0.08); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.12); }}
    .brand-logo img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}
    .brand-copy {{ min-width: 0; }}
    .brand-copy h1 {{ margin: 0 0 14px; font-size: clamp(28px, 3vw, 38px); letter-spacing: -.04em; line-height: 1.15; font-weight: 700; }}
    .metadata {{ display: flex; flex-wrap: wrap; gap: 8px 18px; color: #dbeafe; font-size: 0.92rem; }}
    .metadata span {{ white-space: nowrap; }}
    .hero-status {{ min-width: 190px; padding: 18px 22px; border: 1px solid #ffffff2b;
      border-radius: var(--radius); background: rgba(255,255,255,0.08); text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: 0 10px 25px rgba(15,23,42,0.18); }}
    .hero-status small {{ display: block; color: #bfdbfe; text-transform: uppercase;
      letter-spacing: .12em; font-weight: 700; font-size: 0.72rem; }}
    .hero-status strong {{ display: block; margin: 10px 0 2px; font-size: 24px; }}
    .hero-status .pass-rate {{ color: #86efac; font-size: 17px; }}
    main {{ max-width: 1240px; margin: 28px auto 48px; padding: 0 22px; }}
    .section {{ margin-top: 26px; }}
    .section-heading {{ margin: 0 0 15px; color: #0f172a; font-size: 1.15rem; line-height: 1.3; letter-spacing: .01em; font-weight: 700; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 15px; }}
    .kpi-card, .pipeline-card {{ background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius); box-shadow: 0 4px 16px rgba(15,23,42,0.06); }}
    .kpi-card {{ min-height: 124px; padding: 18px 20px; }}
    .kpi-card > span {{ display: block; color: var(--muted); font-weight: 600; letter-spacing: .01em; }}
    .kpi-card strong {{ display: block; margin: 7px 0 0; font-size: 30px; line-height: 1.15; color: #0f172a; }}
    .kpi-card small {{ display: block; margin-top: 6px; color: var(--muted); }}
    .kpi-card.pass {{ border-top: 3px solid var(--pass); }}
    .kpi-card.fail {{ border-top: 3px solid var(--fail); }}
    .kpi-card.warn {{ border-top: 3px solid var(--warn); }}
    .pipeline-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 15px; }}
    .pipeline-card {{ padding: 18px 20px; }}
    .pipeline-heading {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
    .pipeline-heading h3 {{ margin: 0; font-size: 1.05rem; color: #0f172a; }}
    .pipeline-heading strong {{ color: var(--primary); font-size: 1rem; }}
    .progress-track {{ height: 10px; margin: 13px 0 9px; overflow: hidden;
      border-radius: 999px; background: #e2e8f0; }}
    .progress-fill {{ display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #22c55e, #16a34a); }}
    .pipeline-card p {{ margin: 0; color: var(--muted); font-size: 13px; }}
    .pipeline-card p span {{ padding: 0 5px; color: #cbd5e1; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius);
      background: var(--surface); box-shadow: 0 4px 16px rgba(15,23,42,0.06); }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; table-layout: auto; }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }}
    th {{ color: #0f172a; background: #eff6ff; font-size: 12px; text-transform: uppercase;
      letter-spacing: .06em; white-space: nowrap; font-weight: 700; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    tbody tr:hover {{ background: #f8fafc; }}
    tbody td {{ color: #1f2937; font-size: 0.94rem; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px;
      font-weight: 700; white-space: nowrap; line-height: 1.4; }}
    .badge.pass {{ color: #166534; background: #dcfce7; }}
    .badge.fail {{ color: #991b1b; background: #fee2e2; }}
    .badge.warn {{ color: #92400e; background: #fef3c7; }}
    .badge.rca {{ color: #1e40af; background: #dbeafe; }}
    .reason {{ display: block; min-width: 220px; max-width: 440px; overflow-wrap: anywhere; }}
    .report-links {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .report-link {{ color: #dbeafe; text-decoration: none; font-size: 0.9rem; font-weight: 600;
      padding: 5px 12px; border: 1px solid #ffffff3d; border-radius: 999px; background: rgba(255,255,255,0.06); }}
    .report-link:hover {{ background: rgba(255,255,255,0.16); color: white; }}
    .test-name {{ display: block; margin-top: 3px; color: var(--muted); font-size: 12px; }}
    .empty-state {{ padding: 20px; color: var(--muted); text-align: center; }}
    footer {{ padding: 22px; color: #cbd5e1; background: #0f172a; text-align: center; }}
    footer p {{ margin: 4px 0; font-size: 0.9rem; }}
    @media (max-width: 760px) {{
      .hero-inner {{ align-items: stretch; flex-direction: column; }}
      .hero {{ padding: 24px 20px; }}
      .brand {{ align-items: flex-start; gap: 14px; }}
      .brand-logo {{ width: 150px; height: 58px; }}
      .hero-status {{ min-width: 0; }}
      .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .pipeline-grid {{ grid-template-columns: 1fr; }}
      main {{ padding: 0 14px; }}
    }}
    @media (max-width: 460px) {{
      .kpi-grid {{ grid-template-columns: 1fr; }}
      .metadata {{ display: grid; gap: 6px; }}
      .brand {{ flex-direction: column; }}
      .brand-logo {{ width: 170px; height: 62px; }}
    }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="hero-inner">
      <div class="brand">
        <div class="brand-logo">
          <img src="{logo_uri}" alt="Tecnotree logo">
        </div>
        <div class="brand-copy">
          <h1>{title}</h1>
          <div class="metadata">
            {header_html}
          </div>
          {f'<div class="report-links">{links_html}</div>' if links_html else ""}
        </div>
      </div>
      <div class="hero-status">
        <small>Overall Status</small>
        {_render_badge(status)}
        <strong class="pass-rate">{_format_percentage(pass_width)} Pass</strong>
      </div>
    </div>
  </header>
  <main>
    <section class="section" aria-labelledby="kpi-heading">
      <h2 class="section-heading" id="kpi-heading">Execution Overview</h2>
      <div class="kpi-grid">{card_html}</div>
    </section>
    <section class="section" aria-labelledby="pipeline-heading">
      <h2 class="section-heading" id="pipeline-heading">{group_heading}</h2>
      <div class="pipeline-grid">{_render_pipeline_cards(groups)}</div>
    </section>
    <section class="section" aria-labelledby="attention-heading">
      <h2 class="section-heading" id="attention-heading">{attention_heading}</h2>
      <div class="table-wrap"><table>
        {_render_table(attention, visible, attention_status, True, "No failed tests.")}
      </table></div>
    </section>
    <section class="section" aria-labelledby="completed-heading">
      <h2 class="section-heading" id="completed-heading">{completed_heading}</h2>
      <div class="table-wrap"><table>
        {_render_table(completed, visible, completed_status, False, "No passed tests.")}
      </table></div>
    </section>
  </main>
  <footer>
    <p>Generated { _escape(metadata["date"]) }{footer_environment}</p>
    <p>{_escape(metadata["framework"])}{f" | Build: {_escape(metadata['build'])}" if metadata["build"] != MISSING else ""}</p>
  </footer>
</body>
</html>
"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    return destination


def main():
    parser = argparse.ArgumentParser(description="Generate a dashboard from Robot Framework output.xml.")
    parser.add_argument("output_xml", type=Path, help="Robot Framework output.xml file")
    parser.add_argument(
        "destination",
        nargs="?",
        type=Path,
        help="HTML destination (defaults to execution_dashboard.html beside output.xml)",
    )
    arguments = parser.parse_args()
    report_path = generate_report(arguments.output_xml, arguments.destination)
    print(f"Dashboard report generated: {report_path}")


if __name__ == "__main__":
    main()
