"""Constructed covariance diagnostics fixtures; no study seeds."""
import unittest
import numpy as np

from egrr import Quantized
from covariance_float16 import select_covariance_float16


class GainDiagnosticsTests(unittest.TestCase):
    def run_selector(self, w, k):
        q = Quantized(
            np.zeros(w.shape, dtype=np.int16), 1.0, 3
        )
        x = np.eye(w.shape[0], dtype=np.float64)
        old = select_covariance_float16(w, q, k, x)
        new = select_covariance_float16(
            w, q, k, x, return_diagnostics=True
        )
        np.testing.assert_array_equal(old[0], new[0])
        np.testing.assert_array_equal(old[1], new[1])
        return new

    def test_positive_gains(self):
        w = np.array([[1.0], [2.0]])
        idx, values, d = self.run_selector(w, 2)
        self.assertEqual(d["selection_count"], 2)
        self.assertEqual(d["positive_gain_count"], 2)
        self.assertEqual(d["negative_gain_count"], 0)
        self.assertEqual(d["zero_gain_count"], 0)

    def test_zero_gains(self):
        w = np.zeros((2, 2))
        idx, values, d = self.run_selector(w, 4)
        self.assertEqual(len(idx), 4)
        self.assertEqual(d["zero_gain_count"], 4)

    def test_negative_gains(self):
        # Constructed correlated-feature fixture:
        # fixing one residual makes the other correction harmful.
        w = np.array([[1.0], [-1.0]], dtype=np.float64)
        q = Quantized(
            np.zeros((2, 1), dtype=np.int16), 1.0, 3
        )
        x = np.array([
            [1.0, 1.0],
            [-1.0, -1.0],
        ], dtype=np.float64)

        old = select_covariance_float16(w, q, 2, x)
        idx, values, d = select_covariance_float16(
            w, q, 2, x, return_diagnostics=True
        )

        np.testing.assert_array_equal(idx, old[0])
        np.testing.assert_array_equal(values, old[1])
        # Gains are recorded in greedy selection order.
        # First correction is harmful; second is beneficial.
        np.testing.assert_array_equal(
            d["selected_gains"], [-1.0, 1.0]
        )
        self.assertEqual(d["selection_count"], 2)
        self.assertEqual(d["positive_gain_count"], 1)
        self.assertEqual(d["negative_gain_count"], 1)
        self.assertEqual(d["zero_gain_count"], 0)

    def test_exact_k(self):
        w = np.arange(12, dtype=np.float64).reshape(3, 4)
        idx, values, d = self.run_selector(w, 12)
        self.assertEqual(len(idx), 12)
        self.assertEqual(d["selection_count"], 12)
        self.assertEqual(len(d["selected_gains"]), 12)

    def test_zero_k(self):
        w = np.ones((2, 2))
        idx, values, d = self.run_selector(w, 0)
        self.assertEqual(len(idx), 0)
        self.assertEqual(d["selection_count"], 0)


if __name__ == "__main__":
    unittest.main()
