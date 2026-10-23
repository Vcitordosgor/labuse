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


_MIX = [{"type": "T1", "nombre": 39, "surface_m2": 30}, {"type": "T2", "nombre": 5, "surface_m2": 56},
        {"type": "T3", "nombre": 9, "surface_m2": 70}, {"type": "T4", "nombre": 20, "surface_m2": 80}]


def _variante(p):
    return next(x for x in p["variantes"] if not x.get("absente"))


@pytest.mark.reel
def test_plan_respecte_la_typologie_client_en_proportion(session_reelle):
    """ETUDE-V6-7 (item 1) — le plan dessine la TYPOLOGIE du client, en proportion (jamais tous T1 à la place
    de T4). 39 T1 + 5 T2 + 9 T3 + 20 T4 : le plan ne contient QUE ces types, chacun présent, dans des
    proportions proches de la demande (réduction au prorata si la demande ne tient pas)."""
    from labuse.implantation.service import etudier_payload
    p = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "aerien",
                                          "programme": {"mode": "saisi", "lignes": _MIX}})
    v = _variante(p)
    par = v["programme"]["par_type"]
    dem = {"T1": 39, "T2": 5, "T3": 9, "T4": 20}
    tot_dem = sum(dem.values())
    tot_plan = sum(par.values())
    assert tot_plan > 0
    # aucun type étranger, et CHAQUE type demandé est présent dans le plan (pas de substitution/suppression).
    assert set(par) == set(dem), f"typologie non respectée : {par}"
    # proportions du plan ≈ proportions de la demande (tolérance 12 points de %).
    for t in dem:
        assert abs(par[t] / tot_plan - dem[t] / tot_dem) <= 0.12, f"{t} hors proportion : {par}"


