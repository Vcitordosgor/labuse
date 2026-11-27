import numpy as np
from shapely.geometry import Polygon

from labuse.gabarit.relief_pdf import _altitudes, _polygones, vue_relief_pdf


def test_projection_utilise_les_faces_du_pilote_et_conserve_la_lacune():
    # La première maille comporte deux plans de pente distincte. La suivante a une demi-maille absente.
    faces = {"pas_m": 1, "vertices": [[0, 1, 10], [1, 1, 12], [0, 0, 8], [1, 0, 9],
                                      [2, 1, 16], [2, 0, 12]],
             "triangles": [[0, 1, 3], [0, 3, 2], [1, 4, 5]]}
    x = np.array([0.75, 0.25, 1.75, 1.25, -1])
    y = np.array([0.75, 0.25, 0.75, 0.25, 0.5])
    z, _ = _altitudes(faces, x, y)
    np.testing.assert_allclose(z, [10.75, 8.75, 14, np.nan, np.nan], equal_nan=True)


def test_empreinte_imprimee_conserve_les_cours_et_le_precision_des_reculs():
    contour = [(0, 0), (8.003, 0), (8, 10), (0, 10)]
    cour = [(1, 1), (3, 1), (3, 3), (1, 3)]
    bati, = _polygones([{"ext": contour, "trous": [cour]}])
    assert bati.equals_exact(Polygon(contour, [cour]), 0)
    assert vue_relief_pdf({"disponible": False}, None) is None
