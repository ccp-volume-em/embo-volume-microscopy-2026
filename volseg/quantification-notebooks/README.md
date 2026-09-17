# EMBO Notebook

Quantification of placenta segmentations (villi / intervillous space (not included) / vessels).

Data is in `villi` and `vessel` folders. 

Create a new environment using Python 3.12.
Install dependencies. `pip install -r requirements-combined.txt`

See `Quantification.ipynb` for a worked, end-to-end example. 

## Repository Layout

### `notebooks/`
| folder | what it holds |
|---|---|
| `iuquant/` | Core Python package for quantification |
| `vessel/` | Vessel segmentations |
| `villi/` | Villi segmentation |

### `iuquant` folder layout
| module | what it holds |
|---|---|
| `stats.py` | `calc_vf`, summary stats, inf filters (pure numpy/scipy) |
| `io.py` | load/crop/downsample/upsample TIFFs, binary masks, filenames, save TIFF |
| `preprocess.py` | `PreprocessSettings` + `preprocess_mask`: median / morphology / small-hole filling / size-based filters |
| `measures.py` | marching-cubes `surface_area`, PoreSpy `local_thickness` |
| `skeleton.py` | TEASAR + Lee skeletons, tortuosity, branching angles, `skeleton_stats` |
| `porenetwork.py` | PoreSpy SNOW2 + OpenPNM pore/throat network |
| `metrics.py` | `collect_metrics` (all metric columns) + CSV writers |
| `viz.py` | slice/thickness/histogram figures, `plot_metric_summary` (cross-datapoint), napari `view_maps` |
| `pipeline.py` | `QuantSettings` + `make_measurements` orchestrator |
| `volume_fraction.py` | VF-vs-ROI-size, area-fraction-by-slice, montages |

### Root-level files
| file | what it holds |
|---|---|
| `crop_vol.py` | Standalone script to crop a volume (TIFF stack) down to an ROI before running the pipeline |
| `Files-Description.md` | This file describes the repo layout |
| `README.md` | Project overview / setup instructions |
| `requirements-combined.txt` | Combined pip dependency list for the `iuquant` environment |
| `sample_123531_IMAGE.tiff` | Sample image volume for testing the pipeline |
| `sample_123642_IMAGE.tiff` | Sample image volume for testing the pipeline |
| `sample_123761_IMAGE.tiff` | Sample image volume for testing the pipeline |
| `measurement.ipynb` | exploratory data analysis notebook (plotting/inspecting results from quantification) |
| `Quantification.ipynb` | Main quantification notebook; runs the end-to-end quantification pipeline across multiple samples |