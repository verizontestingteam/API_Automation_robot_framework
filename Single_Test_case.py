import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent

# Load credentials from the local .env file into the environment
load_dotenv(ROOT / ".env")
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
VENV_ROBOT = ROOT / ".venv" / "Scripts" / "robot.exe"

# Use venv executables if available, else current Python environment
PYTHON_EXE = str(VENV_PYTHON if VENV_PYTHON.exists() else sys.executable)
ROBOT_EXE = str(VENV_ROBOT if VENV_ROBOT.exists() else "robot")

TEST_FILE = ROOT / "tests" / "API" / "channel_based_product_filteration.robot"
REPORT_DIR = ROOT / "reports" / "channel_based_product_filteration_retry"
OUTPUT_XML = REPORT_DIR / "output.xml"
DOCX_REPORT = REPORT_DIR / "Product_Offering_Test_Report.docx"
DOCX_SCRIPT = ROOT / "python" / "generate_docx_report.py"


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Step 1: Running Robot Framework Test Suite...")
    print(f"Target: {TEST_FILE}")
    print(f"Output Directory: {REPORT_DIR}")
    print("=" * 60)

    # 1. Execute Robot Framework (generates output.xml, log.html, report.html)
    robot_cmd = [
        ROBOT_EXE,
        "--outputdir", str(REPORT_DIR),
        str(TEST_FILE),
    ]
    robot_proc = subprocess.run(robot_cmd, cwd=str(ROOT))

    print("\n" + "=" * 60)
    print("Step 2: Generating Word (.docx) Test Report...")
    print("=" * 60)

    # 2. Execute DOCX generation script
    if OUTPUT_XML.exists():
        docx_cmd = [
            PYTHON_EXE,
            str(DOCX_SCRIPT),
            str(OUTPUT_XML),
            str(DOCX_REPORT),
        ]
        docx_proc = subprocess.run(docx_cmd, cwd=str(ROOT))
        if docx_proc.returncode == 0:
            print(f"\n[SUCCESS] Word report generated: {DOCX_REPORT}")
        else:
            print("\n[ERROR] Failed to generate Word report.")
    else:
        print(f"\n[ERROR] {OUTPUT_XML} not found. Skipping DOCX generation.")

    print("\n" + "=" * 60)
    print("Generated Reports:")
    print(f" - HTML Report: {REPORT_DIR / 'report.html'}")
    print(f" - HTML Log:    {REPORT_DIR / 'log.html'}")
    print(f" - Word Report: {DOCX_REPORT}")
    print("=" * 60)

    return robot_proc.returncode


if __name__ == "__main__":
    sys.exit(main())
