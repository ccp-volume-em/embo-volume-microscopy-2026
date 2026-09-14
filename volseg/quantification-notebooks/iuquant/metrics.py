"""Assemble the per-volume metrics dictionary and write metric CSVs.


Physical units
--------------
``LENGTH = ds * conv_factor`` micrometres per (downsampled) voxel. Lengths scale
by ``LENGTH``, areas by ``LENGTH**2``, volumes by ``LENGTH**3``. ``*_vx`` keys
are the same quantity in (downsampled) voxel units.

"""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from .stats import filter_out_inf, filter_out_inf_and_zero, calc_vf

# Distribution stat suffixes shared by branch / tortuosity / pore / throat.
_STD_SUFFIXES = ("mean", "median", "max", "min", "std", "q1", "q3", "iqr")
# Local-thickness keeps the original's slightly different suffix set.
_LT_SUFFIXES = ("mean", "std_dev", "median", "max", "min", "iqr", "q1", "q3")


def _dist8(arr: np.ndarray, scale: float = 1.0) -> Dict[str, float]:
    """mean/median/max/min/std/q1/q3/iqr of ``arr`` (each * ``scale``).

    Returns NaNs for an empty array rather than raising (the original would
    crash on an empty distribution)."""
    arr = np.asarray(arr, dtype=float)
    if arr.size == 0:
        return {k: float("nan") for k in _STD_SUFFIXES}
    q1 = np.percentile(arr, 25)
    q3 = np.percentile(arr, 75)
    return {
        "mean": float(np.mean(arr)) * scale,
        "median": float(np.median(arr)) * scale,
        "max": float(np.max(arr)) * scale,
        "min": float(np.min(arr)) * scale,
        "std": float(np.std(arr)) * scale,
        "q1": float(q1) * scale,
        "q3": float(q3) * scale,
        "iqr": float(q3 - q1) * scale,
    }


def _add_dist(md: Dict[str, Any], prefix: str, arr: np.ndarray, scale: float) -> None:
    for suffix, value in _dist8(arr, scale).items():
        md[f"{prefix}_{suffix}"] = value


def _add_lt(md: Dict[str, Any], prefix: str, lt_result: Dict[str, float],
            scale: float) -> None:
    """Emit local-thickness stats both scaled and in voxels (``*_vx``)."""
    for suffix in _LT_SUFFIXES:
        md[f"{prefix}_{suffix}"] = lt_result[suffix] * scale
        md[f"{prefix}_{suffix}_vx"] = lt_result[suffix]


def collect_metrics(
    name: str,
    original_image_shape,
    img: np.ndarray,
    fullsize_mask: np.ndarray,
    *,
    crop,
    ds: int,
    conv_factor: float,
    teasar=None,
    lee=None,
    surface_area: Optional[float] = None,
    pn=None,
) -> Dict[str, Any]:
    """Build the metrics dict for one binary volume.

    ``teasar`` / ``lee`` are the per-skeleton bundles
    ``(branch_data, tortuosity, thickness_result, branching_angles)`` returned by
    :func:`iuquant.skeleton.skeleton_stats` (or ``None`` if disabled/absent).
    ``pn`` is the OpenPNM network (or ``None``).
    """
    length = ds * conv_factor
    area = length ** 2
    volume = length ** 3

    md: Dict[str, Any] = {
        "filename": name,
        "original_image_shape": original_image_shape,
        "largest_crop_vf": calc_vf(img),
        "crop": crop,
        "crop_shape": img.shape,
        "prop_of_1000cube": float(np.prod(fullsize_mask.shape) / 1000 ** 3),
        "conv_factor": conv_factor,
    }

    for tag, bundle in (("teasar", teasar), ("lee", lee)):
        if bundle is None:
            continue
        branch_data, tort, lt_result, angles = bundle

        md[f"{tag}_skeleton_length"] = branch_data["branch-distance"].sum() * length
        md[f"{tag}_number_branches"] = len(tort["branch_tortuosities"])
        md[f"{tag}_skeleton_length_vx"] = branch_data["branch-distance"].sum()

        _add_dist(md, f"{tag}_branch_distance",
                  filter_out_inf(branch_data["branch-distance"]), length)
        # Tortuosity is dimensionless (scale = 1).
        _add_dist(md, f"{tag}_branch_tortuosities",
                  filter_out_inf(tort["branch_tortuosities"]), 1.0)

        if angles is not None:
            ba = filter_out_inf_and_zero(angles["orientation-degrees"].to_numpy())
            _add_dist(md, f"{tag}_ba", ba, 1.0)
            # True 3-D inclination angle (present only for 3-D skeletons).
            if "orientation-3d-degrees" in angles:
                ba3d = filter_out_inf_and_zero(
                    angles["orientation-3d-degrees"].to_numpy())
                _add_dist(md, f"{tag}_ba3d", ba3d, 1.0)

        if lt_result is not None:
            _add_lt(md, f"{tag}_local_thickness", lt_result, length)

    if surface_area is not None:
        # Measured on the ds-downsampled mask (same grid as the rest of the
        # geometry) -> scale by area = (ds*conv)**2. See the module docstring.
        md["surface-area"] = surface_area * area
        md["surface_area_vx"] = surface_area

    if pn is not None:
        _add_pore_network(md, pn, length, area, volume)

    return md


def _add_pore_network(md: Dict[str, Any], pn, length: float, area: float,
                      volume: float) -> None:
    """Pore/throat geometry distributions, scaled and in voxels."""
    specs = [
        ("pore.volume", volume),
        ("pore.surface_area", area),
        ("pore.inscribed_diameter", length),
        ("throat.inscribed_diameter", length),
        ("throat.perimeter", length),
        ("throat.total_length", length),
    ]
    for key, scale in specs:
        values = np.asarray(pn[key], dtype=float)
        _add_dist(md, key, values, scale)
        _add_dist(md, f"{key}_vx", values, 1.0)



# CSV writers



def metrics_to_dataframe(records) -> "pd.DataFrame":
    """Tidy one-row-per-(image/label) DataFrame from a list of metrics dicts."""
    return pd.DataFrame(list(records))


def save_metrics_csv(records, path: str) -> "pd.DataFrame":
    """Write all metric records to a single CSV and return the DataFrame."""
    import os

    df = metrics_to_dataframe(records)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Saved metrics CSV ({len(df)} rows): {path}")
    return df
