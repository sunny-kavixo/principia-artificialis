"""Draft canonical evidence utilities for constructed EGRR fixtures.

No study execution. No experimental seed generation.
"""

import hashlib
import json
import math
import struct


def float64_hex(value):
    """Encode finite Python float as exact big-endian IEEE-754 binary64."""
    if type(value) is not float or not math.isfinite(value):
        raise ValueError("expected finite float64")
    return struct.pack(">d", value).hex()


def hex_float64(value):
    """Decode exactly 16 hexadecimal characters to a finite float64."""
    if (
        type(value) is not str
        or len(value) != 16
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("invalid canonical float64 hex")

    number = struct.unpack(">d", bytes.fromhex(value))[0]
    if not math.isfinite(number):
        raise ValueError("nonfinite float64 not allowed")
    return number


def canonical_json_bytes(document):
    """Produce stable UTF-8 JSON without NaN, BOM or final newline."""
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    encoded = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    # Enforce strict JSON round-trip and reject nonstandard values.
    decoded = json.loads(
        encoded,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=lambda x: (_ for _ in ()).throw(
            ValueError(f"invalid JSON constant: {x}")
        ),
    )

    if decoded != document:
        raise ValueError("canonical JSON round-trip mismatch")

    return encoded


def evidence_sha256(document):
    """Hash precisely the canonical JSON bytes."""
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def verify_evidence_digest(document, expected_digest):
    """Fail closed on a malformed or mismatching SHA-256 digest."""
    if (
        type(expected_digest) is not str
        or len(expected_digest) != 64
        or any(c not in "0123456789abcdef" for c in expected_digest)
    ):
        raise ValueError("invalid SHA-256 digest")

    return hashlib.sha256(
        canonical_json_bytes(document)
    ).hexdigest() == expected_digest


def _encode_nested_float64(value):
    """Recursively encode finite float64 values without changing other types."""
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("nonfinite nested numerical evidence")
        return float64_hex(value)

    if type(value) is list:
        return [_encode_nested_float64(item) for item in value]

    if type(value) is dict:
        return {
            key: _encode_nested_float64(item)
            for key, item in value.items()
        }

    if type(value) in (str, int, bool, type(None)):
        return value

    raise TypeError("unsupported nested evidence type")


def export_case_envelope(envelope):
    """Convert a constructed draft envelope to canonical JSON-safe evidence.

    Finite float64 values become exact big-endian hexadecimal strings.
    Undefined/nonfinite measurements become null and must retain
    their associated failure evidence.
    """
    from copy import deepcopy

    if type(envelope) is not dict:
        raise ValueError("envelope must be a dictionary")

    required = {
        "schema_version", "identity", "arms",
        "pair", "case_status", "errors",
    }
    if set(envelope) != required:
        raise ValueError("invalid envelope structure")

    from case_envelope import SCHEMA_VERSION
    if envelope["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported case-envelope schema version")

    output = deepcopy(envelope)

    if (
        type(output["arms"]) is not dict
        or type(output["pair"]) is not dict
        or type(output["errors"]) is not list
    ):
        raise ValueError("invalid envelope components")

    required_arms = {
        "covariance",
        "magnitude",
        "input_rms",
        "random",
        "uncorrected",
        "smallest_residual",
    }

    if set(output["arms"]) != required_arms:
        raise ValueError("invalid six-arm evidence set")

    for name, arm in output["arms"].items():
        if type(name) is not str or type(arm) is not dict:
            raise ValueError("invalid arm evidence")

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

        missing_fields = required_fields - set(arm)
        if missing_fields:
            raise ValueError(
                "incomplete arm evidence: "
                + name + ": "
                + ", ".join(sorted(missing_fields))
            )

        import re

        if type(arm["status"]) is not str:
            raise ValueError("invalid arm status type")

        if arm["error_code"] is not None and (
            type(arm["error_code"]) is not str
            or not arm["error_code"]
        ):
            raise ValueError("invalid arm error code")

        if type(arm["decode_ok"]) is not bool:
            raise ValueError("invalid decode_ok evidence")

        allowed_statuses = {
            "VALID",
            "UNDEFINED_RATIO",
            "INVALID_NUMERIC",
            "SERIALIZATION_ERROR",
            "INSTRUMENT_FAILED",
        }

        status = arm["status"]
        error_code = arm["error_code"]
        decode_ok = arm["decode_ok"]

        if status not in allowed_statuses:
            raise ValueError("unknown arm status")

        if status == "VALID":
            if error_code is not None or decode_ok is not True:
                raise ValueError("contradictory arm status evidence")
        elif error_code is None:
            raise ValueError("failed arm requires error code")

        if status != "VALID":
            matching_errors = [
                error
                for error in output["errors"]
                if (
                    type(error) is dict
                    and error.get("arm") == name
                    and error.get("code") == error_code
                    and error.get("status") == status
                )
            ]

            if not matching_errors:
                raise ValueError("failed arm error record mismatch")

        size = arm["serialized_bytes"]
        if type(size) is not int or size < 0:
            raise ValueError("invalid serialized byte count")

        digest = arm["payload_sha256"]
        if (
            type(digest) is not str
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise ValueError("invalid payload SHA-256 evidence")

        count = arm["correction_count"]
        indices = arm["correction_indices"]

        if (
            type(count) is not int
            or count < 0
            or type(indices) is not list
            or any(
                type(index) is not int or index < 0
                for index in indices
            )
            or len(indices) != len(set(indices))
            or len(indices) != count
        ):
            raise ValueError("invalid correction indices evidence")

        if name == "uncorrected":
            if count != 0:
                raise ValueError("uncorrected arm must have zero corrections")
        elif count != 128:
            raise ValueError("corrected arm must have exactly 128 corrections")

        for field in ("calibration_mse", "evaluation_mse"):
            if field not in arm:
                raise ValueError(f"missing {name}.{field}")

            value = arm[field]
            if type(value) is float and math.isfinite(value):
                arm[field] = float64_hex(value)
            elif value is None:
                arm[field] = None
            elif type(value) is float and not math.isfinite(value):
                arm[field] = None
                if not any(
                    type(error) is dict
                    and error.get("arm") == name
                    and error.get("status") == "INVALID_NUMERIC"
                    for error in output["errors"]
                ):
                    raise ValueError(
                        f"nonfinite {name}.{field} lacks error evidence"
                    )
            else:
                raise ValueError(f"invalid {name}.{field}")

    if "r" not in output["pair"]:
        raise ValueError("missing paired ratio")

    ratio = output["pair"]["r"]
    if type(ratio) is float and math.isfinite(ratio):
        output["pair"]["r"] = float64_hex(ratio)
    elif ratio is None:
        output["pair"]["r"] = None
    else:
        raise ValueError("invalid paired ratio")

    output = _encode_nested_float64(output)
    canonical_json_bytes(output)
    return output
