"""Constructed R-vs-A selection fixture; no study cases."""
import unittest
import numpy as np

from egrr import Quantized, select_corrections
from storage import serialize, deserialize


class RvsARankingTests(unittest.TestCase):
    def test_rounding_changes_selected_index(self):
        w = np.array([[1.0003, 1.0004]], dtype=np.float64)
        q = Quantized(
            np.zeros((1, 2), dtype=np.int16), 1.0, 3
        )

        r_indices, r_values = select_corrections(
            w, q, 1, "magnitude"
        )

        rounded = w.astype(np.float16).astype(np.float64)
        a_indices = np.argsort(
            -np.abs(rounded).ravel(), kind="stable"
        )[:1]

        np.testing.assert_array_equal(r_indices, [1])
        np.testing.assert_array_equal(a_indices, [0])
        self.assertNotEqual(r_indices[0], a_indices[0])

        # The R-selected correction must still be stored
        # and decoded in float16, not evaluated as float64.
        payload = serialize(q, r_indices, r_values)
        _, decoded_indices, decoded_values = deserialize(payload)

        np.testing.assert_array_equal(decoded_indices, [1])
        np.testing.assert_array_equal(
            decoded_values,
            r_values.astype(np.float16).astype(np.float64)
        )

    def test_original_residual_ties_use_flat_index(self):
        w = np.array([[0.25, -0.25]], dtype=np.float64)
        q = Quantized(
            np.zeros((1, 2), dtype=np.int16), 1.0, 3
        )
        indices, _ = select_corrections(
            w, q, 1, "magnitude"
        )
        np.testing.assert_array_equal(indices, [0])


if __name__ == "__main__":
    unittest.main()
