"""Constructed-only tests for Chad's proposed case-envelope contract."""

import unittest


class CaseEnvelopeContractTests(unittest.TestCase):
    def test_failure_precedence_preserves_all_errors(self):
        from case_envelope import summarize_errors

        errors = [
            {"stage": "pair", "arm": None, "code": "ZERO_DENOMINATOR",
             "status": "UNDEFINED_RATIO"},
            {"stage": "identity", "arm": None, "code": "SEED_MISMATCH",
             "status": "INSTRUMENT_FAILED"},
            {"stage": "serialization", "arm": "random",
             "code": "CHECKSUM_MISMATCH",
             "status": "SERIALIZATION_ERROR"},
        ]

        result = summarize_errors(errors)

        self.assertEqual(result["case_status"], "INSTRUMENT_FAILED")
        self.assertEqual(result["errors"], errors)
        self.assertEqual(len(result["errors"]), 3)

    def test_case_identity_contract(self):
        from copy import deepcopy
        from case_envelope import validate_case_identity

        identity = {
            "study_id": "EGRR-DESC-001-DRAFT",
            "case_id": "000",
            "seed": 900,
            "generator": "constructed-fixture",
            "draw_order": "constructed-only",
            "source_commit": "a" * 40,
            "environment": {"python": "constructed-test"},
            "input_hashes": {"input": "b" * 64},
        }

        self.assertTrue(validate_case_identity(identity))

        for field, bad in (
            ("case_id", "00"),
            ("case_id", "100"),
            ("case_id", "０００"),
            ("seed", True),
            ("source_commit", "invalid"),
            ("input_hashes", {"input": "bad"}),
            ("environment", {}),
        ):
            with self.subTest(field=field, bad=bad):
                broken = deepcopy(identity)
                broken[field] = bad
                with self.assertRaises(ValueError):
                    validate_case_identity(broken)

        broken = deepcopy(identity)
        del broken["draw_order"]
        with self.assertRaises(ValueError):
            validate_case_identity(broken)

        broken = deepcopy(identity)
        broken["unexpected"] = "field"
        with self.assertRaises(ValueError):
            validate_case_identity(broken)

    def test_arm_payload_integrity(self):
        from copy import deepcopy
        from hashlib import sha256
        from case_envelope import validate_arm_evidence

        payload = b"constructed-arm-payload"
        arm = {
            "status": "VALID",
            "error_code": None,
            "serialized_bytes": len(payload),
            "payload_sha256": sha256(payload).hexdigest(),
            "decode_ok": True,
            "correction_count": 2,
            "correction_indices": [1, 3],
            "calibration_mse": 0.8,
            "evaluation_mse": 0.9,
        }

        self.assertTrue(validate_arm_evidence(arm, payload))

        with self.assertRaises(ValueError):
            validate_arm_evidence(arm, payload + b"x")

        broken = deepcopy(arm)
        broken["serialized_bytes"] += 1
        with self.assertRaises(ValueError):
            validate_arm_evidence(broken, payload)

        broken = deepcopy(arm)
        broken["correction_indices"] = [1, 1]
        with self.assertRaises(ValueError):
            validate_arm_evidence(broken, payload)

        broken = deepcopy(arm)
        broken["evaluation_mse"] = float("nan")
        with self.assertRaises(ValueError):
            validate_arm_evidence(broken, payload)

        with self.assertRaises(ValueError):
            validate_arm_evidence(arm, None)

    def test_six_arm_integrity_contract(self):
        from copy import deepcopy
        from hashlib import sha256
        from case_envelope import (
            REQUIRED_ARM_NAMES,
            validate_six_arm_evidence,
        )

        arms = {}
        payloads = {}

        for name in sorted(REQUIRED_ARM_NAMES):
            payload = ("constructed:" + name).encode("ascii")
            indices = [] if name == "uncorrected" else list(range(128))

            payloads[name] = payload
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": len(payload),
                "payload_sha256": sha256(payload).hexdigest(),
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        self.assertTrue(validate_six_arm_evidence(arms, payloads))

        missing = deepcopy(arms)
        del missing["random"]
        with self.assertRaises(ValueError):
            validate_six_arm_evidence(missing, payloads)

        corrupted = dict(payloads)
        corrupted["covariance"] += b"x"
        with self.assertRaises(ValueError):
            validate_six_arm_evidence(arms, corrupted)

        incorrect_k = deepcopy(arms)
        incorrect_k["magnitude"]["correction_indices"] = list(range(127))
        incorrect_k["magnitude"]["correction_count"] = 127
        with self.assertRaises(ValueError):
            validate_six_arm_evidence(incorrect_k, payloads)

        invalid_uncorrected = deepcopy(arms)
        invalid_uncorrected["uncorrected"]["correction_indices"] = [0]
        invalid_uncorrected["uncorrected"]["correction_count"] = 1
        with self.assertRaises(ValueError):
            validate_six_arm_evidence(invalid_uncorrected, payloads)

        with self.assertRaises(ValueError):
            validate_six_arm_evidence(arms, payloads, corrected_k=True)

    def test_structured_paired_comparison(self):
        from case_envelope import build_paired_comparison

        for covariance, magnitude, expected in (
            (0.8, 1.0, 0.2),
            (1.0, 1.0, 0.0),
            (1.2, 1.0, -0.2),
        ):
            with self.subTest(covariance=covariance):
                pair = build_paired_comparison(covariance, magnitude)
                self.assertEqual(pair["status"], "VALID")
                self.assertAlmostEqual(pair["r"], expected)
                self.assertIsNone(pair["error_code"])

        tiny = build_paired_comparison(0.0, 1e-12)
        self.assertEqual(tiny["status"], "VALID")
        self.assertEqual(tiny["r"], 1.0)
        self.assertTrue(tiny["small_positive_denominator"])

        zero = build_paired_comparison(0.5, 0.0)
        self.assertEqual(zero["status"], "UNDEFINED_RATIO")
        self.assertEqual(zero["error_code"], "ZERO_DENOMINATOR")
        self.assertIsNone(zero["r"])

        invalid = build_paired_comparison(-1.0, 1.0)
        self.assertEqual(invalid["status"], "INVALID_NUMERIC")
        self.assertIsNone(invalid["r"])

        nonfinite = build_paired_comparison(float("nan"), 1.0)
        self.assertEqual(nonfinite["status"], "INVALID_NUMERIC")

        overflow = build_paired_comparison(1e308, 1e-308)
        self.assertEqual(overflow["status"], "UNDEFINED_RATIO")
        self.assertEqual(overflow["error_code"], "RATIO_NONFINITE")
        self.assertIsNone(overflow["r"])

    def test_complete_envelope_preserves_simultaneous_failures(self):
        from copy import deepcopy
        from hashlib import sha256
        from case_envelope import (
            REQUIRED_ARM_NAMES,
            build_case_envelope,
        )

        identity = {
            "study_id": "EGRR-DESC-001-DRAFT",
            "case_id": "000",
            "seed": 999,
            "generator": "constructed-fixture",
            "draw_order": "constructed-only",
            "source_commit": "a" * 40,
            "environment": {"python": "constructed-test"},
            "input_hashes": {"input": "b" * 64},
        }

        arms = {}
        payloads = {}

        for arm_name in sorted(REQUIRED_ARM_NAMES):
            payload = ("constructed:" + arm_name).encode()
            indices = (
                [] if arm_name == "uncorrected"
                else list(range(128))
            )
            payloads[arm_name] = payload
            arms[arm_name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": len(payload),
                "payload_sha256": sha256(payload).hexdigest(),
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": (
                    0.0 if arm_name == "magnitude" else 0.5
                ),
            }

        envelope = build_case_envelope(
            identity,
            arms,
            payloads,
            expected_seed=900,
        )

        self.assertEqual(envelope["identity"]["case_id"], "000")
        self.assertEqual(set(envelope["arms"]), REQUIRED_ARM_NAMES)
        self.assertEqual(
            envelope["pair"]["status"], "UNDEFINED_RATIO"
        )
        self.assertIsNone(envelope["pair"]["r"])
        self.assertEqual(
            envelope["case_status"], "INSTRUMENT_FAILED"
        )

        codes = [error["code"] for error in envelope["errors"]]
        self.assertIn("SEED_MISMATCH", codes)
        self.assertIn("ZERO_DENOMINATOR", codes)

        original = deepcopy(envelope)
        identity["seed"] = 900
        arms["covariance"]["evaluation_mse"] = 9.0
        payloads["random"] = b"corrupted"

        self.assertEqual(envelope, original)
    def test_multiple_arm_failures_remain_independent(self):
        from hashlib import sha256
        from case_envelope import REQUIRED_ARM_NAMES, build_case_envelope

        identity = {
            "study_id": "EGRR-DESC-001-DRAFT",
            "case_id": "000",
            "seed": 900,
            "generator": "constructed-fixture",
            "draw_order": "constructed-only",
            "source_commit": "a" * 40,
            "environment": {"python": "constructed-test"},
            "input_hashes": {"input": "b" * 64},
        }

        arms, payloads = {}, {}
        for name in sorted(REQUIRED_ARM_NAMES):
            payload = ("constructed:" + name).encode()
            indices = [] if name == "uncorrected" else list(range(128))
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": len(payload),
                "payload_sha256": sha256(payload).hexdigest(),
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }
            payloads[name] = payload

        arms["input_rms"]["evaluation_mse"] = float("nan")
        payloads["random"] += b"corrupted"

        envelope = build_case_envelope(
            identity, arms, payloads, expected_seed=900
        )

        failures = {
            (error["arm"], error["status"])
            for error in envelope["errors"]
        }

        self.assertIn(("input_rms", "INVALID_NUMERIC"), failures)
        self.assertIn(("random", "SERIALIZATION_ERROR"), failures)
        self.assertEqual(
            envelope["case_status"], "SERIALIZATION_ERROR"
        )
        self.assertIsNone(envelope["pair"]["r"])

    def test_distinct_serialization_root_cause_codes(self):
        from copy import deepcopy
        from hashlib import sha256
        from case_envelope import REQUIRED_ARM_NAMES, build_case_envelope

        identity = {
            "study_id": "EGRR-DESC-001-DRAFT",
            "case_id": "000",
            "seed": 900,
            "generator": "constructed-fixture",
            "draw_order": "constructed-only",
            "source_commit": "a" * 40,
            "environment": {"python": "constructed-test"},
            "input_hashes": {"input": "b" * 64},
        }

        arms, payloads = {}, {}
        for name in sorted(REQUIRED_ARM_NAMES):
            payload = ("constructed:" + name).encode()
            indices = [] if name == "uncorrected" else list(range(128))
            payloads[name] = payload
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": len(payload),
                "payload_sha256": sha256(payload).hexdigest(),
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        bad_payloads = dict(payloads)
        original = bad_payloads["random"]
        bad_payloads["random"] = bytes([original[0] ^ 1]) + original[1:]

        bad_arms = deepcopy(arms)
        bad_arms["covariance"]["decode_ok"] = False

        envelope = build_case_envelope(
            identity, bad_arms, bad_payloads, expected_seed=900
        )

        codes = {
            (error["arm"], error["code"])
            for error in envelope["errors"]
        }

        self.assertIn(("random", "PAYLOAD_HASH_MISMATCH"), codes)
        self.assertIn(("covariance", "DECODE_FAILURE"), codes)
        self.assertEqual(
            envelope["case_status"], "SERIALIZATION_ERROR"
        )

    def test_same_arm_preserves_numeric_and_payload_failures(self):
        from hashlib import sha256
        from case_envelope import REQUIRED_ARM_NAMES, build_case_envelope

        identity = {
            "study_id": "EGRR-DESC-001-DRAFT",
            "case_id": "000",
            "seed": 900,
            "generator": "constructed-fixture",
            "draw_order": "constructed-only",
            "source_commit": "a" * 40,
            "environment": {"python": "constructed-test"},
            "input_hashes": {"input": "b" * 64},
        }

        arms, payloads = {}, {}
        for name in sorted(REQUIRED_ARM_NAMES):
            payload = ("constructed:" + name).encode()
            indices = [] if name == "uncorrected" else list(range(128))
            payloads[name] = payload
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": len(payload),
                "payload_sha256": sha256(payload).hexdigest(),
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        arms["random"]["evaluation_mse"] = float("nan")
        original = payloads["random"]
        payloads["random"] = bytes([original[0] ^ 1]) + original[1:]

        envelope = build_case_envelope(
            identity, arms, payloads, expected_seed=900
        )

        errors = {
            (error["arm"], error["code"])
            for error in envelope["errors"]
        }

        self.assertIn(("random", "INVALID_MSE"), errors)
        self.assertIn(("random", "PAYLOAD_HASH_MISMATCH"), errors)
        self.assertEqual(
            envelope["case_status"], "SERIALIZATION_ERROR"
        )
        self.assertIsNone(envelope["pair"]["r"])

    def test_strict_full_set_aggregator_contract(self):
        from copy import deepcopy
        from case_envelope import aggregate_full_set

        expected = [f"{i:03d}" for i in range(100)]


        records = [
            {
                "identity": {"case_id": case_id, "seed": 900 + i},
                "case_status": "VALID",
                "arms": {
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
                            [] if name == "uncorrected"
                            else list(range(128))
                        ),
                        "calibration_mse": 0.8,
                        "evaluation_mse": (
                            0.8 if name == "covariance" else 0.9
                        ),
                    }
                    for name in (
                        "covariance",
                        "magnitude",
                        "input_rms",
                        "random",
                        "uncorrected",
                        "smallest_residual",
                    )
                },
                "pair": {
                    "status": "VALID",
                    "r": (1.0 - 0.8 / 0.9),
                },
                "errors": [],
            }
            for i, case_id in enumerate(expected)
        ]

        seed_map = {
            case_id: 900 + i
            for i, case_id in enumerate(expected)
        }

        valid = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seed_map,
        )

        self.assertEqual(valid["run_status"], "VALID")
        self.assertAlmostEqual(valid["full_set_mean"], 1.0 - 0.8 / 0.9)
        self.assertEqual(len(valid["cases"]), 100)
        self.assertEqual(valid["failure_manifest"], [])

        missing = aggregate_full_set(
            records[:-1],
            expected_case_ids=expected,
            expected_seeds=seed_map,
        )
        self.assertEqual(missing["run_status"], "INSTRUMENT_FAILED")
        self.assertIsNone(missing["full_set_mean"])
        self.assertTrue(
            any(e["code"] == "MISSING_CASE"
                for e in missing["failure_manifest"])
        )

        failed_records = deepcopy(records)
        failed_records[40]["arms"]["magnitude"]["evaluation_mse"] = 0.0
        failed_records[40]["case_status"] = "UNDEFINED_RATIO"
        failed_records[40]["pair"] = {
            "status": "UNDEFINED_RATIO",
            "r": None,
            "error_code": "ZERO_DENOMINATOR",
        }
        failed_records[40]["errors"] = [{
            "stage": "pair",
            "arm": None,
            "code": "ZERO_DENOMINATOR",
            "status": "UNDEFINED_RATIO",
        }]

        failed = aggregate_full_set(
            failed_records,
            expected_case_ids=expected,
            expected_seeds=seed_map,
        )
        self.assertEqual(failed["run_status"], "UNDEFINED")
        self.assertIsNone(failed["full_set_mean"])
        self.assertTrue(
            any(
                e["case_id"] == "040"
                and e["code"] == "ZERO_DENOMINATOR"
                for e in failed["failure_manifest"]
            )
        )

        duplicated = aggregate_full_set(
            records + [deepcopy(records[0])],
            expected_case_ids=expected,
            expected_seeds=seed_map,
        )
        self.assertEqual(
            duplicated["run_status"], "INSTRUMENT_FAILED"
        )
        self.assertIsNone(duplicated["full_set_mean"])
        self.assertTrue(
            any(e["code"] == "DUPLICATE_CASE"
                for e in duplicated["failure_manifest"])
        )

    def test_aggregator_rejects_missing_six_arm_evidence(self):
        from case_envelope import aggregate_full_set

        expected = [f"{i:03d}" for i in range(100)]
        seed_map = {
            case_id: 900 + i
            for i, case_id in enumerate(expected)
        }

        records = [
            {
                "identity": {"case_id": case_id, "seed": 900 + i},
                "case_status": "VALID",
                "pair": {"status": "VALID", "r": 0.2},
                "errors": [],
            }
            for i, case_id in enumerate(expected)
        ]

        result = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seed_map,
        )

        self.assertEqual(
            result["run_status"], "INSTRUMENT_FAILED"
        )
        self.assertIsNone(result["full_set_mean"])

        missing_errors = [
            error
            for error in result["failure_manifest"]
            if error["code"] == "MISSING_SIX_ARM_EVIDENCE"
        ]

        self.assertEqual(len(missing_errors), 100)
        self.assertEqual(
            {error["case_id"] for error in missing_errors},
            set(expected),
        )

    def test_aggregator_rejects_incomplete_arm_records(self):
        from case_envelope import aggregate_full_set, REQUIRED_ARM_NAMES

        expected = [f"{i:03d}" for i in range(100)]
        seed_map = {
            case_id: 900 + i
            for i, case_id in enumerate(expected)
        }

        records = [
            {
                "identity": {"case_id": case_id, "seed": 900 + i},
                "arms": {
                    name: {"status": "VALID"}
                    for name in REQUIRED_ARM_NAMES
                },
                "case_status": "VALID",
                "pair": {"status": "VALID", "r": 0.2},
                "errors": [],
            }
            for i, case_id in enumerate(expected)
        ]

        result = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seed_map,
        )

        self.assertEqual(result["run_status"], "INSTRUMENT_FAILED")
        self.assertIsNone(result["full_set_mean"])

        incomplete = [
            error
            for error in result["failure_manifest"]
            if error["code"] == "INCOMPLETE_ARM_EVIDENCE"
        ]

        self.assertEqual(len(incomplete), 100)
        self.assertEqual(
            {error["case_id"] for error in incomplete},
            set(expected),
        )

    def test_aggregator_rejects_invalid_arm_field_values(self):
        from copy import deepcopy
        from case_envelope import aggregate_full_set, REQUIRED_ARM_NAMES

        expected = [f"{i:03d}" for i in range(100)]
        seed_map = {
            case_id: 900 + i
            for i, case_id in enumerate(expected)
        }

        arms = {}
        for name in REQUIRED_ARM_NAMES:
            indices = [] if name == "uncorrected" else list(range(128))
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        records = [
            {
                "identity": {"case_id": case_id, "seed": 900 + i},
                "arms": deepcopy(arms),
                "case_status": "VALID",
                "pair": {"status": "VALID", "r": 0.2},
                "errors": [],
            }
            for i, case_id in enumerate(expected)
        ]

        sabotage = (
            ("decode_ok", "yes"),
            ("payload_sha256", "invalid-hash"),
            ("correction_indices", [0] * 128),
            ("evaluation_mse", float("nan")),
            ("correction_count", True),
        )

        for field, value in sabotage:
            with self.subTest(field=field):
                candidate = deepcopy(records)
                candidate[40]["arms"]["covariance"][field] = value

                result = aggregate_full_set(
                    candidate,
                    expected_case_ids=expected,
                    expected_seeds=seed_map,
                )

                self.assertEqual(
                    result["run_status"], "INSTRUMENT_FAILED"
                )
                self.assertIsNone(result["full_set_mean"])
                self.assertTrue(any(
                    error["case_id"] == "040"
                    and error["code"] == "INVALID_ARM_EVIDENCE"
                    for error in result["failure_manifest"]
                ))

    def test_aggregator_preserves_known_numeric_failure(self):
        from copy import deepcopy
        from case_envelope import aggregate_full_set, REQUIRED_ARM_NAMES

        expected = [f"{i:03d}" for i in range(100)]
        seeds = {case_id: 900 + i for i, case_id in enumerate(expected)}

        arms = {}
        for name in REQUIRED_ARM_NAMES:
            indices = [] if name == "uncorrected" else list(range(128))
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        arms["covariance"]["evaluation_mse"] = 0.8

        records = [
            {
                "identity": {"case_id": case_id, "seed": seeds[case_id]},
                "arms": deepcopy(arms),
                "case_status": "VALID",
                "pair": {"status": "VALID", "r": (1.0 - 0.8 / 0.9)},
                "errors": [],
            }
            for case_id in expected
        ]

        affected = records[40]
        affected["arms"]["random"]["status"] = "INVALID_NUMERIC"
        affected["arms"]["random"]["error_code"] = "INVALID_MSE"
        affected["arms"]["random"]["evaluation_mse"] = float("nan")
        affected["case_status"] = "INVALID_NUMERIC"
        affected["pair"] = {
            "status": "INSTRUMENT_FAILED",
            "r": None,
            "error_code": "UPSTREAM_ARM_INTEGRITY_FAILED",
        }
        affected["errors"] = [{
            "stage": "arms",
            "arm": "random",
            "code": "INVALID_MSE",
            "status": "INVALID_NUMERIC",
        }]

        result = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seeds,
        )

        failures = [
            error for error in result["failure_manifest"]
            if error["case_id"] == "040"
        ]

        self.assertEqual(result["run_status"], "UNDEFINED")
        self.assertIsNone(result["full_set_mean"])
        self.assertTrue(any(
            error["code"] == "INVALID_MSE"
            and error["status"] == "INVALID_NUMERIC"
            for error in failures
        ))
        self.assertFalse(any(
            error["code"] == "INVALID_ARM_EVIDENCE"
            for error in failures
        ))

    def test_aggregator_preserves_numeric_and_decode_failures(self):
        from copy import deepcopy
        from case_envelope import aggregate_full_set, REQUIRED_ARM_NAMES

        expected = [f"{i:03d}" for i in range(100)]
        seeds = {case_id: 900 + i for i, case_id in enumerate(expected)}

        arms = {}
        for name in REQUIRED_ARM_NAMES:
            indices = [] if name == "uncorrected" else list(range(128))
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        arms["covariance"]["evaluation_mse"] = 0.8

        records = [
            {
                "identity": {"case_id": case_id, "seed": seeds[case_id]},
                "arms": deepcopy(arms),
                "case_status": "VALID",
                "pair": {"status": "VALID", "r": (1.0 - 0.8 / 0.9)},
                "errors": [],
            }
            for case_id in expected
        ]

        case = records[40]
        arm = case["arms"]["random"]
        arm["status"] = "INVALID_NUMERIC"
        arm["error_code"] = "INVALID_MSE"
        arm["evaluation_mse"] = float("nan")
        arm["decode_ok"] = False

        case["case_status"] = "INVALID_NUMERIC"
        case["pair"] = {
            "status": "INSTRUMENT_FAILED",
            "r": None,
            "error_code": "UPSTREAM_ARM_INTEGRITY_FAILED",
        }
        case["errors"] = [{
            "stage": "arms",
            "arm": "random",
            "code": "INVALID_MSE",
            "status": "INVALID_NUMERIC",
        }]

        result = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seeds,
        )

        failures = [
            error for error in result["failure_manifest"]
            if error["case_id"] == "040"
        ]
        codes = {error["code"] for error in failures}

        self.assertEqual(result["run_status"], "UNDEFINED")
        self.assertIsNone(result["full_set_mean"])
        self.assertIn("INVALID_MSE", codes)
        self.assertIn("DECODE_FAILURE", codes)
        self.assertNotIn("INVALID_ARM_EVIDENCE", codes)
        self.assertTrue(any(
            error["code"] == "DECODE_FAILURE"
            and error["status"] == "SERIALIZATION_ERROR"
            for error in failures
        ))

    def test_aggregator_rejects_contradictory_case_status(self):
        from copy import deepcopy
        from case_envelope import aggregate_full_set, REQUIRED_ARM_NAMES

        expected = [f"{i:03d}" for i in range(100)]
        seeds = {case_id: 900 + i for i, case_id in enumerate(expected)}

        arms = {}
        for name in REQUIRED_ARM_NAMES:
            indices = [] if name == "uncorrected" else list(range(128))
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        records = [
            {
                "identity": {"case_id": case_id, "seed": seeds[case_id]},
                "arms": deepcopy(arms),
                "case_status": "VALID",
                "pair": {"status": "VALID", "r": 0.2},
                "errors": [],
            }
            for case_id in expected
        ]

        records[40]["errors"] = [{
            "stage": "arms",
            "arm": "random",
            "code": "INVALID_MSE",
            "status": "INVALID_NUMERIC",
        }]

        result = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seeds,
        )

        self.assertEqual(result["run_status"], "INSTRUMENT_FAILED")
        self.assertIsNone(result["full_set_mean"])
        self.assertTrue(any(
            error["case_id"] == "040"
            and error["code"] == "CASE_STATUS_MISMATCH"
            for error in result["failure_manifest"]
        ))

    def test_aggregator_rejects_tampered_paired_ratio(self):
        from copy import deepcopy
        from case_envelope import aggregate_full_set, REQUIRED_ARM_NAMES

        expected = [f"{i:03d}" for i in range(100)]
        seeds = {case_id: 900 + i for i, case_id in enumerate(expected)}

        arms = {}
        for name in REQUIRED_ARM_NAMES:
            indices = [] if name == "uncorrected" else list(range(128))
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        arms["covariance"]["evaluation_mse"] = 0.8
        arms["magnitude"]["evaluation_mse"] = 1.0

        records = [
            {
                "identity": {"case_id": case_id, "seed": seeds[case_id]},
                "arms": deepcopy(arms),
                "case_status": "VALID",
                "pair": {"status": "VALID", "r": 0.2},
                "errors": [],
            }
            for case_id in expected
        ]

        records[40]["pair"]["r"] = 0.7

        result = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seeds,
        )

        self.assertEqual(result["run_status"], "INSTRUMENT_FAILED")
        self.assertIsNone(result["full_set_mean"])

        self.assertTrue(any(
            error["case_id"] == "040"
            and error["code"] == "PAIRED_RATIO_MISMATCH"
            for error in result["failure_manifest"]
        ))

    def test_aggregator_rejects_false_undefined_pair_status(self):
        from copy import deepcopy
        from case_envelope import aggregate_full_set, REQUIRED_ARM_NAMES

        expected = [f"{i:03d}" for i in range(100)]
        seeds = {case_id: 900 + i for i, case_id in enumerate(expected)}

        arms = {}
        for name in REQUIRED_ARM_NAMES:
            indices = [] if name == "uncorrected" else list(range(128))
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        arms["covariance"]["evaluation_mse"] = 0.8
        arms["magnitude"]["evaluation_mse"] = 1.0

        records = [
            {
                "identity": {"case_id": case_id, "seed": seeds[case_id]},
                "arms": deepcopy(arms),
                "case_status": "VALID",
                "pair": {"status": "VALID", "r": 0.2},
                "errors": [],
            }
            for case_id in expected
        ]

        records[40]["case_status"] = "UNDEFINED_RATIO"
        records[40]["pair"] = {
            "status": "UNDEFINED_RATIO",
            "r": None,
            "error_code": "ZERO_DENOMINATOR",
        }
        records[40]["errors"] = [{
            "stage": "pair",
            "arm": None,
            "code": "ZERO_DENOMINATOR",
            "status": "UNDEFINED_RATIO",
        }]

        result = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seeds,
        )

        self.assertEqual(result["run_status"], "INSTRUMENT_FAILED")
        self.assertIsNone(result["full_set_mean"])

        self.assertTrue(any(
            error["case_id"] == "040"
            and error["code"] == "PAIR_STATUS_MISMATCH"
            for error in result["failure_manifest"]
        ))

    def test_pair_status_mismatch_preserved_with_unrelated_arm_failure(self):
        from copy import deepcopy
        from case_envelope import aggregate_full_set, REQUIRED_ARM_NAMES

        expected = [f"{i:03d}" for i in range(100)]
        seeds = {case_id: 900 + i for i, case_id in enumerate(expected)}

        arms = {}
        for name in REQUIRED_ARM_NAMES:
            indices = [] if name == "uncorrected" else list(range(128))
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        arms["covariance"]["evaluation_mse"] = 0.8
        arms["magnitude"]["evaluation_mse"] = 1.0

        records = [
            {
                "identity": {"case_id": case_id, "seed": seeds[case_id]},
                "arms": deepcopy(arms),
                "case_status": "VALID",
                "pair": {"status": "VALID", "r": 0.2},
                "errors": [],
            }
            for case_id in expected
        ]

        records[40]["case_status"] = "UNDEFINED_RATIO"
        records[40]["pair"] = {
            "status": "UNDEFINED_RATIO",
            "r": None,
            "error_code": "ZERO_DENOMINATOR",
        }
        records[40]["errors"] = [{
            "stage": "pair",
            "arm": None,
            "code": "ZERO_DENOMINATOR",
            "status": "UNDEFINED_RATIO",
        }]

        random_arm = records[40]["arms"]["random"]
        random_arm["status"] = "INVALID_NUMERIC"
        random_arm["error_code"] = "INVALID_MSE"
        random_arm["evaluation_mse"] = float("nan")

        records[40]["errors"].append({
            "stage": "arms",
            "arm": "random",
            "code": "INVALID_MSE",
            "status": "INVALID_NUMERIC",
        })
        records[40]["case_status"] = "INVALID_NUMERIC"

        result = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seeds,
        )

        self.assertEqual(result["run_status"], "INSTRUMENT_FAILED")
        self.assertIsNone(result["full_set_mean"])

        self.assertTrue(any(
            error["case_id"] == "040"
            and error["code"] == "PAIR_STATUS_MISMATCH"
            for error in result["failure_manifest"]
        ))

        codes = {
            error["code"]
            for error in result["failure_manifest"]
            if error["case_id"] == "040"
        }
        self.assertIn("INVALID_MSE", codes)
        self.assertIn("ZERO_DENOMINATOR", codes)
        self.assertIn("PAIR_STATUS_MISMATCH", codes)

    def test_aggregator_preserves_ratio_overflow_and_status_mismatch(self):
        from copy import deepcopy
        from case_envelope import aggregate_full_set, REQUIRED_ARM_NAMES

        expected = [f"{i:03d}" for i in range(100)]
        seeds = {case_id: 900 + i for i, case_id in enumerate(expected)}

        arms = {}
        for name in REQUIRED_ARM_NAMES:
            indices = [] if name == "uncorrected" else list(range(128))
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        arms["covariance"]["evaluation_mse"] = 0.8
        arms["magnitude"]["evaluation_mse"] = 1.0

        records = [
            {
                "identity": {"case_id": case_id, "seed": seeds[case_id]},
                "arms": deepcopy(arms),
                "case_status": "VALID",
                "pair": {"status": "VALID", "r": 0.2},
                "errors": [],
            }
            for case_id in expected
        ]

        records[40]["arms"]["covariance"]["evaluation_mse"] = 1e308
        records[40]["arms"]["magnitude"]["evaluation_mse"] = 1e-308

        result = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seeds,
        )

        self.assertEqual(result["run_status"], "INSTRUMENT_FAILED")
        self.assertIsNone(result["full_set_mean"])

        case_errors = [
            error for error in result["failure_manifest"]
            if error["case_id"] == "040"
        ]

        self.assertTrue(any(
            error["code"] == "RATIO_NONFINITE"
            and error["status"] == "UNDEFINED_RATIO"
            for error in case_errors
        ))
        self.assertTrue(any(
            error["status"] == "INSTRUMENT_FAILED"
            and error["code"] in (
                "PAIRED_RATIO_MISMATCH",
                "PAIR_STATUS_MISMATCH",
            )
            for error in case_errors
        ))

    def test_aggregator_rejects_valid_pair_with_zero_denominator(self):
        from copy import deepcopy
        from case_envelope import aggregate_full_set, REQUIRED_ARM_NAMES

        expected = [f"{i:03d}" for i in range(100)]
        seeds = {case_id: 900 + i for i, case_id in enumerate(expected)}

        arms = {}
        for name in REQUIRED_ARM_NAMES:
            indices = [] if name == "uncorrected" else list(range(128))
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": 10,
                "payload_sha256": "a" * 64,
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.9,
            }

        arms["covariance"]["evaluation_mse"] = 0.8

        records = [
            {
                "identity": {"case_id": case_id, "seed": seeds[case_id]},
                "arms": deepcopy(arms),
                "case_status": "VALID",
                "pair": {
                    "status": "VALID",
                    "r": 1.0 - 0.8 / 0.9,
                },
                "errors": [],
            }
            for case_id in expected
        ]

        records[40]["arms"]["magnitude"]["evaluation_mse"] = 0.0

        result = aggregate_full_set(
            records,
            expected_case_ids=expected,
            expected_seeds=seeds,
        )

        self.assertEqual(result["run_status"], "INSTRUMENT_FAILED")
        self.assertIsNone(result["full_set_mean"])
        self.assertTrue(any(
            error["case_id"] == "040"
            and error["code"] == "PAIR_DENOMINATOR_STATUS_MISMATCH"
            for error in result["failure_manifest"]
        ))

    def test_empty_errors_are_valid(self):
        from case_envelope import summarize_errors

        result = summarize_errors([])
        self.assertEqual(result["case_status"], "VALID")
        self.assertEqual(result["errors"], [])

    def test_invalid_error_status_fails_closed(self):
        from case_envelope import summarize_errors

        with self.assertRaises(ValueError):
            summarize_errors([
                {"stage": "pair", "arm": None,
                 "code": "UNKNOWN", "status": "SUCCESS"}
            ])
