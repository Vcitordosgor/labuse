from io import BytesIO
from math import pi

import numpy as np
from PIL import Image
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

from labuse.gabarit.relief_carte import tuile
from labuse.gabarit.scene import _polys_local


def test_recul_minces_sans_perte_de_topologie():
    x, y = 336000, 7689000
    parc = Polygon([(x, y), (x + 12, y + 1), (x + 12, y + 1.002), (x, y)])
    local, = _polys_local(parc, x, y)
    assert Polygon(local["ext"]).is_valid
    assert Polygon([(x + i, y + j) for i, j in local["ext"]]).equals_exact(parc, 0.0)


def test_tuile_sur_les_noeuds_maplibre_et_repli_nodata(tmp_path):
    z, x, y = 16, 42868, 36744
    demi = pi * 6378137
    cote = 2 * demi / 2**z
    pas = cote / 512
    tr = from_origin(-demi + x * cote - pas / 2, demi - y * cote + pas / 2, pas, pas)
    grille = np.indices((512, 512), dtype='float32')[1] / 4 - 12
    fonds = []
    for nom, valeurs in [('regional', np.full_like(grille, 80)), ('fin', grille)]:
        valeurs = valeurs.copy()
        if nom == 'fin':
            valeurs[100:105, 200:205] = -9999
        p = tmp_path / f'{nom}.tif'
        with rasterio.open(p, 'w', driver='GTiff', count=1, height=512, width=512,
                           crs='EPSG:3857', transform=tr, dtype='float32', nodata=-9999) as ds:
            ds.write(valeurs, 1)
        fonds.append((p, p.stat().st_mtime_ns))
    image = np.asarray(Image.open(BytesIO(tuile(tuple(fonds), z, x, y)))).astype('int32')
    altitude = image[:, :, 0] * 256 + image[:, :, 1] + image[:, :, 2] / 256 - 32768
    assert altitude[102, 202] == 80
    np.testing.assert_allclose(altitude[250], grille[250], atol=1/256)
    with pytest.raises(ValueError):
        tuile(tuple(fonds), z, 2**z, y)
