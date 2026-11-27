"""OUTIL-PERMIS-FIX-16 (contre-audit 02-PERMIS-ASTRA-8) — FILET (LOT 0, écrit AVANT les correctifs).

Chaque test prouve un point par CE QUE L'UTILISATEUR REÇOIT (fonction de calcul servie, opération
rendue, historique de fiche). Données SEMÉES dans une transaction rollback-ée (`db_session`) → déterministe.
Les preuves sur la base LIVE `labuse` (routes réelles, 30 fiches au hasard) sont dans scripts/outil_permis_fix16/.
"""
from __future__ import annotations

import datetime as dt
import json

import pytest
from sqlalchemy import text


def _seed_parcelle(db, idu, commune="X", lon=55.47, lat=-20.88):
    wkt = f"POLYGON(({lon} {lat},{lon+0.001} {lat},{lon+0.001} {lat-0.001},{lon} {lat-0.001},{lon} {lat}))"
    db.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) "
        "VALUES (:i,:c,:sec,:num, ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975), 500, ST_Centroid(ST_GeomFromText(:w,4326)), "
        " ST_Envelope(ST_GeomFromText(:w,4326)))"),
        {"i": idu, "w": wkt, "c": commune, "sec": idu[8:10], "num": idu[10:14]})


def _seed_permis(db, pid, typ, idus, *, date_aut, etat="2", an_depot=None, date_depot=None,
                 nb_lgt=None, petitioner=None, petitioner_siren=None, lon=55.47, lat=-20.88, commune="X"):
    raw = {"etat": etat}
    if an_depot:
        raw["an_depot"] = an_depot
    if nb_lgt is not None:
        raw["nb_lgt"] = str(nb_lgt)
    if petitioner:
        raw["petitioner_name"] = petitioner
        raw["petitioner_siren"] = petitioner_siren
    db.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, date_depot, commune, geom, idu_codes, raw) "
        "VALUES (:p,:t,:a,:d,:com, ST_SetSRID(ST_MakePoint(:lon,:lat),4326), CAST(:i AS jsonb), CAST(:r AS jsonb))"),
        {"p": pid, "t": typ, "a": date_aut, "d": date_depot, "com": commune,
         "i": json.dumps(idus), "r": json.dumps(raw), "lon": lon, "lat": lat})


# ════════════════ LOT 2 — décret n° 2025-461, article 3 (fonction pure) ════════════════
def test_echeance_autorisation_deja_caduque_garde_droit_commun():
    """97406000AV1068 (04/01/2021) : échéance de droit commun 04/01/2024 < 27/05/2025 → PAS de
    prorogation (art. 3) → 04/01/2024, jamais 04/01/2025."""
    from labuse.ingestion.pc_caducs import _echeance
    echeance, base = _echeance(dt.date(2021, 1, 4))
    assert echeance == dt.date(2024, 1, 4), f"attendu 04/01/2024, obtenu {echeance}"
    assert "art. 3" in base or "R.424-17" in base


def test_echeance_bornes_decret():
    from labuse.ingestion.pc_caducs import _echeance
    # P2 encore valide le 27/05/2025 (dernier jour) → art. 2 (+1 an)
    assert _echeance(dt.date(2022, 5, 27))[0] == dt.date(2026, 5, 27)
    # P2 veille → déjà caduque → droit commun
    assert _echeance(dt.date(2022, 5, 26))[0] == dt.date(2025, 5, 26)
    # P1 → art. 1er (5 ans), toujours encore valide au 27/05/2025
    assert _echeance(dt.date(2022, 11, 6))[0] == dt.date(2027, 11, 6)


# ════════════════ LOT 1 — panne non cachée + preuve au même endroit ════════════════
def test_garde_fou_panne_non_cachee():
    import labuse.api.app as app
    assert app._fiche_contient_panne(
        {"historique_site": {"indisponible": True, "raison": "erreur technique"}}) is True
    assert app._fiche_contient_panne(
        {"historique_site": {"permis": [], "indisponible": None}, "voisinage_proche": None}) is False


@pytest.mark.db
def test_caducite_sert_la_preuve_au_meme_endroit(db_session):
    """L'historique porte le n° du PC, la date d'autorisation, l'échéance, la base légale et la réserve
    « sur les seules données Sitadel » — et « aucun commencement déclaré »."""
    from labuse.ingestion.pc_caducs import build_pc_caducs
    from labuse.api.site_voisinage import historique_permis
    s = db_session
    idu = "97415000DP0016"
    _seed_parcelle(s, idu, "Saint-Paul")
    _seed_permis(s, "97441520A0030", "PC", [idu], date_aut="2020-02-26", an_depot="2020")
    build_pc_caducs(s, ref_date=dt.date(2026, 11, 25), commit=False)
    _seed_permis(s, "97441526A0011", "PC", [idu], date_aut="2026-05-22", an_depot="2026")
    _seed_permis(s, "97441518A0022", "PC", [idu], date_aut="2018-02-02", etat="4", an_depot="2018")
    h = historique_permis(s, idu)
    assert h is not None and h["caducite"] is not None
    cad = h["caducite"]
    assert cad["pc_numeros"] == ["97441520A0030"]          # numéro du PC
    assert cad["date_autorisation"] == "2020-02-26"        # date d'autorisation
    assert cad["echeance"] == "2023-02-26"                 # échéance estimée
    assert "R.424-17" in (cad["base_legale"] or "")        # base légale
    assert cad["reserve"] == "sur les seules données Sitadel"
    assert "aucun commencement déclaré" in cad["libelle_court"]


