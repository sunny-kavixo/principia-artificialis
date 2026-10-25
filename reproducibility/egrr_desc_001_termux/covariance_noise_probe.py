"""Run the constructed covariance-path repeatability probe."""

from pathlib import Path
import sys


EGRR_DIR = Path(__file__).resolve().parents[2] / "experiments" / "egrr_issue28"
sys.path.insert(0, str(EGRR_DIR))

from covariance_repeatability import main


if __name__ == "__main__":
    raise SystemExit(main())
