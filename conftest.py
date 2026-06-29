import os
import sys

# Add each Python package's source root to sys.path so tests can import
# packages without them being installed. Only directories that actually
# exist are appended; missing ones are silently skipped.
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
for _src in (
    "social-data-collector/src",
    "social-common",
    "social-alert-engine/src",
):
    _path = os.path.abspath(os.path.join(_REPO_ROOT, _src))
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.append(_path)