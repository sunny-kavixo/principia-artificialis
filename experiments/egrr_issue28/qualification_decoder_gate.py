"""Constructed real-EGR2 decoder gate and aggregator-boundary diagnostic."""

import argparse
import hashlib
import json
import struct
import zlib

import numpy as np

from egrr import quantize_symmetric, reconstruct
from storage import deserialize, serialize
from verified_aggregate import verified_aggregate


W = np.array([[0.25, -0.75, 1.5, -1.0],
              [0.5, 1.0, -0.25, -1.5]], dtype=np.float64)
INDICES = np.array([1, 6], dtype=np.int64)
CORRECTIONS = np.array([0.1, -0.3333], dtype=np.float64)


def verify_decoder_provenance(payload, metadata):
    """Require actual decoding and decoded/metadata agreement; no flag trust."""
    evidence = {"payload_sha256": hashlib.sha256(payload).hexdigest(),
                "payload_bytes": len(payload),
                "reported_decode_ok": metadata.get("decode_ok")}
    try:
        decoded_q, indices, values = deserialize(payload)
        if metadata.get("payload_sha256") != evidence["payload_sha256"]:
            raise ValueError("PAYLOAD_HASH_MISMATCH")
        if metadata.get("serialized_bytes") != len(payload):
            raise ValueError("SERIALIZED_BYTE_COUNT_MISMATCH")
        if metadata.get("decode_ok") is not True:
            raise ValueError("REPORTED_DECODE_FAILURE")
        if tuple(decoded_q.values.shape) != (2, 4):
            raise ValueError("DECODED_SHAPE_MISMATCH")
        if metadata.get("correction_count") != len(indices):
            raise ValueError("DECODED_COUNT_MISMATCH")
        if metadata.get("correction_indices") != indices.tolist():
            raise ValueError("DECODED_METADATA_INDICES_MISMATCH")
        if not np.array_equal(indices, INDICES):
            raise ValueError("DECODED_INDICES_MISMATCH")
        expected = CORRECTIONS.astype("<f2").astype(np.float64)
        if not np.array_equal(values, expected):
            raise ValueError("DECODED_VALUES_MISMATCH")
        reconstructed = reconstruct(decoded_q, indices, values)
        if not np.all(np.isfinite(reconstructed)):
            raise ValueError("NONFINITE_RECONSTRUCTION")
        evidence.update({"decoded_indices": indices.tolist(),
                         "decoded_values_hex": [float(x).hex() for x in values],
                         "reconstruction_sha256": hashlib.sha256(
                             np.ascontiguousarray(reconstructed).tobytes()
                         ).hexdigest()})
        return {"status": "ACCEPTED", "reason": "EGR2_DECODE_VERIFIED",
                "evidence": evidence}, 0
    except (ValueError, TypeError, OverflowError) as exc:
        return {"status": "REJECTED", "reason": str(exc),
                "evidence": evidence}, 1


def gate(case):
    if case == "aggregate-bypass":
        # Reuses the repository's constructed 100-record stand-ins, never study cases.
        from test_verified_aggregate import constructed_full_set
        records, payloads, digests, expected, seeds = constructed_full_set()
        result = verified_aggregate(
            records, payloads_by_case=payloads,
            evidence_digests_by_case=digests,
            expected_case_ids=expected, expected_seeds=seeds,
        )
        accepted = result["run_status"] == "VALID"
        non_egr2 = all(
            not payload.startswith(b"EGR2")
            for arms in payloads.values() for payload in arms.values()
        )
        observed = accepted and non_egr2
        return ({"case": case,
                 "status": "LIMITATION_CONFIRMED" if observed else "FAIL",
                 "reason": "AGGREGATOR_ACCEPTS_SELF_REPORTED_NON_EGR2"
                 if observed else "AGGREGATOR_BEHAVIOR_CHANGED",
                 "aggregate_status": result["run_status"],
                 "constructed_record_count": len(records),
                 "all_payloads_non_egr2": non_egr2}, 0 if observed else 1)

    q = quantize_symmetric(W, 3)
    payload = serialize(q, INDICES, CORRECTIONS)
    if case == "corrupt":
        corrupted = bytearray(payload)
        corrupted[-5] ^= 1
        payload = bytes(corrupted)
    elif case == "non-egr2":
        payload = b"not an EGR2 payload"
    elif case == "forged":
        invalid = bytearray(payload)
        invalid[:4] = b"NOPE"
        invalid[-4:] = struct.pack("<I", zlib.crc32(invalid[:-4]))
        payload = bytes(invalid)

    metadata = {"decode_ok": True,
                "serialized_bytes": len(payload),
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "correction_count": 2,
                "correction_indices": INDICES.tolist()}
    record, exit_code = verify_decoder_provenance(payload, metadata)
    record["case"] = case
    return record, exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True,
                        choices=("benign", "corrupt", "non-egr2",
                                 "forged", "aggregate-bypass"))
    args = parser.parse_args()
    record, exit_code = gate(args.case)
    print(json.dumps(record, sort_keys=True, separators=(",", ":")))
    raise SystemExit(exit_code)
