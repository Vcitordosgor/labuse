"""GABARIT-3D-3 (LOT 2) — sol mesuré 0,5 m : cache local LRU + repli, SANS réseau (unitaire)."""
from __future__ import annotations

import os

from labuse.gabarit import sol


def test_cache_lru_ecarte_les_plus_anciens(tmp_path, monkeypatch):
    """Le dossier de copies plafonné écarte les copies au DERNIER ACCÈS le plus ancien (LRU)."""
    monkeypatch.setenv("LABUSE_GAB_SOL_CACHE", str(tmp_path))
    for i, name in enumerate(["hr_a.tif", "hr_b.tif", "hr_c.tif"]):
        f = tmp_path / name
        f.write_bytes(b"x" * 1000)
        os.utime(f, (1000 + i, 1000 + i))            # atime croissant : hr_a le plus ancien
    sol._evict_lru(2500)                             # garde ~2 fichiers (2000 o) → supprime hr_a
    restants = {p.name for p in tmp_path.glob("hr_*.tif")}
    assert "hr_a.tif" not in restants
    assert restants == {"hr_b.tif", "hr_c.tif"}


def test_copie_resservie_sans_appel_exterieur(tmp_path, monkeypatch):
    """Une fenêtre déjà en copie est resservie SANS aucun appel WMS."""
    monkeypatch.setenv("LABUSE_GAB_SOL_CACHE", str(tmp_path))
    x0, y0, x1, y1 = sol._fenetre(100.0, 200.0, 110.0, 210.0, marge=5.0)
    (tmp_path / sol._cle(x0, y0, x1, y1)).write_bytes(b"geotiff")
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
    _surf, meta = SC.charger_surface_sol(None, 336420.0, 7689531.0, 336853.0, 7689978.0, marge=20.0)
    assert meta["repli"] is True and meta["source"] == "fond_1m" and meta["maille_m"] == 1.0
    assert "repli" in (meta["message"] or "").lower() or "indisponible" in (meta["message"] or "").lower()
