"""ETUDE-STATIONNEMENT-FIX-4 — chaque cas cité par le relecteur devient un test. La preuve FINALE reste le
PDF régénéré par la vraie route ; ces tests verrouillent le comportement unitaire sous-jacent."""
from __future__ import annotations

import os

import pytest
from shapely.geometry import Polygon

import labuse.implantation.controles as C


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("base applicative absente")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    if s.execute(text("SELECT count(*) FROM parcels WHERE idu = '97416000HT0538'")).scalar() != 1:
        s.close()
        pytest.skip("parcelle témoin HT0538 absente")
    yield s
    s.close()


# ── LOT 1 : dégagement mesuré EXACTEMENT, sans marge cachée ──────────────────────────────────────
def _place_allee(profondeur_allee: float):
    """Une place 2,5 × 5 (nez en y=0) et une allée de `profondeur_allee` m DEVANT elle (y < 0)."""
    place = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
    allee = Polygon([(-1, -profondeur_allee), (3.5, -profondeur_allee), (3.5, 0), (-1, 0)])
    return allee, place


@pytest.mark.parametrize("profondeur, doit_echouer", [
    (5.00, False),   # exactement la largeur exigée → PASSE
    (4.99, True),    # 1 cm sous le minimum → ÉCHOUE (plus de tolérance de 0,60 m ni de 1 m²)
    (4.79, True),    # cas BW2635 relevé par le relecteur → ÉCHOUE
    (4.00, True),    # anciennement validé (0,60 m retranchés) → ÉCHOUE
])
def test_degagement_exact_sans_marge(profondeur, doit_echouer):
    allee, place = _place_allee(profondeur)
    manque = C._pincement_allee([allee], [place], 5.0)
    echoue = manque > C._DEGAGEMENT_SEUIL_M2
    assert echoue is doit_echouer, f"allée {profondeur} m : manque={manque:.4f} m² (seuil {C._DEGAGEMENT_SEUIL_M2})"


def test_degagement_pas_de_marge_cachee():
    """Garde-fou explicite : le code ne retranche plus 0,60 m et ne tolère plus 1 m²."""
    assert C._DEGAGEMENT_SEUIL_M2 <= 0.02, "la tolérance ne doit absorber que le bruit flottant, pas une marge"
    # une allée de 4,40 m (= 5,00 − 0,60, l'ancienne marge) doit désormais ÉCHOUER franchement.
    allee, place = _place_allee(4.40)
    assert C._pincement_allee([allee], [place], 5.0) > C._DEGAGEMENT_SEUIL_M2


# ── LOT 2 : une recherche sans résultat ≠ « impossible pour cause établie » ──────────────────────
@pytest.mark.reel
def test_assemblage_sans_plan_dit_aucun_plan_trouve(session_reelle):
    """Sur un assemblage dont la part d'habitat (UB) est trop étroite, la recherche ne trouve aucun plan.
    Le verdict doit le DIRE (« Aucun plan trouvé sous ces hypothèses »), PAS conclure à une impossibilité
    réglementaire (« Impossible pour cause établie ») : la zone est constructible."""
    from labuse.implantation.service import etudier_payload
    from sqlalchemy import text
    for idus in (["97404000AM0759", "97404000AM0874"], ["97408000AR0468", "97408000AR1302"]):
        if session_reelle.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                                  {"i": idus}).scalar() != len(idus):
            pytest.skip(f"parcelles {idus} absentes")
        p = etudier_payload(session_reelle, {"idus": idus, "type_projet": "collectif", "objectif": "equilibre",
                                             "stationnement": "aerien", "terrain": "libere"})
        assert p.get("verdict") == "Aucun plan trouvé sous ces hypothèses", p.get("verdict")


# ── LOT 2 : le Dossier affiche la MÊME règle de stationnement que l'Étude (jamais « non réglementé ») ──
@pytest.mark.reel
@pytest.mark.parametrize("idu, attendu", [
    ("97422000BW2635", "pl."),                            # barème par typologie (Ua12.2)
    ("97416000HT0538", "1 place / 75 m"),                 # barème par m² de SDP (Ud6)
    ("97422000AD0887", "pl."),                            # barème par typologie (Ud12.2)
])
def test_dossier_affiche_le_bareme_stationnement(session_reelle, idu, attendu):
    import re
    from sqlalchemy import text
    from labuse.exports import builder
    from labuse.api.app import parcel_fiche, vider_fiche_cache_partage
    if session_reelle.execute(text("SELECT count(*) FROM parcels WHERE idu=:i"), {"i": idu}).scalar() != 1:
        pytest.skip(f"parcelle {idu} absente")
    vider_fiche_cache_partage()
    fiche = parcel_fiche(idu, db=session_reelle)
    res = builder.construire(session_reelle, idu, "dossier", fiche=fiche)
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", res.html))
    m = re.search(r"Stationnement\s+([^<]{3,90})", t)
    ligne = m.group(1) if m else ""
    assert "non réglementé" not in ligne, f"{idu} : Dossier dit encore « non réglementé » ({ligne!r})"
    assert attendu in ligne, f"{idu} : règle attendue {attendu!r} absente ({ligne!r})"
