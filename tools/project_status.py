import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from omega.continuity import format_status, inspect_project


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-tests", action="store_true")
    args = parser.parse_args()
    print(format_status(inspect_project(verify_tests=args.verify_tests)))