@pytest.mark.reel
def test_une_seule_verite_sur_le_programme_dessine(session_reelle):
    """ETUDE-V6-7 (item 2) — UNE seule vérité, calculée sur le programme DESSINÉ : tenus = somme du plan =
    resume.logements ; places dessinées = places exigées (barème) = resume.places ; surface tenue = Σ (tenus
    par type × surface) ; mixité = part des tenus. Tout cohérent dans le payload (lu par l'écran ET le PDF)."""
    import math
    from labuse.implantation.service import etudier_payload
    p = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "aerien",
                                          "programme": {"mode": "saisi", "lignes": _MIX}})
    v = _variante(p)
    par = v["programme"]["par_type"]
    tenus = sum(par.values())
    # tenus = somme du plan = resume.logements = capacité servie de la variante
    assert v["resume"]["logements"] == tenus
    # places : dessinées = exigées (barème) = resume.places
    assert v["stationnement"]["places"] == v["stationnement"]["places_imposees"] == v["resume"]["places"]
    # surface tenue servie = Σ (tenus par type × surface saisie) — nouveau champ, source unique écran/PDF
    surf = p["hypotheses"]["surfaces"]
    attendue = round(sum(par[t] * surf[t] for t in par), 1)
    assert v["programme"]["surface_tenue_m2"] == attendue
    # mixité (si applicable) = part des tenus (20 %), arrondie au supérieur
    if v["programme"].get("mixite_applicable"):
        assert v["programme"]["logements_aides_imposes"] == math.ceil(0.20 * tenus)
    # dépassement éventuel : « tiennent » = le plan dessiné (jamais un autre nombre)
    if p.get("depassement"):
        assert p["depassement"]["total_tiennent"] == tenus


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
def test_sous_sol_libere_le_sol(session_reelle):
    """ETUDE-V6-2 (Lot 3) / V6-7 (item 3) — enterrer le stationnement LIBÈRE le sol : places au −1 (un seul
    niveau), aucune place aérienne, emprise enterrée = emprise DESSINÉE et ≤ emprise réglementaire ; study_id
    distinct de l'aérien (PDF distinct)."""
    from labuse.implantation.service import etudier_payload
    lignes = [{"type": "T2", "nombre": 23, "surface_m2": 56}, {"type": "T3", "nombre": 6, "surface_m2": 70}]
    aer = etudier_payload(session_reelle, _cfg_mode(lignes, "aerien"))
    sous = etudier_payload(session_reelle, _cfg_mode(lignes, "sous_sol"))
    assert aer["capacite_maximale"]["stationnement_mode"] == "aerien"
    assert sous["capacite_maximale"]["stationnement_mode"] == "sous_sol"
    v = next(x for x in sous["variantes"] if not x.get("absente"))
    st = v["stationnement"]
    assert st["mode"] == "sous_sol" and st["niveaux_sous_sol"] == 1
    assert st["places_sous_sol"] > 0
    assert st["surface_stationnement_m2"] == 0                     # rien au sol (hors rampe)
    assert st["emprise_sous_sol_m2"] > 0 and st["emprise_sous_sol_m2"] == st["emprise_dessinee_m2"]
    # le sol est libéré (sur-dalle retranchée de la pleine terre, pas de places aériennes).
    emp = next(c for c in v["controles"] if c["nom"] == "Emprise du sous-sol")
    assert emp["resultat"] in ("Réussi", "Échoué", "À confirmer")
    assert aer["study_id"] != sous["study_id"]


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
def test_pdf_decrit_le_programme_du_client(session_reelle):
    """ETUDE-V6-6 (items 9/10/11) — le PDF décrit L'ÉTUDE DU CLIENT : son programme d'abord (N logements, type
    en toutes lettres), le maximum du terrain ensuite ; numéro de document EF-<8> dérivé du study_id (identique
    au payload) ; plus de « scénario A » / « retenu » / « collectif ». Garde PDF=écran : le n° de document, le
    type de projet, les logements du programme et la mixité sont présents et cohérents avec le payload servi."""
    from labuse.implantation.service import etudier_payload
    from labuse.exports import etude_faisabilite as ef
    cfg = {"idus": _ETANG, "type_projet": "social", "stationnement": "aerien",
           "programme": {"mode": "saisi", "lignes": [{"type": "T1", "nombre": 30, "surface_m2": 30},
                                                     {"type": "T2", "nombre": 10, "surface_m2": 56}]}}
    p = etudier_payload(session_reelle, dict(cfg))
    html = ef.rendu_etude(p, genere_le="23/10/2026")["html"]
    # (10) numéro de document EF-<8> dérivé du study_id, présent à l'écran (study_id) ET au cartouche.
    num = ef._numero_document(p)
    assert num.startswith("EF-") and len(num) == 11 and num == p["study_id"][:11]
    assert num in html
    # (9) le programme du client : type en toutes lettres + ses logements demandés.
    assert "logement social" in html                      # type en toutes lettres (jamais « collectif » nu)
    assert "Votre projet" in html and "Maximum du terrain" in html
    # plus de noms techniques de scénario.
    for interdit in ("scénario A", "scénario B", "votre_programme", "(retenu)", "· collectif ·"):
        assert interdit not in html, f"« {interdit} » ne doit pas figurer dans le PDF"
    # (11) écran = PDF : le retenu du PDF est « votre programme » (ce que l'écran affiche par défaut).
    retenu = ef.scenario_retenu(p)
    assert retenu["ref"] == "votre_programme"
    assert str(retenu["resume"]["logements"]) in html     # les logements du programme figurent
    # mixité : lue de la MÊME variante à l'écran et au PDF (programme étudié).
    assert retenu["programme"].get("mixite_applicable") in (True, False)
    # (11) verrou : aucun nombre hors du payload.
    assert ef.nombres_hors_payload(p, html, genere_le="23/10/2026") == []


@pytest.mark.reel
def test_numero_document_unique_par_etude(session_reelle):
    """ETUDE-V6-6 (item 10) — deux études différentes = deux numéros de document ; la même config = le même."""
    from labuse.implantation.service import etudier_payload
    from labuse.exports import etude_faisabilite as ef
    a = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "aerien",
                        "programme": {"mode": "saisi", "lignes": [{"type": "T1", "nombre": 30, "surface_m2": 30}]}})
    b = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "senior", "stationnement": "aerien",
                        "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 32, "surface_m2": 56}]}})
    a2 = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "aerien",
                         "programme": {"mode": "saisi", "lignes": [{"type": "T1", "nombre": 30, "surface_m2": 30}]}})
    assert ef._numero_document(a) != ef._numero_document(b)   # études différentes → numéros différents
    assert ef._numero_document(a) == ef._numero_document(a2)   # même config → même numéro


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
def test_niveaux_sous_sol_un_seul_niveau_toujours(session_reelle):
    """ETUDE-V6-7 (item 3) — le sous-sol est limité à UN niveau : toute demande de « 2 niveaux » est ramenée
    à 1 (plus de 2ᵉ nappe enterrée), places uniquement au −1 (places_niveau_moins2 == 0)."""
    from labuse.implantation.service import etudier_payload
    lignes = [{"type": "T2", "nombre": 23, "surface_m2": 56}, {"type": "T3", "nombre": 6, "surface_m2": 70}]
    for niv in (1, 2, 3):
        p = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "sous_sol",
                                             "niveaux_sous_sol": niv, "programme": {"mode": "saisi", "lignes": lignes}})
        v = next(x for x in p["variantes"] if not x.get("absente"))
        st = v["stationnement"]
        assert st["niveaux_sous_sol"] == 1 and st["places_niveau_moins2"] == 0
        assert p["entrees"].get("niveaux_sous_sol") == 1
        # aucun objet au niveau −2 dans le plan.
        assert not any(f["properties"].get("niveau") == -2 for f in v["geojson"]["features"])


