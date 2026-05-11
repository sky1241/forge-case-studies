## locate skip — pip_install_failed

pip install -e . exit code: 1
pip install -e .[test] exit code: 1

### Last 30 lines of pip output (stderr):
```

         12 | typedef enum {false, true} bool;
            |               ^~~~~
      ast27/Custom/../Include/../Include/asdl.h:12:15: note: ‘false’ is a keyword with ‘-std=c23’ onwards
      ast27/Custom/../Include/../Include/asdl.h:12:28: error: expected ‘;’, identifier or ‘(’ before ‘bool’
         12 | typedef enum {false, true} bool;
            |                            ^~~~
      ast27/Custom/../Include/../Include/asdl.h:12:28: warning: useless type name in empty declaration
      In file included from /usr/include/python3.13/pyport.h:358,
                       from /usr/include/python3.13/Python.h:64,
                       from ast27/Custom/typed_ast.c:1:
      ast27/Custom/../Include/compile.h:12:12: error: unknown type name ‘PyFutureFeatures’
         12 | PyAPI_FUNC(PyFutureFeatures *) PyFuture_FromAST(struct _mod *, const char *);
            |            ^~~~~~~~~~~~~~~~
      /usr/include/python3.13/exports.h:94:53: note: in definition of macro ‘PyAPI_FUNC’
         94 | #       define PyAPI_FUNC(RTYPE) Py_EXPORTED_SYMBOL RTYPE
            |                                                     ^~~~~
      error: command '/usr/bin/x86_64-linux-gnu-gcc' failed with exit code 1
      [end of output]
  
  note: This error originates from a subprocess, and is likely not a problem with pip.
  ERROR: Failed building wheel for typed-ast
error: failed-wheel-build-for-install

× Failed to build installable wheels for some pyproject.toml based projects
╰─> typed-ast

```
