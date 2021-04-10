"""
This module specifies the main testcases for our integration tests. These are
not pytest tests themselves, but rather encode some setup and later assertion
for inclusion in the integration tests.
"""

from .base import TESTCASES

__all__ = ("TESTCASES",)
