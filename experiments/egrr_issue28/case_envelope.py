"""Draft EGRR case-envelope controls.

Constructed fixtures only. No study execution or seed generation.
"""

from copy import deepcopy

SCHEMA_VERSION = "EGRR-DESC-001-DRAFT-1"

FAILURE_PRECEDENCE = {
    "VALID": 0,
    "UNDEFINED_RATIO": 1,
    "INVALID_NUMERIC": 2,
    "SERIALIZATION_ERROR": 3,
    "INSTRUMENT_FAILED": 4,
}

REQUIRED_ERROR_FIELDS = frozenset({
    "stage", "arm", "code", "status"
})


def summarize_errors(errors):
    """Retain every error and derive its overall status.

    Precedence applies to the summary only. It never deletes,
    overwrites, or reorders causal errors.
    """
    if type(errors) is not list:
        raise ValueError("errors must be a list")

    retained = deepcopy(errors)
    overall = "VALID"

    for index, error in enumerate(retained):
        if not isinstance(error, dict):
            raise ValueError(f"error {index}: invalid structure")

        if not REQUIRED_ERROR_FIELDS.issubset(error):
            raise ValueError(f"error {index}: missing required fields")

        status = error["status"]

        if (
            type(status) is not str
            or status not in FAILURE_PRECEDENCE
            or status == "VALID"
        ):
            raise ValueError(f"error {index}: invalid failure status")

        if (
            type(error["stage"]) is not str
            or not error["stage"]
            or type(error["code"]) is not str
            or not error["code"]
            or (
                error["arm"] is not None
                and (
                    type(error["arm"]) is not str
                    or not error["arm"]
                )
            )
        ):
            raise ValueError(f"error {index}: invalid error fields")

        if FAILURE_PRECEDENCE[status] > FAILURE_PRECEDENCE[overall]:
            overall = status

    return {
        "schema_version": SCHEMA_VERSION,
        "case_status": overall,
        "errors": retained,
    }


