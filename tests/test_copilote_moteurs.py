"""M26-A — wrappers de moteurs : criblage lecture seule, filtre géométrique prouvable,
entonnoir faisabilité (parallèle), budget, champion P, garde-fou requalifié.
Session rollback-ée (db_session) pour les moteurs purs ; seeds commités quand les
sessions PARALLÈLES doivent les voir.
"""
from __future__ import annotations

import json
import threading

import pytest
from sqlalchemy import text

from labuse import config
from labuse.copilote import moteurs

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"
# ~11 × 10 m → emprise insetée de 3 m ≈ 20 m² → majorant ≈ 27 m² ≪ 420 (exclue au filtre)
_WKT_PETITE = ("POLYGON((55.45 -20.9,55.4501 -20.9,55.4501 -20.9001,"
               "55.45 -20.9001,55.45 -20.9))")

BRIEF = {"communes": ["Saint-Paul"], "programme": {"logements": 6, "sdp_cible_m2": 420.0},
         "budget_max_eur": None,
         "contraintes": {"exclure_ppr_rouge": True, "exclure_abf": False, "zones": None},
         "surface_min_m2": None}


def _seed_parcelle(s, idu, *, commune="Saint-Paul", surface=1000, tier="chaude", rang=1,
                   zone_lib="U", zone_fam="U", ppr_rouge=False, abf=False, wkt=_WKT):
    pid = s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, "
        " centroid, bbox) VALUES (:i, :c, 'AB', '1', ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975), :s, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) "
        "RETURNING id"), {"i": idu, "c": commune, "w": wkt, "s": surface}).scalar()
    s.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, "
        " rang, contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES (:run, :i, 0.5, 30.0, 90.0, :r, 0.2, 1.5, '[]', false, :t, 'test')"),
        {"run": _run_servi(), "i": idu, "r": rang, "t": tier})
    s.execute(text("INSERT INTO parcel_zone_plu (idu, zone_lib, zone_fam) "
                   "VALUES (:i, :zl, :zf)"), {"i": idu, "zl": zone_lib, "zf": zone_fam})
    if ppr_rouge:
        s.execute(text(
            "INSERT INTO cascade_results (parcel_id, layer_name, result, detail) "
            "VALUES (:p, 'risques', 'HARD_EXCLUDE', 'Exclue : PPR zone rouge (inconstructible).')"),
            {"p": pid})
    if abf:
        s.execute(text(
            "INSERT INTO cascade_results (parcel_id, layer_name, result, severity, detail) "
            "VALUES (:p, 'abf', 'SOFT_FLAG', 'faible', 'Abords monument historique (~500 m).')"),
            {"p": pid})
    return pid


def _run_servi():
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
    return Q_A_RUN_LABEL


# ───────────────────────── criblage ─────────────────────────

@pytest.mark.db
def test_criblage_lecture_seule_du_run_servi(db_session):
    _seed_parcelle(db_session, "97415000CP0001", tier="brulante", rang=1)
    _seed_parcelle(db_session, "97415000CP0002", tier="chaude", rang=2)
    _seed_parcelle(db_session, "97415000CP0003", tier="ecartee", rang=3)   # jamais criblée
    dossier = moteurs.Dossier()
    res = moteurs.criblage(db_session, BRIEF, dossier)
    idus = [c["idu"] for c in dossier.candidats]
    assert "97415000CP0003" not in idus
    assert idus[0] == "97415000CP0001"               # ordre : tier puis rang
    assert res.resultat["run_servi"] == _run_servi() # §7-J gravé dans le payload
    assert res.etiquette == "sourcé"


@pytest.mark.db
def test_criblage_sans_plafond(db_session):
    # Revue plafond (Vic) : AUCUNE troncature au criblage — l'exhaustivité de l'examen
    # est la règle, le garde-fou vit au filtre géométrique.
    for i in range(30):
        _seed_parcelle(db_session, f"97415000CU{i:04d}", rang=i + 1)
    dossier = moteurs.Dossier()
    res = moteurs.criblage(db_session, BRIEF, dossier)
    assert len(dossier.candidats) == 30
    assert "plafonne_a" not in res.resultat


