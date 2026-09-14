"""Per-volume "map" measurements: surface area and local thickness.

``local_thickness`` needs PoreSpy; it is imported lazily so that importing this
module (or using only surface area) doesn't require the pore-network stack.
"""
from __future__ import annotations

import numpy as np
from skimage import measure


def surface_area(binary_mask: np.ndarray) -> float:
    """Surface area of a binary mask via a marching-cubes mesh (in voxel² units).

    Vectorised triangle-area sum over the mesh produced at iso-level 0.5.

    A fully-solid or fully-empty mask has no iso-0.5 surface (marching_cubes
    raises in that case), so we short-circuit to 0.0.
    """
    if binary_mask.min() == binary_mask.max():
        return 0.0
    verts, faces, _, _ = measure.marching_cubes(binary_mask, level=0.5)
    v0, v1, v2 = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    cross = np.cross(v1 - v0, v2 - v0)
    areas = 0.5 * np.linalg.norm(cross, axis=1)
    return float(np.sum(areas))


def local_thickness(mask: np.ndarray, sizes: int = 100) -> np.ndarray:
    """PoreSpy local-thickness map (per-voxel inscribed-sphere **radius**).

    NOTE: PoreSpy returns the *radius* of the largest inscribed sphere, not the diameter.
    """
    import porespy as ps

    return ps.filters.local_thickness(mask, sizes=sizes)
