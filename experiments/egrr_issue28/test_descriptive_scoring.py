"""EGRR-DESC-001 constructed numerical fixtures only; no study cases."""
import unittest
from descriptive_scoring import (
    DescriptiveScoringError,
    relative_improvement,
)


class DescriptiveScoringTests(unittest.TestCase):
    def test_positive_improvement(self):
        self.assertAlmostEqual(relative_improvement(0.8, 1.0), 0.2)

    def test_zero_improvement(self):
        self.assertEqual(relative_improvement(1.0, 1.0), 0.0)

    def test_negative_improvement(self):
        self.assertAlmostEqual(relative_improvement(1.2, 1.0), -0.2)

    def test_tiny_positive_baseline_allowed(self):
        self.assertAlmostEqual(
            relative_improvement(8e-14, 1e-13), 0.2
        )

    def test_zero_baseline_undefined(self):
        with self.assertRaisesRegex(
            DescriptiveScoringError, "UNDEFINED"
        ):
            relative_improvement(0.5, 0.0)

    def test_nonfinite_mse_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(DescriptiveScoringError):
                    relative_improvement(value, 1.0)
                with self.assertRaises(DescriptiveScoringError):
                    relative_improvement(1.0, value)

    def test_negative_mse_rejected(self):
        with self.assertRaisesRegex(
            DescriptiveScoringError, "negative MSE"
        ):
            relative_improvement(-0.1, 1.0)

    def test_overflow_undefined(self):
        with self.assertRaisesRegex(
            DescriptiveScoringError, "UNDEFINED"
        ):
            relative_improvement(1e308, 1e-300)

    def test_invalid_input_rejected(self):
        with self.assertRaises(DescriptiveScoringError):
            relative_improvement("invalid", 1.0)


if __name__ == "__main__":
    unittest.main()
