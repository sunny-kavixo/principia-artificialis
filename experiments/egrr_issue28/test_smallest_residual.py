"""Constructed smallest-residual tests; no study seeds."""
import unittest
import numpy as np

from egrr import Quantized, select_corrections, reconstruct
from storage import serialize, deserialize


class SmallestResidualTests(unittest.TestCase):
    def setUp(self):
        self.q = Quantized(
            np.zeros((2, 3), dtype=np.int16), 1.0, 3
        )
        self.w = np.array([
            [0.5, -0.1, 0.1],
            [0.3, -0.1, 0.9],
        ], dtype=np.float64)

    def test_smallest_ranking_and_ties(self):
        idx, values = select_corrections(
            self.w, self.q, 3, "smallest"
        )
        np.testing.assert_array_equal(idx, [1, 2, 4])
        np.testing.assert_array_equal(
            values, [-0.1, 0.1, -0.1]
        )

    def test_exact_k(self):
        for k in (0, 1, 3, 6):
            with self.subTest(k=k):
                idx, values = select_corrections(
                    self.w, self.q, k, "smallest"
                )
                self.assertEqual(len(idx), k)
                self.assertEqual(len(values), k)
                self.assertEqual(len(np.unique(idx)), k)

    def test_float16_serialization_roundtrip(self):
        idx, values = select_corrections(
            self.w, self.q, 3, "smallest"
        )
        payload = serialize(self.q, idx, values)
        q2, idx2, values2 = deserialize(payload)

        np.testing.assert_array_equal(idx2, idx)
        np.testing.assert_array_equal(
            values2,
            values.astype(np.float16).astype(np.float64)
        )

        expected = reconstruct(
            self.q, idx,
            values.astype(np.float16).astype(np.float64)
        )
        actual = reconstruct(q2, idx2, values2)
        np.testing.assert_array_equal(actual, expected)

    def test_not_a_guaranteed_killer(self):
        # This arm is a diagnostic, not proof of inferior quality.
        idx, _ = select_corrections(
            self.w, self.q, 3, "smallest"
        )
        self.assertEqual(len(idx), 3)


if __name__ == "__main__":
    unittest.main()
