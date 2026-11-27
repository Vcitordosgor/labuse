"""GABARIT-3D-3 (LOT 2) — sol mesuré 0,5 m : cache local LRU + repli, SANS réseau (unitaire)."""
from __future__ import annotations

import os

from labuse.gabarit import sol


def test_cache_lru_ecarte_les_plus_anciens(tmp_path, monkeypatch):
    """Le dossier de copies plafonné écarte les copies au DERNIER ACCÈS le plus ancien (LRU)."""
    monkeypatch.setenv("LABUSE_GAB_SOL_CACHE", str(tmp_path))
    noms = [f"{sol._PREFIXE}_a.tif", f"{sol._PREFIXE}_b.tif", f"{sol._PREFIXE}_c.tif"]
    for i, name in enumerate(noms):
        f = tmp_path / name
        f.write_bytes(b"x" * 1000)
        os.utime(f, (1000 + i, 1000 + i))            # atime croissant : _a le plus ancien
    sol._evict_lru(2500)                             # garde ~2 fichiers (2000 o) → supprime _a
    restants = {p.name for p in tmp_path.glob(f"{sol._PREFIXE}_*.tif")}
    assert noms[0] not in restants
    assert restants == {noms[1], noms[2]}


def test_copie_resservie_sans_appel_exterieur(tmp_path, monkeypatch):
    """Une fenêtre déjà en copie est resservie SANS aucun appel WMS."""
    monkeypatch.setenv("LABUSE_GAB_SOL_CACHE", str(tmp_path))
    x0, y0, x1, y1 = sol._fenetre(100.0, 200.0, 110.0, 210.0, marge=5.0)
    _ecrire_grille(tmp_path, x0, y0, x1, y1)
    sol.appels_wms["n"] = 0
    chemin, source = sol.obtenir_fenetre(100.0, 200.0, 110.0, 210.0, marge=5.0)
    assert source == "copie" and chemin is not None
    assert sol.appels_wms["n"] == 0                  # 0 appel extérieur


def test_repli_quand_service_coupe(tmp_path, monkeypatch):
    """Service coupé ET aucune copie → (None, None) : l'appelant replie sur le fond 1 m (jamais cassé)."""
    monkeypatch.setenv("LABUSE_GAB_SOL_CACHE", str(tmp_path))

    def _coupe(*_a):
        raise RuntimeError("service injoignable")
    monkeypatch.setattr(sol, "_fetch_wms", _coupe)
    chemin, source = sol.obtenir_fenetre(999000.0, 999000.0, 999010.0, 999010.0, marge=5.0)
    assert chemin is None and source is None


def test_charger_surface_sol_repli_meta_dit_le_repli(tmp_path, monkeypatch):
    """Service coupé → la surface vient du fond 1 m et la meta DIT le repli (la vue l'affichera)."""
    monkeypatch.setenv("LABUSE_GAB_SOL_CACHE", str(tmp_path))

    def _coupe(*_a):
        raise RuntimeError("off")
    monkeypatch.setattr(sol, "_fetch_wms", _coupe)
    from labuse.gabarit import scene as SC
    # fenêtre du témoin BZ1065 (couvert par le fond 1 m si présent ; sinon surf=None mais meta identique)
    monkeypatch.setattr(SC.get_settings(), "mnt5m_path", str(tmp_path / "absent.tif"))
    _surf, meta = SC.charger_surface_sol(None, 336420.0, 7689531.0, 336853.0, 7689978.0, marge=20.0)
    assert meta["repli"] is True and meta["source"] == "fond_1m" and meta["maille_m"] == 1.0
    assert "repli" in (meta["message"] or "").lower() or "indisponible" in (meta["message"] or "").lower()


