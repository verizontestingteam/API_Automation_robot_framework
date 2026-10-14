import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor


def format_duration(value):
    try:
        val = float(value or 0)
        # Robot Framework 7+ stores elapsed directly in seconds.
        # If value is unusually large (> 1000), treat as milliseconds.
        seconds = val / 1000 if val > 1000 else val
        return f"{seconds:.3f} seconds"
    except Exception:
        return "0.000 seconds"


def add_status(cell, status):
    cell.text = status
    if status == "PASS":
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x00, 0x80, 0x00)
    elif status == "FAIL":
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xC0, 0x00, 0x00)


def generate_report(output_xml, destination):
    root = ET.parse(output_xml).getroot()
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.6)
    section.right_margin = Inches(0.6)

    title = document.add_heading("Product Offering API Test Report", 0)
    title.alignment = 1
    document.add_paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    suite = root.find(".//suite")
    tests = root.findall(".//test")
    suite_name = suite.get("name", "") if suite is not None else ""

    document.add_heading("Execution Summary", level=1)
    summary = document.add_table(rows=1, cols=2)
    summary.alignment = WD_TABLE_ALIGNMENT.CENTER
    summary.style = "Table Grid"
    summary.rows[0].cells[0].text = "Suite"
    summary.rows[0].cells[1].text = suite_name

    for test in tests:
        status = test.find("./status")
        status_value = status.get("status", "UNKNOWN") if status is not None else "UNKNOWN"
        elapsed = status.get("elapsed", "0") if status is not None else "0"
        row = summary.add_row().cells
        row[0].text = "Test"
        row[1].text = (
            f"{test.get('name', '')} - {status_value} "
            f"({format_duration(elapsed)})"
        )
        add_status(row[1], status_value)

    document.add_heading("Test Cases", level=1)
    table = document.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Test Case", "Status", "Duration", "Failure Details"]
    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header

    for test in tests:
        status = test.find("./status")
        status_value = status.get("status", "UNKNOWN") if status is not None else "UNKNOWN"
        failure_messages = [
            message.text.strip()
            for message in test.findall(".//msg")
            if message.get("level") == "FAIL" and message.text
        ]
        if not failure_messages and status_value == "FAIL" and status is not None and status.text:
            failure_messages = [status.text.strip()]
        cells = table.add_row().cells
        cells[0].text = test.get("name", "")
        add_status(cells[1], status_value)
        cells[2].text = format_duration(status.get("elapsed", "0") if status is not None else "0")
        cells[3].text = "\n".join(failure_messages) or "None"

    document.add_heading("Checks Covered", level=1)
    for item in (
        "HTTP status is 200.",
        "Response body is not empty.",
        "Response Content-Type is application/json.",
        "Response time is within 5000 milliseconds.",
        "Product offering schema and lifecycle status are validated.",
        "Returned product code, related party, and category are checked against the CSV row.",
        "Every root offering must have @type GroupProductOffering.",
        "Every GroupProductOffering channel list must include the requested channel; other channels may also be present.",
        "Every nested SimpleProductOffering channel list must include the requested channel; other channels may also be present.",
        "Every populated productOfferingPrice channel list must include the requested channel; empty lists are skipped.",
        "Nested bundled product offerings and their prices are checked recursively.",
        "A channel list without the requested channel or malformed channel data is reported with requested/actual channel, "
        "offering code, @type, validation level, and failure reason.",
    ):
        document.add_paragraph(item, style="List Bullet")

    destination.parent.mkdir(parents=True, exist_ok=True)
    document.save(destination)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: generate_docx_report.py <output.xml> <report.docx>")
    generate_report(Path(sys.argv[1]), Path(sys.argv[2]))