def validate_case_identity(identity):
    """Validate one draft case identity without generating study data.

    This checks structure only. It does not establish that any
    supplied hashes or provenance statements are truthful.
    """
    required = {
        "study_id",
        "case_id",
        "seed",
        "generator",
        "draw_order",
        "source_commit",
        "environment",
        "input_hashes",
    }

    if type(identity) is not dict or set(identity) != required:
        raise ValueError("invalid case identity fields")

    case_id = identity["case_id"]
    if (
        type(case_id) is not str
        or len(case_id) != 3
        or not case_id.isascii()
        or not case_id.isdecimal()
        or not ("000" <= case_id <= "099")
    ):
        raise ValueError("case ID must be 000 through 099")

    if type(identity["seed"]) is not int or identity["seed"] < 0:
        raise ValueError("invalid seed identity")

    for field in ("study_id", "generator", "draw_order"):
        value = identity[field]
        if type(value) is not str or not value.strip():
            raise ValueError(f"invalid {field}")

    commit = identity["source_commit"]
    if (
        type(commit) is not str
        or len(commit) != 40
        or any(c not in "0123456789abcdef" for c in commit)
    ):
        raise ValueError("invalid source commit")

    environment = identity["environment"]
    if (
        type(environment) is not dict
        or not environment
        or any(
            type(k) is not str or not k
            or type(v) is not str or not v
            for k, v in environment.items()
        )
    ):
        raise ValueError("invalid environment identity")

    hashes = identity["input_hashes"]
    if type(hashes) is not dict or not hashes:
        raise ValueError("missing input hashes")

    for name, digest in hashes.items():
        if (
            type(name) is not str
            or not name
            or type(digest) is not str
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ValueError("invalid input hash")

    return True


def validate_arm_evidence(arm, payload=None):
    """Validate one constructed arm's metadata and optional payload.

    A payload is mandatory for claims of successful serialization.
    This does not independently verify reconstruction quality.
    """
    import hashlib
    import math

    required = {
        "status", "error_code", "serialized_bytes",
        "payload_sha256", "decode_ok", "correction_count",
        "correction_indices", "calibration_mse", "evaluation_mse",
    }

    if type(arm) is not dict or not required.issubset(arm):
        raise ValueError("incomplete arm evidence")

    if arm["status"] != "VALID" or arm["error_code"] is not None:
        raise ValueError("arm is not valid")

    if arm["decode_ok"] is not True:
        raise ValueError("decode integrity not confirmed")

    if type(payload) is not bytes:
        raise ValueError("serialized payload required")

    if (
        type(arm["serialized_bytes"]) is not int
        or arm["serialized_bytes"] != len(payload)
    ):
        raise ValueError("serialized byte count mismatch")

    digest = hashlib.sha256(payload).hexdigest()
    if arm["payload_sha256"] != digest:
        raise ValueError("serialized payload SHA-256 mismatch")

    count = arm["correction_count"]
    indices = arm["correction_indices"]

    if (
        type(count) is not int
        or count < 0
        or type(indices) is not list
        or len(indices) != count
        or any(type(index) is not int or index < 0 for index in indices)
        or len(set(indices)) != count
    ):
        raise ValueError("invalid correction count or indices")

    for field in ("calibration_mse", "evaluation_mse"):
        value = arm[field]
        if (
            type(value) is not float
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(f"invalid {field}")

    return True


REQUIRED_ARM_NAMES = frozenset({
    "covariance",
    "magnitude",
    "input_rms",
    "random",
    "uncorrected",
    "smallest_residual",
})


def validate_six_arm_evidence(arms, payloads, *, corrected_k=128):
    """Validate six constructed arm records and their supplied bytes.

    This is a metadata/integrity gate, not an actual decoder audit.
    """
    if (
        type(arms) is not dict
        or type(payloads) is not dict
        or set(arms) != REQUIRED_ARM_NAMES
        or set(payloads) != REQUIRED_ARM_NAMES
    ):
        raise ValueError("missing or unexpected arm/payload")

    if type(corrected_k) is not int or corrected_k <= 0:
        raise ValueError("invalid corrected K")

    for name in sorted(REQUIRED_ARM_NAMES):
        arm = arms[name]
        validate_arm_evidence(arm, payloads[name])

        count = arm["correction_count"]
        if name == "uncorrected":
            if count != 0 or arm["correction_indices"] != []:
                raise ValueError("uncorrected arm must have zero corrections")
        elif count != corrected_k:
            raise ValueError(
                f"{name}: correction count differs from fixed K"
            )

    return True


def build_paired_comparison(covariance_mse, magnitude_mse):
    """Construct a paired comparison from validated decoded MSEs.

    Constructed instrumentation only; no study execution.
    """
    import math
    from descriptive_scoring import (
        relative_improvement,
        DescriptiveScoringError,
    )

    pair = {
        "candidate": "covariance",
        "baseline": "magnitude",
        "status": "VALID",
        "r": None,
        "small_positive_denominator": False,
        "error_code": None,
    }

    for name, value in (
        ("covariance", covariance_mse),
        ("magnitude", magnitude_mse),
    ):
        if (
            type(value) is not float
            or not math.isfinite(value)
            or value < 0
        ):
            pair["status"] = "INVALID_NUMERIC"
            pair["error_code"] = f"INVALID_{name.upper()}_MSE"
            return pair

    if magnitude_mse == 0.0:
        pair["status"] = "UNDEFINED_RATIO"
        pair["error_code"] = "ZERO_DENOMINATOR"
        return pair

    pair["small_positive_denominator"] = (
        0.0 < magnitude_mse <= 1e-12
    )

    try:
        value = relative_improvement(
            covariance_mse, magnitude_mse
        )
    except (DescriptiveScoringError, ArithmeticError):
        pair["status"] = "UNDEFINED_RATIO"
        pair["error_code"] = "RATIO_NONFINITE"
        return pair

    if type(value) is not float or not math.isfinite(value):
        pair["status"] = "UNDEFINED_RATIO"
        pair["error_code"] = "RATIO_NONFINITE"
        return pair

    pair["r"] = value
    return pair


def build_case_envelope(identity, arms, payloads, *, expected_seed):
    """Build a detached draft envelope from constructed evidence.

    Validation errors are retained independently. This is not a
    study runner, frozen schema, or independent decoder verifier.
    """
    from copy import deepcopy

    if type(expected_seed) is not int or expected_seed < 0:
        raise ValueError("invalid expected seed")

    frozen_identity = deepcopy(identity)
    frozen_arms = deepcopy(arms)
    frozen_payloads = deepcopy(payloads)

    errors = []

    try:
        validate_case_identity(frozen_identity)
    except (ValueError, TypeError, KeyError) as exc:
        errors.append({
            "stage": "identity",
            "arm": None,
            "code": "INVALID_CASE_IDENTITY",
            "status": "INSTRUMENT_FAILED",
            "detail": str(exc),
        })

    if (
        type(frozen_identity) is dict
        and frozen_identity.get("seed") != expected_seed
    ):
        errors.append({
            "stage": "identity",
            "arm": None,
            "code": "SEED_MISMATCH",
            "status": "INSTRUMENT_FAILED",
        })

    arm_integrity_valid = True

    if type(frozen_arms) is not dict or type(frozen_payloads) is not dict:
        errors.append({
            "stage": "arms",
            "arm": None,
            "code": "INVALID_ARM_CONTAINER",
            "status": "INSTRUMENT_FAILED",
        })
        arm_integrity_valid = False
    else:
        missing = REQUIRED_ARM_NAMES - set(frozen_arms)
        extra = set(frozen_arms) - REQUIRED_ARM_NAMES
        missing_payloads = REQUIRED_ARM_NAMES - set(frozen_payloads)
        extra_payloads = set(frozen_payloads) - REQUIRED_ARM_NAMES

        for name in sorted(missing | missing_payloads):
            errors.append({
                "stage": "arms",
                "arm": name,
                "code": "MISSING_ARM_OR_PAYLOAD",
                "status": "INSTRUMENT_FAILED",
            })
            arm_integrity_valid = False

        for name in sorted(extra | extra_payloads):
            errors.append({
                "stage": "arms",
                "arm": name,
                "code": "UNEXPECTED_ARM_OR_PAYLOAD",
                "status": "INSTRUMENT_FAILED",
            })
            arm_integrity_valid = False

        import hashlib
        import math

        for name in sorted(
            REQUIRED_ARM_NAMES & set(frozen_arms) & set(frozen_payloads)
        ):
            arm = frozen_arms[name]
            payload = frozen_payloads[name]

            def add_error(code, status, detail):
                nonlocal_errors.append({
                    "stage": "arms",
                    "arm": name,
                    "code": code,
                    "status": status,
                    "detail": detail,
                })

            nonlocal_errors = errors
            before = len(errors)

            if type(arm) is not dict:
                add_error("ARM_METADATA_FAILED", "INSTRUMENT_FAILED",
                          "arm must be an object")
            else:
                required = {
                    "status", "error_code", "serialized_bytes",
                    "payload_sha256", "decode_ok",
                    "correction_count", "correction_indices",
                    "calibration_mse", "evaluation_mse",
                }

                for field in sorted(required - set(arm)):
                    add_error("MISSING_ARM_FIELD", "INSTRUMENT_FAILED", field)

                for field in ("calibration_mse", "evaluation_mse"):
                    if field in arm:
                        value = arm[field]
                        if (
                            type(value) is not float
                            or not math.isfinite(value)
                            or value < 0
                        ):
                            add_error("INVALID_MSE", "INVALID_NUMERIC", field)

                if arm.get("status") != "VALID":
                    add_error("ARM_STATUS_INVALID", "INSTRUMENT_FAILED",
                              "arm not marked VALID")

                if arm.get("error_code") is not None:
                    add_error("ARM_ERROR_CODE_PRESENT", "INSTRUMENT_FAILED",
                              "arm reports an existing error")

                if arm.get("decode_ok") is not True:
                    add_error("DECODE_FAILURE", "SERIALIZATION_ERROR",
                              "decode success not established")

                if type(payload) is not bytes:
                    add_error("PAYLOAD_MISSING", "SERIALIZATION_ERROR",
                              "payload must be bytes")
                else:
                    size = arm.get("serialized_bytes")
                    if type(size) is not int:
                        add_error("INVALID_BYTE_COUNT", "INSTRUMENT_FAILED",
                                  "serialized byte count type")
                    elif size != len(payload):
                        add_error(
                            "SERIALIZED_BYTE_COUNT_MISMATCH",
                            "SERIALIZATION_ERROR",
                            "payload size differs from record",
                        )

                    digest = arm.get("payload_sha256")
                    if type(digest) is not str or len(digest) != 64:
                        add_error("INVALID_PAYLOAD_DIGEST", "INSTRUMENT_FAILED",
                                  "digest missing or malformed")
                    elif digest != hashlib.sha256(payload).hexdigest():
                        add_error("PAYLOAD_HASH_MISMATCH",
                                  "SERIALIZATION_ERROR",
                                  "payload digest differs")

                count = arm.get("correction_count")
                indices = arm.get("correction_indices")
                if (
                    type(count) is not int
                    or count < 0
                    or type(indices) is not list
                    or any(type(i) is not int or i < 0 for i in indices)
                    or len(indices) != len(set(indices))
                    or len(indices) != count
                ):
                    add_error("INVALID_CORRECTION_METADATA",
                              "INSTRUMENT_FAILED",
                              "count or indices invalid")
                elif name == "uncorrected":
                    if count != 0:
                        add_error("UNCORRECTED_HAS_CORRECTIONS",
                                  "INSTRUMENT_FAILED",
                                  "uncorrected count must be zero")
                elif count != 128:
                    add_error("FIXED_K_MISMATCH", "INSTRUMENT_FAILED",
                              "corrected count must equal 128")

            if len(errors) != before:
                arm_integrity_valid = False

    if arm_integrity_valid:
        pair = build_paired_comparison(
            frozen_arms["covariance"]["evaluation_mse"],
            frozen_arms["magnitude"]["evaluation_mse"],
        )

        if pair["status"] != "VALID":
            errors.append({
                "stage": "pair",
                "arm": None,
                "code": pair["error_code"],
                "status": pair["status"],
            })
    else:
        pair = {
            "candidate": "covariance",
            "baseline": "magnitude",
            "status": "INSTRUMENT_FAILED",
            "r": None,
            "small_positive_denominator": False,
            "error_code": "UPSTREAM_ARM_INTEGRITY_FAILED",
        }

    summary = summarize_errors(errors)

    return {
        "schema_version": SCHEMA_VERSION,
        "identity": frozen_identity,
        "arms": frozen_arms,
        "pair": pair,
        "case_status": summary["case_status"],
        "errors": summary["errors"],
    }


def aggregate_full_set(records, *, expected_case_ids, expected_seeds):
    """Aggregate constructed case summaries; never average survivors.

    Draft reporting layer only. Full six-arm/integrity verification
    must be enforced separately before authoritative use.
    """
    from copy import deepcopy
    import math

    expected = list(expected_case_ids)

    if (
        len(expected) != 100
        or expected != [f"{i:03d}" for i in range(100)]
        or type(expected_seeds) is not dict
        or set(expected_seeds) != set(expected)
        or any(
            type(expected_seeds[k]) is not int
            or expected_seeds[k] < 0
            for k in expected
        )
    ):
        raise ValueError("invalid fixed 100-case registration")

    if type(records) is not list:
        raise ValueError("records must be a list")

    cases = deepcopy(records)
    failures = []
    seen = set()
    observed = set()
    invalid_ratios = False

    def failure(case_id, code, status, stage="aggregate", arm=None):
        failures.append({
            "case_id": case_id,
            "stage": stage,
            "arm": arm,
            "code": code,
            "status": status,
        })

    def check_arm_completeness(record, case_id):
        arms = record.get("arms")

        if (
            type(arms) is not dict
            or set(arms) != REQUIRED_ARM_NAMES
            or any(type(arm) is not dict for arm in arms.values())
        ):
            failure(
                case_id,
                "MISSING_SIX_ARM_EVIDENCE",
                "INSTRUMENT_FAILED",
                stage="arms",
            )
            return False

        required_fields = {
            "status",
            "error_code",
            "serialized_bytes",
            "payload_sha256",
            "decode_ok",
            "correction_count",
            "correction_indices",
            "calibration_mse",
            "evaluation_mse",
        }

        if any(
            not required_fields.issubset(arm)
            for arm in arms.values()
        ):
            failure(
                case_id,
                "INCOMPLETE_ARM_EVIDENCE",
                "INSTRUMENT_FAILED",
                stage="arms",
            )
            return False

        import math
        import re

        for name, arm in arms.items():
            count = arm["correction_count"]
            indices = arm["correction_indices"]
            digest = arm["payload_sha256"]

            reported_status = arm["status"]
            reported_code = arm["error_code"]

            recorded_failure = (
                type(reported_status) is str
                and reported_status in (
                    "INVALID_NUMERIC",
                    "SERIALIZATION_ERROR",
                )
                and type(reported_code) is str
                and bool(reported_code)
                and type(record.get("errors")) is list
                and any(
                    type(error) is dict
                    and error.get("arm") == name
                    and error.get("status") == reported_status
                    and error.get("code") == reported_code
                    for error in record["errors"]
                )
            )

            valid = (
                (arm["status"] == "VALID" or recorded_failure)
                and (
                    arm["error_code"] is None
                    or recorded_failure
                )
                and type(arm["decode_ok"]) is bool
                and type(arm["serialized_bytes"]) is int
                and arm["serialized_bytes"] >= 0
                and type(digest) is str
                and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
                and type(count) is int
                and type(indices) is list
                and all(type(i) is int and i >= 0 for i in indices)
                and len(indices) == len(set(indices))
                and len(indices) == count
                and count == (0 if name == "uncorrected" else 128)
                and all(
                    (
                        type(arm[field]) is float
                        and math.isfinite(arm[field])
                        and arm[field] >= 0
                    )
                    or (
                        recorded_failure
                        and reported_status == "INVALID_NUMERIC"
                        and type(arm[field]) is float
                        and not math.isfinite(arm[field])
                    )
                    for field in ("calibration_mse", "evaluation_mse")
                )
            )

            if type(arm["decode_ok"]) is bool and not arm["decode_ok"]:
                failure(
                    case_id,
                    "DECODE_FAILURE",
                    "SERIALIZATION_ERROR",
                    stage="serialization",
                    arm=name,
                )

            if not valid:
                failure(
                    case_id,
                    "INVALID_ARM_EVIDENCE",
                    "INSTRUMENT_FAILED",
                    stage="arms",
                    arm=name,
                )
                return False

        return True

    for record in cases:
        if type(record) is not dict:
            failure(None, "INVALID_CASE_RECORD", "INSTRUMENT_FAILED")
            continue

        identity = record.get("identity")
        case_id = (
            identity.get("case_id")
            if type(identity) is dict else None
        )

        if type(case_id) is not str or case_id not in expected:
            failure(case_id, "UNEXPECTED_CASE", "INSTRUMENT_FAILED")
            continue

        check_arm_completeness(record, case_id)

        if case_id in seen:
            failure(case_id, "DUPLICATE_CASE", "INSTRUMENT_FAILED")
        seen.add(case_id)
        observed.add(case_id)

        seed = identity.get("seed")
        if (
            type(seed) is not int
            or seed != expected_seeds[case_id]
        ):
            failure(case_id, "SEED_MISMATCH", "INSTRUMENT_FAILED")

        errors = record.get("errors")
        if type(errors) is not list:
            failure(case_id, "INVALID_ERROR_LIST", "INSTRUMENT_FAILED")
            continue

        for error in errors:
            if (
                type(error) is not dict
                or not {
                    "stage", "arm", "code", "status"
                }.issubset(error)
                or error["status"] not in FAILURE_PRECEDENCE
                or error["status"] == "VALID"
            ):
                failure(case_id, "INVALID_ERROR_RECORD",
                        "INSTRUMENT_FAILED")
                continue

            failure(
                case_id,
                error["code"],
                error["status"],
                error["stage"],
                error["arm"],
            )

        pair = record.get("pair")
        case_status = record.get("case_status")

        if (
            type(pair) is not dict
            or case_status not in FAILURE_PRECEDENCE
        ):
            failure(case_id, "INVALID_CASE_ENVELOPE",
                    "INSTRUMENT_FAILED")
            continue

        recorded_statuses = [
            error["status"]
            for error in errors
            if (
                type(error) is dict
                and error.get("status") in FAILURE_PRECEDENCE
                and error.get("status") != "VALID"
            )
        ]

        if recorded_statuses:
            highest_status = max(
                recorded_statuses,
                key=lambda status: FAILURE_PRECEDENCE[status],
            )
        else:
            highest_status = "VALID"

        if case_status != highest_status:
            failure(
                case_id,
                "CASE_STATUS_MISMATCH",
                "INSTRUMENT_FAILED",
                stage="case",
            )

        ratio = pair.get("r")

        arms_for_status = record.get("arms")
        if (
            type(arms_for_status) is dict
            and all(
                type(arms_for_status.get(name)) is dict
                for name in ("covariance", "magnitude")
            )
        ):
            cov_status_mse = arms_for_status["covariance"].get("evaluation_mse")
            mag_status_mse = arms_for_status["magnitude"].get("evaluation_mse")

            if (
                type(cov_status_mse) is float
                and type(mag_status_mse) is float
                and math.isfinite(cov_status_mse)
                and math.isfinite(mag_status_mse)
                and cov_status_mse >= 0
                and mag_status_mse >= 0
            ):
                expected_pair = build_paired_comparison(
                    cov_status_mse,
                    mag_status_mse,
                )

                if (
                    pair.get("status") != expected_pair["status"]
                    and (
                        pair.get("status") == "UNDEFINED_RATIO"
                        or not any(
                            type(error) is dict
                            and error.get("stage") == "arms"
                            and error.get("status") != "VALID"
                            for error in errors
                        )
                    )
                ):
                    failure(
                        case_id,
                        "PAIR_STATUS_MISMATCH",
                        "INSTRUMENT_FAILED",
                        stage="pair",
                    )

        if case_status == "VALID" and pair.get("status") == "VALID":
            arms = record.get("arms")

            if (
                type(arms) is dict
                and all(
                    type(arms.get(name)) is dict
                    for name in ("covariance", "magnitude")
                )
            ):
                cov = arms["covariance"].get("evaluation_mse")
                mag = arms["magnitude"].get("evaluation_mse")

                if (
                    type(mag) is float
                    and math.isfinite(mag)
                    and mag == 0.0
                ):
                    failure(
                        case_id,
                        "PAIR_DENOMINATOR_STATUS_MISMATCH",
                        "INSTRUMENT_FAILED",
                        stage="pair",
                    )

                if (
                    type(cov) is float
                    and type(mag) is float
                    and math.isfinite(cov)
                    and math.isfinite(mag)
                    and cov >= 0
                    and mag > 0
                ):
                    authoritative = build_paired_comparison(cov, mag)

                    if authoritative["status"] == "UNDEFINED_RATIO":
                        failure(
                            case_id,
                            authoritative["error_code"],
                            "UNDEFINED_RATIO",
                            stage="pair",
                        )

                    recomputed = authoritative["r"]

                    if (
                        authoritative["status"] != "VALID"
                        or type(ratio) is not float
                        or not math.isfinite(ratio)
                        or (
                            type(recomputed) is float
                            and math.isfinite(recomputed)
                            and not math.isclose(
                                ratio,
                                recomputed,
                                rel_tol=1e-12,
                                abs_tol=1e-15,
                            )
                        )
                    ):
                        failure(
                            case_id,
                            "PAIRED_RATIO_MISMATCH",
                            "INSTRUMENT_FAILED",
                            stage="pair",
                        )

        if (
            case_status != "VALID"
            or pair.get("status") != "VALID"
            or type(ratio) is not float
            or not math.isfinite(ratio)
        ):
            invalid_ratios = True

            if case_status == "VALID" and not errors:
                failure(case_id, "INVALID_PAIR_RATIO",
                        "INSTRUMENT_FAILED")

    for case_id in expected:
        if case_id not in observed:
            failure(case_id, "MISSING_CASE", "INSTRUMENT_FAILED")

    if len(cases) != 100:
        failure(None, "CASE_COUNT_MISMATCH", "INSTRUMENT_FAILED")

    instrument_failed = any(
        error["status"] == "INSTRUMENT_FAILED"
        for error in failures
    )

    if instrument_failed:
        run_status = "INSTRUMENT_FAILED"
    elif failures or invalid_ratios:
        run_status = "UNDEFINED"
    else:
        run_status = "VALID"

    mean = None

    if run_status == "VALID":
        by_id = {
            record["identity"]["case_id"]: record
            for record in cases
        }

        try:
            mean = math.fsum(
                by_id[k]["pair"]["r"] for k in expected
            ) / 100
        except (ValueError, OverflowError, ArithmeticError):
            mean = None

        if mean is None or not math.isfinite(mean):
            failure(None, "MEAN_ARITHMETIC_FAILURE",
                    "INVALID_NUMERIC")
            mean = None
            run_status = "UNDEFINED"

    return {
        "run_status": run_status,
        "full_set_mean": mean,
        "cases": cases,
        "failure_manifest": failures,
    }
