"""ETUDE-V6-2 (Lot 2) — CAPACITÉ STABLE (maximum calculé une fois, indépendant de la demande : deux
demandes différentes sur la même assiette → même maximum) et FACTEUR LIMITANT JUSTE (classé par impact,
le stationnement affirmé limitant/non limitant seulement après un contrefactuel « sans places »).
Rejoué sur Étang-Salé (collectif)."""
from __future__ import annotations

import os

import pytest

_ETANG = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent")
    eng = make_engine(url=url)
    s = sessionmaker(bind=eng, future=True)()
    n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"), {"i": _ETANG}).scalar()
    if n != 4:
        s.close()
        pytest.skip("parcelles témoins absentes")
    yield s
    s.close()


def _cfg(lignes):
    return {"idus": _ETANG, "type_projet": "collectif", "programme": {"mode": "saisi", "lignes": lignes}}


@pytest.mark.reel
def test_capacite_maximale_stable_entre_deux_demandes(session_reelle):
    """Deux demandes de QUANTITÉS différentes (même type/surface) renvoient le MÊME maximum : la capacité
    est une propriété du terrain, pas de la demande. La demande est seulement CONFRONTÉE à ce maximum."""
    from labuse.implantation.service import etudier_payload
    a = etudier_payload(session_reelle, _cfg([{"type": "T2", "nombre": 10, "surface_m2": 56}]))
    b = etudier_payload(session_reelle, _cfg([{"type": "T2", "nombre": 40, "surface_m2": 56}]))
    ca, cb = a["capacite_maximale"], b["capacite_maximale"]
    assert ca is not None and cb is not None
    # le maximum est IDENTIQUE malgré deux demandes différentes
    assert ca["logements"] == cb["logements"]
    assert ca["par_type"] == cb["par_type"]
    assert ca["niveaux"] == cb["niveaux"]
    # mais la confrontation, elle, dépend de la demande
    assert a["confrontation"]["demande_logements"] == 10
    assert b["confrontation"]["demande_logements"] == 40
    assert a["confrontation"]["capacite_maximale_logements"] == ca["logements"]
    assert a["confrontation"]["tient"] is True          # 10 ≤ max
    assert b["confrontation"]["tient"] is False          # 40 > max
    assert b["confrontation"]["reserve_logements"] < 0


@pytest.mark.reel
def test_facteur_stationnement_prouve_par_contrefactuel(session_reelle):
    """Le stationnement n'est déclaré limitant qu'APRÈS un contrefactuel « sans places » : à Étang-Salé il
    l'est (retirer les places ajoute des logements). Les facteurs sont classés par impact décroissant."""
    from labuse.implantation.service import etudier_payload
    d = etudier_payload(session_reelle, _cfg([{"type": "T2", "nombre": 23, "surface_m2": 56},
                                              {"type": "T3", "nombre": 6, "surface_m2": 70}]))
    facteurs = d["facteurs_limitants"]
    assert facteurs, "au moins un facteur limitant attendu"
    # classement par impact décroissant
    impacts = [f["impact_logements"] for f in facteurs]
    assert impacts == sorted(impacts, reverse=True)
    stat = next(f for f in facteurs if f["facteur"].startswith("stationnement"))
    # à Étang-Salé le stationnement aérien EST limitant, prouvé par le contrefactuel
    assert stat["limitant"] is True
    assert stat["impact_logements"] > 0
    assert "contrefactuel" in stat["preuve"]
    assert "sans stationnement" in stat["detail"]
    # la mesure cite la surface occupée sur l'assiette (ex. « 612 m² occupés sur 1746 m² »)
    assert "m²" in stat["mesure"]
    # le stationnement, prouvé limitant, est en tête du classement (impact le plus fort)
    assert facteurs[0]["facteur"].startswith("stationnement")


@pytest.mark.reel
def test_facteur_non_limitant_jamais_affirme_sans_preuve(session_reelle):
    """Un facteur sans impact mesuré (ex. largeur de zone ici) n'est JAMAIS marqué « limitant »."""
    from labuse.implantation.service import etudier_payload
    d = etudier_payload(session_reelle, _cfg([{"type": "T2", "nombre": 10, "surface_m2": 56}]))
    for f in d["facteurs_limitants"]:
        if f["impact_logements"] == 0:
            assert f["limitant"] is False


def _cfg_mode(lignes, mode):
    c = _cfg(lignes)
    c["stationnement"] = mode
    return c