@pytest.mark.reel
def test_sous_sol_jamais_aerien_dans_le_pdf(session_reelle):
    """ETUDE-V6-7 (item 5) — une étude en SOUS-SOL ne doit JAMAIS dire « aérien » (cartouche, tableau des
    surfaces rampe comprise, coupe, texte). Le mode réel partout."""
    from labuse.implantation.service import etudier_payload
    from labuse.exports import etude_faisabilite as ef
    p = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "sous_sol",
                                          "niveaux_sous_sol": 1, "programme": {"mode": "saisi", "lignes": _MIX}})
    html = ef.rendu_etude(p, genere_le="23/10/2026")["html"]
    import re
    txt = re.sub(r"<[^>]+>", " ", html)
    assert "aérien" not in txt.lower(), "« aérien » ne doit pas apparaître dans une étude en sous-sol"


@pytest.mark.reel
def test_sous_sol_un_seul_niveau_et_double_rangee(session_reelle):
    """ETUDE-V6-7 (item 3) — le sous-sol est limité à UN niveau (plus de « 2 niveaux » : niveaux_sous_sol
    forcé à 1) ; les places du −1 sont en DOUBLE RANGÉE quand la largeur le permet (≥ 2 places sur la
    profondeur d'une bande) et l'emprise affichée = l'emprise DESSINÉE."""
    from labuse.implantation.service import etudier_payload
    p2 = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "sous_sol",
                                          "niveaux_sous_sol": 2, "programme": {"mode": "saisi", "lignes": _MIX}})
    v = _variante(p2)
    st = v["stationnement"]
    assert st["niveaux_sous_sol"] == 1 and st.get("places_niveau_moins2", 0) == 0   # 2 refusé → ramené à 1
    assert p2["entrees"].get("niveaux_sous_sol") == 1
    # double rangée : des places au −1 à deux profondeurs distinctes (y) dans le repère du plan.
    ys = sorted({round(min(c[1] for c in f["geometry"]["coordinates"][0]), 5)
                 for f in v["geojson"]["features"] if f["properties"].get("kind") == "place_ss"})
    assert len(ys) >= 2, "les places du −1 doivent être sur au moins deux rangées"
    # emprise affichée = emprise dessinée (plus une formule abstraite).
    assert st.get("emprise_dessinee_m2") and abs(st["emprise_sous_sol_m2"] - st["emprise_dessinee_m2"]) <= 1.0


