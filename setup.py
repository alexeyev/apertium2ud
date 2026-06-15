# Project metadata now lives in pyproject.toml (PEP 621); resource generation
# is handled by the in-tree build backend (_build_backend.py).
# This shim is kept only for tooling that still invokes `setup.py` directly.
from setuptools import setup

if __name__ == "__main__":
    setup()
