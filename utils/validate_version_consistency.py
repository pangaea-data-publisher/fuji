# -*- coding: utf-8 -*-
"""
A simple script that checks the consistency between the version number specified in
setup.json, and the version in the __init__.py file.
"""

import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, os.path.pardir)

# Get the __init__.py version number
with open(os.path.join(ROOT_DIR, 'masci_tools/__init__.py')) as f:
    MATCH_EXPR = "__version__[^'\"]+(['\"])([^'\"]+)"
    VERSION_INIT = re.search(MATCH_EXPR, f.read()).group(2).strip()  # type: ignore

# Get the setup.py version number
with open(os.path.join(ROOT_DIR, 'setup.py')) as f:
    MATCH_EXPR = "version[^'\"]+(['\"])([^'\"]+)"
    VERSION_SETUP = re.search(MATCH_EXPR, f.read()).group(2).strip()  # type: ignore

# Get the pyproject.toml version number
with open(os.path.join(ROOT_DIR, 'pyproject.toml')) as f:
    MATCH_EXPR = "version[^'\"]+(['\"])([^'\"]+)"
    VERSION_PYPROJECT = re.search(MATCH_EXPR, f.read()).group(2).strip()  # type: ignore

# Get the .bumpversion.cfg current_version number
with open(os.path.join(ROOT_DIR, '.bumpversion.cfg')) as f:
    MATCH_EXPR = r'current_version\s*=\s*([^\\S\r\n]+)'
    VERSION_BUMPVERSION = re.search(MATCH_EXPR, f.read()).group(1).strip()  # type: ignore

if VERSION_INIT != VERSION_SETUP:
    print(f"Version numbers don't match: init:'{VERSION_INIT}', setup:'{VERSION_SETUP}' ")
    sys.exit(1)

if VERSION_INIT != VERSION_PYPROJECT:
    print(f"Version numbers don't match: init:'{VERSION_INIT}', pyproject:'{VERSION_PYPROJECT}' ")
    sys.exit(1)

if VERSION_INIT != VERSION_BUMPVERSION:
    print(f"Version numbers don't match: init:'{VERSION_INIT}', bumpversion:'{VERSION_BUMPVERSION}' ")
    sys.exit(1)
