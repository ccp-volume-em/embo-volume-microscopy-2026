"""Pore / throat network extraction via PoreSpy (SNOW2) + OpenPNM.

The network is computed on the (downsampled) binary image, so its geometric properties are in that frame's
voxel units and scaled to physical units downstream.
"""
from __future__ import annotations

from typing import Any, Tuple

import numpy as np


def pore_network(img: np.ndarray) -> Tuple[Any, Any]:
    """Extract a pore network.

    Returns ``(snow_result, pn)`` where ``snow_result`` is the raw PoreSpy
    SNOW2 result (carries ``.regions`` for visualisation) and ``pn`` is the
    OpenPNM network with ``pore.*`` / ``throat.*`` property arrays.
    """
    import openpnm as op
    import porespy as ps

    snow = ps.networks.snow2(phases=img.astype(int), boundary_width=0)
    pn = op.io.network_from_porespy(snow.network)
    return snow, pn
