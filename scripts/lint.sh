#!/usr/bin/env bash

set -x

mypy -p app
black app --check
isort --check-only app
flake8