@pytest.mark.reel
def test_sous_sol_libere_le_sol_et_ajoute_des_logements(session_reelle):
    """ETUDE-V6-2 (Lot 3) — enterrer le stationnement libère le sol : à Étang-Salé (où l'aérien plafonne),
    le sous-sol accueille PLUS de logements que l'aérien. Les places sont au −1, l'emprise enterrée tient
    sous l'emprise réglementaire (contrôle dédié), et le sol ne porte plus de places aériennes."""
    from labuse.implantation.service import etudier_payload
    lignes = [{"type": "T2", "nombre": 23, "surface_m2": 56}, {"type": "T3", "nombre": 6, "surface_m2": 70}]
    aer = etudier_payload(session_reelle, _cfg_mode(lignes, "aerien"))
    sous = etudier_payload(session_reelle, _cfg_mode(lignes, "sous_sol"))
    assert aer["capacite_maximale"]["stationnement_mode"] == "aerien"
    assert sous["capacite_maximale"]["stationnement_mode"] == "sous_sol"
    # le sous-sol accueille au moins autant de logements que l'aérien (ici strictement plus)
    assert sous["capacite_maximale"]["logements"] >= aer["capacite_maximale"]["logements"]
    assert sous["capacite_maximale"]["logements"] > aer["capacite_maximale"]["logements"]
    # la variante sous-sol : places au −1, aucune place aérienne, emprise enterrée > 0
    v = next(x for x in sous["variantes"] if not x.get("absente"))
    st = v["stationnement"]
    assert st["mode"] == "sous_sol"
    assert st["places_sous_sol"] > 0
    assert st["surface_stationnement_m2"] == 0          # rien au sol (hors rampe)
    assert st["emprise_sous_sol_m2"] > 0
    # un contrôle « Emprise du sous-sol » ≤ emprise réglementaire est présent et vérifié
    emp = next(c for c in v["controles"] if c["nom"] == "Emprise du sous-sol")
    assert emp["resultat"] in ("Réussi", "Échoué", "À confirmer")
    # study_id différent de l'aérien (le mode entre dans l'empreinte → PDF distinct)
    assert sous["study_id"] != aer["study_id"]


@pytest.mark.reel
def test_jauge_enveloppe_estimee(session_reelle):
    """ETUDE-V6-2 (Lot 4) — enveloppe ESTIMÉE (étape 3), rapide et SANS moteur : zone d'implantation,
    niveaux (hauteur PLU), coef plancher, places par type. Étang-Salé UA : estimable."""
    import time
    from labuse.implantation.service import jauge_payload
    t = time.monotonic()
    j = jauge_payload(session_reelle, _ETANG, "social")
    assert time.monotonic() - t < 10.0          # rapide (pas de recherche)
    assert j["estimable"] is True
    assert j["zone_implantation_m2"] > 0
    assert j["niveaux"] == 4 and j["niveaux_label"] == "R+3"   # UA 12 m à l'égout / 3 m
    assert 0.5 <= j["coef_plancher"] <= 1.0
    assert j["etiquette"] == "estimé"
    assert j["manquant"] == []
    # barème UA : T2 = 1 place, T3 = 1,5
    assert j["places_par_type"]["T2"] == 1.0 and j["places_par_type"]["T3"] == 1.5


@pytest.mark.reel
def test_regles_plu_par_parcelle(session_reelle):
    """ETUDE-V6-2 (Lot 5) — l'étape 1 sert les règles PLU de la zone de CHAQUE parcelle, citées
    (article). Étang-Salé UA : hauteur, CES, reculs, pleine terre + espaces verts / marge (calibrés §2)."""
    from labuse.implantation.assiette import valider_parcelles
    out = valider_parcelles(session_reelle, ["97404000AW0099"])
    rp = out["parcelles"][0]["regles_plu"]
    assert rp, "règles PLU attendues pour UA"
    noms = {r["nom"] for r in rp}
    assert "Emprise au sol (CES)" in noms and "Pleine terre" in noms
    assert "Espaces verts" in noms and "Marge plantée" in noms   # calibrés Lot 3 §2
    # chaque règle servie est chiffrée et citée
    for r in rp:
        assert r["valeur"] is not None and r["article"]


