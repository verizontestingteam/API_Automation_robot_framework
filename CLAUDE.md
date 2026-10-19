# CLAUDE.md

Robot Framework API automation for Tecnotree TMF620 product offering,
compatibility check and IAM auth. See readme.md for setup and structure.

## Working rules
- Before changing any file, show the proposed diff and wait for my approval ("apply").
- Never commit, merge or push unless I ask in the current conversation.
  A past approval does not count for a new commit or push.
- Don't run the live API suites unless I ask (they need VPN and .env).
  Use the offline checks below by default.
- If a request is unclear, ask me in chat before guessing.
- Report results honestly: real counts and real error output; never say
  "should work" without having run it.

## Commands (use the venv, PowerShell)
- pytest:     .\.venv\Scripts\python.exe -m pytest tests/python -q
- ruff:       .\.venv\Scripts\python.exe -m ruff check <changed .py files>
- Robot dry:  $env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe -m robot --dryrun --outputdir reports/dryrun tests
- All suites: .\.venv\Scripts\python.exe run_entire_tests.py   (live API)

## Code rules
- Validators live in python/api_custom_validations.py; every new or changed
  validator needs a pytest in tests/python/.
- Changed Python files must not add new ruff errors (existing old ones are known).
- Shared Robot keywords go in resources/keywords/; URLs/endpoints in
  resources/variables/; suites in tests/Regression Suite/ only call keywords.
- Test data is CSV in testdata/api/ (DataDriver): first column = unique,
  non-empty test name; one row = one test.
- Match the existing style: naming, comment density, keyword format.
- Update readme.md when behaviour or usage changes.

## Reuse and efficiency
- Before writing new code, search python/ and resources/keywords/ for an
  existing function or keyword that already does it; reuse or extend it.
- Never copy-paste logic. If the same steps appear twice, move them into one
  shared Python helper or Robot keyword with arguments.
- Keep functions and keywords small with a single job; pass values as
  arguments instead of hard-coding URLs, channels, IDs or test data.
- Put generic helpers (HTTP, JSON, CSV, dates) in python/ or
  resources/keywords/ so any suite can use them, not inside one test suite.
- Avoid wasted work: don't call the same API or parse the same response
  twice in one test; reuse the cached token; avoid fixed sleeps; prefer one
  pass over the data to repeated loops.
- Keep it simple: optimise only where it is clearly slow or wasteful, and
  don't add abstraction a single use doesn't need.

## Security
- Never read, print or commit .env. Secrets (CLIENT_ID, CLIENT_SECRET,
  API_USERNAME, API_PASSWORD, COMPATIBILITY_COOKIE) come only from .env.
- No tokens, passwords or cookies in code, CSV, readme, logs or reports.

## Agents (.claude/agents/)
- head: features/fixes/refactors (plan → preview → implement → test → review)
- tester: runs checks, never edits
- code-reviewer: reviews the uncommitted diff, never edits
- git-publisher: commits, and pushes only on explicit approval
