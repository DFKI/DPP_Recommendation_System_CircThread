from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_SUITES = [
    "services/eprel_provider/tests",
    "services/resolver/tests",
    "services/service_registry/tests",
    "services/recommendation_engine/tests",
    "services/repair_service_provider/tests",
]


def main() -> int:
    for suite in TEST_SUITES:
        print(f"\n== {suite} ==")
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", suite, "-v"],
            cwd=REPO_ROOT,
            check=False,
        )
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