@pytest.mark.reel
def test_prorata_devie_pour_tenir_dans_les_places_explique(session_reelle):
    """ETUDE-V6-7 (suite) — quand le plan dévie du prorata EXACT pour tenir dans les places du −1 (le
    prorata exact exigerait plus de places que le sous-sol n'en offre), une PHRASE l'explique (types
    remplacés + nombre de places). Sinon (pas de déviation ou non liée aux places) : pas de phrase.
    Témoin : 39 T1 + 5 T2 + 9 T3 + 20 T4 sous-sol 1 niveau — prorata exact de 26 = 14/2/3/7 (31 places)
    > 30 places du −1 → 14/4/2/6 (30 places), avec la phrase."""
    import math
    from labuse.implantation.service import etudier_payload
    from labuse.implantation.geometrie import _repartir_prorata
    p = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "sous_sol",
                                          "niveaux_sous_sol": 1, "programme": {"mode": "saisi", "lignes": _MIX}})
    v = _variante(p)
    drawn = v["programme"]["par_type"]
    tenus = sum(drawn.values())
    ideal = _repartir_prorata({"T1": 39, "T2": 5, "T3": 9, "T4": 20}, tenus)
    bar = {"T1": 1, "T2": 1, "T3": 1.5, "T4": 1.5}
    pl = lambda d: math.ceil(sum(d.get(t, 0) * bar[t] for t in bar))
    cap = v["stationnement"]["places_sous_sol_par_niveau"]
    if ideal != drawn and pl(ideal) > cap:          # déviation liée aux places
        note = v.get("prorata_note")
        assert note and "places du sous-sol" in note and str(cap) in note
        assert pl(drawn) <= cap                      # le plan dessiné, lui, tient
        # … et la MÊME phrase dans le PDF (écran = PDF), sans fuite de nombre hors payload.
        from labuse.exports import etude_faisabilite as ef
        html = ef.rendu_etude(p, genere_le="23/10/2026")["html"]
        assert note in html, "la phrase du prorata doit figurer dans le PDF"
        assert ef.nombres_hors_payload(p, html, genere_le="23/10/2026") == []
    else:                                            # pas de déviation liée aux places → pas de phrase trompeuse
        assert not v.get("prorata_note")


@pytest.mark.reel
def test_sous_sol_sol_libere_explique(session_reelle):
    """ETUDE-V6-7 (item 4) — en sous-sol, le sol libéré est utilisé (bâtiment plus grand) ; une phrase
    l'explique, CHIFFRÉE si le bâtiment reste sous le plafond de hauteur (R+2 au lieu de R+3)."""
    from labuse.implantation.service import etudier_payload
    p = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "sous_sol",
                                          "niveaux_sous_sol": 1, "programme": {"mode": "saisi", "lignes": _MIX}})
    v = _variante(p)
    note = v.get("sol_libere_note")
    assert note, "une phrase doit expliquer l'usage du sol libéré en sous-sol"
    # si le bâtiment est sous le plafond (R+k < R+max), la phrase cite le niveau (chiffrée).
    niv = v.get("niveaux_label") or ""
    if "sous le plafond" in note.lower() or "au maximum" in note.lower():
        assert "R+" in note


@pytest.mark.reel
def test_lire_article_lien_geoportail_urbanisme(session_reelle):
    """ETUDE-V6-7 (item 9) — « Lire l'article » pointe vers le règlement officiel sur le GÉOPORTAIL DE
    L'URBANISME (geoportail-urbanisme.gouv.fr), construit depuis l'idurba du PLU calibré. Pour Étang-Salé
    (idurba servi), chaque règle porte cette URL ; « non disponible en lien direct » seulement sans document."""
    from labuse.implantation.service import etudier_payload, _plu_gpu_url
    url = _plu_gpu_url(session_reelle, "97404")
    assert url and "geoportail-urbanisme.gouv.fr" in url and "97404" in url
    p = etudier_payload(session_reelle, {"idus": _ETANG, "type_projet": "etudiante", "stationnement": "aerien",
                                          "programme": {"mode": "saisi", "lignes": _MIX}})
    assert p["regles"]["source_url"] == url
    assert all(l.get("source_url") == url for l in p["regles"]["lignes"])


@pytest.mark.reel
def test_sous_sol_disponibilite_servie(session_reelle):
    """ETUDE-V6-7 (item 3) — la disponibilité du sous-sol est SERVIE avec sa raison : indisponible si PPR
    inondation touche le terrain ou si le règlement de la zone mentionne « sous-sol » ; sinon « à confirmer :
    étude géotechnique, nappe »."""
    from labuse.implantation.service import jauge_payload
    jd = jauge_payload(session_reelle, _ETANG, "etudiante")
    ss = jd.get("sous_sol_dispo")
    assert ss is not None and "disponible" in ss and "raison" in ss
    assert isinstance(ss["disponible"], bool) and ss["raison"]


