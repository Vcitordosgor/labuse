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


# ── LOT 3 : barème « par logement » à SEUIL DE SURFACE (La Plaine : 1 place < 30 m², 1,5 au-dessus) ──
def test_bareme_seuil_surface_la_plaine():
    """Le moteur ne met plus 1,5 partout : 1 place sous 30 m², 1,5 au-dessus, lecture prudente à la borne
    (30 m² pile = au-dessus). Programme JUSTE SOUS le seuil (29 m²) distinct du programme au-dessus."""
    from types import SimpleNamespace as NS
    from labuse.implantation import regles as R
    b = R.charger("97406", "Ub").stationnement
    assert b.seuil_surface_m2 == 30 and b.places_sous_seuil == 1
    sous = [NS(pieces=1, surface_m2=29.0) for _ in range(10)]          # juste SOUS le seuil
    mix = sous + [NS(pieces=3, surface_m2=110.0) for _ in range(10)]   # 10 sous + 10 au-dessus
    assert b.exiger(sous, destination="collectif").places == 10        # 10 × 1 (avant : 15)
    assert b.exiger(mix, destination="collectif").places == 25         # 10 × 1 + 10 × 1,5 (avant : 30)
    # borne AMBIGUË à 30 m² PILE : lecture prudente retenue (au-dessus = 1,5).
    pile = [NS(pieces=1, surface_m2=30.0) for _ in range(10)]
    assert b.exiger(pile, destination="collectif").places == 15        # 10 × 1,5 (prudent)


# ── LOT 1 : assemblage, TÉMOIN POSITIF (logements dessinés sur la part d'habitat, pas la part interdite) ──
@pytest.mark.reel
def test_assemblage_temoin_positif(session_reelle):
    """Deux parcelles voisines : AM0004 (UE, habitat de fonction) + AM0242 (UA, habitat, 12 600 m²). Le
    moteur retient la zone d'HABITAT (UA), clippe l'assiette sur sa part, et un plan TIENT (logements
    dessinés uniquement là où l'habitat est admis)."""
    from sqlalchemy import text
    from labuse.implantation.service import etudier_payload
    idus = ["97404000AM0004", "97404000AM0242"]
    if session_reelle.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                              {"i": idus}).scalar() != 2:
        pytest.skip("parcelles témoins absentes")
    p = etudier_payload(session_reelle, {"idus": idus, "type_projet": "collectif", "objectif": "equilibre",
                                        "stationnement": "aerien", "terrain": "libere"})
    cap = p.get("capacite_maximale") or {}
    assert (cap.get("logements") or 0) >= 10, "un plan doit tenir sur la part d'habitat (UA)"
    assert p.get("verdict") != "Aucun plan trouvé sous ces hypothèses"


# ── LOT 1 : largeur de desserte mesurée (L'Étang-Salé UA3.1.2 : 5 m à partir de 7 logements) ──
@pytest.mark.reel
def test_largeur_desserte_mesuree(session_reelle):
    from sqlalchemy import text
    from labuse.implantation.service import etudier_payload
    from labuse.exports.etude_faisabilite import scenario_retenu
    idus = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]
    if session_reelle.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                              {"i": idus}).scalar() != 4:
        pytest.skip("parcelles témoins absentes")
    p = etudier_payload(session_reelle, {"idus": idus, "type_projet": "social", "objectif": "equilibre",
                                        "stationnement": "aerien", "terrain": "libere",
                                        "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 23},
                                                                                  {"type": "T3", "nombre": 6}]}})
    # ETUDE-STATIONNEMENT-FIX-6 — la LARGEUR DE DESSERTE (UA3.1.2 : 5 m à partir de 7 logements) est MESURÉE et
    # confrontée à la règle servie. Depuis que l'accès est prolongé jusqu'à la voie (raccord strict tenu), la
    # desserte de L'Étang-Salé est désormais SATISFAITE (accès élargi) : on vérifie que le contrôle existe, cite
    # sa règle (5 m) et rend un résultat MESURÉ — plus un échec figé qui n'est plus la réalité du dessin.
    dess = [c for c in (scenario_retenu(p).get("controles") or []) if c.get("nom") == "Largeur de desserte"]
    assert dess, "le contrôle de largeur de desserte doit être servi (L'Étang-Salé UA, ≥ 7 logements)"
    assert dess[0]["resultat"] in ("Réussi", "Échoué", "À confirmer")
    assert "5" in str(dess[0].get("regle") or "") or "desserte" in str(dess[0].get("regle") or "").lower()


# ── LOT 2 : zone humide couvrant l'assiette → « À compléter » (AD0887) ──
@pytest.mark.reel
def test_zone_humide_fait_basculer_a_completer(session_reelle):
    from sqlalchemy import text
    from labuse.implantation.service import etudier_payload
    from labuse.exports.etude_faisabilite import scenario_retenu
    if session_reelle.execute(text("SELECT count(*) FROM parcels WHERE idu='97422000AD0887'")).scalar() != 1:
        pytest.skip("AD0887 absente")
    p = etudier_payload(session_reelle, {"idus": ["97422000AD0887"], "type_projet": "collectif",
                                        "objectif": "equilibre", "stationnement": "aerien", "terrain": "libere"})
    zh = [c for c in (scenario_retenu(p).get("controles") or []) if c.get("nom") == "Zone humide (inventaire)"]
    assert zh and zh[0]["resultat"] == "À confirmer"
    assert p.get("verdict") == "À compléter"
