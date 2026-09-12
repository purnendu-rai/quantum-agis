#!/bin/bash
cd backend
# Prefer the repo venv interpreter when present; fall back to PATH pytest.
if [ -f ../venv/Scripts/python.exe ]; then
  PY=../venv/Scripts/python.exe
elif [ -f ../venv/bin/python ]; then
  PY=../venv/bin/python
else
  PY=python
fi
"$PY" -m pytest tests/ -v --cov=app --cov-report=html
cd ..
