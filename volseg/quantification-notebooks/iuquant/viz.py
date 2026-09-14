"""Visualisation helpers: slice montages, metric histograms, napari viewing.

matplotlib only at import time; napari/openpnm are lazy.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

from .stats import filter_out_inf


def show_images(images: Sequence[np.ndarray], titles: Optional[List[str]] = None,
                figsize=(12, 12), save_path: Optional[str] = None) -> None:
    """Display images side by side; optionally save to ``save_path``."""
    n = len(images)
    if titles is None:
        titles = [f"{im.shape} {im.dtype}" for im in images]
    fig = plt.figure(figsize=figsize)
    for i, (image, title) in enumerate(zip(images, titles)):
        ax = fig.add_subplot(1, n, i + 1)
        if image.ndim == 2:
            plt.gray()
        plt.imshow(image)
        ax.set_title(title)
    fig.set_size_inches(np.array(fig.get_size_inches()) * n)
    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved slice images: {save_path}")
    plt.show()


def plot_image_on_top(image, x, y, ax, zoom=1.0) -> None:
    """Overlay ``image`` as an inset at data-coordinate ``(x, y)`` on ``ax``."""
    ab = AnnotationBbox(OffsetImage(image, zoom=zoom), (x, y),
                        xycoords="data", frameon=False)
    ax.add_artist(ab)


def _auto_bins(data: np.ndarray, cap: int = 512) -> int:
    """Freedman–Diaconis bin count, capped.

    ``bins="auto"`` can request millions of bins for heavy-tailed data with a
    tiny IQR and a few outliers (→ MemoryError); this computes the FD count
    cheaply and clamps it instead of letting numpy allocate the edge array.
    """
    n = data.size
    if n < 2:
        return 1
    q1, q3 = np.percentile(data, [25, 75])
    iqr = q3 - q1
    rng = float(data.max() - data.min())
    if iqr <= 0 or rng <= 0:
        return max(1, min(int(np.sqrt(n)), cap))
    width = 2 * iqr / np.cbrt(n)
    return max(1, min(int(np.ceil(rng / width)), cap))


def _hist(values, xlabel, save_path, log=False):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if log:
        values = values[values > 0]   # log of <=0 is -inf/nan
    if values.size == 0:
        return
    data = np.log(values) if log else values
    fig, ax = plt.subplots()
    ax.hist(data, bins=_auto_bins(data))
    ax.set_xlabel(xlabel)
    ax.set_ylabel("count")
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_visualizations(base: str, *, img=None, thickness=None, skeleton=None,
                        pn=None, snow=None, teasar_tort=None, lee_tort=None,
                        ds: int = 1, conv_factor: float = 1.0,
                        slice_idx: int = 10) -> None:
    """Save the standard slice + histogram PNGs for one volume.

    """
    length = ds * conv_factor

    def _z(arr):
        """Clamp slice_idx into range so small/thin volumes don't IndexError."""
        return min(slice_idx, arr.shape[0] - 1)

    if img is not None:
        fig, ax = plt.subplots()
        ax.imshow(img[_z(img), :])
        fig.savefig(f"{base}_Seg_Slice{slice_idx}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

    if thickness is not None:
        fig, ax = plt.subplots()
        im = ax.imshow(thickness[_z(thickness), :])
        fig.colorbar(im, ax=ax, fraction=0.036, pad=0.04)
        ax.set_title(f"Local Thickness (radius) - Slice {slice_idx}")
        fig.savefig(f"{base}_LT_Slice{slice_idx}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)
        _hist(thickness[thickness > 0] * length, "Local Thickness radius µm",
              f"{base}_LocalThicknessHistogram.png")

    if skeleton is not None:
        fig, ax = plt.subplots()
        ax.imshow(skeleton[_z(skeleton), :])
        fig.savefig(f"{base}_Skeleton_Slice{slice_idx}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)
    if teasar_tort is not None:
        _hist(filter_out_inf(teasar_tort["branch_tortuosities"]),
              "TEASAR branch tortuosities", f"{base}_TEASARBranchTortuosities_Histo.png")
    if lee_tort is not None:
        _hist(filter_out_inf(lee_tort["branch_tortuosities"]),
              "Lee branch tortuosities", f"{base}_LeeBranchTortuosities_Histo.png")

    if pn is not None:
        _hist(pn["pore.volume"] * (length ** 3), "pore.volume µm³",
              f"{base}_Pore_Volume_Histo.png", log=True)
        _hist(pn["pore.inscribed_diameter"] * length, "pore.inscribed_diameter µm",
              f"{base}_Pore_Inscribed_Diameter_Histo.png")
        _hist(pn["throat.inscribed_diameter"] * length, "throat.inscribed_diameter µm",
              f"{base}_Throat_Inscribed_Diameter_Histo.png")
        _hist(pn["throat.total_length"] * length, "throat.total_length µm",
              f"{base}_Throat_TotalLength_Histo.png")


def view_maps(*arrays, scale=None, **named) -> "napari.Viewer":  # noqa: F821
    """Open a napari viewer with each array as a (named) image layer.

    Accepts positional arrays, a single ``{name: array}`` dict, and/or
    ``name=array`` keywords — e.g.
    ``view_maps({"mask": r.mask, **r.maps})`` or
    ``view_maps(image=orig, **r.maps)``. ``None`` layers are skipped.

    ``scale`` (an int or per-axis tuple) is applied to every layer. Use it to
    overlay *downsampled* maps on a full-resolution image without upsampling the
    data — pass the maps with ``scale=ds`` and the full-res image with its own
    layer (this is the lightweight alternative to ``upscale_maps``).
    """
    import napari

    layers = {}
    if len(arrays) == 1 and isinstance(arrays[0], dict):
        layers.update(arrays[0])
    else:
        layers.update({f"arr_{i}": a for i, a in enumerate(arrays)})
    layers.update(named)

    viewer = napari.Viewer()
    for name, arr in layers.items():
        if arr is None:
            continue
        kw = {"name": name}
        if scale is not None:
            kw["scale"] = scale if not np.isscalar(scale) else (scale,) * arr.ndim
        viewer.add_image(arr, **kw)
    return viewer


# ──────────────────────────────────────────────────────────────────────
# Cross-datapoint metric summary (across rows of the combined metrics CSV)
# ──────────────────────────────────────────────────────────────────────

# Headline scalar metrics to plot by default (only those present are used).
DEFAULT_SUMMARY_METRICS = [
    "largest_crop_vf", "surface-area",
    "teasar_skeleton_length", "teasar_number_branches",
    "teasar_branch_distance_mean", "teasar_branch_tortuosities_mean",
    "teasar_local_thickness_mean",
    "lee_skeleton_length", "lee_number_branches",
    "pore.inscribed_diameter_mean", "pore.volume_mean",
]


def plot_metric_summary(df, columns: Optional[Sequence[str]] = None, *,
                        kind: str = "bar", label_col: str = "filename",
                        ncols: int = 3, output_folder: Optional[str] = None,
                        save_name: Optional[str] = None, figsize=None,
                        show: bool = True):
    """Plot scalar metrics across every row (datapoint) of a metrics table.

    Each subplot is one metric; the comparison is *across datapoints* (the rows
    produced by :func:`iuquant.make_measurements` / saved by ``save_metrics_csv``).

    Parameters
    ----------
    df : DataFrame | str
        The combined metrics table, or a path to the metrics CSV.
    columns : list of str, optional
        Which metric columns to plot. Defaults to the headline metrics in
        :data:`DEFAULT_SUMMARY_METRICS` that are present, else the first dozen
        numeric columns.
    kind : {"bar", "box", "hist"}
        ``bar`` = one bar per datapoint (compare samples); ``box`` = a boxplot of
        the metric's spread across datapoints with the individual points
        overlaid; ``hist`` = histogram of the metric across datapoints.
    label_col : str
        Column used for per-datapoint x labels (``bar``). Defaults to ``filename``.
    output_folder : str, optional
        If given, save the figure there as ``metric_summary_<kind>.png``.

    Returns the matplotlib ``Figure`` (or ``None`` if there's nothing to plot).
    """
    import os
    import pandas as pd

    if isinstance(df, str):
        df = pd.read_csv(df)
    if df is None or len(df) == 0:
        print("plot_metric_summary: empty table, nothing to plot.")
        return None
    if kind not in ("bar", "box", "hist"):
        raise ValueError(f"kind must be 'bar', 'box' or 'hist', got {kind!r}")

    if columns is None:
        columns = [c for c in DEFAULT_SUMMARY_METRICS if c in df.columns]
        if not columns:
            skip = {"conv_factor", "prop_of_1000cube"}
            columns = [c for c in df.select_dtypes("number").columns
                       if c not in skip][:12]
    columns = [c for c in columns if c in df.columns]
    if not columns:
        print("plot_metric_summary: none of the requested columns are present.")
        return None

    labels = ([str(x) for x in df[label_col]] if label_col in df.columns
              else [str(i) for i in range(len(df))])
    x = np.arange(len(df))

    n = len(columns)
    ncols = max(1, min(ncols, n))
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=figsize or (5 * ncols, 3.6 * nrows),
                             squeeze=False)

    for idx, col in enumerate(columns):
        ax = axes[idx // ncols][idx % ncols]
        vals = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        finite = vals[np.isfinite(vals)]
        if finite.size == 0:
            ax.set_title(f"{col}\n(no numeric data)", fontsize=9)
            ax.axis("off")
            continue
        if kind == "bar":
            ax.bar(x, np.nan_to_num(vals, nan=0.0))
            ax.set_xticks(x)
            ax.set_xlabel('scan ID')
            ax.set_xticklabels(labels,  fontsize=7)
            ax.set_ylabel("value")
        elif kind == "box":
            ax.boxplot(finite, positions=[1], widths=0.5)
            jit = (1 + np.linspace(-0.15, 0.15, finite.size)
                   if finite.size > 1 else np.array([1.0]))
            ax.scatter(jit, finite, s=14, alpha=0.6, zorder=3)
            ax.set_xticks([1])
            ax.set_xticklabels([f"n={finite.size}"], fontsize=8)
        else:  # hist
            ax.hist(finite, bins=_auto_bins(finite))
            ax.set_xlabel(col)
            ax.set_ylabel("count")
        ax.set_title(col, fontsize=9)

    for j in range(n, nrows * ncols):          # blank any unused axes
        axes[j // ncols][j % ncols].axis("off")

    fig.suptitle(f"Metric summary across {len(df)} datapoint(s) — {kind}",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
        path = os.path.join(output_folder, save_name or f"metric_summary_{kind}.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"Saved metric summary: {path}")
    if show:
        plt.show()
    return fig
