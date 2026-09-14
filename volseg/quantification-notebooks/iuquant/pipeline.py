"""Top-level quantification pipeline.

    for each file:
        read + crop once
        for each (label, binary mask):
            downsample -> local thickness -> skeletons -> surface area
                       -> pore network -> collect metrics -> save -> visualise

Single-label is just the special case of one mask = "all foreground" (optionally
inverted for IVS). 
"""
from __future__ import annotations

import os
import pickle
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import io, measures, metrics, porenetwork, preprocess, skeleton, viz
from .preprocess import PreprocessSettings
from .skeleton import DEFAULT_DUST_THRESHOLD, DEFAULT_TEASAR_PARAMS


@dataclass
class QuantSettings:
    """Configuration for :func:`make_measurements`.

    Measurement toggles
        local_thickness, skeletonization, surface_area, pore_network
    Processing
        ds              integer downsample factor
        conv_factor     micrometres per (original) voxel
        crop            ``[z0,z1,y0,y1,x0,x1]`` or ``None`` for the whole volume
        multilabel      analyse each integer label separately
        calc_ivs        invert the mask (measure intervillous space) -- whole
                        foreground mode only
        preprocess      :class:`PreprocessSettings` — optional median /
                        morphology / size-based component filtering applied to
                        the full-res binary mask before downsampling (off by
                        default)
        from_scratch    compute maps, or reload previously-saved ones
        save_maps       write ALL on-disk artefacts (crops, skeletons,
                        thickness, pore regions, skeleinfo CSVs, figures);
                        False = compute metrics in-memory, write nothing
        upscale_maps    nearest-neighbour upsample the returned ``maps`` back to
                        the full-resolution (cropped) frame so they align with
                        ``r.mask`` / the original image in napari. Only affects
                        the in-memory ``VolumeResult.maps`` (saved TIFFs and
                        metrics stay at the downsampled resolution).
        output_dir      where artefacts go (``None`` = next to the source file)
    Tunables
        lt_sizes, teasar_params, dust_threshold, slice_idx
    """
    local_thickness: bool = True
    skeletonization: bool = True
    surface_area: bool = True
    pore_network: bool = True
    save_maps: bool = False
    upscale_maps: bool = False
    from_scratch: bool = True
    ds: int = 1
    conv_factor: float = 0.8125
    multilabel: bool = False
    calc_ivs: bool = False
    preprocess: PreprocessSettings = field(default_factory=PreprocessSettings)
    crop: Optional[Sequence[int]] = None
    output_dir: Optional[str] = None
    lt_sizes: int = 100
    teasar_params: Dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_TEASAR_PARAMS))
    dust_threshold: int = DEFAULT_DUST_THRESHOLD
    teasar_parallel: int = 1   # kimimaro workers; 0 = all cores (Linux only — see skeletonize_teasar)
    skeletonize_kwargs: Dict[str, Any] = field(default_factory=dict)  # extra kimimaro.skeletonize opts
    slice_idx: int = 10

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "QuantSettings":
        """Build from the original notebook's settings dict (``calc_IVS`` alias
        accepted)."""
        d = dict(d)
        if "calc_IVS" in d:
            d.setdefault("calc_ivs", d.pop("calc_IVS"))
        if isinstance(d.get("preprocess"), dict):
            d["preprocess"] = PreprocessSettings.from_dict(d["preprocess"])
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class VolumeResult:
    """Outcome for one analysed binary volume.

    ``mask`` is the full-resolution binary mask actually measured — i.e. after
    cropping, label selection / IVS inversion **and preprocessing**. It is kept
    so the same cleaned data can be fed straight into
    :func:`iuquant.analyze_volume_fractions` (with ``fg_idx=1``). For very large
    volumes you can ``del r.mask`` once you no longer need it to free memory.
    """
    image: str
    label: Optional[int]
    metrics: Dict[str, Any]
    maps: Dict[str, np.ndarray] = field(default_factory=dict)
    mask: Optional[np.ndarray] = None



# Per-map compute-or-load helpers



