"""Small numeric helpers shared across the quantification pipeline.


"""
from __future__ import annotations

from typing import Dict, Sequence

import numpy as np
from scipy.stats import kurtosis, skew


def calc_vf(img: np.ndarray, fg_idx: int = 1) -> float:
    """Volume (or area) fraction of foreground voxels.

    Fraction = (voxels == fg_idx) / (valid voxels). A caller may mark voxels as
    "ignore" with a negative sentinel value to drop them from the denominator. 
    Returns NaN for an empty / all-ignored input instead of raising on a 0/0 division.
    """
    img = np.asarray(img)
    fg_count = int(np.count_nonzero(img == fg_idx))
    if img.dtype == bool or np.issubdtype(img.dtype, np.unsignedinteger):
        # Unsigned/bool data can't carry a negative "ignore" sentinel, so every
        # voxel is valid. Skipping the ``img > -1`` comparison here also avoids
        # an unsigned-vs-negative promotion (NEP 50) that segfaults on strided
        # array views in some numpy builds.
        total = img.size
    else:
        total = int(np.count_nonzero(img > -1))
    if total == 0:
        return float("nan")
    return float(fg_count / total)


def filter_out_inf(values: Sequence[float]) -> np.ndarray:
    """Drop non-finite (inf/-inf/nan) entries; return a 1-D float array."""
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def filter_out_inf_and_zero(values: Sequence[float]) -> np.ndarray:
    """Drop non-finite and exactly-zero entries (zeros are typically noise
    fragments with no measured value)."""
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr) & (arr != 0)]


def array_summary_stats(arr: np.ndarray) -> Dict[str, float]:
    """Mean/median/std/min/max/quartiles/IQR/skew/kurtosis of an array.

    Returns ``{"error": ...}`` for an empty input (preserving the original
    notebook's contract).
    """
    arr = np.asarray(arr)
    if arr.size == 0:
        return {"error": "Input array is empty"}

    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))
    flat = arr.flatten()
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std_dev": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "range": float(np.ptp(arr)),
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "count": int(arr.size),
        "non_zero_count": int(np.count_nonzero(arr)),
        "unique_count": int(np.unique(arr).size),
        "skewness": float(skew(flat)),
        "kurtosis": float(kurtosis(flat)),
    }
