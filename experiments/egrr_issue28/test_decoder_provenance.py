"""Constructed tests for the real-decoder evidence boundary."""

from hashlib import sha256
import struct
import unittest
import zlib

import numpy as np

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


class DecoderProvenanceTests(unittest.TestCase):
    def setUp(self):
        weights = np.array(
            [[0.25, -0.75], [1.5, -1.0]], dtype=np.float64
        )
        self.quantized = quantize_symmetric(weights, 3)
        self.indices = np.array([1, 2], dtype=np.int64)
        self.residuals = np.array([0.1, -0.2], dtype=np.float64)
        self.payload = serialize(
            self.quantized, self.indices, self.residuals
        )

    def test_real_egr2_payload_is_accepted(self):
        result = verify_payload_provenance(
            self.payload, evidence_for(self.payload, self.indices)
        )
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["error_code"], None)
        self.assertEqual(result["shape"], [2, 2])

    def test_forged_non_egr2_payload_is_rejected(self):
        data = bytearray(b"NOPE" + bytes(HEADER_SIZE - 4))
        payload = bytes(data) + struct.pack("<I", zlib.crc32(data))
        result = verify_payload_provenance(
            payload, evidence_for(payload, self.indices)
        )
        self.assertEqual(result["status"], "SERIALIZATION_ERROR")
        self.assertEqual(result["error_code"], "EGR2_DECODE_FAILED")
        self.assertEqual(result["detail"], "invalid format")

    def test_crc_corruption_is_rejected_after_metadata_is_refreshed(self):
        payload = bytearray(self.payload)
        payload[HEADER_SIZE] ^= 1
        payload = bytes(payload)
        result = verify_payload_provenance(
            payload, evidence_for(payload, self.indices)
        )
        self.assertEqual(result["status"], "SERIALIZATION_ERROR")
        self.assertEqual(result["error_code"], "EGR2_DECODE_FAILED")
        self.assertEqual(result["detail"], "CRC32 checksum mismatch")


if __name__ == "__main__":
    unittest.main()