@pytest.mark.db
def test_criblage_filtres_compteurs_avant_apres(db_session):
    _seed_parcelle(db_session, "97415000CQ0001", surface=1500)
    _seed_parcelle(db_session, "97415000CQ0002", surface=400)              # sous surface_min
    _seed_parcelle(db_session, "97415000CQ0003", surface=2000, ppr_rouge=True)
    brief = dict(BRIEF, surface_min_m2=800)
    dossier = moteurs.Dossier()
    res = moteurs.criblage(db_session, brief, dossier)
    f = res.resultat["filtres"]
    assert f["surface_min"] == {"avant": 3, "apres": 2}
    assert f["exclure_ppr_rouge"] == {"avant": 2, "apres": 1}
    assert [c["idu"] for c in dossier.candidats] == ["97415000CQ0001"]
    assert res.n_avant == 3 and res.n_apres == 1


@pytest.mark.db
def test_criblage_abf_signalee_pas_exclue_par_defaut(db_session):
    _seed_parcelle(db_session, "97415000CS0001", abf=True)
    dossier = moteurs.Dossier()
    res = moteurs.criblage(db_session, BRIEF, dossier)
    assert dossier.candidats[0]["abf"] is True       # signalé…
    assert "exclure_abf" not in res.resultat["filtres"]   # …pas exclu (défaut mandat)


# ───────────────────── filtre géométrique (prouvablement conservateur) ──────────────────

@pytest.mark.db
def test_filtre_geometrique_generique_ecarte_les_trop_petites(db_session):
    # Commune SANS YAML PLU → repli générique du MOTEUR (hé 9 m → 3 niveaux), Estimé.
    _seed_parcelle(db_session, "97499000FG0001", commune="X-Generique", wkt=_WKT)        # grande
    _seed_parcelle(db_session, "97499000FG0002", commune="X-Generique", wkt=_WKT_PETITE)  # minuscule
    brief = dict(BRIEF, communes=["X-Generique"])
    dossier = moteurs.Dossier()
    moteurs.criblage(db_session, brief, dossier)
    res = moteurs.filtre_geometrique(db_session, brief, dossier)
    assert res.etiquette == "estimé"
    assert res.resultat["calibrage"] == {"X-Generique": "regle_generique"}
    assert [c["idu"] for c in dossier.retenus()] == ["97499000FG0001"]
    petit = next(c for c in dossier.candidats if c["idu"] == "97499000FG0002")
    assert "capacité géométrique insuffisante" in petit["motif_ecarte"]
    assert "règle générique" in petit["motif_ecarte"]     # provenance dans le motif
    assert res.resultat["coef_occupation"] == 0.45        # lu via Hypotheses.charger()


@pytest.mark.db
def test_filtre_geometrique_zone_sans_plafond_non_filtree(db_session):
    # Saint-Paul (calibré) zone U1lec = à_vérifier → pas de plafond exploitable →
    # la parcelle N'EST PAS filtrée, même minuscule (règle Vic : on ne devine pas).
    _seed_parcelle(db_session, "97415000FG0003", zone_lib="U1lec", wkt=_WKT_PETITE)
    dossier = moteurs.Dossier()
    moteurs.criblage(db_session, BRIEF, dossier)
    res = moteurs.filtre_geometrique(db_session, BRIEF, dossier)
    assert [c["idu"] for c in dossier.retenus()] == ["97415000FG0003"]
    assert res.resultat["calibrage"] == {"Saint-Paul": "article_plu"}


@pytest.mark.db
def test_filtre_geometrique_calibre_ecarte_selon_article(db_session):
    # Saint-Paul zone U2d (hé 4,5 m → 1 niveau) : parcelle ~11 500 m² → inset ~10 900 m²
    # × 1 × 0,45 ≈ 4 900 m² ≥ 420 → retenue ; la minuscule → écartée, motif Sourcé.
    _seed_parcelle(db_session, "97415000FG0004", zone_lib="U2d", wkt=_WKT)
    _seed_parcelle(db_session, "97415000FG0005", zone_lib="U2d", wkt=_WKT_PETITE)
    dossier = moteurs.Dossier()
    moteurs.criblage(db_session, BRIEF, dossier)
    moteurs.filtre_geometrique(db_session, BRIEF, dossier)
    assert [c["idu"] for c in dossier.retenus()] == ["97415000FG0004"]
    petit = next(c for c in dossier.candidats if c["idu"] == "97415000FG0005")
    assert "Sourcé, article PLU" in petit["motif_ecarte"]