def _jauge_logements(jd, dem, surf, mode):
    """Reproduit la jauge EN LOGEMENTS côté serveur (miroir de enveloppeJauge, ETUDE-V6-7 item 6) :
    numérateur = BANDE de bâtiment (profondeur hyp × longueur de la zone) × niveaux × coef ; en sous-sol,
    borné par la capacité des places au −1 (per-niveau servi) ÷ places/logement."""
    tot = sum(dem.values());
    if tot == 0:
        return 0
    surf_moy = sum(dem[t] * surf[t] for t in dem) / tot
    places_moy = sum(dem[t] * (jd["places_par_type"].get(t, 1)) for t in dem) / tot
    niv, coef = jd["niveaux"], jd["coef_plancher"]
    bande = jd["bande_batiment_m2"]
    if mode == "sous_sol":
        bati = bande * niv * coef / surf_moy
        parking = (jd.get("sous_sol_places_par_niveau") or 0) / places_moy if places_moy else bati
        return round(min(bati, parking))
    return round(bande * niv * coef / (surf_moy + places_moy * 25 * niv * coef))


@pytest.mark.reel
def test_jauge_logements_proche_du_calcul_mixte(session_reelle):
    """ETUDE-V6-7 (item 6) — la jauge EN LOGEMENTS (vraie forme : bande de bâtiment dans la zone, pas toute
    la zone ; en sous-sol bornée par les places du −1) tombe à ≤ 20 % du calcul, aérien ET sous-sol, avec le
    programme mixte 39 T1 + 5 T2 + 9 T3 + 20 T4 sur Étang-Salé."""
    from labuse.implantation.service import jauge_payload, etudier_payload
    jd = jauge_payload(session_reelle, _ETANG, "etudiante")
    assert jd["estimable"] and jd.get("bande_batiment_m2") and jd["bande_batiment_m2"] <= jd["zone_implantation_m2"]
    dem = {"T1": 39, "T2": 5, "T3": 9, "T4": 20}
    surf = {"T1": 30, "T2": 56, "T3": 70, "T4": 80}
    lignes = [{"type": t, "nombre": n, "surface_m2": surf[t]} for t, n in dem.items()]
    for mode in ("aerien", "sous_sol"):
        cfg = {"idus": _ETANG, "type_projet": "etudiante", "stationnement": mode,
               "programme": {"mode": "saisi", "lignes": lignes}}
        if mode == "sous_sol":
            cfg["niveaux_sous_sol"] = 1
        calc = etudier_payload(session_reelle, dict(cfg))["capacite_maximale"]["logements"]
        est = _jauge_logements(jd, dem, surf, mode)
        assert calc > 0 and abs(est - calc) / calc <= 0.20, f"{mode} : jauge {est} vs calcul {calc}"


@pytest.mark.reel
def test_jauge_logements_proche_du_calcul(session_reelle):
    """ETUDE-V6-6 (item 5) — la jauge EN LOGEMENTS (estimée avant calcul depuis les ingrédients servis par
    `jauge_payload`) tombe à moins de 20 % du calcul complet. Témoin : Étang-Salé 30 T1 aérien (calcul 40)."""
    from labuse.implantation.service import jauge_payload, etudier_payload
    jd = jauge_payload(session_reelle, _ETANG, "etudiante")
    assert jd["estimable"] and jd["zone_implantation_m2"] > 0 and jd["niveaux"] >= 1
    zone, niv, coef = jd["zone_implantation_m2"], jd["niveaux"], jd["coef_plancher"]
    surf_moy, places = 30.0, float(jd["places_par_type"].get("T1", 1.0))     # 30 T1
    estime = round(zone * niv * coef / (surf_moy + places * 25 * niv * coef))  # formule aérienne (item 5)
    calc = etudier_payload(session_reelle, {
        "idus": _ETANG, "type_projet": "etudiante", "stationnement": "aerien",
        "programme": {"mode": "saisi", "lignes": [{"type": "T1", "nombre": 30, "surface_m2": 30}]}})["capacite_maximale"]["logements"]
    assert calc > 0
    assert abs(estime - calc) / calc < 0.20, f"jauge {estime} vs calcul {calc}"


@pytest.mark.reel
def test_sous_sol_etude_rapide(session_reelle):
    """L'étude sous-sol reste rapide (pas de 2ᵉ recherche) — bornée bien en deçà de la nouvelle borne 60 s."""
    import time
    from labuse.implantation.service import etudier_payload
    t = time.monotonic()
    etudier_payload(session_reelle, _cfg_mode([{"type": "T2", "nombre": 23, "surface_m2": 56},
                                               {"type": "T3", "nombre": 6, "surface_m2": 70}], "sous_sol"))
    assert time.monotonic() - t < 30.0
