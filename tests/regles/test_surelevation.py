"""Témoin CIRCUIT-4 — surélévation : marge = hf − hauteur bâtie (FAÎTAGE prioritaire, RECETTE-7
E1 : le bâti BD TOPO est un faîtage), recomparée indépendamment ; hauteur du bâti = max des
bâtiments intersectants (seedé)."""
from __future__ import annotations

import pytest
from sqlalchemy import text


class _Rules:
    def __init__(self, he=None, hf=None):
        self.he_m, self.hf_m = he, hf


class _Ctx:
    zone, commune = "Utest", "Saint-Paul"


@pytest.mark.db
def test_hauteur_max_batiments(engine):
    from labuse.faisabilite.potentiel import _hauteur_bati_m
    from labuse.db import session_scope
    with engine.begin() as c:
        c.execute(text("DELETE FROM spatial_layers WHERE kind = 'batiment'"
                       " AND name LIKE 'c4-bat%'"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinSur-C4'"))
        c.execute(text(
            "INSERT INTO parcels (idu, commune, surface_m2, geom, geom_2975) VALUES "
            "('C4SUR0000000', 'TemoinSur-C4', 100, ST_GeomFromText('POINT(55.5 -21.1)', 4326),"
            " ST_GeomFromText('POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))', 2975))"))
        pid = c.execute(text("SELECT id FROM parcels WHERE idu = 'C4SUR0000000'")).scalar()
        for nom, h in (("c4-bat1", 4.5), ("c4-bat2", 7.0)):
            c.execute(text(
                "INSERT INTO spatial_layers (kind, name, attrs, geom, geom_2975) VALUES "
                "('batiment', :n, :a, ST_GeomFromText('POINT(55.5 -21.1)', 4326),"
                " ST_GeomFromText('POLYGON((1 1, 3 1, 3 3, 1 3, 1 1))', 2975))"),
                {"n": nom, "a": f'{{"hauteur": "{h}"}}'})
    with session_scope() as s:
        h = _hauteur_bati_m(s, pid)
    with engine.begin() as c:   # nettoyage : aucun legs (bâtiments fantômes)
        c.execute(text("DELETE FROM spatial_layers WHERE kind = 'batiment' AND name LIKE 'c4-bat%'"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinSur-C4'"))
    assert h == 7.0                             # max(4,5 ; 7,0) — recompté à la main


@pytest.mark.db
def test_marge_faitage_prioritaire(engine, monkeypatch):
    # RECETTE-7 (E1) — le bâti mesuré (BD TOPO) est un FAÎTAGE : on le compare à la règle de
    # FAÎTAGE (hf), pas à l'égout. L'égout n'est qu'un repli, converti en faîtage estimé.
    from labuse.faisabilite import potentiel
    from labuse.db import session_scope
    monkeypatch.setattr(potentiel, "_hauteur_bati_m", lambda s, p: 6.0)
    with session_scope() as s:
        # hé ET hf présents → le FAÎTAGE prime : marge = 16 − 6 = 10 m (recalcul indépendant)
        out = potentiel.surelevation(s, 1, rules=_Rules(he=12.0, hf=16.0), ctx=_Ctx())
        assert out["base"] == "faîtage" and out["marge_m"] == 16.0 - 6.0
        assert out["possible"] is True and not out["avertissement"]
        # hf présent seul → faîtage direct, sans avertissement
        out2 = potentiel.surelevation(s, 1, rules=_Rules(he=None, hf=9.0), ctx=_Ctx())
        assert out2["base"] == "faîtage" and not out2["avertissement"]
        # hf absent, hé seul → repli faîtage ESTIMÉ (égout + toiture type) AVEC avertissement
        out3 = potentiel.surelevation(s, 1, rules=_Rules(he=12.0, hf=None), ctx=_Ctx())
        assert out3["base"].startswith("faîtage (estimé") and out3["avertissement"]
        assert out3["marge_m"] == (12.0 + potentiel.TOITURE_TYPIQUE_M) - 6.0
        # aucune hauteur → possible=None (jamais un faux « non »)
        out4 = potentiel.surelevation(s, 1, rules=_Rules(), ctx=_Ctx())
        assert out4["possible"] is None
        # RECETTE-10 T1 — les deux règles exposées BRUTES pour le calcul à deux contraintes (LiDAR)
        assert out["he_regle_m"] == 12.0 and out["hf_regle_m"] == 16.0


def test_surelevation_mesuree_deux_contraintes_la_plus_serree():
    """RECETTE-10 T1 — cas EL0157 : le LiDAR a mesuré égout ET faîtage. On garde la contrainte la
    plus serrée et on nomme celle qui mord. Recalculé à la main :
      égout   : 7,0 (règle) − 3,0 (mesuré) = 4,0 m
      faîtage : 10,0 (règle) − 6,9 (mesuré) = 3,1 m  → mord (3,1 < 4,0)."""
    from labuse.faisabilite.potentiel import surelevation_mesuree
    out = surelevation_mesuree(he_regle=7.0, hf_regle=10.0, egout_mesure=3.0, faitage_mesure=6.9)
    assert out["marge_m"] == 3.1                    # PAS 7,0 (l'inversion T9→T1)
    assert out["contrainte"] == "faîtage"           # c'est le faîtage qui limite
    assert out["possible"] is True                  # 3,1 ≥ 2,8 (un niveau)
    marges = {c["base"]: c["marge_m"] for c in out["contraintes"]}
    assert marges == {"égout": 4.0, "faîtage": 3.1}


def test_surelevation_mesuree_jamais_regle_egout_contre_faitage():
    """RECETTE-10 T1 — le verrou anti-inversion : une règle d'ÉGOUT ne se compare JAMAIS à un
    faîtage, une règle de FAÎTAGE JAMAIS à un égout. Chaque contrainte apparie règle et mesure de
    la MÊME base ; aucune marge ne peut naître d'un croisement (7,0−6,9 ni 10,0−3,0)."""
    from labuse.faisabilite.potentiel import surelevation_mesuree
    out = surelevation_mesuree(he_regle=7.0, hf_regle=10.0, egout_mesure=3.0, faitage_mesure=6.9)
    for c in out["contraintes"]:
        # marge = règle − mesure, appariées par base : les deux valeurs partagent la même unité
        assert round(c["regle_m"] - c["mesure_m"], 1) == c["marge_m"]
    croisements = {round(7.0 - 6.9, 1), round(10.0 - 3.0, 1)}   # 0,1 (rè.égout−faîtage) ; 7,0 (rè.faît−égout)
    assert out["marge_m"] not in croisements
    # une seule base présente → une seule contrainte, pas de croisement possible
    seul_faitage = surelevation_mesuree(he_regle=None, hf_regle=10.0, egout_mesure=3.0, faitage_mesure=6.9)
    assert [c["base"] for c in seul_faitage["contraintes"]] == ["faîtage"]
    assert seul_faitage["marge_m"] == 3.1
    seul_egout = surelevation_mesuree(he_regle=7.0, hf_regle=None, egout_mesure=3.0, faitage_mesure=6.9)
    assert [c["base"] for c in seul_egout["contraintes"]] == ["égout"]
    assert seul_egout["marge_m"] == 4.0
    # aucune règle en regard d'une mesure → None (jamais un faux calcul)
    assert surelevation_mesuree(None, None, 3.0, 6.9) is None
