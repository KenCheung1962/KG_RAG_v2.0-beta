#!/usr/bin/env python3
"""
Run all backend tests.
Usage: python run_tests.py [options]
"""

import os
import sys
import subprocess


def main():
    """Run pytest with coverage."""
    # Get the tests directory
    tests_dir = os.path.dirname(os.path.abspath(__file__))

    # Default pytest args
    args = [
        sys.executable, "-m", "pytest",
        tests_dir,
        "-v",
        "--tb=short",
        "-asyncio-mode=auto"
    ]

    # Allow passing additional pytest arguments
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    print(f"Running tests in: {tests_dir}")
    print(f"Command: {' '.join(args)}")
    print()

    result = subprocess.run(args)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
