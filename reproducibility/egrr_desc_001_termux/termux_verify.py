"""Constructed-only Android Termux verification for EGRR-DESC-001.

This does not generate either research seed block or execute a study.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


EXPECTED_COMMIT = "29c63fe399fa1cbc45974717b8de14a1cd989401"
EXPECTED_SOURCES = {
    "experiments/egrr_issue28/storage.py":
        "1a20b6ec271ec4bb7d47e3d0f65a284559efc83ab2f0a1457e09dbd349b4f6f1",
    "experiments/egrr_issue28/test_egr2_integration.py":
        "5f8fad442bd2c144358bba6001cb9fc7ff505608209e71c707cfeaed61100987",
    "experiments/egrr_issue28/test_verified_aggregate.py":
        "8f46b13e9ced0e354b954781fc7321fc97c0a49c2874c39a183cb79029491f03",
    "experiments/egrr_issue28/verified_aggregate.py":
        "3384fe449c3482b1e86af321674c8ac119714e0cdaf1f95246a013eadbacb69b",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_check(name, command, cwd, expected_exit, raw_dir):
    completed = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, check=False
    )
    (raw_dir / f"{name}.stdout.txt").write_text(
        completed.stdout, encoding="utf-8"
    )
    (raw_dir / f"{name}.stderr.txt").write_text(
        completed.stderr, encoding="utf-8"
    )
    return {
        "name": name,
        "command": command,
        "expected_exit": expected_exit,
        "actual_exit": completed.returncode,
        "passed": completed.returncode == expected_exit,
        "stdout_file": f"raw/{name}.stdout.txt",
        "stderr_file": f"raw/{name}.stderr.txt",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path,
        help="directory for JSON and raw output (default: package directory)",
    )
    args = parser.parse_args()
    package_dir = Path(__file__).resolve().parent
    root = package_dir.parents[1]
    egrr_dir = root / "experiments" / "egrr_issue28"
    output_dir = (
        args.output_dir.resolve() if args.output_dir else package_dir
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        capture_output=True, check=False,
    ).stdout.strip()
    identities = {
        relative: sha256(root / relative)
        for relative in EXPECTED_SOURCES
    }
    identity_ok = (
        commit == EXPECTED_COMMIT and identities == EXPECTED_SOURCES
    )

    checks = [
        run_check(
            "malformed_registration",
            [
                sys.executable, "-m", "pytest", "-q",
                "test_verified_aggregate.py::VerifiedAggregateTests::test_invalid_registration_inputs_fail_closed",
            ],
            egrr_dir, 0, raw_dir,
        ),
        run_check(
            "benign_egr2_round_trip",
            [
                sys.executable, "-m", "pytest", "-q",
                "test_egr2_integration.py::EGR2IntegrationTests::test_corrected_and_uncorrected_round_trip_bytes_and_sha256",
            ],
            egrr_dir, 0, raw_dir,
        ),
        run_check(
            "benign_structural_gate",
            [sys.executable, "structural_gate.py"],
            egrr_dir, 0, raw_dir,
        ),
        run_check(
            "crc_sabotage_gate",
            [sys.executable, "structural_gate.py", "--sabotage"],
            egrr_dir, 1, raw_dir,
        ),
    ]

    summary = {
        "schema": "EGRR-DESC-001-TERMUX-VERIFY-1",
        "scientific_status": "DRAFT / NOT FROZEN / NOT RUN",
        "python": sys.version,
        "executable": sys.executable,
        "commit_expected": EXPECTED_COMMIT,
        "commit_actual": commit,
        "source_sha256_expected": EXPECTED_SOURCES,
        "source_sha256_actual": identities,
        "identity_ok": identity_ok,
        "checks": checks,
    }
    summary["verification_ok"] = identity_ok and all(
        item["passed"] for item in checks
    )
    summary_path = output_dir / "termux-verification.json"
    summary_path.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["verification_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
