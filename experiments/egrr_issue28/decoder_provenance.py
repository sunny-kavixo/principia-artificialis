"""Constructed-only EGR2 decoder provenance checks.

This module is a pre-aggregation qualification boundary. It uses the
repository's real EGR2 decoder and does not generate or execute study cases.
"""

from __future__ import annotations

from hashlib import sha256

from storage import deserialize


DECODE_FAILURE = "EGR2_DECODE_FAILED"


def verify_payload_provenance(payload, evidence):
    """Validate bytes, metadata and a real EGR2 decode before aggregation.

    A caller-provided ``decode_ok`` flag is never accepted as decoder
    provenance by itself. The returned record is deliberately structured so a
    future study entrypoint can veto aggregation on any failure.
    """
    if type(payload) is not bytes:
        return {
            "status": "SERIALIZATION_ERROR",
            "error_code": DECODE_FAILURE,
            "detail": "payload is not bytes",
            "decode_ok": False,
        }

    if type(evidence) is not dict:
        return {
            "status": "INSTRUMENT_FAILED",
            "error_code": "INVALID_PAYLOAD_EVIDENCE",
            "detail": "payload evidence is not a mapping",
            "decode_ok": False,
        }

    if evidence.get("serialized_bytes") != len(payload):
        return {
            "status": "SERIALIZATION_ERROR",
            "error_code": "PAYLOAD_BYTE_COUNT_MISMATCH",
            "detail": "reported byte count does not match payload",
            "decode_ok": False,
        }

    if evidence.get("payload_sha256") != sha256(payload).hexdigest():
        return {
            "status": "SERIALIZATION_ERROR",
            "error_code": "PAYLOAD_HASH_MISMATCH",
            "detail": "reported payload SHA-256 does not match payload",
            "decode_ok": False,
        }

    if evidence.get("decode_ok") is not True:
        return {
            "status": "SERIALIZATION_ERROR",
            "error_code": "DECODE_FLAG_FALSE",
            "detail": "decode_ok must not replace a real decoder result",
            "decode_ok": False,
        }

    try:
        decoded_q, decoded_indices, decoded_residuals = deserialize(payload)
    except (ValueError, TypeError, OverflowError) as exc:
        return {
            "status": "SERIALIZATION_ERROR",
            "error_code": DECODE_FAILURE,
            "detail": str(exc),
            "decode_ok": False,
        }

    correction_count = int(len(decoded_indices))
    if evidence.get("correction_count") != correction_count:
        return {
            "status": "SERIALIZATION_ERROR",
            "error_code": "CORRECTION_COUNT_MISMATCH",
            "detail": "decoded correction count does not match evidence",
            "decode_ok": False,
        }

    if evidence.get("correction_indices") != decoded_indices.tolist():
        return {
            "status": "SERIALIZATION_ERROR",
            "error_code": "CORRECTION_INDICES_MISMATCH",
            "detail": "decoded correction indices do not match evidence",
            "decode_ok": False,
        }

    return {
        "status": "VALID",
        "error_code": None,
        "detail": None,
        "decode_ok": True,
        "shape": list(decoded_q.values.shape),
        "correction_count": correction_count,
        "residual_count": int(len(decoded_residuals)),
    }
