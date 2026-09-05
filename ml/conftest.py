"""
conftest.py — pytest configuration for RecoverAI ML tests.

Adds the monorepo root to sys.path so that `ml.src.*` imports work correctly
in all test files regardless of how pytest is invoked.
"""

import sys
import os

# Add the monorepo root (parent of ml/) to sys.path
# This enables: from ml.src.simulation.xxx import yyy
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
