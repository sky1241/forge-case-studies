## locate skip — pytest_collect_failed

coverage run -m pytest tests/ -x exit code: 4

### Last 30 lines of pytest output:
```
============================= test session starts ==============================
platform linux -- Python 3.13.12, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/sky/forge-case-studies/clones/luigi
plugins: hypothesis-6.152.4, cov-7.1.0, timeout-2.4.0
collected 0 items

============================ no tests ran in 0.36s =============================
ERROR: file or directory not found: tests/

/home/sky/Bureau/forge/.venv/lib/python3.13/site-packages/coverage/control.py:958: CoverageWarning: No data was collected. (no-data-collected); see https://coverage.readthedocs.io/en/7.13.5/messages.html#warning-no-data-collected
  self._warn("No data was collected.", slug="no-data-collected")

```
