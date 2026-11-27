import io

import numpy as np
import pytest
import rasterio
from fastapi import HTTPException
from PIL import Image
from rasterio.transform import from_bounds
from shapely.geometry import box

from labuse.api import relief


def test_tuile_lidar_et_repli_par_pixel(tmp_path, monkeypatch):
    z, x, y = 18, 171434, 146628
    bounds = relief._tuile_bounds(z, x, y)
    monkeypatch.setattr(relief, "_ile", lambda: box(*bounds).buffer(1))
    fin, large = tmp_path / "fin.tif", tmp_path / "large.tif"
    nord = np.full((512, 512), 404.125, dtype="float32")
    nord[256:, :] = 398.5
    nord[200:220, 100:120] = -9999
    for path, a in [(fin, nord), (large, np.full_like(nord, 401.25))]:
        with rasterio.open(path, "w", driver="GTiff", width=512, height=512, count=1,
                           crs="EPSG:3857", transform=from_bounds(*bounds, 512, 512),
                           dtype="float32", nodata=-9999) as ds:
            ds.write(a, 1)
    from types import SimpleNamespace
    monkeypatch.setattr(relief, "get_settings", lambda: SimpleNamespace(
        mnt1m_cog_file=tmp_path / "absent", mnt5m_file=large))
    monkeypatch.setattr(relief.sol, "obtenir_fenetre", lambda *a, **kw: (fin, "copie"))
    data, sources = relief._tuile.__wrapped__(z, x, y, 0)
    assert sources == "lidar-0.5m+rge-5m"
    rgb = np.asarray(Image.open(io.BytesIO(data)), dtype=float)
    hauteurs = rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256 - 32768
    assert hauteurs[0, 0] == 404.125
    assert hauteurs[-1, -1] == 398.5
    assert hauteurs[210, 110] == 401.25


def test_zoom_invalide():
    with pytest.raises(HTTPException) as exc:
        relief.relief(20, 0, 0)
    assert exc.value.status_code == 404


@pytest.mark.parametrize("lacune_interieure", [False, True])
def test_raccord_cotier_limite_aux_cellules_proches(tmp_path, monkeypatch, lacune_interieure):
    from types import SimpleNamespace

    z, x, y = 15, 21416, 18356
    ouest, sud, est, nord = relief._tuile_bounds(z, x, y)
    t = from_bounds(ouest, sud, est, nord, 512, 512)
    cote = ouest + 128 * t.a
    monkeypatch.setattr(relief, "_ile", lambda: box(cote, sud - 100, est + 100, nord + 100))
    raster = np.full((512, 512), 3.25, dtype="float32")
    raster[:, :132] = -9999
    if lacune_interieure:
        raster[256, 256] = -9999
    path = tmp_path / "rge.tif"
    with rasterio.open(path, "w", driver="GTiff", width=512, height=512, count=1,
                       crs="EPSG:3857", transform=t, dtype="float32", nodata=-9999) as ds:
        ds.write(raster, 1)
    monkeypatch.setattr(relief, "get_settings", lambda: SimpleNamespace(mnt5m_file=path))
    if lacune_interieure:
        with pytest.raises(HTTPException) as exc:
            relief._tuile.__wrapped__(z, x, y, 0)
        assert exc.value.status_code == 503
    else:
        data, _ = relief._tuile.__wrapped__(z, x, y, 0)
        pixels = Image.open(io.BytesIO(data))
        assert pixels.getpixel((128, 256)) == pixels.getpixel((132, 256)) == (128, 3, 64)
        assert pixels.getpixel((127, 256)) == (128, 0, 0)
