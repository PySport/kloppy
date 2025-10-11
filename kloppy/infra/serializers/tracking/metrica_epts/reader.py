# This module re-exports common EPTS functionality for backwards compatibility.
# The actual implementations have been moved to epts_common.py

from ..epts_common import build_regex, read_raw_data

__all__ = ["build_regex", "read_raw_data"]
