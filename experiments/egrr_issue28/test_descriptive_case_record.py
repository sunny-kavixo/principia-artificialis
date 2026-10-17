"""Constructed reporting tests only; no study seeds."""
import unittest

from descriptive_case_record import score_case, complete_report, validate_six_arms


class CaseRecordTests(unittest.TestCase):
    def test_positive_zero_negative_retained(self):
        cases = [
            score_case(0, 900, 0.8, 1.0),
            score_case(1, 901, 1.0, 1.0),
            score_case(2, 902, 1.2, 1.0),
        ]
        self.assertEqual([r["status"] for r in cases], ["VALID"] * 3)
        self.assertGreater(cases[0]["improvement"], 0)
        self.assertEqual(cases[1]["improvement"], 0)
        self.assertLess(cases[2]["improvement"], 0)
        result = complete_report(cases, [0, 1, 2], require_six_arms=False)
        self.assertEqual(result["status"], "VALID")
        self.assertAlmostEqual(result["mean"], 0)

    def test_zero_denominator_undefined(self):
        record = score_case(0, 900, 0.5, 0.0)
        self.assertEqual(record["status"], "UNDEFINED_RATIO")
        self.assertIsNone(record["improvement"])
        result = complete_report([record], [0], require_six_arms=False)
        self.assertEqual(result["status"], "UNDEFINED")
        self.assertIsNone(result["mean"])

    def test_tiny_positive_not_censored(self):
        record = score_case(0, 900, 8e-14, 1e-13)
        self.assertEqual(record["status"], "VALID")
        self.assertTrue(record["tiny_positive_baseline"])
        self.assertAlmostEqual(record["improvement"], 0.2)

    def test_missing_negative_case_fails(self):
        records = [
            score_case(0, 900, 0.8, 1.0),
            score_case(1, 901, 1.0, 1.0),
        ]
        self.assertEqual(
            complete_report(records, [0, 1, 2], require_six_arms=False)["status"],
            "INSTRUMENT_FAILED",
        )

    def test_duplicate_case_fails(self):
        records = [
            score_case(0, 900, 0.8, 1.0),
            score_case(0, 900, 1.2, 1.0),
        ]
        self.assertEqual(
            complete_report(records, [0, 1], require_six_arms=False)["status"],
            "INSTRUMENT_FAILED",
        )

    def test_nonfinite_mse_retained_as_failure(self):
        record = score_case(0, 900, float("nan"), 1.0)
        self.assertEqual(record["status"], "INVALID_NUMERIC")
        self.assertIsNone(record["improvement"])

    def test_ratio_overflow_undefined(self):
        record = score_case(0, 900, 1e308, 1e-300)
        self.assertEqual(record["status"], "UNDEFINED_RATIO")
        self.assertIsNone(record["improvement"])


    def test_invalid_valid_record_improvements(self):
        for bad in (None, float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=repr(bad)):
                record = score_case(0, 900, 0.8, 1.0)
                record["improvement"] = bad

                result = complete_report([record], [0], require_six_arms=False)

                self.assertEqual(result["status"], "INSTRUMENT_FAILED")
                self.assertIsNone(result["mean"])


    def test_six_arm_validation(self):
        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        def fixture():
            return {
                name: {
                    "calibration_mse": 0.5,
                    "evaluation_mse": 0.6,
                    "serialized_bytes": 1311 if name != "uncorrected"
                                        else 1000,
                    "decode_ok": True,
                }
                for name in names
            }

        self.assertEqual(validate_six_arms(fixture()), "VALID")

        missing = fixture()
        del missing["smallest_residual"]
        self.assertEqual(
            validate_six_arms(missing), "INSTRUMENT_FAILED"
        )

        extra = fixture()
        extra["unknown"] = extra["covariance"]
        self.assertEqual(
            validate_six_arms(extra), "INSTRUMENT_FAILED"
        )

        broken = fixture()
        broken["covariance"]["evaluation_mse"] = float("nan")
        self.assertEqual(
            validate_six_arms(broken), "INVALID_NUMERIC"
        )

        negative = fixture()
        negative["magnitude"]["calibration_mse"] = -0.1
        self.assertEqual(
            validate_six_arms(negative), "INVALID_NUMERIC"
        )

        decode = fixture()
        decode["random"]["decode_ok"] = False
        self.assertEqual(
            validate_six_arms(decode), "INSTRUMENT_FAILED"
        )

        bytes_error = fixture()
        bytes_error["smallest_residual"]["serialized_bytes"] = -1
        self.assertEqual(
            validate_six_arms(bytes_error), "INSTRUMENT_FAILED"
        )

        print("PASS: six-arm constructed sabotage fixtures")


    def test_six_arm_report_integration(self):
        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        def arms():
            return {
                name: {
                    "calibration_mse": 0.5,
                    "evaluation_mse": (
                        0.8 if name == "covariance"
                        else 1.0 if name == "magnitude"
                        else 0.6
                    ),
                    "serialized_bytes": 1311,
                    "decode_ok": True,
                }
                for name in names
            }

        good = score_case(0, 900, 0.8, 1.0)
        good["arms"] = arms()

        result = complete_report([good], [0], require_six_arms=True)
        self.assertEqual(result["status"], "VALID")

        missing = score_case(0, 900, 0.8, 1.0)
        result = complete_report([missing], [0], require_six_arms=True)
        self.assertEqual(result["status"], "INSTRUMENT_FAILED")

        broken = score_case(0, 900, 0.8, 1.0)
        broken["arms"] = arms()
        del broken["arms"]["smallest_residual"]
        result = complete_report([broken], [0], require_six_arms=True)
        self.assertEqual(result["status"], "INSTRUMENT_FAILED")

        invalid = score_case(0, 900, 0.8, 1.0)
        invalid["arms"] = arms()
        invalid["arms"]["covariance"]["evaluation_mse"] = float("nan")
        result = complete_report([invalid], [0], require_six_arms=True)
        self.assertEqual(result["status"], "INVALID_NUMERIC")
        self.assertIsNone(result["mean"])


    def test_paired_mse_mismatch_rejected(self):
        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )
        record = score_case(0, 900, 0.8, 1.0)
        record["arms"] = {
            name: {
                "calibration_mse": 0.5,
                "evaluation_mse": (
                    0.9 if name == "covariance"
                    else 1.0 if name == "magnitude"
                    else 0.6
                ),
                "serialized_bytes": 1311,
                "decode_ok": True,
            }
            for name in names
        }

        result = complete_report(
            [record], [0], require_six_arms=True
        )
        self.assertEqual(result["status"], "INSTRUMENT_FAILED")
        self.assertIsNone(result["mean"])


    def test_default_requires_six_arms(self):
        record = score_case(0, 900, 0.8, 1.0)

        # Default must reject incomplete six-arm data.
        result = complete_report([record], [0])
        self.assertEqual(result["status"], "INSTRUMENT_FAILED")
        self.assertIsNone(result["mean"])

        # Explicit opt-out is retained only for scoring-unit fixtures.
        legacy = complete_report(
            [record], [0], require_six_arms=False
        )
        self.assertEqual(legacy["status"], "VALID")


    def test_forged_improvement_rejected(self):
        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        def fixture():
            record = score_case(0, 900, 0.8, 1.0)
            record["arms"] = {
                name: {
                    "calibration_mse": 0.5,
                    "evaluation_mse": (
                        0.8 if name == "covariance"
                        else 1.0 if name == "magnitude"
                        else 0.6
                    ),
                    "serialized_bytes": 1311,
                    "decode_ok": True,
                }
                for name in names
            }
            return record

        self.assertEqual(
            complete_report([fixture()], [0])["status"], "VALID"
        )

        for forged in (0.95, -0.5, float("nan"), None):
            with self.subTest(forged=repr(forged)):
                record = fixture()
                record["improvement"] = forged
                result = complete_report([record], [0])
                self.assertEqual(
                    result["status"], "INSTRUMENT_FAILED"
                )
                self.assertIsNone(result["mean"])


    def test_mixed_failure_precedence(self):
        names = (
            "covariance", "magnitude", "input_rms",
            "random", "uncorrected", "smallest_residual",
        )

        def fixture(case_id, cov, mag):
            record = score_case(case_id, 900 + case_id, cov, mag)
            record["arms"] = {
                name: {
                    "calibration_mse": 0.5,
                    "evaluation_mse": (
                        cov if name == "covariance"
                        else mag if name == "magnitude"
                        else 0.6
                    ),
                    "serialized_bytes": 1311,
                    "decode_ok": True,
                }
                for name in names
            }
            return record

        undefined = fixture(0, 0.5, 0.0)
        broken = fixture(1, 0.8, 1.0)
        broken["arms"]["random"]["decode_ok"] = False

        self.assertEqual(undefined["status"], "UNDEFINED_RATIO")

        for records in (
            [undefined, broken],
            [broken, undefined],
        ):
            with self.subTest(order=[r["case_id"] for r in records]):
                expected_ids = [r["case_id"] for r in records]
                result = complete_report(records, expected_ids)

                self.assertEqual(
                    result["status"], "INSTRUMENT_FAILED"
                )
                self.assertIsNone(result["mean"])


    def test_undefined_ratio_arm_classification(self):
        from descriptive_case_record import (
            validate_paired_mse, build_failure_manifest, REQUIRED_ARMS
        )

        def fixture():
            record = score_case(0, 900, 0.5, 0.0)
            record["arms"] = {
                name: {
                    "calibration_mse": 0.5,
                    "evaluation_mse": (
                        0.5 if name == "covariance"
                        else 0.0 if name == "magnitude"
                        else 0.6
                    ),
                    "serialized_bytes": 1311,
                    "decode_ok": True,
                }
                for name in REQUIRED_ARMS
            }
            return record

        valid = fixture()
        self.assertEqual(valid["status"], "UNDEFINED_RATIO")
        self.assertEqual(validate_paired_mse(valid), "VALID")

        manifest = build_failure_manifest([valid])
        self.assertEqual(manifest[0]["status"], "UNDEFINED_RATIO")
        self.assertEqual(manifest[0]["arm_status"], "VALID")

        forged = fixture()
        forged["status"] = "VALID"
        self.assertEqual(
            validate_paired_mse(forged), "INSTRUMENT_FAILED"
        )

        broken = fixture()
        broken["arms"]["random"]["decode_ok"] = False
        manifest = build_failure_manifest([broken])
        self.assertEqual(
            manifest[0]["arm_status"], "INSTRUMENT_FAILED"
        )


    def test_missing_case_manifest(self):
        from descriptive_case_record import build_failure_manifest

        records = [
            score_case(0, 900, 0.8, 1.0),
            score_case(2, 902, 1.2, 1.0),
        ]

        manifest = build_failure_manifest(
            records, expected_case_ids=[0, 1, 2]
        )

        self.assertEqual(len(manifest), 3)

        missing = [
            item for item in manifest
            if item["status"] == "MISSING_CASE"
        ]

        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["case_id"], 1)
        self.assertEqual(
            missing[0]["arm_status"], "INSTRUMENT_FAILED"
        )
        self.assertEqual(
            [item["case_id"] for item in manifest],
            [0, 1, 2],
        )


    def test_manifest_invalid_case_ids(self):
        from descriptive_case_record import build_failure_manifest

        def make(case_id):
            return score_case(case_id, 900, 0.8, 1.0)

        fixtures = (
            ([make(0), make(0), make(2)], "DUPLICATE_CASE"),
            ([make(0), make(1), make(99)], "UNEXPECTED_CASE"),
            ([make(0), make("bad"), make(2)], "INVALID_CASE_ID"),
        )

        for records, expected_status in fixtures:
            with self.subTest(fault=expected_status):
                manifest = build_failure_manifest(
                    records, expected_case_ids=[0, 1, 2]
                )

                matches = [
                    item for item in manifest
                    if item["status"] == expected_status
                ]

                self.assertEqual(len(matches), 1)
                self.assertEqual(
                    matches[0]["arm_status"],
                    "INSTRUMENT_FAILED",
                )

                # Every original record plus the missing case
                # must remain visible.
                self.assertEqual(len(manifest), 4)
                self.assertTrue(any(
                    item["status"] == "MISSING_CASE"
                    for item in manifest
                ))


    def test_expected_seed_identity(self):
        from descriptive_case_record import REQUIRED_ARMS

        def fixture(case_id, seed):
            record = score_case(case_id, seed, 0.8, 1.0)
            record["arms"] = {
                name: {
                    "calibration_mse": 0.5,
                    "evaluation_mse": (
                        0.8 if name == "covariance"
                        else 1.0 if name == "magnitude"
                        else 0.6
                    ),
                    "serialized_bytes": 1311,
                    "decode_ok": True,
                }
                for name in REQUIRED_ARMS
            }
            return record

        expected = {0: 900, 1: 901}
        good = [fixture(0, 900), fixture(1, 901)]

        self.assertEqual(
            complete_report(
                good, [0, 1], expected_seeds=expected
            )["status"],
            "VALID",
        )

        forged = [fixture(0, 999), fixture(1, 901)]
        result = complete_report(
            forged, [0, 1], expected_seeds=expected
        )
        self.assertEqual(result["status"], "INSTRUMENT_FAILED")
        self.assertIsNone(result["mean"])

        incomplete = complete_report(
            good, [0, 1], expected_seeds={0: 900}
        )
        self.assertEqual(
            incomplete["status"], "INSTRUMENT_FAILED"
        )


    def test_seed_manifest_classification(self):
        from descriptive_case_record import build_failure_manifest

        fixtures = (
            (900, {0: 900}, "VALID"),
            (999, {0: 900}, "SEED_MISMATCH"),
            ("bad", {0: 900}, "SEED_MISMATCH"),
            (900, {}, "SEED_MAPPING_MISSING"),
        )

        for seed, mapping, expected in fixtures:
            with self.subTest(seed=seed, expected=expected):
                record = score_case(0, seed, 0.8, 1.0)
                manifest = build_failure_manifest(
                    [record],
                    expected_case_ids=[0],
                    expected_seeds=mapping,
                )

                self.assertEqual(len(manifest), 1)
                self.assertEqual(manifest[0]["status"], expected)

                if expected != "VALID":
                    self.assertEqual(
                        manifest[0]["arm_status"],
                        "INSTRUMENT_FAILED",
                    )


    def test_undefined_ratio_does_not_hide_seed_mismatch(self):
        """Constructed case: score failure must not hide identity failure."""
        from descriptive_case_record import build_failure_manifest

        record = score_case(0, 999, 0.5, 0.0)
        self.assertEqual(record["status"], "UNDEFINED_RATIO")

        manifest = build_failure_manifest(
            [record],
            expected_case_ids=[0],
            expected_seeds={0: 900},
        )

        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["status"], "UNDEFINED_RATIO")
        self.assertEqual(
            manifest[0].get("seed_status"),
            "SEED_MISMATCH",
            "Seed mismatch must be independently reported even when ratio fails",
        )

    def test_finite_set_mean_overflow(self):
        records = [
            score_case(0, 900, 0.0, 1.0),
            score_case(1, 901, 0.0, 1.0),
        ]

        # Constructed arithmetic fault injection.
        # The scoring-only bypass must never be used by a study runner.
        for record in records:
            record["improvement"] = -1e308

        result = complete_report(
            records, [0, 1], require_six_arms=False
        )

        self.assertEqual(result["status"], "INVALID_NUMERIC")
        self.assertIsNone(result["mean"])
        self.assertEqual(
            result["reason"],
            "finite-set mean arithmetic failure",
        )


if __name__ == "__main__":
    unittest.main()
