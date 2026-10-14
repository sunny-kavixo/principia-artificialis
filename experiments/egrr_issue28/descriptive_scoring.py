"""EGRR-DESC-001 descriptive ratio helper — design instrumentation only.

Not a hypothesis test, not a population inference procedure.
No study seeds or evaluation arrays are generated here.
"""
import math


class DescriptiveScoringError(ValueError):
    """Invalid or undefined case-level descriptive ratio."""


def relative_improvement(covariance_mse, magnitude_mse):
    """Compute 1 - covariance_mse/magnitude_mse for finite valid inputs."""
    try:
        cov = float(covariance_mse)
        mag = float(magnitude_mse)
    except (TypeError, ValueError, OverflowError) as exc:
        raise DescriptiveScoringError("invalid MSE input") from exc

    if not math.isfinite(cov) or not math.isfinite(mag):
        raise DescriptiveScoringError("non-finite MSE")

    if cov < 0 or mag < 0:
        raise DescriptiveScoringError("negative MSE")

    if mag == 0:
        raise DescriptiveScoringError("zero magnitude MSE: UNDEFINED")

    ratio = cov / mag
    improvement = 1.0 - ratio

    if not math.isfinite(ratio) or not math.isfinite(improvement):
        raise DescriptiveScoringError("non-finite ratio: UNDEFINED")

    return improvement