def _local_thickness(mask, base, s: QuantSettings):
    if not s.local_thickness:
        return None
    if s.from_scratch:
        print("Calculating local thickness.")
        return measures.local_thickness(mask, sizes=s.lt_sizes)
    import tifffile
    # Keep the float radii on reload — the original ``.astype(int)`` truncated
    # the thickness map, so reloaded stats disagreed with freshly computed ones.
    return tifffile.imread(f"{base}_LT.tif")


def _skeletons(mask, base, s: QuantSettings):
    if not s.skeletonization:
        return None, None
    if s.from_scratch:
        print("Skeletonising (TEASAR + Lee).")
        teasar = skeleton.skeletonize_teasar(mask, s.teasar_params, s.dust_threshold,
                                             parallel=s.teasar_parallel,
                                             **s.skeletonize_kwargs)
        lee = skeleton.skeletonize_lee(mask)
        return teasar, lee
    import tifffile
    return (tifffile.imread(f"{base}_TEASARSKELETON.tif").astype(int),
            tifffile.imread(f"{base}_LEESKELETON.tif").astype(int))


def _pore_network(img, base, s: QuantSettings):
    if not s.pore_network:
        return None, None
    if s.from_scratch:
        print("Extracting pore network.")
        snow, pn = porenetwork.pore_network(img)
        if s.save_maps:
            with open(f"{base}_PORESPY.pickle", "wb") as fh:
                pickle.dump(snow, fh)
        return snow, pn
    import openpnm as op
    with open(f"{base}_PORESPY.pickle", "rb") as fh:
        snow = pickle.load(fh)
    return snow, op.io.network_from_porespy(snow.network)


def _save_maps(base, fullname, teasar, lee, lt, snow, s: QuantSettings) -> None:
    if not s.save_maps:
        return
    if s.from_scratch:
        if teasar is not None:
            io.save_tiff(teasar, f"{base}_TEASARSKELETON.tif")
        if lee is not None:
            io.save_tiff(lee, f"{base}_LEESKELETON.tif")
        if lt is not None:
            io.save_tiff(lt, f"{base}_LT.tif")
    if snow is not None:
        io.save_tiff(snow.regions, f"{base}_PORESPY.tif")


def _save_skeleinfo(base, fullname, teasar_bundle, lee_bundle) -> None:
    import pandas as pd
    src = os.path.basename(fullname)
    if teasar_bundle is not None:
        pd.DataFrame(teasar_bundle[3]).to_csv(f"{base}_TEASAR_skeleinfo_{src}.csv")
    if lee_bundle is not None:
        pd.DataFrame(lee_bundle[3]).to_csv(f"{base}_Lee_skeleinfo_{src}.csv")



# Core per-mask processing


