"""M26-A — wrappers de moteurs : criblage lecture seule, entonnoir faisabilité,
champion P, scoreur unitaire. Session rollback-ée (db_session) : rien ne persiste.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.copilote import moteurs

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"

BRIEF = {"communes": ["Saint-Paul"], "programme": {"logements": 6, "sdp_cible_m2": 420.0},
         "budget_max_eur": None,
         "contraintes": {"exclure_ppr_rouge": True, "exclure_abf": False, "zones": None},
         "surface_min_m2": None}


def _seed_parcelle(s, idu, *, commune="Saint-Paul", surface=1000, tier="chaude", rang=1,
                   zone_fam="U", ppr_rouge=False, abf=False):
    pid = s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, "
        " centroid, bbox) VALUES (:i, :c, 'AB', '1', ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975), :s, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) "
        "RETURNING id"), {"i": idu, "c": commune, "w": _WKT, "s": surface}).scalar()
    s.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, "
        " rang, contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES (:run, :i, 0.5, 30.0, 90.0, :r, 0.2, 1.5, '[]', false, :t, 'test')"),
        {"run": _run_servi(), "i": idu, "r": rang, "t": tier})
    s.execute(text("INSERT INTO parcel_zone_plu (idu, zone_lib, zone_fam) "
                   "VALUES (:i, :z, :z)"), {"i": idu, "z": zone_fam})
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
def test_criblage_ppr_rouge_conservee_si_brief_le_dit(db_session):
    _seed_parcelle(db_session, "97415000CR0001", ppr_rouge=True)
    brief = dict(BRIEF, contraintes=dict(BRIEF["contraintes"], exclure_ppr_rouge=False))
    dossier = moteurs.Dossier()
    moteurs.criblage(db_session, brief, dossier)
    assert [c["idu"] for c in dossier.candidats] == ["97415000CR0001"]


@pytest.mark.db
def test_criblage_abf_signalee_pas_exclue_par_defaut(db_session):
    _seed_parcelle(db_session, "97415000CS0001", abf=True)
    dossier = moteurs.Dossier()
    res = moteurs.criblage(db_session, BRIEF, dossier)
    assert dossier.candidats[0]["abf"] is True       # signalé…
    assert "exclure_abf" not in res.resultat["filtres"]   # …pas exclu (défaut mandat)


@pytest.mark.db
def test_criblage_plafond_journalise(db_session, monkeypatch):
    from labuse import config
    monkeypatch.setattr(config.get_settings(), "copilote_max_candidats", 2)
    for i in range(4):
        _seed_parcelle(db_session, f"97415000CT000{i}", rang=i + 1)
    dossier = moteurs.Dossier()
    res = moteurs.criblage(db_session, BRIEF, dossier)
    assert len(dossier.candidats) == 2
    assert res.resultat["plafonne_a"] == 2           # jamais un plafond silencieux


# ───────────────────────── faisabilité (entonnoir) ─────────────────────────

def _faisa(constructible, sdp):
    class _F:
        pass
    f = _F()
    f.constructible, f.verdict, f.zone, f.calibree = constructible, "test", "U", True
    f.fourchette = {"surface_plancher_m2": sdp, "shab_vendable_m2": int(sdp * 0.7) if sdp else 0,
                    "logements_sous_sol": (3, 8)}
    return f


@pytest.mark.db
def test_faisabilite_entonnoir_motifs_traces(db_session, monkeypatch):
    dossier = moteurs.Dossier()
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
    assert res.n_avant == 4 and res.n_apres == 1


# ───────────────────────── mutation = champion P, lecture seule ─────────────────────────

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


# ───────────────────────── scoreur unitaire (verifier_adresse) ─────────────────────────

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


# ───────────────────────── assemblage : persistance retenues/écartées ───────────────────

@pytest.mark.db
def test_assemblage_persiste_verdicts_et_recap(db_session, engine):
    from sqlalchemy.orm import sessionmaker
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    run_id = s.execute(text(
        "INSERT INTO agent_runs (mission, brief_raw) VALUES ('instruire', 'test-moteur') "
        "RETURNING id::text")).scalar_one()
    s.commit()
    dossier = moteurs.Dossier()
    dossier.candidats = [
        {"idu": "97415000CW0001", "commune": "Saint-Paul", "surface_m2": 1000,
         "tier": "chaude", "retenu": True, "faisabilite": {"sdp_m2": 500}},
        {"idu": "97415000CW0002", "commune": "Saint-Paul", "surface_m2": 400,
         "tier": "chaude", "retenu": False, "motif_ecarte": "SDP estimée insuffisante"},
    ]
    try:
        res = moteurs.assemblage(s, BRIEF, dossier, run_id=run_id)
        s.commit()
        assert res.resultat["n_retenues"] == 1 and res.resultat["n_ecartees"] == 1
        assert res.resultat["retenues"][0]["idu"] == "97415000CW0001"
        rows = s.execute(text(
            "SELECT parcel_idu, verdict, motif FROM agent_run_parcels "
            "WHERE run_id = CAST(:r AS uuid) ORDER BY parcel_idu"), {"r": run_id}).all()
        assert [(r[0], r[1]) for r in rows] == [("97415000CW0001", "retenue"),
                                                ("97415000CW0002", "ecartee")]
        assert rows[1][2] == "SDP estimée insuffisante"
    finally:
        s.rollback()
        s.execute(text("DELETE FROM agent_runs WHERE id = CAST(:r AS uuid)"), {"r": run_id})
        s.commit()
        s.close()
