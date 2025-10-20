"""
This placeholder exists to avoid shadowing Python's standard library package
named 'http'. If you intended to use the legacy custom HTTP server code, import
from 'legacy_http' instead.

Note: Keeping this file tiny ensures `import http.client` from stdlib works.
"""

# Intentionally empty; do not add names that would interfere with stdlib.
"""
This file previously implemented a custom HTTP-like server and conflicted with
Python's standard library package name 'http'. It has been replaced to avoid
shadowing stdlib. See 'legacy_http.py' for the old implementation.
"""

from legacy_http import HttpServer  # noqa: F401