def _process_mask(name: str, fullname: str, label: Optional[int],
                  mask_full: np.ndarray, original_shape, s: QuantSettings,
                  output_dir: Optional[str]) -> VolumeResult:
    base = io.base_filename(fullname, output_dir)
    if s.save_maps:
        io.save_tiff(mask_full, f"{base}_SEG_CROP.tif")

    img = io.downsample(mask_full, s.ds)
    print(f"  downsampled shape {img.shape}  ({np.prod(img.shape) / 1000 ** 3:.4f} of a 1000³ cube)")

    lt = _local_thickness(img, base, s)
    teasar_skel, lee_skel = _skeletons(img, base, s)
    # An all-empty skeleton (e.g. parameters that prune everything) is treated as
    # absent so skeleton_stats / collect_metrics don't choke on a 0-branch skan.
    if teasar_skel is not None and not teasar_skel.any():
        teasar_skel = None
    if lee_skel is not None and not lee_skel.any():
        lee_skel = None
    # Surface area on the same downsampled grid as the rest of the geometry
    # (scaled by (ds*conv)**2 in collect_metrics); see metrics module docstring.
    surface = measures.surface_area(img) if s.surface_area else None
    snow, pn = _pore_network(img, base, s)

    teasar_bundle = skeleton.skeleton_stats(teasar_skel, lt) if teasar_skel is not None else None
    lee_bundle = skeleton.skeleton_stats(lee_skel, lt) if lee_skel is not None else None

    md = metrics.collect_metrics(
        name, original_shape, img, mask_full, crop=s.crop, ds=s.ds,
        conv_factor=s.conv_factor, teasar=teasar_bundle, lee=lee_bundle,
        surface_area=surface, pn=pn,
    )


    if s.save_maps:
        _save_maps(base, fullname, teasar_skel, lee_skel, lt, snow, s)
        _save_skeleinfo(base, fullname, teasar_bundle, lee_bundle)
        viz.save_visualizations(
            base, img=img, thickness=lt, skeleton=teasar_skel, pn=pn, snow=snow,
            teasar_tort=teasar_bundle[1] if teasar_bundle else None,
            lee_tort=lee_bundle[1] if lee_bundle else None,
            ds=s.ds, conv_factor=s.conv_factor, slice_idx=s.slice_idx,
        )

    maps = {k: v for k, v in (("thickness", lt), ("teasar", teasar_skel),
                              ("lee", lee_skel),
                              ("pore_regions", snow.regions if snow else None))
            if v is not None}
    if s.upscale_maps:
        # Upsample each map back to the full-res (cropped) frame so napari can
        # overlay them on r.mask / the original image. View-only — does not
        # touch the saved TIFFs or the computed metrics.
        maps = {k: io.upsample(v, s.ds, mask_full.shape) for k, v in maps.items()}
    return VolumeResult(image=name, label=label, metrics=md, maps=maps,
                        mask=mask_full)


def _iter_label_masks(raw: np.ndarray, s: QuantSettings):
    """Yield ``(label, full_res_binary_mask)`` for each thing to analyse."""
    if s.multilabel:
        labels = np.unique(raw)
        for label in labels[labels > 0]:
            yield int(label), io.binary_mask(raw, label=int(label))
    else:
        yield None, io.binary_mask(raw, label=None, calc_ivs=s.calc_ivs)


def make_measurements(names: Sequence[Tuple[str, str]],
                      settings: Optional[QuantSettings] = None) -> List[VolumeResult]:
    """Run the full pipeline over ``(basename, fullpath)`` pairs.

    Returns a list of :class:`VolumeResult` (one per image, or per label in
    multilabel mode). Use :func:`iuquant.metrics.save_metrics_csv` on
    ``[r.metrics for r in results]`` for a combined CSV.
    """
    s = settings or QuantSettings()
    if isinstance(s, dict):
        s = QuantSettings.from_dict(s)

    enabled = [k for k in ("local_thickness", "skeletonization", "surface_area",
                           "pore_network") if getattr(s, k)]
    print(f"Processing {len(names)} scan(s). Enabled: {', '.join(enabled) or 'none'}")
    print(f"  ds={s.ds} conv_factor={s.conv_factor} crop={s.crop} "
          f"multilabel={s.multilabel} calc_ivs={s.calc_ivs} from_scratch={s.from_scratch}")
    print(f"  preprocess: {s.preprocess.describe()}")

    results: List[VolumeResult] = []
    for basename, fullname in names:
        print(f"\nReading {fullname}")
        raw = io.load_and_crop(fullname, s.crop)
        original_shape = raw.shape
        for label, mask_full in _iter_label_masks(raw, s):
            if s.preprocess.enabled:
                before = int(mask_full.sum())
                mask_full = preprocess.preprocess_mask(mask_full, s.preprocess)
                after = int(mask_full.sum())
                print(f"  preprocess label {label}: {before} -> {after} fg voxels "
                      f"({100 * after / before:.1f}% kept)" if before else
                      f"  preprocess label {label}: empty input")
            if mask_full.sum() == 0:
                print(f"  label {label}: empty mask, skipping.")
                continue
            name = basename if label is None else f"{basename}_label_{label}"
            out_dir = (io.label_directory(fullname, label, s.output_dir)
                       if (s.multilabel and label is not None) else s.output_dir)
            print(f"  analysing {name}")
            results.append(_process_mask(name, fullname, label, mask_full,
                                         original_shape, s, out_dir))
    return results