def test_lire_tif_respecte_le_nodata_declare(tmp_path):
    import rasterio
    import numpy as np
    path = tmp_path / "test.tif"
    with rasterio.open(path, "w", driver="GTiff", height=2, width=2, count=1,
                       dtype="float32", nodata=9999, crs="EPSG:2975",
                       transform=rasterio.transform.from_origin(336000, 7689000, 0.5, 0.5)) as ds:
        ds.write(np.array([[0, 3], [9999, 4]], dtype="float32"), 1)
    a, _, _, pas = sol.lire_tif(path)
    assert pas == 0.5 and np.isnan(a[1, 0]) and a[0, 0] == 0

def _ecrire_grille(dossier, x0, y0, x1, y1):
    import numpy as np
    import rasterio
    w, h = 2 * (x1 - x0), 2 * (y1 - y0)
    grille = np.arange(w * h, dtype=np.float32).reshape(h, w)
    with rasterio.open(dossier / sol._cle(x0, y0, x1, y1), "w", driver="GTiff", height=h, width=w,
                       count=1, dtype="float32", crs="EPSG:2975",
                       transform=rasterio.transform.from_origin(x0, y1, 0.5, 0.5)) as ds:
        ds.write(grille, 1)
    return grille


def test_fenetre_voisine_couverte_ou_partielle(tmp_path, monkeypatch):
    import numpy as np
    monkeypatch.setenv("LABUSE_GAB_SOL_CACHE", str(tmp_path))
    grille = _ecrire_grille(tmp_path, 100, 200, 120, 220)
    appels = []
    def hors_ligne(*bounds):
        appels.append(bounds)
        raise OSError("hors ligne")
    monkeypatch.setattr(sol, "_fetch_wms", hors_ligne)
    bounds = (103, 204, 112, 216)
    chemin, source = sol.obtenir_fenetre(*bounds, marge=0)
    assert source == "copie" and appels == []
    a, x, y, pas = sol.lire_tif(chemin, bounds)
    assert (x, y, pas) == (103, 216, 0.5)
    np.testing.assert_array_equal(a, grille[8:32, 6:24])
    assert sol.obtenir_fenetre(103, 204, 121, 216, marge=0) == (None, None)
    assert len(appels) == 1


def test_fond_regional_natif_et_couverture(tmp_path, monkeypatch):
    import numpy as np
    import rasterio
    from labuse.gabarit import scene

    fond = tmp_path / "regional.tif"
    terrain = np.arange(48, dtype="float32").reshape(6, 8)
    terrain[2:4, 2:4] = -99999
    with rasterio.open(fond, "w", driver="GTiff", width=8, height=6, count=1,
                       dtype="float32", nodata=-99999, crs="EPSG:2975",
                       transform=rasterio.transform.from_origin(100, 230, 5, 5)) as ds:
        ds.write(terrain, 1)

    monkeypatch.setattr(sol, "obtenir_fenetre", lambda *args: (None, None))
    monkeypatch.setattr(scene, "charger_surface", lambda *args, **kwargs: None)
    monkeypatch.setattr(scene.get_settings(), "mnt5m_path", str(fond))
    surf, meta = scene.charger_surface_sol(None, 105, 205, 125, 225, marge=0)
    assert (surf.ox, surf.oy, surf.pas) == (105, 225, 5)
    assert np.isnan(surf.a[1, 1])
    assert surf.a[0, 0] == terrain[1, 1]
    assert (meta["source"], meta["maille_m"], meta["acquisition"]) == ("rge_alti_5m", 5, None)
    # Deux cas distincts : la marge seule contient des données, ou le raster est entièrement hors champ.
    for bounds in ((110, 210, 120, 220), (200, 300, 210, 310)):
        vide, _ = scene.charger_surface_sol(None, *bounds, marge=10)
        assert vide is None
    assert scene._lire_fond_local(fond, 1, 105, 205, 125, 225, 0) is None


def test_identifiant_scene_stable_entre_lidar_et_copie():
    from labuse.gabarit.scene import Scene, _hash_scene

    def signature(source):
        return _hash_scene(Scene(idu="A", scene_id="", meta={"sol_source": source}))

    assert signature("lidar_05m") == signature("copie")
    assert signature("lidar_05m") != signature("rge_alti_5m")
