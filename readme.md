# API Automation – Robot Framework

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env` with `CLIENT_ID`, `CLIENT_SECRET`, `API_USERNAME`, `API_PASSWORD`
and `COMPATIBILITY_COOKIE`. `.env` is ignored by Git — never commit it.

## Project structure

```text
tests/API/                     Robot test suites (product offering, compatibility, auth)
tests/python/                  Pytest tests for the Python validators
resources/auth/                Token keywords and IAM settings
resources/keywords/            Shared API keywords
resources/variables/           API URLs and endpoints
python/                        Validators and report generators
testdata/api/                  CSV test data (one row = one test)
run_entire_tests.py            Run all suites in parallel (Pabot)
Single_Test_case.py            Run the product offering suite only
```

## Run tests

```powershell
.\.venv\Scripts\python.exe run_entire_tests.py   # all suites in parallel
.\.venv\Scripts\python.exe Single_Test_case.py   # product offering suite only
```

`.env` is loaded automatically, so suites can also be run directly with
`robot` or from VS Code.
`run_entire_tests.py` writes reports to `reports\parallel_<run-id>\`
(`report.html`, `log.html`, `Test_report.html` dashboard and Word report) and a
copy per suite to `reports\parallel_<run-id>\suites\<suite name>\`.

## Add a test case

Add a row to the CSV in `testdata\api\`. The first column is the test name;
each row runs as its own test (DataDriver).

In `product_offering.csv`, any extra `${...}` column is sent to the API as a
query parameter. Use the API's parameter name as the header (for example
`${limit}` or `${q.deviceType}`); leave a cell empty to not send it. Columns
such as `[Tags]` are not sent, and a column that repeats a built-in parameter
the test already sends (`relatedParty.name`, or `channel.name` /
`category.name` / `fields` when set) fails the test.
Test names (first column) must be unique.

## Generate a DOCX test report

Robot Framework does not generate DOCX files by itself. After running the
channel-based product-offering suite, convert its `output.xml` with:

```powershell
.\.venv\Scripts\python.exe python\generate_docx_report.py reports\channel_based_product_filteration_retry\output.xml reports\channel_based_product_filteration_retry\Product_Offering_Test_Report.docx
```

## Technical Overview

### Architecture

This is a Python-based, keyword-driven Robot Framework automation project. It
uses a layered test architecture: Robot Framework test suites call reusable
keywords and shared resources; those keywords use Python libraries and HTTP
client libraries to exercise APIs. CSV files provide data for data-driven
tests.

```text
Robot Framework test suites
        |
        v
Reusable Robot keywords, resources, and variables
        |
        v
Python helper libraries and HTTP request libraries
        |
        v
External APIs        CSV test data
        |
        v
Robot output.xml
   |                       |
   v                       v
Rebot HTML reports    Custom Python dashboard
                      execution_dashboard.html
```

`run_entire_tests.py` runs suites in parallel with Pabot, copies each suite's
results into `suites\<suite name>` inside the run's report folder, and preserves Robot's
standard `output.xml`, `log.html`, and `report.html` generation. The custom
dashboard is an additional report generated from Robot's XML results; it does
not replace Robot Framework's reporting.

### Languages and Frameworks

| Technology | Purpose |
| --- | --- |
| Python | Parallel-run orchestration, custom validation and data helpers, and HTML dashboard generation |
| Robot Framework | Test definitions, reusable keyword execution, and standard XML/HTML reports |
| Pabot | Parallel Robot Framework test execution |
| Robot Framework Requests / RequestsLibrary | HTTP API interactions in Robot keywords |
| Robot Framework Browser / Playwright | Browser automation capability available in the project dependencies |
| Selenium / Robot Framework SeleniumLibrary | Browser automation capability available in the project dependencies |
| HTML and embedded CSS | Standalone, responsive execution dashboard |
| CSV | Data-driven test inputs |

The dependency file recommends Python 3.13. Browser automation dependencies
are installed as project capabilities; the inspected test suites primarily
cover API scenarios.

### Main Project Directories

| Path | Responsibility |
| --- | --- |
| `tests\API\` | Robot Framework API test suites |
| `tests\python\` | Pytest tests for Python validation helpers |
| `resources\keywords\` | Shared Robot Framework API keywords |
| `resources\auth\` | Authentication keywords and related variables |
| `resources\variables\` | Shared API endpoints and test configuration |
| `python\` | Python validation, CSV, and report-generation helpers |
| `testdata\api\` | CSV datasets used by API tests |
| `run_entire_tests.py` | Pabot orchestration and per-suite report handling |
| `reports\` | All run output: consolidated and per-suite reports, dashboard, Word report |

### Test and Report Data Flow

Robot suites call shared keywords that send HTTP requests and validate
responses, including status codes, headers, response time, schemas, and
business data. Some tests obtain their inputs from CSV files. Robot records
execution results in `output.xml`; Rebot uses this result data to create the
standard HTML log and report. The custom dashboard parser reads the same XML
to calculate execution totals, pass/fail percentages, pipeline summaries, and
failure details.

PI IDs, pipeline labels, action types, environment metadata, and RCA values
are shown only when available in result metadata or the execution environment.
When the current results do not provide them, the dashboard uses fallback
labels rather than inventing values.