# ════════════════ LOT 3 — un permis sur plusieurs parcelles garde toutes ses lignes ════════════════
@pytest.mark.db
def test_num_a_deux_types_garde_ses_deux_lignes(db_session):
    """Le NUM 9744121620163 porte un PC (BO0239) ET un DP (CO0082) : la clé (permit_id, type) garde les
    deux ; l'historique de BO0239 porte bien son PC. ÉCHOUE sous la clé permit_id seule (2e insert rejeté)."""
    from labuse.ingestion.permits_sdes import ensure_indexes
    from labuse.ingestion.pc_caducs import build_pc_caducs
    from labuse.api.site_voisinage import historique_permis
    s = db_session
    ensure_indexes(s)   # bascule l'unicité sur (permit_id, type)
    bo, co = "97412000BO0239", "97412000CO0082"
    _seed_parcelle(s, bo, "Saint-Joseph")
    _seed_parcelle(s, co, "Saint-Joseph")
    _seed_permis(s, "9744121620163", "PC", [bo], date_aut="2016-12-21")
    _seed_permis(s, "9744121620163", "DP", [co], date_aut="2016-11-16")
    build_pc_caducs(s, ref_date=dt.date(2026, 11, 25), commit=False)   # schéma pc_caducs à jour + BO0239 caduc
    h = historique_permis(s, bo)
    assert h is not None, "BO0239 n'a aucun historique (PC perdu)"
    nums = {(p["permit_id"], p["type"]) for p in h["permis"]}
    assert ("9744121620163", "PC") in nums, f"PC absent de BO0239 ; vus : {nums}"


# ════════════════ LOT 4 — pétitionnaire Sitadel ≠ propriétaire cadastral ════════════════
@pytest.mark.db
def test_petitionnaire_sitadel_distinct_du_proprietaire(db_session):
    """Le pétitionnaire est celui que Sitadel nomme (GUYAB IMMO) ; IDEA GROUPE n'est que le propriétaire
    cadastral et n'est jamais appelé demandeur."""
    import labuse.api.veille_promoteurs as vp
    s = db_session
    idu = "97416000IM0092"
    _seed_parcelle(s, idu, "Saint-Pierre", lon=55.48, lat=-21.31)
    _seed_permis(s, "97441626A0008", "PC", [idu], date_aut="2026-03-26", an_depot="2026", nb_lgt=3,
                 petitioner="GUYAB IMMO", petitioner_siren="910668011", lon=55.48, lat=-21.31, commune="Saint-Pierre")
    s.execute(text("DELETE FROM parcelle_personne_morale WHERE idu = :i"), {"i": idu})
    s.execute(text("INSERT INTO parcelle_personne_morale (idu, groupe, denomination, siren) "
                   "VALUES (:i, 0, 'IDEA GROUPE', '510150501')"), {"i": idu})
    ops = vp._operations(s, [0], "Saint-Pierre", "2026-01-01")
    op = next((o for o in ops if idu in o.get("idus", [])), None)
    assert op is not None
    assert op.get("petitionnaire_nom") == "GUYAB IMMO"
    assert op.get("petitionnaire_siren") == "910668011"
    assert op.get("proprietaire_cadastral_nom") == "IDEA GROUPE"


def test_note_veille_ne_confond_pas_proprietaire_et_demandeur():
    """La note de pied d'écran ne présente plus le propriétaire foncier comme le demandeur."""
    import labuse.api.veille_promoteurs as vp
    note = vp.NOTE_SOURCE.lower()
    assert "le demandeur = propriétaire" not in note
    assert "propriétaire" in note and "pétitionnaire" in note


