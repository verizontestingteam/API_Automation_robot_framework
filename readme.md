<!-- ----------------------To activate Vurital environment----------------------------- -->
.venv\Scripts\activate


<!-- --------------------------------------------------- -->
<!-- basic configuration -->
API-Automation-Robot-Framework/
│
├── tests/
│   └── api/
│       ├── test_auth.robot              → Token API test
│       └── test_product_offering.robot  → Product Offering API test
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
# API_Automation_robot_framework
