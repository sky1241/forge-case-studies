## locate skip — pytest_collect_failed

coverage run -m pytest tests/ -x exit code: 1

### Last 30 lines of pytest output:
```
ureau/forge/.venv/lib/python3.13/site-packages/pytest/__main__.py", line 9, in <module>
    raise SystemExit(pytest.console_main())
SystemExit: 1

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/sky/Bureau/forge/.venv/lib/python3.13/site-packages/coverage/__main__.py", line 12, in <module>
    sys.exit(main())
             ~~~~^^
  File "/home/sky/Bureau/forge/.venv/lib/python3.13/site-packages/coverage/cmdline.py", line 1163, in main
    status = CoverageScript().command_line(argv)
  File "/home/sky/Bureau/forge/.venv/lib/python3.13/site-packages/coverage/cmdline.py", line 853, in command_line
    return self.do_run(options, args)
           ~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/home/sky/Bureau/forge/.venv/lib/python3.13/site-packages/coverage/cmdline.py", line 1047, in do_run
    self.coverage.stop()
    ~~~~~~~~~~~~~~~~~~^^
  File "/home/sky/Bureau/forge/.venv/lib/python3.13/site-packages/coverage/control.py", line 732, in stop
    self._collector.stop()
    ~~~~~~~~~~~~~~~~~~~~^^
  File "/home/sky/Bureau/forge/.venv/lib/python3.13/site-packages/coverage/collector.py", line 344, in stop
    assert self._collectors[-1] is self, (
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Expected current collector to be <Collector at 0x7f4658fe82f0: CTracer>, but it's <Collector at 0x7f465880e5d0: CTracer>

```