@pytest.mark.db
def test_garde_fou_requalifie_jamais_exhaustif(db_session, monkeypatch):
    monkeypatch.setattr(config.get_settings(), "copilote_max_candidats", 2)
    for i in range(5):
        _seed_parcelle(db_session, f"97415000GF000{i}", rang=i + 1)
    dossier = moteurs.Dossier()
    moteurs.criblage(db_session, BRIEF, dossier)
    res = moteurs.filtre_geometrique(db_session, BRIEF, dossier)
    gf = res.resultat["garde_fou"]
    assert gf == {"plafond": 2, "a_mordu": True, "n_non_examinees": 3}
    assert sum(1 for c in dossier.candidats if not c.get("examine", True)) == 3
    # Récap : requalification INTÉGRALE, jamais « aucune opportunité ».
    recap = moteurs._recap(dossier, 5)
    assert recap["exhaustif"] is False
    assert "2 examinées sur 5 candidates" in recap["requalification"]


# ───────────────────── faisabilité : entonnoir parallèle + calibrage ────────────────────

def _faisa(constructible, sdp, calibree=True):
    class _F:
        pass
    f = _F()
    f.constructible, f.verdict, f.zone, f.calibree = constructible, "test", "U", calibree
    f.fourchette = {"surface_plancher_m2": sdp, "shab_vendable_m2": int(sdp * 0.7) if sdp else 0,
                    "logements_sous_sol": (3, 8)}
    return f


@pytest.mark.db
def test_faisabilite_entonnoir_motifs_traces(db_session, monkeypatch):
    dossier = moteurs.Dossier()
    dossier.calibrage = {"Saint-Paul": "article_plu"}
    dossier.candidats = [
        {"idu": "A", "parcel_id": 1, "surface_m2": 1000, "retenu": True},
        {"idu": "B", "parcel_id": 2, "surface_m2": 900, "retenu": True},
        {"idu": "C", "parcel_id": 3, "surface_m2": 800, "retenu": True},
        {"idu": "D", "parcel_id": 4, "surface_m2": 700, "retenu": True},
    ]
    faisas = {1: (None, _faisa(True, 800)), 2: (None, _faisa(True, 300)),
              3: (None, _faisa(False, 0)), 4: None}
    monkeypatch.setattr("labuse.faisabilite.db.parcel_faisabilite",
                        lambda db, pid: faisas[pid])
    res = moteurs.faisabilite(db_session, BRIEF, dossier)
    assert [c["idu"] for c in dossier.retenus()] == ["A"]
    motifs = {c["idu"]: c.get("motif_ecarte") for c in dossier.candidats}
    assert "300 m² < cible 420 m²" in motifs["B"]
    assert "non constructible" in motifs["C"]
    assert "non vérifiable" in motifs["D"]           # boussole : jamais servi sans vérif
    assert res.etiquette == "estimé"                 # pré-faisabilité = hypothèses
    assert res.resultat["calibrage"] == {"Saint-Paul": "article_plu"}
    assert res.resultat["mention_sdp"] == moteurs.MENTION_SDP_CALIBREE


@pytest.mark.db
def test_faisabilite_parallele_traite_tout(db_session, monkeypatch):
    vus, lock = [], threading.Lock()

    def fake(db, pid):
        with lock:
            vus.append(pid)
        return (None, _faisa(True, 800))

    monkeypatch.setattr("labuse.faisabilite.db.parcel_faisabilite", fake)
    dossier = moteurs.Dossier()
    dossier.candidats = [{"idu": f"P{i}", "parcel_id": i, "surface_m2": 1000, "retenu": True}
                         for i in range(50)]
    res = moteurs.faisabilite(db_session, BRIEF, dossier)
    assert sorted(vus) == list(range(50))            # tout examiné, une seule fois
    assert res.resultat["sessions_paralleles"] == 4  # pool borné (arbitrage Vic)
    assert len(dossier.retenus()) == 50


