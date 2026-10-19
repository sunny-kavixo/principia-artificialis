"""Constructed-only canonical evidence regression tests."""

import hashlib
import math
import struct
import unittest

from canonical_evidence import (
    float64_hex,
    hex_float64,
    canonical_json_bytes,
    evidence_sha256,
    verify_evidence_digest,
)


class CanonicalEvidenceTests(unittest.TestCase):
    def test_float64_exact_roundtrip_and_signed_zero(self):
        values = [0.0, -0.0, 0.2, -1.25, 1e-12]

        for value in values:
            with self.subTest(value=value):
                encoded = float64_hex(value)
                decoded = hex_float64(encoded)

                self.assertEqual(len(encoded), 16)
                self.assertEqual(
                    struct.pack(">d", decoded),
                    struct.pack(">d", value),
                )

        self.assertNotEqual(float64_hex(0.0), float64_hex(-0.0))

    def test_reject_nonfinite_float64(self):
        for value in [float("nan"), float("inf"), -float("inf")]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    float64_hex(value)

        with self.assertRaises(ValueError):
            hex_float64("7ff0000000000000")

    def test_golden_digest_and_roundtrip(self):
        document = {
            "schema_version": "EGRR-DESC-001-DRAFT-1",
            "case_id": "000",
            "evaluation_mse_f64": float64_hex(0.8),
            "signed_zero_f64": float64_hex(-0.0),
            "status": "VALID",
        }

        encoded = canonical_json_bytes(document)

        self.assertEqual(
            encoded,
            (
                b'{"case_id":"000","evaluation_mse_f64":'
                b'"3fe999999999999a","schema_version":'
                b'"EGRR-DESC-001-DRAFT-1","signed_zero_f64":'
                b'"8000000000000000","status":"VALID"}'
            ),
        )

        golden_digest = hashlib.sha256(encoded).hexdigest()
        self.assertEqual(evidence_sha256(document), golden_digest)
        self.assertTrue(verify_evidence_digest(document, golden_digest))

        self.assertFalse(encoded.startswith(b"\\xef\\xbb\\xbf"))
        self.assertFalse(encoded.endswith(b"\\n"))

    def test_one_bit_mutation_is_detected(self):
        original = {
            "case_id": "000",
            "mse_f64": float64_hex(1.0),
        }
        original_digest = evidence_sha256(original)

        mutated = {
            "case_id": "000",
            "mse_f64": "3ff0000000000001",
        }

        self.assertFalse(
            verify_evidence_digest(mutated, original_digest)
        )
        self.assertNotEqual(
            evidence_sha256(mutated),
            original_digest,
        )

    def test_envelope_json_rejects_raw_bytes_and_nonfinite(self):
        """Constructed evidence must not silently enter canonical JSON."""
        from canonical_evidence import canonical_json_bytes

        for document in (
            {"schema_version": "DRAFT", "payload": b"raw-bytes"},
            {"schema_version": "DRAFT", "mse": float("nan")},
            {"schema_version": "DRAFT", "mse": float("inf")},
        ):
            with self.subTest(document=str(document)):
                with self.assertRaises((TypeError, ValueError)):
                    canonical_json_bytes(document)

    def test_constructed_envelope_export(self):
        from copy import deepcopy
        from canonical_evidence import (
            export_case_envelope,
            float64_hex,
            canonical_json_bytes,
            evidence_sha256,
            verify_evidence_digest,
        )

        arms = {}
        for name in (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual"
        ):
            arms[name] = {
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": 0 if name == "uncorrected" else 128,
                "correction_indices": [] if name == "uncorrected" else list(range(128)),
            }

        envelope = {
            "schema_version": "EGRR-DESC-001-DRAFT-1",
            "identity": {"case_id": "000", "seed": 900},
            "arms": arms,
            "pair": {"status": "VALID", "r": -0.0},
            "case_status": "VALID",
            "errors": [],
        }

        original = deepcopy(envelope)
        exported = export_case_envelope(envelope)

        self.assertEqual(envelope, original)
        self.assertEqual(
            exported["arms"]["covariance"]["evaluation_mse"],
            float64_hex(0.9),
        )
        self.assertEqual(
            exported["pair"]["r"],
            "8000000000000000",
        )

        digest = evidence_sha256(exported)
        self.assertTrue(verify_evidence_digest(exported, digest))
        self.assertIsInstance(canonical_json_bytes(exported), bytes)

        failed = deepcopy(envelope)
        failed["arms"]["random"]["evaluation_mse"] = float("nan")
        failed["arms"]["random"]["status"] = "INVALID_NUMERIC"
        failed["arms"]["random"]["error_code"] = "INVALID_MSE"
        failed["case_status"] = "INVALID_NUMERIC"
        failed["errors"] = [{
            "stage": "arms",
            "arm": "random",
            "code": "INVALID_MSE",
            "status": "INVALID_NUMERIC",
        }]
        failed["pair"] = {
            "status": "INSTRUMENT_FAILED",
            "r": None,
            "error_code": "UPSTREAM_ARM_INTEGRITY_FAILED",
        }

        exported_failed = export_case_envelope(failed)
        self.assertIsNone(
            exported_failed["arms"]["random"]["evaluation_mse"]
        )

        missing_evidence = deepcopy(failed)
        missing_evidence["errors"] = []
        with self.assertRaises(ValueError):
            export_case_envelope(missing_evidence)

    def test_nested_float_diagnostics_not_silently_exported(self):
        from canonical_evidence import export_case_envelope

        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        arms = {
            name: {
                "status": "VALID",
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": 0 if name == "uncorrected" else 128,
                "correction_indices": [] if name == "uncorrected" else list(range(128)),
            }
            for name in names
        }

        arms["covariance"]["gain_diagnostics"] = {
            "selected_gains": [0.125, -0.0, -0.25]
        }

        envelope = {
            "schema_version": "EGRR-DESC-001-DRAFT-1",
            "identity": {"case_id": "000", "seed": 900},
            "arms": arms,
            "pair": {"status": "VALID", "r": 0.1},
            "case_status": "VALID",
            "errors": [],
        }

        exported = export_case_envelope(envelope)
        gains = exported["arms"]["covariance"][
            "gain_diagnostics"
        ]["selected_gains"]

        self.assertEqual(
            gains,
            [
                "3fc0000000000000",
                "8000000000000000",
                "bfd0000000000000",
            ],
        )

    def test_nested_evidence_tampering_invalidates_digest(self):
        from copy import deepcopy
        from canonical_evidence import (
            export_case_envelope,
            evidence_sha256,
            verify_evidence_digest,
        )

        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        arms = {
            name: {
                "status": "VALID",
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": 0 if name == "uncorrected" else 128,
                "correction_indices": [] if name == "uncorrected" else list(range(128)),
            }
            for name in names
        }

        arms["covariance"]["gain_diagnostics"] = {
            "selected_gains": [0.125, -0.0, -0.25]
        }

        envelope = {
            "schema_version": "EGRR-DESC-001-DRAFT-1",
            "identity": {"case_id": "000", "seed": 900},
            "arms": arms,
            "pair": {"status": "VALID", "r": 0.1},
            "case_status": "VALID",
            "errors": [],
        }

        exported = export_case_envelope(envelope)
        original_digest = evidence_sha256(exported)

        self.assertTrue(
            verify_evidence_digest(exported, original_digest)
        )

        tampered = deepcopy(exported)
        gains = tampered["arms"]["covariance"][
            "gain_diagnostics"
        ]["selected_gains"]

        gains[0] = "3fc0000000000001"

        self.assertFalse(
            verify_evidence_digest(tampered, original_digest)
        )

        self.assertNotEqual(
            evidence_sha256(tampered), original_digest
        )

    def test_export_rejects_missing_required_arm(self):
        from canonical_evidence import export_case_envelope

        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        arms = {
            name: {
                "status": "VALID",
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }
            for name in names
        }

        envelope = {
            "schema_version": "EGRR-DESC-001-DRAFT-1",
            "identity": {"case_id": "000", "seed": 900},
            "arms": arms,
            "pair": {"status": "VALID", "r": 0.1},
            "case_status": "VALID",
            "errors": [],
        }

        del envelope["arms"]["random"]

        with self.assertRaises(ValueError):
            export_case_envelope(envelope)

    def test_export_rejects_incomplete_arm_evidence(self):
        from copy import deepcopy
        from canonical_evidence import export_case_envelope

        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        arms = {
            name: {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": 128 if name != "uncorrected" else 0,
                "correction_indices": (
                    list(range(128)) if name != "uncorrected" else []
                ),
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }
            for name in names
        }

        envelope = {
            "schema_version": "EGRR-DESC-001-DRAFT-1",
            "identity": {"case_id": "000", "seed": 900},
            "arms": arms,
            "pair": {"status": "VALID", "r": 0.1},
            "case_status": "VALID",
            "errors": [],
        }

        for missing_field in (
            "payload_sha256",
            "serialized_bytes",
            "decode_ok",
            "correction_count",
            "correction_indices",
            "error_code",
        ):
            with self.subTest(field=missing_field):
                incomplete = deepcopy(envelope)
                del incomplete["arms"]["covariance"][missing_field]

                with self.assertRaises(ValueError):
                    export_case_envelope(incomplete)

    def test_export_rejects_invalid_arm_field_values(self):
        from copy import deepcopy
        from canonical_evidence import export_case_envelope

        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        arms = {
            name: {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": (
                    0 if name == "uncorrected" else 128
                ),
                "correction_indices": (
                    [] if name == "uncorrected" else list(range(128))
                ),
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }
            for name in names
        }

        envelope = {
            "schema_version": "EGRR-DESC-001-DRAFT-1",
            "identity": {"case_id": "000", "seed": 900},
            "arms": arms,
            "pair": {"status": "VALID", "r": 0.1},
            "case_status": "VALID",
            "errors": [],
        }

        invalid_cases = (
            ("decode_ok", "yes"),
            ("correction_count", True),
            ("serialized_bytes", "10"),
            ("payload_sha256", "not-a-sha256"),
            ("correction_indices", [0] * 128),
        )

        for field, invalid_value in invalid_cases:
            with self.subTest(field=field):
                candidate = deepcopy(envelope)
                candidate["arms"]["covariance"][field] = invalid_value

                with self.assertRaises((ValueError, TypeError)):
                    export_case_envelope(candidate)

    def test_export_rejects_contradictory_arm_status(self):
        from copy import deepcopy
        from canonical_evidence import export_case_envelope

        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        arms = {
            name: {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": 0 if name == "uncorrected" else 128,
                "correction_indices": (
                    [] if name == "uncorrected" else list(range(128))
                ),
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }
            for name in names
        }

        envelope = {
            "schema_version": "EGRR-DESC-001-DRAFT-1",
            "identity": {"case_id": "000", "seed": 900},
            "arms": arms,
            "pair": {"status": "VALID", "r": 0.1},
            "case_status": "VALID",
            "errors": [],
        }

        cases = (
            ("error_code", "PAYLOAD_HASH_MISMATCH"),
            ("decode_ok", False),
        )

        for field, value in cases:
            with self.subTest(field=field):
                candidate = deepcopy(envelope)
                candidate["arms"]["covariance"][field] = value

                with self.assertRaises(ValueError):
                    export_case_envelope(candidate)

    def test_failed_arm_error_code_requires_matching_error_record(self):
        from copy import deepcopy
        from canonical_evidence import export_case_envelope

        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        arms = {
            name: {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": 0 if name == "uncorrected" else 128,
                "correction_indices": (
                    [] if name == "uncorrected" else list(range(128))
                ),
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }
            for name in names
        }

        arms["random"]["status"] = "INVALID_NUMERIC"
        arms["random"]["error_code"] = "INVALID_MSE"
        arms["random"]["evaluation_mse"] = float("nan")

        envelope = {
            "schema_version": "EGRR-DESC-001-DRAFT-1",
            "identity": {"case_id": "000", "seed": 900},
            "arms": arms,
            "pair": {
                "status": "INSTRUMENT_FAILED",
                "r": None,
                "error_code": "UPSTREAM_ARM_INTEGRITY_FAILED",
            },
            "case_status": "INVALID_NUMERIC",
            "errors": [],
        }

        with self.assertRaises(ValueError):
            export_case_envelope(envelope)

        matching = deepcopy(envelope)
        matching["errors"] = [{
            "stage": "arms",
            "arm": "random",
            "code": "INVALID_MSE",
            "status": "INVALID_NUMERIC",
        }]

        exported = export_case_envelope(matching)
        self.assertIsNone(
            exported["arms"]["random"]["evaluation_mse"]
        )

        mismatched = deepcopy(matching)
        mismatched["errors"][0]["code"] = "UNRELATED_FAILURE"

        with self.assertRaises(ValueError):
            export_case_envelope(mismatched)

    def test_invalid_json_and_digest_rejected(self):
        with self.assertRaises(ValueError):
            canonical_json_bytes({"bad": float("nan")})

        with self.assertRaises(ValueError):
            verify_evidence_digest({"ok": True}, "wrong")

        with self.assertRaises(ValueError):
            hex_float64("NOT_HEX")
