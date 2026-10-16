# Project Architecture

## Overview

This is a Python-based API automation project built around Robot Framework.
Robot suites define test scenarios, CSV files provide data-driven inputs,
RequestsLibrary sends HTTP requests, and Python libraries perform response
validation and report generation.

The current test suites exercise APIs; Playwright and Selenium are listed as
dependencies but are not currently used by the test code.

## High-Level Data Flow

```text
CSV test data
     |
     v
Robot Framework test suites <--- shared resources, keywords, and variables
     |
     v
RequestsLibrary ---> IAM token API and application APIs
     |
     v
Python response validation helpers
     |
     v
Robot output.xml
     |
     +---> Robot Framework HTML log and report
     +---> Custom HTML dashboard
     +---> Word (.docx) report
```

## Folder Structure

```text
API Automation robot framework/
├── tests/
│   ├── API/                         # Robot Framework API suites
│   └── python/                      # Pytest tests for Python helpers
├── resources/
│   ├── auth/                        # Authentication, credentials, and log masking
│   ├── keywords/                    # Reusable HTTP/API Robot keywords
│   └── variables/                   # Shared API endpoints and variables
├── testdata/
│   └── api/                         # CSV data used to create test cases
├── python/                          # Validators and report-generation modules
├── reports/                         # Local generated run reports (Git-ignored)
├── docs/                            # Framework workflow documentation
├── scripts/                         # Setup, validation, and search utilities
├── adapters/                        # AI assistant integration instructions
├── .agent/                          # Agent workflows
├── .agents/
│   ├── agents/                      # Specialized agent role descriptions
│   └── skills/                      # Project-specific skills
├── .gemini/                         # Gemini assistant instructions
├── .gsd/
│   ├── examples/                    # Example project workflows
│   └── templates/                   # Planning and execution templates
├── .env.example                     # Safe template for local settings
├── requirements.txt                 # Python dependencies
├── run_entire_tests.py              # Parallel suite runner and report orchestration
└── Single_Test_case.py              # Single product-offering suite runner
```

### Main test and helper files

| File | Responsibility |
| --- | --- |
| `tests\API\channel_based_product_filteration.robot` | Data-driven product-offering API validation |
| `tests\API\test_compatibility_check.robot` | Data-driven compatibility API validation |
| `tests\API\test_auth.robot` | OAuth token acquisition check |
| `resources\keywords\api_keywords.robot` | Builds and sends product-offering and compatibility requests |
| `resources\auth\auth_keywords.robot` | Gets and caches OAuth tokens; integrates secret masking |
| `resources\auth\credentials.py` | Loads local `.env` credentials into the process environment |
| `resources\variables\api_variables.robot` | Shared application API URLs and endpoints |
| `python\api_custom_validations.py` | Response, schema, timing, price, validity, and channel assertions |
| `python\secret_masker.py` | Masks sensitive values in Robot Framework log messages |
| `python\generate_html_dashboard.py` | Builds a dashboard from Robot's XML results |
| `python\generate_docx_report.py` | Creates a Word report from Robot's XML results |

## Test Execution

`run_entire_tests.py` loads values from the root `.env` file, starts the API
suites using Pabot, and places the combined and per-suite reports in a
timestamped subdirectory under `reports\`. `Single_Test_case.py` runs the
product-offering suite and produces its reports.

DataDriver reads CSV files in `testdata\api\` and creates a test case for each
data row. Shared Robot resources supply keywords, authentication, endpoints,
and variables. API responses are checked by Python validation keywords and
Robot assertions.

## Reporting

Robot Framework produces `output.xml`, `log.html`, and `report.html`. The
parallel runner additionally creates a custom HTML dashboard and a Word
report from the XML output. These are generated artifacts, not source files,
and are excluded from Git.

The current test code uses Robot Framework reporting and the custom dashboard.
Allure reporting is not configured as an active project report, and the
Playwright/Selenium dependencies do not affect the current API test flow.

## Configuration and Secrets

Copy `.env.example` to `.env` and set the environment-specific values there.
The runner and the authentication resource load configuration from the
environment. `.env` is ignored by Git; do not commit credentials or access
tokens. `.env.example` is the shareable template and should contain no real
secrets.

## Technology Stack

| Technology | Role |
| --- | --- |
| Python | Test orchestration, custom validation, and report generation |
| Robot Framework | Test suites, keyword execution, and XML/HTML reporting |
| Pabot | Parallel Robot Framework execution |
| RequestsLibrary / Requests | HTTP API requests |
| DataDriver | CSV-driven Robot test cases |
| Pytest | Unit tests for Python validation helpers |
| Playwright / Selenium | Installed browser automation dependencies; not currently used by the API suites |

## Run Commands

Run all API suites in parallel:

```powershell
.\.venv\Scripts\python.exe run_entire_tests.py
```

Run the product-offering suite:

```powershell
.\.venv\Scripts\python.exe Single_Test_case.py
```

Run Python helper tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\python
```
