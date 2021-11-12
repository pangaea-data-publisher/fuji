# -*- coding: utf-8 -*-
"""
A simple script that checks the consistency between the version number specified in
setup.json, and the version in the __init__.py file.
"""

import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, os.path.pardir)

# Get the __init__.py version number
with open(os.path.join(ROOT_DIR, 'fuji_server/__init__.py')) as f:
    MATCH_EXPR = "__version__[^'\"]+(['\"])([^'\"]+)"
    VERSION_INIT = re.search(MATCH_EXPR, f.read()).group(2).strip()  # type: ignore

# Get the setup.py version number
with open(os.path.join(ROOT_DIR, 'pyproject.toml')) as f:
    MATCH_EXPR = "version[^'\"]+(['\"])([^'\"]+)"
    VERSION_SETUP = re.search(MATCH_EXPR, f.read()).group(2).strip()  # type: ignore

# Get the .fuji current_version number
with open(os.path.join(ROOT_DIR, 'fuji_server/controllers/fair_check.py')) as f:
    MATCH_EXPR = "FUJI_VERSION[^'\"]+(['\"])([^'\"]+)"
    VERSION_FAIRCHECK = re.search(MATCH_EXPR, f.read()).group(2).strip()  # type: ignore

# Check in docs, because there the version is currently also hardcoded
with open(os.path.join(ROOT_DIR, 'docs/source/conf.py')) as f:
    MATCH_EXPR = "version =[^'\"]+(['\"])([^'\"]+)"
    VERSION_DOCS = re.search(MATCH_EXPR, f.read()).group(2).strip()  # type: ignore

if VERSION_INIT != VERSION_SETUP:
    print(f"Version numbers don't match: init:'{VERSION_INIT}', setup:'{VERSION_SETUP}' ")
    sys.exit(1)

if VERSION_INIT != VERSION_FAIRCHECK:
    print(f"Version numbers don't match: init:'{VERSION_INIT}', FAIRCheck:'{VERSION_FAIRCHECK}' ")
    sys.exit(1)

if VERSION_INIT != VERSION_DOCS:
    print(f"Version numbers don't match: init:'{VERSION_INIT}', Docs:'{VERSION_DOCS}' ")
    sys.exit(1)
