#!/usr/bin/env python3
"""
Wrapper script to run the verification demo from scripts/ directory.
"""
from __future__ import annotations

import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from run_demo import run_demo

if __name__ == "__main__":
    sys.exit(run_demo())
