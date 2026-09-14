"""Volume-fraction / area-fraction sampling analysis and plots.


For each segmentation it:
  1. samples a few 300³ "main" ROIs and keeps the one whose volume fraction is
     closest to their mean (a representative sub-volume),
  2. on that sub-volume, measures area fraction per slice and volume fraction
     over many random crops at a range of ROI sizes,
  3. plots a VF-vs-ROI-size boxplot, an area-fraction-by-slice curve and a slice
     montage, and writes a per-image stats file (+ an optional summary).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import tifffile
from matplotlib import pyplot as plt
from scipy.signal import find_peaks
from scipy.stats import kurtosis

from .stats import calc_vf
from .viz import show_images

DEFAULT_ROI_SIZES = [150, 200, 250, 300, 350, 400, 450]
DEFAULT_IMG_SLICES = [50, 100, 150, 200, 250]
DEFAULT_SUBVOL_SIZE = 500


# ──────────────────────────────────────────────────────────────────────
# Random cropping
# ──────────────────────────────────────────────────────────────────────


def random_points(vol: np.ndarray, num_pts: int,
                  border: Tuple[int, int, int] = (32, 32, 32)) -> np.ndarray:
    """``num_pts`` random centre points inside ``vol``, keeping ``border`` clear.

    The sampleable span on each axis is ``shape - 2*border`` (clamped at 0, so a
    border that fills the axis collapses to its single centre rather than
    producing negative coordinates).
    """
    pts = np.random.random((num_pts, 3))
    for ax in range(3):
        span = max(vol.shape[ax] - 2 * border[ax], 0)
        pts[:, ax] = pts[:, ax] * span + border[ax]
    return pts


def random_crops(img: np.ndarray, num_crops: int = 10,
                 roi_size: Tuple[int, int, int] = (256, 256, 256),
                 locations: Optional[np.ndarray] = None
                 ) -> Tuple[List[np.ndarray], np.ndarray]:
    """Extract ``num_crops`` cubic crops; return ``(crops, centre_locations)``.

    Centres are kept ``roi_size//2`` from each border, the crop's own
    half-width, so every crop is fully inside the volume. 
    """
    half = np.array(roi_size) // 2
    if any(r > s for r, s in zip(roi_size, img.shape)):
        raise ValueError(f"roi_size {tuple(roi_size)} does not fit in volume "
                         f"{img.shape}")
    if locations is None:
        locations = random_points(img, num_crops,
                                  border=tuple(int(h) for h in half)).astype(np.uint32)
    crops = []
    for c in locations:
        crops.append(img[c[0] - half[0]:c[0] + half[0],
                         c[1] - half[1]:c[1] + half[1],
                         c[2] - half[2]:c[2] + half[2]])
    return crops, locations


# ──────────────────────────────────────────────────────────────────────
# Measurements
# ──────────────────────────────────────────────────────────────────────


def area_fraction_by_slice(img: np.ndarray, fg_idx: int = 1) -> List[float]:
    """Foreground area fraction of each z-slice."""
    return [calc_vf(img[z], fg_idx=fg_idx) for z in range(img.shape[0])]


def vf_by_roi_size(img: np.ndarray, roi_sizes: Sequence[int], n_crops: int,
                   fg_idx: int = 1) -> List[List[float]]:
    """For each ROI size, volume fraction of ``n_crops`` random cubes."""
    out = []
    for side in roi_sizes:
        crops, _ = random_crops(img, num_crops=n_crops, roi_size=(side, side, side))
        out.append([calc_vf(c, fg_idx=fg_idx) for c in crops])
    return out


def representative_subvolume(img: np.ndarray, n_main: int = 5,
                            size: Tuple[int, int, int] = (300, 300, 300),
                            fg_idx: int = 1) -> Tuple[np.ndarray, List[float]]:
    """Pick the main ROI whose VF is closest to the mean of ``n_main`` ROIs."""
    crops, _ = random_crops(img, num_crops=n_main, roi_size=size)
    vfs = [calc_vf(c, fg_idx=fg_idx) for c in crops]
    mean_vf = np.mean(vfs)
    idx = min(range(len(vfs)), key=lambda i: abs(vfs[i] - mean_vf))
    return crops[idx], vfs


@dataclass
class VFResult:
    """Volume/area-fraction outcome for one image."""
    filename: str
    shape: Tuple[int, ...]
    whole_volume_fraction: float
    main_roi_vfs: List[float]
    slice_area_fractions: List[float]
    slice_kurtosis: float
    slice_peaks: int
    roi_sizes: List[int]
    vf_by_roi_size: List[List[float]] = field(default_factory=list)

    @property
    def mean_vf_by_roi_size(self) -> List[float]:
        return [float(np.mean(v)) for v in self.vf_by_roi_size]


# ──────────────────────────────────────────────────────────────────────
# Plots
# ──────────────────────────────────────────────────────────────────────


def _plot_vf_boxplot(res: VFResult, title: str, save: Optional[str]) -> None:
    plt.figure(figsize=(10, 6))
    plt.boxplot(res.vf_by_roi_size)
    plt.title(f"Volume fraction for {title}")
    plt.xlabel("ROI size (voxels)")
    plt.ylabel("Volume fraction")
    plt.xticks(range(1, len(res.roi_sizes) + 1), res.roi_sizes)
    if save:
        plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.show()


def _plot_af_by_slice(res: VFResult, title: str, save: Optional[str]) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(range(len(res.slice_area_fractions)), res.slice_area_fractions)
    ax.set_title(f"Area fraction by slice index for {title}")
    ax.set_xlabel("Slice number")
    ax.set_ylabel("Area fraction")
    if save:
        fig.savefig(save, dpi=150, bbox_inches="tight")
    plt.show()


def _write_stats_file(res: VFResult, path: str, title: str) -> None:
    with open(path, "w") as fh:
        fh.write(f"Statistics for: {res.filename}\nPlot title: {title}\n")
        fh.write(f"Image shape: {res.shape}\n" + "=" * 50 + "\n\n")
        fh.write(f"Whole-volume fraction: {res.whole_volume_fraction:.6f}\n")
        fh.write(f"Main ROI VF: {np.mean(res.main_roi_vfs):.6f} "
                 f"± {np.std(res.main_roi_vfs):.6f}\n")
        fh.write(f"Slice AF: {np.mean(res.slice_area_fractions):.6f} "
                 f"± {np.std(res.slice_area_fractions):.6f}\n")
        fh.write(f"Slice kurtosis: {res.slice_kurtosis:.6f}, peaks: {res.slice_peaks}\n\n")
        fh.write(f"ROI sizes: {res.roi_sizes}\n")
        for size, mean_vf in zip(res.roi_sizes, res.mean_vf_by_roi_size):
            fh.write(f"  ROI {size}: mean VF = {mean_vf:.6f}\n")


def _write_summary(results: List[VFResult], path: str) -> None:
    with open(path, "w") as fh:
        fh.write("VOLUME FRACTION ANALYSIS SUMMARY\n" + "=" * 50 + "\n\n")
        fh.write(f"{len(results)} image(s)\n\n")
        fh.write("File\tWhole_VF\tMain_VF_mean\tMain_VF_std\tSlice_AF_mean\n")
        for r in results:
            fh.write(f"{r.filename}\t{r.whole_volume_fraction:.6f}\t"
                     f"{np.mean(r.main_roi_vfs):.6f}\t{np.std(r.main_roi_vfs):.6f}\t"
                     f"{np.mean(r.slice_area_fractions):.6f}\n")


# ──────────────────────────────────────────────────────────────────────
# Orchestrator
# ──────────────────────────────────────────────────────────────────────


def analyze_volume_fractions(
    names: Sequence[Tuple[str, str]],
    output_folder: Optional[str] = None,
    roi_sizes: Optional[Sequence[int]] = None,
    img_slices: Optional[Sequence[int]] = None,
    n_crops: int = 10,
    plot_titles: Optional[Sequence[str]] = None,
    save_summary: bool = True,
    fg_idx: int = 1,
    subvol_size: int = DEFAULT_SUBVOL_SIZE,
    seed: Optional[int] = None,
) -> List[VFResult]:
    """Run the VF/AF analysis over ``(name, source)`` pairs.

    ``source`` may be a file path (read with tifffile) or an in-memory
    ``np.ndarray``. The array form lets you feed the preprocessed masks from
    :func:`make_measurements` straight in — e.g.
    ``analyze_volume_fractions([(r.image, r.mask) for r in results], fg_idx=1)``
    (preprocessed masks are binary 0/1, so use ``fg_idx=1``).

    Returns one :class:`VFResult` per image (cleaner than the original, which
    returned only the last image's intermediate arrays). Plots are shown and,
    if ``output_folder`` is set, saved alongside per-image + summary stat files.

    ``subvol_size`` is the side of the "representative" sub-volume the random
    crops are drawn from; it is clamped to the image and any ``roi_sizes``
    larger than it are skipped (with a printed note), so the random-crop VF can
    never be measured on a clipped/degenerate region. Pass ``seed`` for
    reproducible sampling.
    """
    roi_sizes = list(roi_sizes or DEFAULT_ROI_SIZES)
    img_slices = list(img_slices or DEFAULT_IMG_SLICES)
    if seed is not None:
        np.random.seed(seed)
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)

    results: List[VFResult] = []
    for i, (basename, source) in enumerate(names):
        img = source if isinstance(source, np.ndarray) else tifffile.imread(source)
        print(f"Processing {basename}, shape {img.shape}")
        title = plot_titles[i] if (plot_titles and i < len(plot_titles)) else basename
        prefix = os.path.splitext(basename)[0]
        path = (lambda suffix: os.path.join(output_folder, f"{prefix}{suffix}")
                if output_folder else None)

        # Sub-volume side fits inside the image; ROI sizes must fit inside it.
        size = min(subvol_size, *img.shape)
        if size < subvol_size:
            print(f"  subvolume {subvol_size} exceeds image {img.shape}; using {size}.")
        usable_rois = [s for s in roi_sizes if s <= size]
        dropped = [s for s in roi_sizes if s > size]
        if dropped:
            print(f"  ROI sizes {dropped} exceed subvolume side {size}; skipped.")

        whole_vf = calc_vf(img, fg_idx=fg_idx)
        sub_img, main_vfs = representative_subvolume(
            img, size=(size, size, size), fg_idx=fg_idx)
        slice_afs = area_fraction_by_slice(sub_img, fg_idx=fg_idx)
        res = VFResult(
            filename=basename, shape=img.shape, whole_volume_fraction=whole_vf,
            main_roi_vfs=main_vfs, slice_area_fractions=slice_afs,
            slice_kurtosis=float(kurtosis(slice_afs, fisher=False)),
            slice_peaks=int(len(find_peaks(slice_afs, prominence=0.001)[0])),
            roi_sizes=usable_rois,
            vf_by_roi_size=vf_by_roi_size(sub_img, usable_rois, n_crops, fg_idx),
        )

        _plot_vf_boxplot(res, title, path("_volume_fraction_boxplot.png"))
        _plot_af_by_slice(res, title, path("_area_fraction_by_slice.png"))
        montage = [sub_img[z] for z in img_slices if z < sub_img.shape[0]]
        show_images(montage, titles=[str(z) for z in img_slices[:len(montage)]],
                    figsize=(4.5, 1.5), save_path=path("_slice_images.png"))
        if output_folder:
            _write_stats_file(res, path("_statistics.txt"), title)
        results.append(res)
        del img

    if output_folder and save_summary and results:
        _write_summary(results, os.path.join(output_folder, "analysis_summary.txt"))
        print(f"Saved summary: {os.path.join(output_folder, 'analysis_summary.txt')}")
    return results
