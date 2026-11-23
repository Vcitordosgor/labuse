"""SCAN-FIX-1 (bloquants 2-4) — « qui construit ». Attribution du permis au propriétaire foncier
DÉTERMINISTE (majorité, départage stable) et INDÉPENDANTE de la catégorie (partition) ; cas ambigus
signalés ; logements de permis ANNULÉS hors « construit ou en cours » ; PC/DP distingués ; un groupe
« achevé » seulement si TOUS ses permis le sont ; deux listes (déposés vs foncier)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

A, B = "100000001", "200000002"   # deux SIREN promoteurs (groupe 0)
# points : le cluster A au même endroit (une opération), l'ambigu et les autres AILLEURS (séparés).
PT_A = "POINT(55.300 -20.900)"
PT_FAR = "POINT(55.600 -21.300)"


def _pm(db, idu, siren, groupe=0):
    db.execute(text("INSERT INTO parcelle_personne_morale (idu, siren, denomination, groupe) "
                    "VALUES (:i,:s,:d,:g)"), {"i": idu, "s": siren, "d": f"SCI {siren}", "g": groupe})


def _permit(db, pid, idus, wkt, nb_lgt, *, typ="PC", etat="2", daact=None, petitioner=None,
            commune="Patville", date="2024-03-01"):
    import json
    raw = {"nb_lgt": str(nb_lgt), "etat": etat}
    if daact:
        raw["daact"] = daact
    if petitioner:
        raw["petitioner_siren"] = petitioner
    db.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, idu_codes, commune, geom, raw, date_depot) "
        "VALUES (:p,:t, CAST(:iducodes AS jsonb), :c, ST_GeomFromText(:w,4326), CAST(:raw AS jsonb), :d)"),
        {"p": pid, "t": typ, "iducodes": json.dumps(idus), "c": commune, "w": wkt,
         "raw": json.dumps(raw), "d": date})


def _seed(db):
    for idu, s in (("97499000VP0001", A), ("97499000VP0002", A), ("97499000VP0003", A),
                   ("97499000VP0004", B)):
        _pm(db, idu, s)
    # opération A (cluster, même point) : P1 (10 lgt, en cours) + P_ach (4 lgt, achevé via DAACT)
    _permit(db, "P1", ["97499000VP0001", "97499000VP0002"], PT_A, 10, date="2024-01-01")
    _permit(db, "PACH", ["97499000VP0001"], PT_A, 4, daact="2024-06-01", date="2024-02-01")
    # P_ANNULE (etat=4, 5 lgt) — AILLEURS (séparé) → opération entièrement annulée
    _permit(db, "PANN", ["97499000VP0002"], PT_FAR, 5, etat="4", commune="Loinville")
    # P_DP (déclaration préalable, 3 lgt) — AILLEURS
    _permit(db, "PDP", ["97499000VP0003"], "POINT(55.100 -21.000)", 3, typ="DP", commune="DPville")
    # P_AMBIGU : 1 parcelle A + 1 parcelle B (ex æquo) — AILLEURS, pétitionnaire B déclaré
    _permit(db, "PAMB", ["97499000VP0003", "97499000VP0004"], "POINT(55.000 -21.200)", 7,
            petitioner=B, commune="Ambiville")


def test_attribution_deterministe_et_annules_et_pcdp(db_session):
    from labuse.api.veille_promoteurs import veille_promoteurs
    s = db_session
    _seed(s)
    r1 = veille_promoteurs(commune=None, categorie=None, depuis=None, siren=None, limit=200, db=s)
    r2 = veille_promoteurs(commune=None, categorie=None, depuis=None, siren=None, limit=200, db=s)
    # déterminisme : deux exécutions, mêmes opérations (mêmes SIREN, même ordre)
    assert [o["siren"] for o in r1["operations"]] == [o["siren"] for o in r2["operations"]]
    ops = {(o["siren"], o["commune"]): o for o in r1["operations"]}
    # opération A (cluster) : 10 + 4 = 14 logements, état « 1/2 achevés » (un seul des deux achevé)
    opA = ops[(A, "Patville")]
    assert opA["nb_logements"] == 14 and opA["n_permis"] == 2
    assert "achevé" in opA["etat_libelle"] and opA["etat_libelle"] != "travaux achevés"
    # ANNULÉ : exclu du « construit ou en cours » (compté à part)
    assert r1["n_logements_annules"] == 5
    assert all(o["commune"] != "Loinville" or o["annule"] for o in r1["operations"])
    # l'opération annulée ne compte pas ses logements dans le total construit/en cours
    assert (A, "Loinville") not in ops or ops[(A, "Loinville")]["nb_logements"] == 0
    # PC vs DP distingués
    opDP = ops[(A, "DPville")]
    assert opDP["n_permis_dp"] == 1 and opDP["n_permis_pc"] == 0
    # AMBIGU : parcelle ex æquo A/B → signalé ; attribution déterministe au plus petit SIREN (A)
    assert r1["n_operations_ambigues"] >= 1
    opAmb = ops.get((A, "Ambiville"))
    assert opAmb is not None and opAmb["ambigu"] is True
    # par_promoteur calculé sur TOUT (pas sur une page)
    assert any(c["siren"] == A for c in r1["par_promoteur"])


def test_partition_le_filtre_ne_change_pas_l_attribution(db_session):
    """Un filtre de catégorie ne doit PAS changer le propriétaire attribué à un permis (l'owner est
    choisi AVANT le filtre). Ici tous sont promoteurs (groupe 0) → le filtre 'promoteur' rend le même
    jeu, et 'bailleur' rend 0 — jamais une ré-attribution à un autre SIREN."""
    from labuse.api.veille_promoteurs import veille_promoteurs
    s = db_session
    _seed(s)
    tous = veille_promoteurs(commune=None, categorie=None, depuis=None, siren=None, limit=200, db=s)
    promo = veille_promoteurs(commune=None, categorie="promoteur", depuis=None, siren=None, limit=200, db=s)
    bail = veille_promoteurs(commune=None, categorie="bailleur", depuis=None, siren=None, limit=200, db=s)
    # les opérations 'promoteur' sont exactement celles de 'tous' (tous nos SIREN sont groupe 0)
    assert {(o["siren"], o["commune"]) for o in promo["operations"]} == {(o["siren"], o["commune"]) for o in tous["operations"]}
    assert bail["n_total"] == 0   # aucun bailleur → partition, pas de recouvrement


def test_frise_deux_listes_et_part_inconnue(db_session):
    from labuse.api.veille_promoteurs import promoteur_frise
    s = db_session
    _seed(s)
    fr = promoteur_frise(A, db=s)
    assert fr["sur_son_foncier"]["n_operations"] >= 1
    # A détient 5 permis fonciers ; un seul (le permis ambigu) porte un pétitionnaire déclaré (B) →
    # pétitionnaire inconnu sur 4/5 = 80 %.
    assert fr["sur_son_foncier"]["part_petitionnaire_inconnu"] == 80
    # A n'est pétitionnaire-déposant d'AUCUN permis (le seul petitioner déclaré, B, n'est pas A).
    assert fr["deposes_petitionnaire"]["n_permis"] == 0
