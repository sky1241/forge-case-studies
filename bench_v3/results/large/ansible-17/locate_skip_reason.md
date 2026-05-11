## locate skip — pytest_collect_failed

coverage run -m pytest tests/ -x exit code: 4

### Last 30 lines of pytest output:
```
============================= test session starts ==============================
platform linux -- Python 3.13.12, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/sky/forge-case-studies/clones/ansible
configfile: tox.ini
plugins: hypothesis-6.152.4, cov-7.1.0, timeout-2.4.0
collected 0 items

=============================== warnings summary ===============================
../../../Bureau/forge/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:1434
  /home/sky/Bureau/forge/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:1434: PytestConfigWarning: Unknown config option: mock_use_standalone_module
  
    self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
============================== 1 warning in 0.31s ==============================
ERROR: file or directory not found: tests/

/home/sky/Bureau/forge/.venv/lib/python3.13/site-packages/coverage/control.py:958: CoverageWarning: No data was collected. (no-data-collected); see https://coverage.readthedocs.io/en/7.13.5/messages.html#warning-no-data-collected
  self._warn("No data was collected.", slug="no-data-collected")

```