@pytest.mark.reel
def test_pdf_genere_meme_si_ne_tient_pas(session_reelle):
    """ETUDE-V6-3 (item 12) — le PDF se génère TOUJOURS, même quand la demande ne tient pas : le
    dépassement est écrit dans le document (comme à l'écran). Reproduit l'échec de Vic : 42 T1 aérien."""
    from labuse.implantation.service import etudier_payload
    from labuse.exports import etude_faisabilite as ef
    cfg = {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "aerien",
           "programme": {"mode": "saisi", "lignes": [{"type": "T1", "nombre": 42, "surface_m2": 30}]}}
    p = etudier_payload(session_reelle, dict(cfg))
    assert p["statut_global"] == "ne tient pas" and not p["scenarios"]   # la demande ne tient pas
    rendu = ef.rendu_etude(p, genere_le="22/10/2026")                    # ne lève PLUS de ValueError
    assert rendu["html"] and "Dépassement" in rendu["html"]              # dépassement écrit
    assert "votre_programme" not in rendu["html"]                         # item 10 : aucun nom technique


@pytest.mark.reel
def test_pdf_pas_de_nombre_ni_facteur_hors_ecran(session_reelle):
    """ETUDE-V6-4 (item 13) — l'écran et le PDF disent EXACTEMENT la même chose : le PDF ne contient AUCUN
    nombre ni facteur limitant absent du payload servi à l'écran (même study_id). On le prouve sur l'aérien
    ET le sous-sol (le plus riche : niveau −1 dessiné, facteur limitant pente/hauteur, mixité)."""
    from labuse.implantation.service import etudier_payload
    from labuse.exports import etude_faisabilite as ef
    for mode in ("aerien", "sous_sol"):
        cfg = {"idus": _ETANG, "type_projet": "etudiante", "stationnement": mode,
               "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 23, "surface_m2": 56},
                                                         {"type": "T3", "nombre": 6, "surface_m2": 70}]}}
        p = etudier_payload(session_reelle, dict(cfg))
        html = ef.rendu_etude(p, genere_le="22/10/2026")["html"]
        # 1) AUCUN nombre imprimé hors du payload (verrou V5d/V5f étendu).
        manquants = ef.nombres_hors_payload(p, html, genere_le="22/10/2026")
        assert manquants == [], f"{mode} : nombres hors écran dans le PDF : {manquants}"
        # 2) LE facteur limitant du PDF = celui du payload (source unique lue par l'écran ET le PDF).
        fl = p.get("facteur_limitant")
        if fl:
            assert fl in html, f"{mode} : facteur limitant « {fl} » absent du PDF"
        # 3) pas de nom technique (item 12).
        for interdit in ("votre_programme", "IMPLANTATION-2", "version_conventions", "non simulé"):
            assert interdit not in html, f"{mode} : « {interdit} » ne doit pas figurer dans le PDF"


@pytest.mark.reel
def test_sous_sol_plan_dessine_sur_geometrie(session_reelle):
    """ETUDE-V6-4 (item 9) — le niveau −1 est DESSINÉ sur la vraie géométrie : le GeoJSON porte l'emprise
    enterrée, l'allée et des places au niveau −1 (plus une grille générique) ; le nb de niveaux est servi."""
    from labuse.implantation.service import etudier_payload
    cfg = {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "sous_sol",
           "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 23, "surface_m2": 56},
                                                     {"type": "T3", "nombre": 6, "surface_m2": 70}]}}
    p = etudier_payload(session_reelle, dict(cfg))
    v = next(x for x in p["variantes"] if not x.get("absente"))
    kinds = {f["properties"]["kind"] for f in v["geojson"]["features"]}
    assert {"sous_sol_emprise", "place_ss", "allee_ss"} <= kinds       # objets du −1 dessinés
    st = v["stationnement"]
    assert st["mode"] == "sous_sol" and st["places_sous_sol"] > 0
    assert st["places_sous_sol_par_niveau"] > 0 and st["niveaux_sous_sol"] >= 1
    # cohérence : niveaux × places/niveau ≥ places demandées (plan de principe honnête)
    assert st["niveaux_sous_sol"] * st["places_sous_sol_par_niveau"] >= st["places_sous_sol"]


@pytest.mark.reel
def test_sous_sol_etude_rapide(session_reelle):
    """L'étude sous-sol reste rapide (pas de 2ᵉ recherche) — bornée bien en deçà de la nouvelle borne 60 s."""
    import time
    from labuse.implantation.service import etudier_payload
    t = time.monotonic()
    etudier_payload(session_reelle, _cfg_mode([{"type": "T2", "nombre": 23, "surface_m2": 56},
                                               {"type": "T3", "nombre": 6, "surface_m2": 70}], "sous_sol"))
    assert time.monotonic() - t < 30.0