# ════════════════ LOT 5 — dépôt connu à l'année seule : pas de falaise du 2 janvier ════════════════
@pytest.mark.db
def test_depot_annee_seule_pas_de_falaise(db_session):
    """Un dépôt connu à l'année seule (an_depot=2026, sans jour affichable) reste compté au 01/01 ET au
    02/01 : même compte. ÉCHOUE avant (jour 01-01 inventé → chute à 0 le 02/01)."""
    import labuse.api.veille_promoteurs as vp
    s = db_session
    idu = "97416000ZZ0001"
    _seed_parcelle(s, idu, "Saint-Pierre", lon=55.49, lat=-21.32)
    _seed_permis(s, "97441626Z0001", "PC", [idu], date_aut="2026-05-10", an_depot="2026", nb_lgt=4,
                 lon=55.49, lat=-21.32, commune="Saint-Pierre")   # pas de date_depot affichable
    s.execute(text("DELETE FROM parcelle_personne_morale WHERE idu = :i"), {"i": idu})
    s.execute(text("INSERT INTO parcelle_personne_morale (idu, groupe, denomination, siren) "
                   "VALUES (:i, 0, 'PROMO Z', '900000001')"), {"i": idu})
    n1 = len(vp._operations(s, [0], "Saint-Pierre", "2026-01-01"))
    n2 = len(vp._operations(s, [0], "Saint-Pierre", "2026-01-02"))
    assert vp._operations(s, [0], "Saint-Pierre", "2026-10-01") == []
    assert vp._operations(s, [0], "Saint-Pierre", "2026-01-02")[0]["depot_a_confirmer"]
    assert n1 == n2 == 1, f"falaise : {n1} au 01/01 vs {n2} au 02/01"


@pytest.mark.db
def test_actes_de_meme_numero_fiche_et_voisinage(db_session):
    from labuse.api.modules import parcelle_permis, permis_fiche
    from labuse.ingestion.permits_sdes import ensure_indexes
    s = db_session
    ensure_indexes(s)
    num = "9744121620163"
    dp, pc = "97412000CO0082", "97412000BO0239"
    for idu, typ, lon in [(dp, "DP", 55.60), (pc, "PC", 55.67)]:
        _seed_parcelle(s, idu, "Saint-Joseph", lon=lon)
        _seed_permis(s, num, typ, [idu], date_aut="2016-11-16", an_depot="2016")
        s.execute(text("UPDATE sitadel_permits SET geom=(SELECT centroid FROM parcels WHERE idu=:idu) "
                       "WHERE permit_id=:n AND type=:t"), {"idu": idu, "n": num, "t": typ})
    assert {r["nature"] for r in permis_fiche(num, s)["choix"]} == {"PC", "DP"}
    for idu, typ in [(dp, "DP"), (pc, "PC")]:
        assert permis_fiche(num, s, typ)["parcelles"] == [idu]
        near = parcelle_permis(idu, s)
        assert [(r["nature"], r["distance_m"]) for r in near["items"] if r["permit_id"] == num] == [(typ, 0)]
        assert near["c200"] == len(near["items"])


@pytest.mark.db
def test_acte_sur_deux_parcelles_eloignees(db_session):
    from labuse.api.modules import parcelle_permis
    db = db_session
    a, b = "97499000XY0801", "97499000XY0802"
    _seed_parcelle(db, a, lon=55.47)
    _seed_parcelle(db, b, lon=55.49)
    _seed_permis(db, "TEST_MULTIPARCELLE", "PC", [a, b], date_aut="2024-05-01")
    resultat = parcelle_permis(b, db, complet=True)
    assert "TEST_MULTIPARCELLE" in {r["permit_id"] for r in resultat["rattaches"]}
    assert "TEST_MULTIPARCELLE" not in {r["permit_id"] for r in resultat["items"]}


@pytest.mark.db
def test_import_sans_parcelle_et_provenance(db_session, monkeypatch):
    from labuse.api.modules import permis_fiche
    from labuse.ingestion import permits_sdes as sdes
    db = db_session
    sdes.ensure_indexes(db)
    # Un acte mixte sans cadastre est consultable par numéro. Un retrait de la
    # publication suivante conserve sa fiche, avec une provenance historique.
    fichiers = {
        "logements": "NUM_DAU;TYPE_DAU;COMM;SURF_HAB_CREEE;SURF_LOC_CREEE\nXT_MIX;PC;97499;36.25;0",
        "locaux": "NUM_DAU;TYPE_DAU;COMM;SURF_HEB_CREEE;SURF_COM_CREEE;SURF_LOC_CREEE\nXT_MIX;PC;97499;85.4;85.4;85.4",
        "pa": "NUM_PA;COMM\nXT_PA;97499",
        "pd": "NUM_PD;COMM\nXT_PD;97499",
    }
    famille = {v["rid"]: k for k, v in sdes.DATAFILES.items()}
    monkeypatch.setattr(sdes, "_fetch_csv", lambda rid, **_: fichiers[famille[rid]])
    sdes.ingest_sdes(db, millesime="2026-10")
    fiche = permis_fiche("XT_MIX", db)
    assert fiche["parcelles"] == [] and fiche["geom"] is None
    assert fiche["source"].endswith("2026-10")
    assert {s["destination"]: s["m2"] for s in fiche["surfaces_plancher_creees"]} == {
        "habitation": 36.25, "locaux non résidentiels": 85.4, "dont hébergement hôtelier": 85.4}
    fichiers["pa"] = fichiers["pa"].replace("XT_PA", "XT_NOUVEAU")
    sdes.ingest_sdes(db, millesime="2026-11")
    assert "ancien import" in permis_fiche("XT_PA", db)["source"]
