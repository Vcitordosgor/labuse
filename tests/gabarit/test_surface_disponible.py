import pytest
from shapely.geometry import box, mapping

from labuse.gabarit._geom import to_wgs
from labuse.gabarit.builder import deduire_bati_de_zone
from labuse.gabarit.contract import GabaritResult
from labuse.gabarit.plan_svg import _bati_features


def rectangle(x, y, xmax, ymax):
    return mapping(to_wgs(box(336000 + x, 7689000 + y, 336000 + xmax, 7689000 + ymax)))


@pytest.mark.parametrize(("batiment", "reste"), [
    ((-1, -1, 11, 11), 0),
    ((12, 0, 18, 10), 80),
    ((-1, -1, 5, 11), 40),
])
def test_surface_disponible_a_echelle_constante(batiment, reste):
    resultat = GabaritResult(
        status="ok", zoneImplantationM2=80, zoneImplantationGeoJSON=rectangle(0, 0, 10, 10),
        contourGeoJSON=rectangle(-2, -2, 20, 20), hauteurReglementaireM=7, plafondEmpriseM2=50,
        batiExistantGeoJSON={"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": rectangle(*batiment), "properties": {}},
        ]},
    )
    deduire_bati_de_zone(resultat)
    assert resultat.zoneImplantationM2 == reste
    assert resultat.batiDeduitM2 == 80 - reste
    assert bool(resultat.zoneImplantationGeoJSON) == bool(reste)
    if not reste:
        assert resultat.hauteurReglementaireM is None
        assert resultat.plafondEmpriseM2 is None
        assert "bâti conservé" in resultat.terrainNote


@pytest.mark.parametrize(("props", "attendu"), [
    ({"h_source": "lidar", "hauteur_m": 12, "hauteur_bdtopo_m": 4}, 4),
    ({"h_source": "lidar", "hauteur_m": 12}, 0),
    ({"h_source": "bdtopo", "hauteur_m": 6}, 6),
    ({}, 0),
])
def test_pdf_hauteur_propre_au_batiment(props, attendu):
    geom = rectangle(0, 0, 5, 5)
    assert _bati_features({"features": [{"geometry": geom, "properties": props}]}) == [(geom, attendu)]


def test_cache_scene_expire_apres_modification(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from labuse.gabarit import scene

    temps = [0]
    donnees = ["première version"]
    monkeypatch.setattr(scene, "_MEMO", {})
    settings = SimpleNamespace(mnt1m_cog_file=tmp_path / "fond", mnt5m_file=tmp_path / "regional")
    monkeypatch.setattr(scene, "get_settings", lambda: settings)
    monkeypatch.setattr(scene, "monotonic", lambda: temps[0])
    monkeypatch.setattr(scene, "_build_scene", lambda db, idu: donnees[0])
    assert scene.build_scene(None, "A") == "première version"
    donnees[0] = "nouvelle version"
    assert scene.build_scene(None, "A") == "première version"
    temps[0] += scene._SCENE_TTL_S
    assert scene.build_scene(None, "A") == "nouvelle version"
    donnees[0] = "fond régional installé"
    settings.mnt5m_file.touch()
    assert scene.build_scene(None, "A") == "fond régional installé"


def test_morceaux_disjoints_et_cour():
    from shapely.geometry import MultiPolygon
    from labuse.gabarit.builder import surfaces_continues
    from labuse.gabarit.scene import _empreintes_metriques
    ext = box(0, 0, 10, 10)
    cour = box(2, 2, 8, 8)
    bati, = _empreintes_metriques([{"empreinte": [{"ext": list(ext.exterior.coords),
                              "trous": [list(cour.exterior.coords)]}]}], 336000, 7689000)
    assert bati.area == 64
    parc = MultiPolygon([bati, box(336020, 7689000, 336026, 7689006)])
    assert surfaces_continues(mapping(to_wgs(parc)), 80) == [51.2, 28.8]


def test_plan_pilote_reculs_et_exclusions():
    from labuse.gabarit.coupe_svg import plan_cle_svg
    poly = {"ext": list(box(0, 0, 10, 10).exterior.coords), "trous": []}
    svg = plan_cle_svg({"contour_cadastral": [poly], "reculs": [poly], "exclusions": [poly]})
    assert 'data-couche="reculs"' in svg and 'data-couche="exclusions"' in svg


def test_solde_deduit_tout_le_bati_conserve_sur_assiette_sans_doubles():
    from labuse.gabarit.builder import renseigner_emprise_projet
    from labuse.gabarit._geom import shape_from_geojson, to_metric
    # Les deux empreintes chevauchent la limite de l’assiette et se recouvrent sur 10 m².
    empreintes = [rectangle(-2, 0, 7, 5), rectangle(5, 0, 14, 5)]
    gr = GabaritResult(status="ok", surfaceParcelleM2=100, contourGeoJSON=rectangle(0, 0, 10, 10),
                       zoneImplantationM2=50, zoneImplantationGeoJSON=rectangle(0, 5, 10, 10),
                       hauteurReglementaireM=6.5, plafondEmpriseM2=70,
                       batiExistantGeoJSON={"features": [{"geometry": g} for g in empreintes]})
    renseigner_emprise_projet(gr)
    assert gr.batiConserveM2 == 50 and gr.empriseSupplementaireM2 == 20
    exemple = to_metric(shape_from_geojson(gr.exempleEmpriseGeoJSON))
    assert exemple.area == pytest.approx(20, abs=.01)
    assert gr.exempleEmpriseM2 == 20
    assert exemple.difference(to_metric(shape_from_geojson(gr.zoneImplantationGeoJSON))).area < 1e-6
    gr.plafondEmpriseM2 = 45
    renseigner_emprise_projet(gr)
    assert gr.zoneImplantationM2 == 50 and gr.empriseSupplementaireM2 == 0
    assert gr.exempleEmpriseGeoJSON is None


def test_exemple_sur_un_seul_morceau_en_conservant_la_cour():
    from shapely.geometry import MultiPolygon, shape
    from labuse.gabarit.builder import renseigner_emprise_projet
    from labuse.gabarit._geom import to_metric

    cour = shape(rectangle(2, 2, 4, 4))
    principal = shape(rectangle(0, 0, 10, 10)).difference(cour)
    zone = MultiPolygon([principal, shape(rectangle(12, 0, 16, 10))])
    gr = GabaritResult(status="ok", surfaceParcelleM2=160, contourGeoJSON=rectangle(0, 0, 16, 10),
                       zoneImplantationM2=136, zoneImplantationGeoJSON=mapping(zone),
                       hauteurReglementaireM=6.5, plafondEmpriseStatus="absent")
    renseigner_emprise_projet(gr)
    assert gr.surfacesContinuesM2 == [96, 40] and gr.empriseSupplementaireM2 == 136
    assert gr.exempleEmpriseM2 == 96
    assert to_metric(shape(gr.exempleEmpriseGeoJSON)).symmetric_difference(to_metric(principal)).area < 1e-6
    gr.plafondEmpriseStatus = "not_integrated"
    renseigner_emprise_projet(gr)
    assert gr.empriseSupplementaireM2 is None and gr.exempleEmpriseGeoJSON is None
