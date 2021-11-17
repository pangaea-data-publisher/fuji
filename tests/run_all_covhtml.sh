#!/usr/bin/env sh
pytest -v --xkill --cov-report=html --cov=fuji_server --cov=./
