"""Skeletonisation and skeleton-derived metrics.


"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from skimage import morphology

from .stats import array_summary_stats

# Default TEASAR parameters 
DEFAULT_TEASAR_PARAMS = {"scale": 2, "const": 50}
DEFAULT_DUST_THRESHOLD = 1000


def _summarize(skel) -> "pd.DataFrame":
    """``skan.summarize`` with hyphen column names pinned across skan versions.

    """
    import skan

    try:
        return skan.summarize(skel, separator="-")
    except TypeError:
        return skan.summarize(skel)


def skeletonize_teasar(mask: np.ndarray,
                       teasar_params: Optional[dict] = None,
                       dust_threshold: int = DEFAULT_DUST_THRESHOLD,
                       parallel: int = 1, **extra) -> np.ndarray:
    """TEASAR centreline skeleton as a binary volume (via ``kimimaro``).

    Skeleton *shape* is governed by ``teasar_params`` (passed straight to
    kimimaro). 

    * ``scale`` / ``const`` — the invalidation-ball radius is
      ``scale * DBF + const`` (DBF = local inscribed-sphere radius). Smaller
      values keep more, finer branches; larger values prune side branches.
    * ``max_paths`` — hard cap on the number of extracted paths/branches.
    * ``pdrf_exponent`` / ``pdrf_scale`` — bias paths toward the object centre.
    * ``soma_detection_threshold`` / ``soma_*`` — soma handling; for tubular
      villi/vessels set ``soma_detection_threshold=0`` to disable it.

    ``dust_threshold`` drops disconnected components below N voxels — it
    does nothing to a single connected structure. ``**extra`` is forwarded to
    ``kimimaro.skeletonize`` (e.g. ``anisotropy=(z,y,x)``, ``fix_branching``,
    ``fill_holes``, ``fix_borders``).

    ``parallel`` is the kimimaro worker count: ``1`` (default) runs in-process,
    ``0`` uses all cores. The default is 1 because kimimaro's multiprocessing
    uses ``spawn`` on Windows, which re-imports the caller and raises
    ``freeze_support`` errors outside an ``if __name__ == '__main__'`` guard.
    Set ``parallel=0`` for the original all-core behaviour (fine on Linux).
    """
    import kimimaro

    kwargs = dict(dust_threshold=dust_threshold, progress=True,
                  parallel=parallel, parallel_chunk_size=200)
    kwargs.update(extra)            # caller-supplied kimimaro options win
    skels = kimimaro.skeletonize(
        mask, teasar_params=teasar_params or DEFAULT_TEASAR_PARAMS, **kwargs)
    out = np.zeros(mask.shape, dtype=np.uint8)
    if not skels:
        # No skeleton survived (e.g. dust_threshold > object size, or an overly
        # tight max_paths / scale). Return an empty skeleton rather than crash.
        print("  WARNING: TEASAR produced no skeleton for these parameters.")
        return out
    skel = skels[list(skels.keys())[0]]
    # Round (don't truncate) to the nearest voxel, and use int64 indices so
    # volumes wider than the old int16 limit (32767) can't silently overflow.
    verts = np.rint(skel.vertices).astype(np.int64)
    np.clip(verts, 0, np.array(mask.shape) - 1, out=verts)
    out[verts[:, 0], verts[:, 1], verts[:, 2]] = 1
    return out


def skeletonize_lee(mask: np.ndarray) -> np.ndarray:
    """Lee (skimage) 3-D thinning skeleton as a binary volume."""
    binary = mask.astype(bool)
    try:
        skel = morphology.skeletonize(binary, method="lee")
    except TypeError:
        skel = morphology.skeletonize_3d(binary)
    return (np.asarray(skel) > 0).astype(np.uint8)


def branching_angles(branch_data: "pd.DataFrame") -> "pd.DataFrame":
    """Add branch-orientation columns to a skan summary.

    * ``orientation-radians`` / ``orientation-degrees`` — the original in-plane
      angle, taken in the (axis-0, axis-1) plane only (the third coordinate is
      ignored). Branches are undirected, so these wrap to ``[0, pi)`` / ``[0, 180)``.
    * ``orientation-3d-radians`` / ``orientation-3d-degrees`` — a true 3-D
      inclination: the angle between the branch vector and axis-0, using all
      three coordinates. Undirected, so it folds to ``[0, pi/2]`` / ``[0, 90]``
      (0 = aligned with axis-0, 90 = perpendicular). 
    """
    src = branch_data[["image-coord-src-0", "image-coord-src-1"]].to_numpy()
    dst = branch_data[["image-coord-dst-0", "image-coord-dst-1"]].to_numpy()
    vectors = dst - src
    angle = np.arctan2(vectors[:, 1], vectors[:, 0])
    branch_data["orientation-radians"] = angle % np.pi
    branch_data["orientation-degrees"] = np.degrees(angle) % 180

    cols3 = [f"image-coord-{end}-{i}" for end in ("src", "dst") for i in range(3)]
    if all(c in branch_data.columns for c in cols3):
        s3 = branch_data[[f"image-coord-src-{i}" for i in range(3)]].to_numpy()
        d3 = branch_data[[f"image-coord-dst-{i}" for i in range(3)]].to_numpy()
        v3 = d3 - s3
        norm = np.linalg.norm(v3, axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            cos_incl = np.abs(v3[:, 0]) / norm   # |axis-0 component| / length
        incl = np.arccos(np.clip(cos_incl, 0.0, 1.0))  # NaN where norm == 0
        branch_data["orientation-3d-radians"] = incl
        branch_data["orientation-3d-degrees"] = np.degrees(incl)
    return branch_data


def _tortuosity_from_summary(branch_data: "pd.DataFrame") -> Dict[str, object]:
    """Per-branch tortuosity (branch length / straight-line length) from a
    pre-computed skan summary — avoids re-running ``skan.Skeleton``.

    """
    with np.errstate(invalid="ignore", divide="ignore"):
        tort = (branch_data["branch-distance"]
                / branch_data["euclidean-distance"]).to_numpy()
    finite = tort[np.isfinite(tort)]
    return {
        "average_tortuosity": float(np.mean(finite)) if finite.size else float("nan"),
        "branch_tortuosities": tort.tolist(),
    }


def tortuosity(skeleton: np.ndarray) -> Dict[str, object]:
    """Per-branch tortuosity for a standalone skeleton volume.

    Returns ``{"average_tortuosity", "branch_tortuosities"}``. (The pipeline
    uses :func:`skeleton_stats`, which derives tortuosity from its already-built
    summary rather than calling this — see :func:`_tortuosity_from_summary`.)
    """
    return _tortuosity_from_summary(_summarize(_skeleton_obj(skeleton)))


def _skeleton_obj(skeleton: np.ndarray, **kwargs):
    import skan

    return skan.Skeleton(skeleton.astype(bool), **kwargs)


def skeleton_stats(skeleton: np.ndarray, thickness_map: Optional[np.ndarray]
                   ) -> Tuple["pd.DataFrame", Dict[str, object],
                              Optional[Dict[str, float]], "pd.DataFrame"]:
    """Summarise a skeleton: branch table, tortuosity, thickness-along-skeleton,
    and branching angles.

    The skan summary is computed once and reused for both branching angles and
    tortuosity (the original rebuilt the skan ``Skeleton`` a second time).

    """
    branch_data = _summarize(_skeleton_obj(skeleton, spacing=1,
                                           source_image=thickness_map))
    angles = branching_angles(branch_data)
    tort = _tortuosity_from_summary(branch_data)

    thickness_result: Optional[Dict[str, float]] = None
    if thickness_map is not None:
        along_skeleton = (thickness_map * skeleton).flatten()
        nonzero = along_skeleton[np.nonzero(along_skeleton)]
        thickness_result = array_summary_stats(nonzero)

    return branch_data, tort, thickness_result, angles
