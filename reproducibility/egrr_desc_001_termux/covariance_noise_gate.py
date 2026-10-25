"""Constructed-only covariance-path C-NOISE gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sabotage", action="store_true")
    args = parser.parse_args()
    probe = Path(__file__).with_name("covariance_noise_probe.py")
    outputs = []
    for _ in range(3):
        completed = subprocess.run(
            [sys.executable, str(probe)],
            text=False,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0 or completed.stderr:
            print("GATE: FAIL — covariance-path probe execution failed")
            return 1
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            print("GATE: FAIL — covariance-path probe output was not JSON")
            return 1
        required = {
            "fixture": "constructed-covariance-noise-903",
            "seed": 903,
            "shape": [64, 32],
            "correction_count": 128,
            "selection_count": 128,
        }
        if any(result.get(key) != value for key, value in required.items()):
            print("GATE: FAIL — covariance-path probe contract mismatch")
            return 1
        outputs.append(completed.stdout)

    if args.sabotage:
        outputs[-1] += b"\nplanted repeat mismatch\n"

    if len(set(outputs)) != 1:
        print("GATE: FAIL — covariance-path repeat mismatch detected")
        return 1

    print("GATE: PASS — covariance-path repeats byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
