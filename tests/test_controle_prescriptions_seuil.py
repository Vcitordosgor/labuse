"""MISE-EN-LIGNE-7 LOT 2 — régression du plancher de bruit du contrôle indépendant.

Le contrôle « qui fait foi » comparait des polygones par différence d'aire. La différence de deux
polygones quasi-coïncidents rend souvent une GeometryCollection (polygones + bouts de lignes) : son
geom_type n'est NI « Multi… » NI « Polygon », donc l'ancien filtre la gardait EN BLOC, contournant le
plancher de 200 m² → 6 fausses « DIFFÉRENT » (slivers de 35–560 m²). On verrouille le correctif :
seules les composantes POLYGONALES au-dessus du plancher comptent."""
import importlib.util
import pathlib

from shapely.geometry import GeometryCollection, LineString, Polygon

_mod_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "controle_prescriptions_gpu.py"
_spec = importlib.util.spec_from_file_location("controle_prescriptions_gpu", _mod_path)
cpg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpg)


def _carre_m2(m2: float) -> Polygon:
    # côté en degrés pour une aire ~ m2 (K = deg²→m²) : côté = sqrt(m2/K)
    cote = (m2 / cpg.K) ** 0.5
    return Polygon([(0, 0), (cote, 0), (cote, cote), (0, cote)])


def test_sliver_sous_plancher_ecarte():
    petit = _carre_m2(50)        # 50 m² < 200 → bruit
    assert cpg._sig_components(petit) == []


def test_polygone_au_dessus_plancher_garde():
    gros = _carre_m2(500)        # 500 m² > 200 → vrai objet
    assert len(cpg._sig_components(gros)) == 1


def test_geometrycollection_est_mise_a_plat_et_filtree():
    # une GeometryCollection (polygone sous plancher + ligne) ne doit RIEN rendre : c'était la faille.
    gc = GeometryCollection([_carre_m2(35), LineString([(0, 0), (1, 1)])])
    assert cpg._sig_components(gc) == []


def test_geometrycollection_garde_le_gros_polygone():
    gc = GeometryCollection([_carre_m2(300), LineString([(0, 0), (1, 1)]), _carre_m2(10)])
    comps = cpg._sig_components(gc)
    assert len(comps) == 1               # le 300 m² gardé, le 10 m² et la ligne écartés
