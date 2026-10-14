<!-- ----------------------To activate Vurital environment----------------------------- -->
.venv\Scripts\activate


<!-- --------------------------------------------------- -->
<!-- basic configuration -->
API-Automation-Robot-Framework/
│
├── tests/
│   └── api/
│       ├── test_auth.robot              → Token API test
│       └── channel_based_product_filteration.robot  → Channel-based Product Offering API test
│
├── resources/
│   ├── auth/
│   │   ├── auth_variables.robot         → Token URL + credentials
│   │   └── auth_keywords.robot          → Function/keyword to generate token
│   │
│   ├── keywords/
│   │   └── api_keywords.robot           → Product API reusable keywords
│   │
│   └── variables/
│       └── api_variables.robot           → Product API URL + parameters
│
├── testdata/
│   └── api/                             → Request/test data
│
├── reports/                             → Robot execution reports
│
└── requirements.txt                     → All Python packages

<!-- Pabot -->
Pabot is a tool that runs your Robot Framework tests in parallel instead of one by one.

To run all API tests in parallel and classify each test result:

```powershell
.\.venv\Scripts\python.exe run_parallel_tests.py
```

Passed tests are written to `results\passed\<test name>`. Failed tests are
written only to `results\failed\<test name>` and do not update the existing
top-level result files.# API_Automation_robot_framework

The same run also generates an additional dashboard at
`reports\parallel_<run-id>\execution_dashboard.html`. Open that file in a
browser to view the dynamic execution summary; Robot Framework's standard
`output.xml`, `log.html`, and `report.html` files are still generated as before.# API_Automation_robot_framework
# API_Automation_robot_framework
# API_Automation_robot_framework

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

`run_parallel_tests.py` runs suites in parallel with Pabot, classifies
individual suite results into passed and failed folders, and preserves Robot's
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
| `run_parallel_tests.py` | Pabot orchestration and per-suite report handling |
| `results\` | Per-suite reports grouped by pass/fail result |
| `reports\` | Parallel run artifacts and consolidated execution reports |

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
