"""Constructed covariance-path C-NOISE probe; no study seeds are used."""

from __future__ import annotations

from hashlib import sha256
import json
import struct

import numpy as np

from canonical_evidence import float64_hex
from covariance_float16 import select_covariance_float16
from egrr import quantize_symmetric, reconstruct
from storage import deserialize, serialize


CONSTRUCTED_SEED = 903


def _mse(inputs, weights, reconstructed):
    value = float(np.mean((inputs @ (weights - reconstructed)) ** 2))
    if not np.isfinite(value):
        raise RuntimeError("non-finite decoded MSE")
    return value


def build_result(seed=CONSTRUCTED_SEED):
    rng = np.random.default_rng(seed)
    weights = rng.normal(size=(64, 32))
    x_cal = rng.normal(size=(256, 64))
    x_eval = rng.normal(size=(1024, 64))
    quantized = quantize_symmetric(weights, 3)
    indices, residuals, diagnostics = select_covariance_float16(
        weights,
        quantized,
        128,
        x_cal,
        return_diagnostics=True,
    )
    payload = serialize(quantized, indices, residuals)
    decoded_q, decoded_indices, decoded_residuals = deserialize(payload)
    if not np.array_equal(decoded_indices, indices):
        raise RuntimeError("decoded correction indices changed")
    reconstructed = reconstruct(
        decoded_q, decoded_indices, decoded_residuals
    )
    expected_reconstructed = reconstruct(
        quantized,
        indices,
        residuals.astype("<f2").astype(np.float64),
    )
    if not np.array_equal(reconstructed, expected_reconstructed):
        raise RuntimeError("decoded reconstruction changed")

    result = {
        "fixture": "constructed-covariance-noise-903",
        "seed": int(seed),
        "shape": [64, 32],
        "correction_count": int(len(decoded_indices)),
        "selection_count": diagnostics["selection_count"],
        "negative_gain_count": diagnostics["negative_gain_count"],
        "zero_gain_count": diagnostics["zero_gain_count"],
        "positive_gain_count": diagnostics["positive_gain_count"],
        "payload_sha256": sha256(payload).hexdigest(),
        "calibration_mse_f64_be_hex": float64_hex(
            _mse(x_cal, weights, reconstructed)
        ),
        "evaluation_mse_f64_be_hex": float64_hex(
            _mse(x_eval, weights, reconstructed)
        ),
        "indices_sha256": sha256(
            np.asarray(decoded_indices, dtype="<i8").tobytes()
        ).hexdigest(),
    }
    if result["correction_count"] != 128:
        raise RuntimeError("covariance path did not select exactly K=128")
    return result


def main():
    print(json.dumps(build_result(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
