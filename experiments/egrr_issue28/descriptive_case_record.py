"""Constructed-fixture case reporting; no EGRR study execution."""

import math

from descriptive_scoring import relative_improvement, DescriptiveScoringError

TINY_BASELINE_THRESHOLD = 1e-12  # Proposed; not frozen.


def score_case(case_id, seed, covariance_mse, magnitude_mse):
    """Always retain an explicit result record, including failures."""
    record = {
        "case_id": case_id,
        "seed": seed,
        "covariance_mse": covariance_mse,
        "magnitude_mse": magnitude_mse,
        "improvement": None,
        "status": "VALID",
        "reason": None,
        "tiny_positive_baseline": False,
    }

    try:
        mag = float(magnitude_mse)
        if math.isfinite(mag) and 0 < mag < TINY_BASELINE_THRESHOLD:
            record["tiny_positive_baseline"] = True

        record["improvement"] = relative_improvement(
            covariance_mse, magnitude_mse
        )

    except (DescriptiveScoringError, TypeError, ValueError, OverflowError) as exc:
        reason = str(exc)
        record["status"] = (
            "UNDEFINED_RATIO"
            if "UNDEFINED" in reason
            else "INVALID_NUMERIC"
        )
        record["reason"] = reason

    return record


def complete_report(
    records, expected_case_ids, *,
    require_six_arms=True, expected_seeds=None
):
    """Validate case IDs, seed identity, six-arm data and ratios."""
    expected = list(expected_case_ids)
    observed = [record["case_id"] for record in records]

    if len(observed) != len(expected) or observed != expected:
        return {
            "status": "INSTRUMENT_FAILED",
            "mean": None,
            "reason": "missing, duplicate, or out-of-order case IDs",
        }

    if expected_seeds is not None:
        if (
            not isinstance(expected_seeds, dict)
            or set(expected_seeds) != set(expected)
        ):
            return {
                "status": "INSTRUMENT_FAILED",
                "mean": None,
                "reason": "invalid expected seed mapping",
            }

        for record in records:
            case_id = record["case_id"]
            actual_seed = record.get("seed")
            expected_seed = expected_seeds[case_id]

            if (
                type(actual_seed) is not int
                or type(expected_seed) is not int
                or actual_seed != expected_seed
            ):
                return {
                    "status": "INSTRUMENT_FAILED",
                    "mean": None,
                    "reason": f"seed mismatch for case {case_id}",
                }

    if require_six_arms:
        for record in records:
            arm_status = validate_six_arms(record.get("arms"))
            if arm_status == "VALID":
                arm_status = validate_paired_mse(record)
            if arm_status != "VALID":
                return {
                    "status": arm_status,
                    "mean": None,
                    "reason": "six-arm or paired-MSE validation failed",
                }

    if any(record["status"] != "VALID" for record in records):
        return {
            "status": "UNDEFINED",
            "mean": None,
            "reason": "one or more case ratios invalid or undefined",
        }

    if not records:
        return {
            "status": "INSTRUMENT_FAILED",
            "mean": None,
            "reason": "empty report",
        }

    for record in records:
        value = record.get("improvement")
        if type(value) is not float or not math.isfinite(value):
            return {
                "status": "INSTRUMENT_FAILED",
                "mean": None,
                "reason": "invalid improvement in VALID record",
            }

    try:
        mean = math.fsum(
            record["improvement"] for record in records
        ) / len(records)
    except (OverflowError, ValueError, ArithmeticError):
        return {
            "status": "INVALID_NUMERIC",
            "mean": None,
            "reason": "finite-set mean arithmetic failure",
        }

    if not math.isfinite(mean):
        return {
            "status": "INVALID_NUMERIC",
            "mean": None,
            "reason": "non-finite finite-set mean",
        }

    return {
        "status": "VALID",
        "mean": mean,
        "reason": None,
    }


# Proposed descriptive schema — constructed fixtures only.
REQUIRED_ARMS = frozenset({
    "covariance", "magnitude", "sensitivity",
    "random", "uncorrected", "smallest",
})


def validate_six_arms(arms):
    """Fail closed on missing arms or invalid measurements."""
    if not isinstance(arms, dict) or set(arms) != REQUIRED_ARMS:
        return "INSTRUMENT_FAILED"

    for name, arm in arms.items():
        if not isinstance(arm, dict):
            return "INSTRUMENT_FAILED"

        required = {"calibration_mse", "evaluation_mse",
                    "serialized_bytes", "decode_ok"}

        if not required.issubset(arm):
            return "INSTRUMENT_FAILED"

        for field in ("calibration_mse", "evaluation_mse"):
            value = arm[field]
            if (type(value) is not float
                    or not math.isfinite(value)
                    or value < 0):
                return "INVALID_NUMERIC"

        if type(arm["serialized_bytes"]) is not int:
            return "INSTRUMENT_FAILED"

        if arm["serialized_bytes"] < 0:
            return "INSTRUMENT_FAILED"

        if arm["decode_ok"] is not True:
            return "INSTRUMENT_FAILED"

    return "VALID"


