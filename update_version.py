"""Backward-compatible entry point for version metadata updates."""
from common.update_version import *  # noqa: F401,F403
from common.update_version import main

if __name__ == "__main__":
    main()
