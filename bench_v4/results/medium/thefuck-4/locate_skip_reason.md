## locate skip — pip_install_failed

pip install -e . exit code: 1
pip install -e .[test] exit code: 1

### Last 30 lines of pip output (stderr):
```
lay/lib/python3.13/site-packages/setuptools/build_meta.py", line 481, in get_requires_for_build_editable
          return self.get_requires_for_build_wheel(config_settings)
                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
        File "/tmp/pip-build-env-w9g9xxii/overlay/lib/python3.13/site-packages/setuptools/build_meta.py", line 333, in get_requires_for_build_wheel
          return self._get_build_requires(config_settings, requirements=[])
                 ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        File "/tmp/pip-build-env-w9g9xxii/overlay/lib/python3.13/site-packages/setuptools/build_meta.py", line 301, in _get_build_requires
          self.run_setup()
          ~~~~~~~~~~~~~~^^
        File "/tmp/pip-build-env-w9g9xxii/overlay/lib/python3.13/site-packages/setuptools/build_meta.py", line 520, in run_setup
          super().run_setup(setup_script=setup_script)
          ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
        File "/tmp/pip-build-env-w9g9xxii/overlay/lib/python3.13/site-packages/setuptools/build_meta.py", line 317, in run_setup
          exec(code, locals())
          ~~~~^^^^^^^^^^^^^^^^
        File "<string>", line 3, in <module>
      ModuleNotFoundError: No module named 'pkg_resources'
      [end of output]
  
  note: This error originates from a subprocess, and is likely not a problem with pip.
ERROR: Failed to build 'file:///home/sky/forge-case-studies/clones/thefuck' when getting requirements to build editable

```
