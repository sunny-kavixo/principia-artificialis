"""Constructed-only decoder-provenance gate for the aggregation boundary."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys
import zlib

import numpy as np


EGRR_DIR = Path(__file__).resolve().parents[2] / "experiments" / "egrr_issue28"
sys.path.insert(0, str(EGRR_DIR))

from decoder_provenance import verify_payload_provenance
from egrr import quantize_symmetric
from storage import HEADER_SIZE, serialize


def evidence_for(payload, indices):
    return {
        "serialized_bytes": len(payload),
        "payload_sha256": sha256(payload).hexdigest(),
        "decode_ok": True,
        "correction_count": len(indices),
        "correction_indices": list(indices),
    }


def constructed_payload():
    weights = np.array(
        [[0.25, -0.75], [1.5, -1.0]], dtype=np.float64
    )
    quantized = quantize_symmetric(weights, 3)
    indices = np.array([1, 2], dtype=np.int64)
    residuals = np.array([0.1, -0.2], dtype=np.float64)
    return serialize(quantized, indices, residuals), indices


def forged_non_egr2_payload():
    data = bytearray(b"NOPE" + bytes(HEADER_SIZE - 4))
    return bytes(data) + struct.pack("<I", zlib.crc32(data))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sabotage", action="store_true")
    args = parser.parse_args()
    payload, indices = constructed_payload()
    benign = verify_payload_provenance(
        payload, evidence_for(payload, indices)
    )
    if benign["status"] != "VALID":
        print("GATE: FAIL — benign EGR2 payload was rejected")
        return 1

    if not args.sabotage:
        print("GATE: PASS — decoder provenance accepted")
        return 0

    forged_payload = forged_non_egr2_payload()
    corrupted_payload = bytearray(payload)
    corrupted_payload[HEADER_SIZE] ^= 1
    corrupted_payload = bytes(corrupted_payload)
    failures = {
        "non_egr2": verify_payload_provenance(
            forged_payload, evidence_for(forged_payload, indices)
        ),
        "crc_corruption": verify_payload_provenance(
            corrupted_payload, evidence_for(corrupted_payload, indices)
        ),
    }
    expected = {
        "non_egr2": "invalid format",
        "crc_corruption": "CRC32 checksum mismatch",
    }
    if any(
        result.get("status") != "SERIALIZATION_ERROR"
        or result.get("error_code") != "EGR2_DECODE_FAILED"
        or result.get("detail") != expected[name]
        for name, result in failures.items()
    ):
        print("GATE: FAIL — decoder provenance rejection contract mismatch")
        return 1

    print("GATE: FAIL — forged decoder provenance rejected")
    print(json.dumps(failures, sort_keys=True, separators=(",", ":")))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
