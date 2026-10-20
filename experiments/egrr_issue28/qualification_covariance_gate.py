"""Constructed covariance-path qualification; no scientific study cases."""

import argparse
import hashlib
import json

import numpy as np

from covariance_float16 import select_covariance_float16
from egrr import heldout_mse, quantize_symmetric, reconstruct
from storage import deserialize, serialize


W = np.array([[0.25, -0.75, 1.5, -1.0],
              [0.5, 1.0, -0.25, -1.5]], dtype=np.float64)
X_CAL = np.array([[1.0, 0.0], [0.0, 1.0],
                  [1.0, 1.0], [-1.0, 2.0]], dtype=np.float64)
X_EVAL = np.array([[2.0, -1.0], [1.0, 2.0],
                   [-2.0, 1.0]], dtype=np.float64)


def digest(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def gate(case):
    evidence = {"fixture": "COV-LOCAL-001", "case": case,
                "weight_sha256": digest(W),
                "calibration_sha256": digest(X_CAL),
                "evaluation_sha256": digest(X_EVAL)}
    try:
        evaluation = X_EVAL.copy()
        calibration = X_CAL.copy()
        if case == "drift":
            evaluation[0, 0] += 1.0
        if digest(evaluation) != evidence["evaluation_sha256"]:
            raise ValueError("FIXTURE_INPUT_DRIFT")
        if case == "malformed":
            calibration = calibration[:, :1]

        quantized = quantize_symmetric(W, 3)
        indices, corrections, diagnostics = select_covariance_float16(
            W, quantized, 2, calibration, return_diagnostics=True
        )
        if len(indices) != 2 or diagnostics["selection_count"] != 2:
            raise ValueError("CANDIDATE_SELECTION_COUNT_MISMATCH")
        payload = serialize(quantized, indices, corrections)
        if case == "corrupt":
            corrupted = bytearray(payload)
            corrupted[-5] ^= 1
            payload = bytes(corrupted)

        decoded_q, decoded_indices, decoded_values = deserialize(payload)
        if not np.array_equal(decoded_q.values, quantized.values):
            raise ValueError("DECODED_QUANTIZER_MISMATCH")
        if not np.array_equal(decoded_indices, indices):
            raise ValueError("DECODED_SELECTION_MISMATCH")
        if not np.array_equal(decoded_values,
                              corrections.astype("<f2").astype(np.float64)):
            raise ValueError("DECODED_CORRECTION_MISMATCH")

        decoded_weights = reconstruct(
            decoded_q, decoded_indices, decoded_values
        )
        scores = {}
        for name, inputs in (("calibration", X_CAL), ("evaluation", evaluation)):
            measured = heldout_mse(W, decoded_weights, inputs)
            independent = float(np.mean((inputs @ (W - decoded_weights)) ** 2))
            if not np.isfinite(measured) or measured < 0 or not np.isclose(
                measured, independent, rtol=1e-12, atol=1e-15
            ):
                raise ValueError("DECODED_SCORING_MISMATCH")
            scores[name + "_mse_hex"] = measured.hex()

        evidence.update({
            "status": "PASS", "reason": "DECODED_COVARIANCE_PATH_VERIFIED",
            "selected_indices": indices.tolist(),
            "selected_gains_hex": [float(x).hex()
                                   for x in diagnostics["selected_gains"]],
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            **scores,
        })
        return evidence, 0
    except (ValueError, FloatingPointError, OverflowError) as exc:
        evidence.update({"status": "FAIL", "reason": str(exc)})
        return evidence, 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True,
                        choices=("benign", "drift", "corrupt", "malformed"))
    args = parser.parse_args()
    record, exit_code = gate(args.case)
    print(json.dumps(record, sort_keys=True, separators=(",", ":")))
    raise SystemExit(exit_code)