@pytest.mark.db
def test_annulation_coupe_les_sessions_en_cours(db_session, monkeypatch):
    vus, lock = [], threading.Lock()

    def fake(db, pid):
        with lock:
            vus.append(pid)
        return (None, _faisa(True, 800))

    monkeypatch.setattr("labuse.faisabilite.db.parcel_faisabilite", fake)
    dossier = moteurs.Dossier()
    dossier.candidats = [{"idu": f"P{i}", "parcel_id": i, "surface_m2": 1000, "retenu": True}
                         for i in range(200)]
    moteurs.faisabilite(db_session, BRIEF, dossier, annule=lambda: True)
    # annule() vu dès la première vérification de lot → quasiment rien n'est traité.
    assert len(vus) < 200


@pytest.mark.db
def test_faisabilite_mention_generique_jamais_tracee_par_article(db_session, monkeypatch):
    # Exigence Vic (revue calibrage) : commune non calibrée → jamais « tracée par article ».
    monkeypatch.setattr("labuse.faisabilite.db.parcel_faisabilite",
                        lambda db, pid: (None, _faisa(True, 800, calibree=False)))
    dossier = moteurs.Dossier()
    dossier.calibrage = {"X-Generique": "regle_generique"}
    dossier.candidats = [{"idu": "P1", "parcel_id": 1, "surface_m2": 1000, "retenu": True}]
    res = moteurs.faisabilite(db_session, dict(BRIEF, communes=["X-Generique"]), dossier)
    assert res.resultat["mention_sdp"] == moteurs.MENTION_SDP_GENERIQUE
    assert "tracée par article" not in json.dumps(res.resultat, ensure_ascii=False)


# ───────────────────── filtre budget (avant toute troncature) ───────────────────────────

def _cand(idu, prix_probable, retenu=True):
    return {"idu": idu, "parcel_id": 1, "surface_m2": 1000, "retenu": retenu,
            "marche": {"disponible": True, "prix_probable_eur": prix_probable}}


@pytest.mark.db
def test_filtre_budget_ecarte_hors_budget_et_garde_non_estimables(db_session):
    dossier = moteurs.Dossier()
    dossier.candidats = [_cand("DANS", 300_000), _cand("HORS", 900_000), _cand("SANS", None)]
    brief = dict(BRIEF, budget_max_eur=480_000)
    res = moteurs.filtre_budget(db_session, brief, dossier)
    assert [c["idu"] for c in dossier.retenus()] == ["DANS", "SANS"]
    hors = next(c for c in dossier.candidats if c["idu"] == "HORS")
    assert "au-dessus du budget" in hors["motif_ecarte"] and "Estimé" in hors["motif_ecarte"]
    sans = next(c for c in dossier.candidats if c["idu"] == "SANS")
    assert sans["budget"] == "non estimable — non filtrée"   # jamais écartée sur une absence
    assert res.resultat == {"applique": True, "budget_max_eur": 480_000, "n_avant": 3,
                            "n_dans_budget": 1, "n_non_estimables_non_filtrees": 1,
                            "n_ecartees_budget": 1}


@pytest.mark.db
def test_filtre_budget_sans_budget_au_brief(db_session):
    dossier = moteurs.Dossier()
    dossier.candidats = [_cand("A", 900_000)]
    res = moteurs.filtre_budget(db_session, BRIEF, dossier)
    assert res.resultat["applique"] is False
    assert len(dossier.retenus()) == 1


# ───────────────────── mutation = champion P, lecture seule ─────────────────────────────

@pytest.mark.db
def test_mutation_lit_champion_p_source(db_session):
    _seed_parcelle(db_session, "97415000CU0001", tier="brulante", rang=7)
    dossier = moteurs.Dossier()
    dossier.candidats = [{"idu": "97415000CU0001", "parcel_id": 1, "retenu": True}]
    res = moteurs.mutation(db_session, BRIEF, dossier)
    assert res.etiquette == "sourcé"                 # décision GO Q1
    assert res.resultat["run_servi"] == _run_servi()
    assert dossier.candidats[0]["champion_p"] == {"tier": "brulante", "rang": 7,
                                                  "percentile": 90.0}


