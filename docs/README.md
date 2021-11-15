How to build the docs:

You need to have installed fuji with the developer dependencies:
```
pip install .[dev]
```

Then to build the docs execute:
```
sphinx-build -b html -d build/doctrees  source build/html
```
or
```
make html
```
from this folder.
The resulting html pages will be under .build/html with the starting page being,
index.html. By opening this with a browser you can look at the documentation.

Every file in the 'module guide' folder is auto generated with sphinx-apidoc:

```
sphinx-apidoc -f -o docs/source ../fuji_server/
```

At some point this part can/should be moved into the CI pipeline.