def validate_paired_mse(record):
    """Check reported MSE pair against six-arm evaluation measurements.

    Constructed instrumentation only; not a study-result verdict.
    """
    arms = record.get("arms")
    if validate_six_arms(arms) != "VALID":
        return "INSTRUMENT_FAILED"

    for reported, arm_name in (
        ("covariance_mse", "covariance"),
        ("magnitude_mse", "magnitude"),
    ):
        value = record.get(reported)
        actual = arms[arm_name]["evaluation_mse"]

        if type(value) is not float or not math.isfinite(value):
            return "INVALID_NUMERIC"

        # Both measurements must originate from the same decoded MSE.
        # Exact equality is intentional: independent rounded summaries
        # must not replace the canonical source measurement.
        if value != actual:
            return "INSTRUMENT_FAILED"

    try:
        expected = relative_improvement(
            arms["covariance"]["evaluation_mse"],
            arms["magnitude"]["evaluation_mse"],
        )
    except DescriptiveScoringError as exc:
        reason = str(exc)

        if "UNDEFINED" in reason:
            if (
                record.get("status") == "UNDEFINED_RATIO"
                and record.get("improvement") is None
            ):
                return "VALID"
            return "INSTRUMENT_FAILED"

        return "INVALID_NUMERIC"

    reported = record.get("improvement")
    if type(reported) is not float or not math.isfinite(reported):
        return "INSTRUMENT_FAILED"

    if reported != expected:
        return "INSTRUMENT_FAILED"

    return "VALID"


def build_failure_manifest(
    records, expected_case_ids=None, *, expected_seeds=None
):
    """Preserve per-case failures, including explicitly missing IDs.

    Constructed instrumentation only; schema not frozen.
    """
    manifest = []

    if expected_case_ids is not None:
        expected = list(expected_case_ids)
        observed = [record.get("case_id") for record in records]

        if len(expected) != len(set(expected)):
            raise ValueError("duplicate expected case IDs")

        for case_id in expected:
            if case_id not in observed:
                manifest.append({
                    "case_id": case_id,
                    "seed": None,
                    "status": "MISSING_CASE",
                    "reason": "expected case record absent",
                    "arm_status": "INSTRUMENT_FAILED",
                })

    for record in records:
        case_id = record.get("case_id")
        seed = record.get("seed")
        status = record.get("status")
        reason = record.get("reason")

        arm_status = validate_six_arms(record.get("arms"))
        if arm_status == "VALID":
            arm_status = validate_paired_mse(record)

        manifest.append({
            "case_id": case_id,
            "seed": seed,
            "status": status,
            "reason": reason,
            "arm_status": arm_status,
        })

    if expected_seeds is not None:
        if not isinstance(expected_seeds, dict):
            raise ValueError("expected_seeds must be a mapping")

        for item in manifest:
            case_id = item["case_id"]
            if type(case_id) is int and item["status"] == "VALID":
                if case_id not in expected_seeds:
                    item["status"] = "SEED_MAPPING_MISSING"
                    item["reason"] = "expected case seed absent from mapping"
                    item["arm_status"] = "INSTRUMENT_FAILED"
                else:
                    expected_seed = expected_seeds[case_id]
                    if (
                        type(expected_seed) is not int
                        or type(item["seed"]) is not int
                        or item["seed"] != expected_seed
                    ):
                        item["status"] = "SEED_MISMATCH"
                        item["reason"] = "case seed does not match registration"
                        item["arm_status"] = "INSTRUMENT_FAILED"

    if expected_case_ids is not None:
        expected = list(expected_case_ids)
        expected_set = set(expected)
        seen = set()

        for item in manifest:
            case_id = item["case_id"]

            if type(case_id) is not int or case_id < 0:
                item["status"] = "INVALID_CASE_ID"
                item["arm_status"] = "INSTRUMENT_FAILED"
                item["reason"] = "malformed case ID"
                continue

            if case_id not in expected_set:
                item["status"] = "UNEXPECTED_CASE"
                item["arm_status"] = "INSTRUMENT_FAILED"
                item["reason"] = "case ID outside expected set"
                continue

            if case_id in seen:
                item["status"] = "DUPLICATE_CASE"
                item["arm_status"] = "INSTRUMENT_FAILED"
                item["reason"] = "duplicate case ID"
                continue

            seen.add(case_id)

        # Valid expected IDs first; invalid/unexpected IDs retained.
        manifest.sort(
            key=lambda item: (
                type(item["case_id"]) is not int
                or item["case_id"] not in expected_set,
                item["case_id"]
                if type(item["case_id"]) is int else -1,
            )
        )

    return manifest
