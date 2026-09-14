"""Loading, cropping, downsampling and filename helpers for segmentation TIFFs.

Only depends on numpy + tifffile (both light), so this is safe to import
without the heavy skeletonisation / pore-network stack.
"""
from __future__ import annotations

import os
from typing import Iterator, List, Optional, Sequence, Tuple

import numpy as np
import tifffile

# A crop is six ints: [z0, z1, y0, y1, x0, x1].
Crop = Sequence[int]


def list_segmentations(folder: str, pattern: str = "*.tif") -> List[Tuple[str, str]]:
    """Return sorted ``(basename, fullpath)`` pairs for every TIFF in ``folder``."""
    import glob

    fullnames = glob.glob(os.path.join(folder, pattern))
    names = [(os.path.basename(n), n) for n in fullnames]
    names.sort()
    return names


def load_and_crop(fullname: str, crop: Optional[Crop]) -> np.ndarray:
    """Read a TIFF and apply a ``[z0,z1,y0,y1,x0,x1]`` crop (``None`` = whole)."""
    img = tifffile.imread(fullname)
    if crop is not None:
        z0, z1, y0, y1, x0, x1 = crop
        img = img[z0:z1, y0:y1, x0:x1]
    return img


def binary_mask(labelmap: np.ndarray, label: Optional[int] = None,
                calc_ivs: bool = False) -> np.ndarray:
    """Derive a uint8 binary mask from a (possibly multi-label) segmentation.

    * ``label`` given  -> mask of exactly that label (multi-label mode).
    * ``label`` None   -> any non-zero voxel is foreground.
    * ``calc_ivs``     -> invert the mask, so the *background* (intervillous
      space) becomes the measured foreground. Only meaningful for the
      whole-foreground (``label is None``) case.
    """
    if label is not None:
        mask = (labelmap == label).astype(np.uint8)
    else:
        mask = (labelmap > 0).astype(np.uint8)
        if calc_ivs:
            mask = 1 - mask
    return mask


def downsample(mask: np.ndarray, ds: int) -> np.ndarray:
    """Integer stride downsample by ``ds`` in every axis; re-binarise to uint8."""
    if ds <= 1:
        return (mask > 0).astype(np.uint8)
    return (mask[::ds, ::ds, ::ds] > 0).astype(np.uint8)


def upsample(arr: np.ndarray, factor: int,
             target_shape: Optional[Tuple[int, ...]] = None) -> np.ndarray:
    """Nearest-neighbour upsample by ``factor`` on every axis (inverse of the
    stride downsample), then crop/pad to ``target_shape`` if given.

    Block-repeats each voxel ``factor`` times so a map computed on the
    ``[::factor]``-downsampled volume lines up with the full-resolution frame
    (downsampled index ``i`` expands to original ``i*factor : i*factor+factor``).
    Cropping/padding to ``target_shape`` fixes the off-by-a-few-voxels when the
    original size isn't an exact multiple of ``factor``.
    """
    if factor and factor > 1:
        for ax in range(arr.ndim):
            arr = np.repeat(arr, factor, axis=ax)
    if target_shape is not None:
        arr = arr[tuple(slice(0, t) for t in target_shape)]
        pad = [(0, max(0, t - s)) for t, s in zip(target_shape, arr.shape)]
        if any(hi for _, hi in pad):
            arr = np.pad(arr, pad)
    return arr


def unique_labels(fullname: str) -> np.ndarray:
    """Unique positive (foreground) label values in a multi-label TIFF."""
    img = tifffile.imread(fullname)
    labels = np.unique(img)
    return labels[labels > 0]


def base_filename(fullname: str, output_dir: Optional[str] = None) -> str:
    """Path stem for derived artefacts: ``<output_dir or src_dir>/<name-without-ext>``."""
    stem = os.path.basename(fullname)
    stem = os.path.splitext(stem)[0]
    root = output_dir if output_dir is not None else os.path.dirname(fullname)
    return os.path.join(root, stem)


def label_directory(fullname: str, label: int,
                    output_dir: Optional[str] = None) -> str:
    """Create and return ``<root>/<name>_label_<label>/`` for per-label output.

    ``root`` is ``output_dir`` when given, else the source file's directory.
    """
    stem = os.path.splitext(os.path.basename(fullname))[0]
    root = output_dir if output_dir is not None else os.path.dirname(fullname)
    label_dir = os.path.join(root, f"{stem}_label_{label}")
    os.makedirs(label_dir, exist_ok=True)
    return label_dir


def save_tiff(arr: np.ndarray, path: str) -> None:
    """LZW-compressed TIFF write (matches the original notebook's outputs)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tifffile.imwrite(path, arr, compression="lzw")
