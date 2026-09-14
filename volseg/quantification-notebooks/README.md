# EMBO Notebook

Quantification of placenta segmentations (villi / intervillous space (not included) / vessels).


Data is in villi, vessel and villi_batch folders. Villi batch example is currently only 2 files.

Create a new environment using Python 3.12. 
Install dependencies. `pip install -r requirements-combined.txt`

See `WL_IU_Quantification_main.ipynb` for a worked, end-to-end example. The Villi and Vessel notebook have been combined into this one notebook. The IVS notebook can be created easily by setting the calc_ivs=True, but that hasn't been done yet.


## iuquant Layout

| module | what it holds |
|---|---|
| `stats.py` | `calc_vf`, summary stats, inf filters (pure numpy/scipy) |
| `io.py` | load/crop/downsample/upsample TIFFs, binary masks, filenames, save TIFF |
| `preprocess.py` | `PreprocessSettings` + `preprocess_mask`: median / morphology / small-hole filling / size-based component filtering on the full-res mask |
| `measures.py` | marching-cubes `surface_area`, PoreSpy `local_thickness` |
| `skeleton.py` | TEASAR + Lee skeletons, tortuosity, branching angles, `skeleton_stats` |
| `porenetwork.py` | PoreSpy SNOW2 + OpenPNM pore/throat network |
| `metrics.py` | `collect_metrics` (all metric columns) + CSV writers |
| `viz.py` | slice/thickness/histogram figures, `plot_metric_summary` (cross-datapoint), napari `view_maps` |
| `pipeline.py` | `QuantSettings` + `make_measurements` orchestrator |
| `volume_fraction.py` | VF-vs-ROI-size, area-fraction-by-slice, montages |


## iuquant Usage

```python
from iuquant import QuantSettings, make_measurements, save_metrics_csv, list_segmentations
names = list_segmentations("/path/to/segs")
settings = QuantSettings(ds=2, conv_factor=1.0, crop=[500, 900, 500, 900, 500, 900],
                         calc_ivs=True, save_maps=True)
results = make_measurements(names, settings)
save_metrics_csv([r.metrics for r in results], "metrics.csv")
```

```python
from iuquant import analyze_volume_fractions
analyze_volume_fractions(names, output_folder="vfaf_out", roi_sizes=[150, 250, 350, 450])
```

