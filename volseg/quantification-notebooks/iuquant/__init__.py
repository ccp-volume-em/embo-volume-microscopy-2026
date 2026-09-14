"""iuquant — placenta (villi / IVS / vessel) segmentation quantification.



"""
from __future__ import annotations

from .io import list_segmentations, load_and_crop, unique_labels, upsample
from .metrics import collect_metrics, metrics_to_dataframe, save_metrics_csv
from .preprocess import PreprocessSettings, preprocess_mask
from .pipeline import QuantSettings, VolumeResult, make_measurements
from .stats import array_summary_stats, calc_vf
from .viz import plot_metric_summary, show_images, view_maps
from .volume_fraction import VFResult, analyze_volume_fractions

__all__ = [
    # quantification
    "QuantSettings", "VolumeResult", "make_measurements",
    "PreprocessSettings", "preprocess_mask",
    "collect_metrics", "metrics_to_dataframe", "save_metrics_csv",
    # volume / area fractions
    "analyze_volume_fractions", "VFResult",
    # io + helpers
    "list_segmentations", "load_and_crop", "unique_labels", "upsample",
    "calc_vf", "array_summary_stats", "show_images", "view_maps",
    "plot_metric_summary",
]
