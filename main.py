#!/usr/bin/env python3
"""Backwards-compatible entry point.

Historically selkokortti was run as ``python main.py ...``. The logic now lives
in the ``selkokortti`` package; this shim keeps the old invocation working.
"""

from selkokortti.cli import app

if __name__ == "__main__":
    app()
