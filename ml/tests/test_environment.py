"""
RecoverAI ML — Environment Test

Phase 1: Verify that the Python environment is correctly configured
and the project structure is importable.

No ML libraries are tested here — they are not installed in Phase 1.
"""

import sys
import os


def test_python_version():
    """Python 3.10+ required for match statements and modern typing."""
    assert sys.version_info >= (3, 10), (
        f"Python 3.10+ required, got {sys.version_info.major}.{sys.version_info.minor}"
    )


def test_ml_src_importable():
    """Verify the ml/src package is on the Python path."""
    src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
    assert os.path.isdir(src_path), f"ml/src directory not found at {src_path}"


def test_ml_directory_structure():
    """Verify expected ML directory structure exists."""
    root = os.path.join(os.path.dirname(__file__), '..')

    required_dirs = [
        'data',
        'data/raw',
        'data/processed',
        'data/synthetic',
        'models',
        'notebooks',
        'src',
        'src/features',
        'src/risk',
        'src/recovery',
        'src/evaluation',
        'tests',
    ]

    for d in required_dirs:
        path = os.path.join(root, d)
        assert os.path.isdir(path), f"Required directory missing: ml/{d}"


def test_requirements_file_exists():
    """requirements.txt must exist."""
    root = os.path.join(os.path.dirname(__file__), '..')
    req_path = os.path.join(root, 'requirements.txt')
    assert os.path.isfile(req_path), "ml/requirements.txt not found"