# ───────────────────── scoreur unitaire (verifier_adresse) ──────────────────────────────

@pytest.mark.db
def test_scoreur_unitaire_idu_trouve_et_introuvable(db_session):
    _seed_parcelle(db_session, "97415000CV0001", tier="chaude", rang=4)
    dossier = moteurs.Dossier()
    brief = {"refs": [{"type": "idu", "valeur": "97415000CV0001"},
                      {"type": "idu", "valeur": "97415000ZZ9999"}]}
    res = moteurs.scoreur_unitaire(db_session, brief, dossier)
    assert res.resultat == {"n_refs": 2, "n_trouvees": 1}
    v_ok, v_ko = dossier.verdicts
    assert v_ok["trouvee"] and v_ok["tier"] == "chaude"
    assert not v_ko["trouvee"] and "non vérifié" in v_ko["motif"]


# ───────────────────── assemblage : entonnoir, tri P, top-N, persistance ────────────────

@pytest.mark.db
def test_assemblage_entonnoir_tri_p_et_persistance(db_session, engine, monkeypatch):
    from sqlalchemy.orm import sessionmaker
    monkeypatch.setattr(config.get_settings(), "copilote_top_restitution", 2)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    run_id = s.execute(text(
        "INSERT INTO agent_runs (mission, brief_raw) VALUES ('instruire', 'test-moteur') "
        "RETURNING id::text")).scalar_one()
    s.commit()
    dossier = moteurs.Dossier()
    dossier._n_pool = 10
    dossier._n_apres_geo = 4
    dossier.calibrage = {"Saint-Paul": "article_plu"}
    dossier.candidats = [
        # tri P attendu : chaude rang 2 avant a_creuser rang 1 (ordre des tiers d'abord)
        {"idu": "97415000CW0001", "commune": "Saint-Paul", "surface_m2": 1000,
         "tier": "a_creuser", "rang": 1, "retenu": True, "faisabilite": {"sdp_m2": 500}},
        {"idu": "97415000CW0002", "commune": "Saint-Paul", "surface_m2": 900,
         "tier": "chaude", "rang": 2, "retenu": True, "faisabilite": {"sdp_m2": 600}},
        {"idu": "97415000CW0003", "commune": "Saint-Paul", "surface_m2": 800,
         "tier": "chaude", "rang": 9, "retenu": True, "faisabilite": {"sdp_m2": 450}},
        {"idu": "97415000CW0004", "commune": "Saint-Paul", "surface_m2": 400,
         "tier": "chaude", "rang": 5, "retenu": False,
         "motif_ecarte": "SDP estimée insuffisante"},
        {"idu": "97415000CW0005", "commune": "Saint-Paul", "surface_m2": 400,
         "tier": "a_creuser", "rang": 3, "retenu": False, "examine": False,
         "motif_ecarte": "non examinée — garde-fou"},
    ]
    try:
        res = moteurs.assemblage(s, BRIEF, dossier, run_id=run_id)
        s.commit()
        r = res.resultat
        assert [e["etape"] for e in r["entonnoir"]] == [
            "pool", "filtre_geometrique", "examinees", "retenues", "dans_budget", "restituees"]
        assert [e["n"] for e in r["entonnoir"]] == [10, 4, 4, 3, 3, 2]
        # tri champion P APRÈS faisabilité : chaude r2, chaude r9 (top-2)
        assert [x["idu"] for x in r["restituees"]] == ["97415000CW0002", "97415000CW0003"]
        assert r["exhaustif"] is False and "3 retenue(s)" in r["requalification"]
        rows = dict((x[0], x[1]) for x in s.execute(text(
            "SELECT parcel_idu, verdict FROM agent_run_parcels WHERE run_id = CAST(:r AS uuid)"),
            {"r": run_id}).all())
        assert rows["97415000CW0001"] == "retenue"
        assert rows["97415000CW0004"] == "ecartee"
        assert rows["97415000CW0005"] == "non_examinee"
    finally:
        s.rollback()
        s.execute(text("DELETE FROM agent_runs WHERE id = CAST(:r AS uuid)"), {"r": run_id})
        s.commit()
        s.close()
