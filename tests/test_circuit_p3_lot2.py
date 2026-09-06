"""CIRCUIT-P3 lot 2 — l'état des robinets. La recette montrait « 2 fuites » au Résumé et « 0 à
regarder » au Circuit : les colonnes robinet_* des tables sont des LIBELLÉS, pas des ids de robinet ;
le lien passe par le chiffre_id. Ce test part des tables + du registre, construit l'ensemble des ids
attendus « à regarder » et exige l'ÉGALITÉ STRICTE avec ce que rend /admin/circuit (2.2), sans
doublon côté réservoirs (2.3). Il REMPLACE le test synthétique P2 (qui passait sur une page fausse)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import circuit_etats as E


# ── 2.1 — le join par chiffre_id (pur) ────────────────────────────────────────────────────────
def test_robinets_touches_via_chiffre():
    fuites = [{"chiffre_id": "cA", "robinet_a": "libellé (brut)", "robinet_b": "libellé (servi)"}]
    eau = [{"chiffre_id": "cB", "robinet": "fiche parcelle / filtres", "statut": "ouvert"},
           {"chiffre_id": "cC", "robinet": "x", "statut": "etiquete"}]   # pas ouvert → ignoré
    chiffres_par_robinet = {"rob1": ["cA", "cZ"], "rob2": ["cB"], "rob3": ["cC"], "rob4": ["cZ"]}
    fuite_rob, eau_rob = E.robinets_touches(fuites, eau, chiffres_par_robinet)
    assert fuite_rob == {"rob1"}        # sert cA (la fuite), via le chiffre — pas via le libellé
    assert eau_rob == {"rob2"}          # sert cB (eau ouverte) ; cC étiquetée n'est pas remontée


@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    return TestClient(app)


def _deux_chiffres_avec_robinets():
    """Deux (chiffre_id, ids de robinets qui le servent) distincts, tirés du VRAI registre."""
    from labuse.registre import ROBINETS
    par_chiffre: dict[str, set] = {}
    for rid, rb in ROBINETS.items():
        for cid in rb.chiffres:
            par_chiffre.setdefault(cid, set()).add(rid)
    paires = sorted(par_chiffre.items())
    # deux chiffres dont les ensembles de robinets sont disjoints (fuite ≠ eau, sans recouvrement)
    for i in range(len(paires)):
        for j in range(i + 1, len(paires)):
            if not (paires[i][1] & paires[j][1]):
                return paires[i], paires[j]
    return paires[0], paires[1]


# ── 2.2 / 2.3 — égalité stricte tables ↔ /admin/circuit ───────────────────────────────────────
@pytest.mark.db
def test_egalite_robinets_a_regarder(client, engine):
    from labuse import sonde_circuit
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    from labuse.registre import CHIFFRES, ROBINETS
    (cid_fuite, rob_fuite), (cid_eau, rob_eau) = _deux_chiffres_avec_robinets()
    with engine.begin() as c:
        appliquer_modes_cadences(c)
        sonde_circuit.ensure(c)
        # état de fuite/eau CONNU : on repart de zéro puis on pose une fuite et une eau, chacune
        # sur un chiffre RÉEL servi par des robinets du registre (colonnes robinet_* = libellés).
        c.execute(text("DELETE FROM circuit_ecarts"))
        c.execute(text("DELETE FROM circuit_eau_ancienne"))
        c.execute(text(
            "INSERT INTO circuit_ecarts (chiffre_id, cle, robinet_a, valeur_a, robinet_b, valeur_b,"
            " cause, type, statut) VALUES (:cid, 'p3', 'libellé A (brut)', '1', 'libellé B (servi)',"
            " '2', 'test P3', 'nombre', 'ouvert')"), {"cid": cid_fuite})
        c.execute(text(
            "INSERT INTO circuit_eau_ancienne (chiffre_id, robinet, tampon, attendu, mecanisme,"
            " statut) VALUES (:cid, 'fiche parcelle / filtres', 'vieux', 'neuf', 'test P3', 'ouvert')"),
            {"cid": cid_eau})

    circ = client.get("/admin/circuit").json()

    # attendu, construit DES TABLES + REGISTRE + FICHES DE RÈGLE (le code est la vérité)
    from labuse import regles as R4
    hm_rob = {rid for rid, rb in ROBINETS.items()
              if any(E.est_hors_moteur(CHIFFRES[cid].calcul) for cid in rb.chiffres if cid in CHIFFRES)}
    # CIRCUIT-4 (lot 5.3) — les robinets servant une donnée d'une fiche verdict=ecart sont rouges
    ecart_rob = R4.robinets_par_verdict({rid: list(rb.chiffres) for rid, rb in ROBINETS.items()})["ecart"]
    attendu_ko = set(rob_fuite) | set(rob_eau) | hm_rob | ecart_rob

    # rendu par /admin/circuit
    rendu_ko = {rb["id"] for rb in circ["robinets"] if E.ko_robinet(*rb["etat"])}
    assert rendu_ko == attendu_ko, f"en trop: {rendu_ko - attendu_ko} · en moins: {attendu_ko - rendu_ko}"
    # le compteur de colonne dit exactement ce nombre
    assert circ["compteurs"]["robinets_a_regarder"] == len(attendu_ko)

    # le Résumé compte les MÊMES robinets (fini « 2 fuites » à gauche / « 0 » à droite)
    lignes = {li["titre"]: li for g in circ["resume"]["groupes"] for li in g["lignes"]}
    assert set(lignes["fuites mesurées"]["cible"]["ids"]) == set(rob_fuite)
    assert set(lignes["robinets servent de l'eau ancienne"]["cible"]["ids"]) == set(rob_eau)


@pytest.mark.db
def test_detail_robinet_coherent_avec_liste(client, engine):
    """La page de détail d'un robinet dit le MÊME état que la liste du Circuit (recette P3 : le détail
    disait « cohérent » quand la liste disait « fuite », car il joignait par libellé, pas par chiffre)."""
    from labuse import sonde_circuit
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    (cid_fuite, rob_fuite), _ = _deux_chiffres_avec_robinets()
    with engine.begin() as c:
        appliquer_modes_cadences(c)
        sonde_circuit.ensure(c)
        c.execute(text("DELETE FROM circuit_ecarts"))
        c.execute(text(
            "INSERT INTO circuit_ecarts (chiffre_id, cle, robinet_a, valeur_a, robinet_b, valeur_b,"
            " cause, type, statut) VALUES (:cid, 'p3', 'libellé (brut)', '1', 'libellé (servi)', '2',"
            " 'test P3', 'nombre', 'ouvert')"), {"cid": cid_fuite})
    circ = client.get("/admin/circuit").json()
    for rid in rob_fuite:
        etat_liste = next(rb["etat"] for rb in circ["robinets"] if rb["id"] == rid)
        detail = client.get(f"/admin/circuit/robinet/{rid}").json()
        assert detail["robinet"]["etat"] == etat_liste          # le détail == la liste
        assert etat_liste[1] == "fuite mesurée"                 # et c'est bien une fuite


@pytest.mark.db
def test_reservoirs_a_regarder_sans_doublon(client, engine):
    """2.3 — « n à regarder » à gauche = les ids de réservoirs des lignes du Résumé, SANS doublon
    (un réservoir dans deux lignes ne compte qu'une fois)."""
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    with engine.begin() as c:
        appliquer_modes_cadences(c)
    circ = client.get("/admin/circuit").json()

    # les lignes « à regarder » = celles qui portent une couleur ko (rouge/ambre/mauve) sur des
    # réservoirs. Les lignes grises « À décider » (cadences, choix) NE sont PAS « à regarder ».
    ids_ko = []
    for g in circ["resume"]["groupes"]:
        for li in g["lignes"]:
            if li["cible"]["type"] == "reservoir" and li["couleur"] in ("rouge", "ambre", "mauve"):
                ids_ko.extend(li["cible"]["ids"])
    distincts = set(ids_ko)
    # « n à regarder » à gauche = les réservoirs distincts des lignes ko du Résumé (2.3)
    assert circ["compteurs"]["a_regarder"] == len(distincts)
    # sans doublon : un réservoir = un état = une seule ligne ko
    assert len(ids_ko) == len(distincts)
    # cohérence : ces ids sont bien « à regarder » (ko) dans le rendu du Circuit, et réciproquement
    etat_par_id = {r["id"]: r["etat"] for r in circ["reservoirs"]}
    for rid in distincts:
        assert E.ko_reservoir(*etat_par_id[rid])
    tous_ko = {r["id"] for r in circ["reservoirs"] if E.ko_reservoir(*r["etat"])}
    assert distincts == tous_ko          # aucun réservoir à regarder sans ligne (réciprocité)
