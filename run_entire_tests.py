import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from python.generate_html_dashboard import generate_report


ROOT = Path(__file__).resolve().parent

# Load credentials from the local .env file into the environment
load_dotenv(ROOT / ".env")
TESTS = ROOT / "tests" / "Regression Suite"
REPORTS = ROOT / "reports"
VENV_SCRIPTS = ROOT / ".venv" / "Scripts"

# Word report generator
DOCX_SCRIPT = ROOT / "python" / "generate_docx_report.py"


def safe_name(value):
    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789-_ ."
    )

    return "".join(
        character if character in allowed else "_"
        for character in value
    ).strip()


def get_suite_name(output_file):
    root = ET.parse(output_file).getroot()
    suite = root.find(".//test/..")

    if suite is None:
        raise RuntimeError(
            f"No test case found in {output_file}"
        )

    return suite.attrib.get(
        "name",
        output_file.parent.name
    )


def create_report(source_output, destination):
    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = destination / "output.xml"
    log_file = destination / "log.html"
    report_file = destination / "report.html"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "robot.rebot",
            "--output",
            str(output_file),
            "--log",
            str(log_file),
            "--report",
            str(report_file),
            str(source_output),
        ],
        cwd=ROOT,
        check=False,
    )


def generate_word_report(output_xml, word_report):
    """
    Generate the consolidated Word report
    from the combined Pabot output.xml.
    """

    if not output_xml.exists():
        print(
            f"[ERROR] Combined output.xml not found: "
            f"{output_xml}"
        )
        return False

    if not DOCX_SCRIPT.exists():
        print(
            f"[ERROR] DOCX generator not found: "
            f"{DOCX_SCRIPT}"
        )
        return False

    word_report.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\n" + "=" * 60)
    print("Generating Word Report...")
    print("=" * 60)

    docx_python = VENV_SCRIPTS / "python.exe"

    if not docx_python.exists():
        docx_python = Path(sys.executable)

    docx_command = [
        str(docx_python),
        str(DOCX_SCRIPT),
        str(output_xml),
        str(word_report),
    ]

    docx_result = subprocess.run(
        docx_command,
        cwd=ROOT,
    )

    if docx_result.returncode == 0:
        print(
            f"[SUCCESS] Word report generated: "
            f"{word_report}"
        )
        return True

    print(
        f"[ERROR] Failed to generate Word report. "
        f"Return code: {docx_result.returncode}"
    )

    return False


def main():
    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    run_report_dir = (
        REPORTS / f"Test_Case_Report_{run_id}"
    )

    pabot_executable = (
        VENV_SCRIPTS / "pabot.exe"
    )

    if not pabot_executable.exists():
        raise FileNotFoundError(
            f"Pabot executable not found: "
            f"{pabot_executable}"
        )

    environment = dict(
        __import__("os").environ
    )

    environment["PATH"] = (
        f"{VENV_SCRIPTS};"
        f"{environment.get('PATH', '')}"
    )

    print("=" * 60)
    print("Starting Parallel API Automation")
    print("=" * 60)
    print(f"Test Directory : {TESTS}")
    print(f"Report Directory: {run_report_dir}")
    print("Processes      : 4")
    print("=" * 60)

    # --------------------------------------------------
    # STEP 1: Execute tests using Pabot
    # --------------------------------------------------

    REPORTS.mkdir(parents=True, exist_ok=True)

    pabot_result = subprocess.run(
        [
            str(pabot_executable),
            "--processes",
            "4",
            "--outputdir",
            str(run_report_dir),
            str(TESTS),
        ],
        # Run from reports/ so Pabot's .pabotsuitenames file is written there too
        cwd=REPORTS,
        env=environment,
    )

    # --------------------------------------------------
    # STEP 2: Generate individual Robot reports
    # --------------------------------------------------

    pabot_results_dir = (
        run_report_dir / "pabot_results"
    )

    for output_file in sorted(
        pabot_results_dir.glob("*/output.xml")
    ):
        suite_name = get_suite_name(
            output_file
        )

        destination = (
            run_report_dir / "suites" /
            safe_name(suite_name)
        )

        create_report(
            output_file,
            destination
        )

    # --------------------------------------------------
    # Remove Pabot's working files; keep them only if Pabot itself
    # errored (exit code above 251), since they hold the console output
    # --------------------------------------------------

    if pabot_result.returncode <= 251:
        shutil.rmtree(pabot_results_dir, ignore_errors=True)
        (REPORTS / ".pabotsuitenames").unlink(missing_ok=True)

    # --------------------------------------------------
    # STEP 3: Get combined Pabot output
    # --------------------------------------------------

    combined_output = (
        run_report_dir / "output.xml"
    )

    if combined_output.exists():

        # --------------------------------------------------
        # STEP 4: Generate custom HTML dashboard
        # --------------------------------------------------

        html_report = (
            run_report_dir /
            "Test_report.html"
        )

        print("\n" + "=" * 60)
        print("Generating HTML Dashboard...")
        print("=" * 60)

        generate_report(
            combined_output,
            html_report
        )

        print(
            f"[SUCCESS] HTML report generated: "
            f"{html_report}"
        )

        # --------------------------------------------------
        # STEP 5: Generate Word report
        # --------------------------------------------------

        word_report = (
            run_report_dir /
            "Product_Offering_Test_Report.docx"
        )

        generate_word_report(
            combined_output,
            word_report
        )

    else:
        print(
            f"[ERROR] Combined Pabot output not found: "
            f"{combined_output}"
        )

    # --------------------------------------------------
    # STEP 6: Print final report locations
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("EXECUTION COMPLETED")
    print("=" * 60)

    print(
        f"Pabot return code : "
        f"{pabot_result.returncode}"
    )

    print(
        f"Reports directory : "
        f"{run_report_dir}"
    )

    print(
        f"HTML Dashboard    : "
        f"{run_report_dir / 'Test_report.html'}"
    )

    print(
        f"Word Report       : "
        f"{run_report_dir / 'Product_Offering_Test_Report.docx'}"
    )

    print(
        f"Robot Report      : "
        f"{run_report_dir / 'report.html'}"
    )

    print(
        f"Robot Log         : "
        f"{run_report_dir / 'log.html'}"
    )

    print(
        f"Suite Reports     : "
        f"{run_report_dir / 'suites'}"
    )

    print("=" * 60)

    return pabot_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())