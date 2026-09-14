"""Read TIFF label volumes and extract random crops of a fixed size."""

from pathlib import Path

import numpy as np
import tifffile


def random_crop(volume, crop_size, rng):
    """Return one random crop of shape `crop_size` from `volume`.

    Both are interpreted as (Z, Y, X). If the volume is smaller than the
    crop along any axis, an error is raised.
    """
    if any(v < c for v, c in zip(volume.shape, crop_size)):
        raise ValueError(f"volume {volume.shape} smaller than crop {crop_size}")

    starts = [rng.integers(0, v - c + 1) for v, c in zip(volume.shape, crop_size)]
    slices = tuple(slice(s, s + c) for s, c in zip(starts, crop_size))
    return volume[slices]


def crop_volume_file(path, crop_size, n_crops, out_dir, rng):
    """Load a TIFF volume and write `n_crops` random crops to `out_dir`."""
    volume = tifffile.imread(path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(path).stem
    for i in range(n_crops):
        crop = random_crop(volume, crop_size, rng)
        out_path = out_dir / f"{stem}_crop{i:03d}.tif"
        tifffile.imwrite(out_path, crop)
        print(f"wrote {out_path}  shape={crop.shape}  dtype={crop.dtype}")


if __name__ == "__main__":
    # --- configure here ---
    input_dir = "c:\\work\\embo\\batch\\"          # folder of .tif/.tiff label volumes
    output_dir = "c:\\work\\embo\\batch\\"
    crop_size = (256, 256, 256)     # (Z, Y, X)
    crops_per_volume = 1
    seed = 0
    # ----------------------

    rng = np.random.default_rng(seed)
    files = sorted(Path(input_dir).glob("*.tif*"))
    if not files:
        raise SystemExit(f"no .tif/.tiff files found in {input_dir!r}")

    for f in files:
        crop_volume_file(f, crop_size, crops_per_volume, output_dir, rng)