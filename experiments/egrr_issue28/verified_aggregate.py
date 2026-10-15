"""Draft fail-closed payload-verified aggregation entry point.

Constructed fixtures only; not an independent decoder or study runner.
"""

from copy import deepcopy
import hashlib

from case_envelope import (
    REQUIRED_ARM_NAMES,
    SCHEMA_VERSION,
    aggregate_full_set,
    validate_case_identity,
    validate_six_arm_evidence,
)
from canonical_evidence import (
    export_case_envelope,
    verify_evidence_digest,
)


def verified_aggregate(
    records,
    *,
    payloads_by_case,
    evidence_digests_by_case,
    expected_case_ids,
    expected_seeds,
):
    """Verify actual payload bytes and canonical digests before aggregation.

    Verification is exhaustive for a structurally usable registration: one
    failure never suppresses another case's independently observable failure.
    ``decode_ok`` remains a recorded instrument claim, not a repeated decode.
    """
    detached = deepcopy(records) if type(records) is list else []
    failures = []

    def failure(code, case_id=None, *, stage="verification", arm=None,
                status="INSTRUMENT_FAILED"):
        failures.append({
            "case_id": case_id, "stage": stage, "arm": arm,
            "code": code, "status": status,
        })

    expected = list(expected_case_ids) if type(expected_case_ids) is list else []
    registration_valid = (
        expected == [f"{index:03d}" for index in range(100)]
        and type(expected_seeds) is dict
        and set(expected_seeds) == set(expected)
        and all(type(expected_seeds[k]) is int and expected_seeds[k] >= 0
                for k in expected)
    )
    if not registration_valid:
        failure("INVALID_FIXED_REGISTRATION")
    if type(records) is not list:
        failure("INVALID_RECORD_CONTAINER")
    if type(payloads_by_case) is not dict:
        failure("INVALID_PAYLOAD_CONTAINER")
        payloads_by_case = {}
    if type(evidence_digests_by_case) is not dict:
        failure("INVALID_EVIDENCE_DIGEST_CONTAINER")
        evidence_digests_by_case = {}

    expected_set = set(expected)
    for case_id in expected:
        if case_id not in payloads_by_case:
            failure("MISSING_CASE_PAYLOADS", case_id, stage="serialization")
        if case_id not in evidence_digests_by_case:
            failure("MISSING_EVIDENCE_DIGEST", case_id, stage="canonical")
    for case_id in sorted(set(payloads_by_case) - expected_set, key=str):
        failure("UNEXPECTED_CASE_PAYLOADS", case_id, stage="serialization")
    for case_id in sorted(set(evidence_digests_by_case) - expected_set, key=str):
        failure("UNEXPECTED_EVIDENCE_DIGEST", case_id, stage="canonical")

    seen = set()
    for record in detached:
        if type(record) is not dict:
            failure("INVALID_VERIFIED_RECORD")
            continue
        identity = record.get("identity")
        case_id = identity.get("case_id") if type(identity) is dict else None
        if case_id in seen:
            failure("DUPLICATE_CASE", case_id, stage="identity")
        seen.add(case_id)

        try:
            validate_case_identity(identity)
        except (ValueError, TypeError, KeyError):
            failure("INVALID_CASE_IDENTITY", case_id, stage="identity")
        if (
            type(case_id) is not str or case_id not in expected_set
            or case_id not in expected_seeds
            or type(identity) is not dict
            or identity.get("seed") != expected_seeds.get(case_id)
        ):
            failure("VERIFIED_CASE_IDENTITY_MISMATCH", case_id,
                    stage="identity")

        arms = record.get("arms")
        payloads = payloads_by_case.get(case_id)
        if type(arms) is dict and type(payloads) is dict:
            for arm_name in sorted(REQUIRED_ARM_NAMES):
                arm = arms.get(arm_name)
                payload = payloads.get(arm_name)
                if arm_name not in arms or arm_name not in payloads:
                    failure("MISSING_ARM_OR_PAYLOAD", case_id,
                            stage="serialization", arm=arm_name)
                    continue
                if type(payload) is not bytes:
                    failure("PAYLOAD_NOT_BYTES", case_id,
                            stage="serialization", arm=arm_name)
                    continue
                if type(arm) is not dict:
                    failure("INVALID_ARM_EVIDENCE", case_id,
                            stage="arms", arm=arm_name)
                    continue
                if arm.get("serialized_bytes") != len(payload):
                    failure("SERIALIZED_BYTE_COUNT_MISMATCH", case_id,
                            stage="serialization", arm=arm_name,
                            status="SERIALIZATION_ERROR")
                if arm.get("payload_sha256") != hashlib.sha256(payload).hexdigest():
                    failure("PAYLOAD_HASH_MISMATCH", case_id,
                            stage="serialization", arm=arm_name,
                            status="SERIALIZATION_ERROR")
                if arm.get("decode_ok") is not True:
                    failure("DECODE_FAILURE", case_id,
                            stage="serialization", arm=arm_name,
                            status="SERIALIZATION_ERROR")
        else:
            failure("INVALID_SIX_ARM_CONTAINER", case_id, stage="arms")

        try:
            validate_six_arm_evidence(arms, payloads)
        except (ValueError, TypeError, KeyError, OverflowError):
            failure("VERIFIED_SIX_ARM_EVIDENCE_FAILED", case_id, stage="arms")

        if record.get("schema_version") != SCHEMA_VERSION:
            failure("SCHEMA_VERSION_MISMATCH", case_id, stage="canonical")
        try:
            canonical = export_case_envelope(record)
            if not verify_evidence_digest(
                canonical, evidence_digests_by_case.get(case_id)
            ):
                failure("EVIDENCE_DIGEST_MISMATCH", case_id,
                        stage="canonical")
        except (ValueError, TypeError, KeyError, OverflowError):
            failure("MALFORMED_CANONICAL_EVIDENCE", case_id,
                    stage="canonical")

    if seen != expected_set:
        failure("VERIFIED_CASE_SET_MISMATCH", stage="identity")

    aggregate = None
    if registration_valid and type(records) is list:
        aggregate = aggregate_full_set(
            detached, expected_case_ids=expected, expected_seeds=expected_seeds
        )
        failures.extend(aggregate["failure_manifest"])

    if failures:
        order = {case_id: index for index, case_id in enumerate(expected)}
        failures.sort(key=lambda item: (
            order.get(item["case_id"], len(order)), str(item["case_id"]),
            item["stage"], "" if item["arm"] is None else item["arm"],
            item["code"], item["status"],
        ))
        run_status = (
            "INSTRUMENT_FAILED"
            if any(item["status"] == "INSTRUMENT_FAILED" for item in failures)
            else "UNDEFINED"
        )
        return {
            "run_status": run_status, "full_set_mean": None,
            "cases": detached, "failure_manifest": failures,
        }
    return aggregate
