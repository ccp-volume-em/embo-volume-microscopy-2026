"""Optional binary-mask preprocessing: denoise / morphology / size filtering.

Runs on the full-resolution binary mask after TIFF load + crop and before
downsampling and any measurement (so the cleaned mask drives every metric and
the saved ``*_SEG_CROP.tif``). Depends only on numpy + scipy — no heavy deps.

Order of operations (fixed, each step skipped when its setting is off):

    1. **median filter**       — majority filter, removes salt-and-pepper voxels
    2. **morphology**          — a user-ordered list of open/close/erode/dilate
    3. **fill small holes**    — fill enclosed background holes up to a size
    4. **size-based removal**  — drop connected components outside [min, max]

Hole filling runs before size removal (so filled volume counts toward an
object's size), and size removal runs last. All sizes / radii are in full-resolution voxels 
(this runs before downsampling).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import ndimage as ndi

# operation name -> scipy binary morphology function
_MORPH_OPS = {
    "open": ndi.binary_opening,
    "close": ndi.binary_closing,
    "erode": ndi.binary_erosion,
    "dilate": ndi.binary_dilation,
}

# (operation, iterations) steps, e.g. [("open", 1), ("close", 2)].
MorphStep = Tuple[str, int]


@dataclass
class PreprocessSettings:
    """Configuration for :func:`preprocess_mask`.

    enabled           master switch; ``False`` = identity (default)
    median_size       cubic median-filter side in voxels (0/1 = off; use odd)
    morphology        ordered ``[(op, iterations), ...]`` with op in
                      ``{"open", "close", "erode", "dilate"}``
    fill_hole_size    fill enclosed background holes of at most this many voxels
                      (0 = off). Holes touching the volume border are never
                      filled (they're open, not enclosed).
    min_object_size   drop connected components smaller than this many voxels
                      (0 = off)
    max_object_size   drop components larger than this many voxels (None = off)
    connectivity      1/2/3 → 6/18/26-neighbourhood, used for morphology,
                      component labelling and hole detection
    """
    enabled: bool = False
    median_size: int = 0
    morphology: List[MorphStep] = field(default_factory=list)
    fill_hole_size: int = 0
    min_object_size: int = 0
    max_object_size: Optional[int] = None
    connectivity: int = 1

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PreprocessSettings":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in dict(d).items() if k in known})

    def describe(self) -> str:
        if not self.enabled:
            return "off"
        bits = []
        if self.median_size and self.median_size > 1:
            bits.append(f"median={self.median_size}")
        if self.morphology:
            bits.append("morph=" + "+".join(f"{op}x{n}" for op, n in self.morphology))
        if self.fill_hole_size:
            bits.append(f"fill_holes<={self.fill_hole_size}")
        if self.min_object_size:
            bits.append(f"min_size={self.min_object_size}")
        if self.max_object_size is not None:
            bits.append(f"max_size={self.max_object_size}")
        return ", ".join(bits) or "no-op"


def median_filter(mask: np.ndarray, size: int) -> np.ndarray:
    """Cubic median (majority) filter; re-binarised to uint8. ``size<=1`` = off."""
    if not size or size <= 1:
        return (mask > 0).astype(np.uint8)
    filtered = ndi.median_filter((mask > 0).astype(np.uint8), size=size)
    return (filtered > 0).astype(np.uint8)


def apply_morphology(mask: np.ndarray, steps: List[MorphStep],
                     connectivity: int = 1) -> np.ndarray:
    """Apply an ordered list of binary morphology operations."""
    structure = ndi.generate_binary_structure(mask.ndim, connectivity)
    out = mask > 0
    for op, iterations in steps:
        if op not in _MORPH_OPS:
            raise ValueError(f"unknown morphology op {op!r}; "
                             f"expected one of {sorted(_MORPH_OPS)}")
        out = _MORPH_OPS[op](out, structure=structure,
                             iterations=max(1, int(iterations)))
    return out.astype(np.uint8)


def fill_small_holes(mask: np.ndarray, max_size: int,
                     connectivity: int = 1) -> np.ndarray:
    """Fill enclosed background holes of at most ``max_size`` voxels.

    A "hole" is a background component not connected to the volume border;
    border-connected background (the outside) is never filled. ``max_size <= 0``
    is a no-op.
    """
    fg = mask > 0
    if max_size <= 0:
        return fg.astype(np.uint8)
    structure = ndi.generate_binary_structure(mask.ndim, connectivity)
    labels, n = ndi.label(~fg, structure=structure)
    if n == 0:
        return fg.astype(np.uint8)

    sizes = np.bincount(labels.ravel())
    # Background components touching any face are "outside", not holes.
    border = set()
    for ax in range(mask.ndim):
        for end in (0, -1):
            sl = [slice(None)] * mask.ndim
            sl[ax] = end
            border.update(np.unique(labels[tuple(sl)]).tolist())

    fillable = (sizes <= max_size)        # small enough to be a "small hole"
    fillable[0] = False                   # label 0 is not a real component
    for b in border:
        fillable[b] = False               # open background, never fill
    return (fg | fillable[labels]).astype(np.uint8)


def remove_objects_by_size(mask: np.ndarray, min_size: int = 0,
                           max_size: Optional[int] = None,
                           connectivity: int = 1) -> np.ndarray:
    """Keep only connected components whose voxel count is in ``[min, max]``."""
    if not min_size and max_size is None:
        return (mask > 0).astype(np.uint8)
    structure = ndi.generate_binary_structure(mask.ndim, connectivity)
    labels, n = ndi.label(mask > 0, structure=structure)
    if n == 0:
        return np.zeros_like(mask, dtype=np.uint8)
    sizes = np.bincount(labels.ravel())
    keep = np.ones(sizes.size, dtype=bool)
    if min_size:
        keep &= sizes >= min_size
    if max_size is not None:
        keep &= sizes <= max_size
    keep[0] = False  # background label is never foreground
    return keep[labels].astype(np.uint8)


def preprocess_mask(mask: np.ndarray, s: PreprocessSettings) -> np.ndarray:
    """Run the configured preprocessing chain on a binary mask (uint8 0/1)."""
    if not s.enabled:
        return mask
    out = (mask > 0).astype(np.uint8)
    out = median_filter(out, s.median_size)
    if s.morphology:
        out = apply_morphology(out, s.morphology, s.connectivity)
    out = fill_small_holes(out, s.fill_hole_size, s.connectivity)
    out = remove_objects_by_size(out, s.min_object_size, s.max_object_size,
                                 s.connectivity)
    return out
