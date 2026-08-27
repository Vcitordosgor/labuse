"""M137-O — l'endpoint /moteurs/simulplu (« Changement PLU ») ne doit JAMAIS lever.

Il n'avait aucun test : ce verrou casse si la requête SQL se casse (colonne manquante, mauvaise
concaténation du prédicat de zone, alias mort…). Couvre aussi : le plafond DIT (n_total/tronquee)
et le ménage q_score/q_actuel (payload propre).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import moteurs
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL as RUN

pytestmark = pytest.mark.db

_WKT = "POLYGON((55.45 -20.90, 55.451 -20.90, 55.451 -20.901, 55.45 -20.901, 55.45 -20.90))"


def _parcel(s, idu: str, surface: int) -> int:
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) "
        "VALUES (:i, 'Testville', 'AS', '1', ST_GeomFromText(:w, 4326), "
        "        ST_Transform(ST_GeomFromText(:w, 4326), 2975), :sf, "
        "        ST_Centroid(ST_GeomFromText(:w, 4326)), ST_Envelope(ST_GeomFromText(:w, 4326))) "
        "RETURNING id"), {"i": idu, "w": _WKT, "sf": surface}).scalar()


def _cascade_zone(s, pid: int, detail: str) -> None:
    s.execute(text(
        "INSERT INTO dryrun_cascade_results (run_label, parcel_id, layer_name, result, detail) "
        "VALUES (:r, :p, 'zonage_plu_gpu', 'PASS', :d)"), {"r": RUN, "p": pid, "d": detail})


def _eval(s, pid: int, status: str) -> None:
    s.execute(text(
        "INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, "
        "opportunity_score, status) VALUES (:r, :p, 80, 40, :st)"), {"r": RUN, "p": pid, "st": status})


def _score(s, idu: str, tier: str) -> None:
    s.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, contrib_z, contrib_d, "
        "  top5_contributions, copro, tier, model_version) "
        "VALUES (:r, :i, 0.2, 3.0, 0, 0, '[]', false, :t, 'm137-test')"), {"r": RUN, "i": idu, "t": tier})


def _residuel(s, pid: int, sdp: int) -> None:
    s.execute(text("INSERT INTO parcel_residuel (parcel_id, sdp_residuelle_m2) VALUES (:p, :s)"),
              {"p": pid, "s": sdp})


def _seed(s):
    # run v2 servi (pour _v2run / _score_v2_run_id)
    s.execute(text("INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, n_parcelles) "
                   "VALUES (:r, 'm137', 'sha', '{}', 0) ON CONFLICT (run_id) DO NOTHING"), {"r": RUN})
    # 1 parcelle U → sert le RATIO d'analogie (sdp/surface = 200/1000 = 0,2)
    up = _parcel(s, "97499000ZU0001", 1000)
    _cascade_zone(s, up, "Zone PLU « U » (urbaine).")
    _residuel(s, up, 200)
    # 2 parcelles AUc ≥ 300 m² → le vivier de la zone à simuler
    for i, idu in enumerate(("97499000ZA0001", "97499000ZA0002")):
        pid = _parcel(s, idu, 2000)
        _cascade_zone(s, pid, "Zone PLU « AUc » (à urbaniser).")
        _eval(s, pid, "a_creuser")
        _score(s, idu, "a_creuser")
    s.flush()


def test_simulplu_ne_leve_pas_et_dit_son_total(db_session):
    _seed(db_session)
    out = moteurs.simulplu(zone="AUc", commune="Testville", offset=0, db=db_session)   # ne lève pas
    assert out["zone"] == "AUc"
    assert out["n_total"] == 2 and out["n_parcelles"] == 2
    assert out["cap"] >= 2 and out["tronquee"] is False        # tout tient sous le plafond
    assert out["ratio_analogie"] > 0                            # ratio d'analogie servi par la parcelle U
    assert len(out["items"]) == 2
    it = out["items"][0]
    assert "q_actuel" not in it and "q_score" not in it        # ménage M137-O : plus d'alias mort servi
    assert it["bascule_potentielle"] is True                   # 2000 × 0,2 = 400 ≥ 300, tier a_creuser


def test_simulplu_dit_la_troncature_quand_plafonnee(db_session, monkeypatch):
    _seed(db_session)
    monkeypatch.setattr(moteurs, "_moteurs_cap", lambda name, defaut: 1)   # plafond forcé à 1
    out = moteurs.simulplu(zone="AUc", commune="Testville", offset=0, db=db_session)
    assert out["n_total"] == 2 and out["n_parcelles"] == 1 and out["cap"] == 1
    assert out["tronquee"] is True                             # l'écran DIT « les 1 premières sur 2 »


def test_simulplu_zones_liste_les_au(db_session):
    _seed(db_session)
    # spatial_layers alimente /simulplu/zones — vide en base de test, l'endpoint ne doit pas lever.
    assert isinstance(moteurs.simulplu_zones(commune="Testville", db=db_session), list)


# ── M137-Q — fusion « Procédure & changement » : le radar liste les communes en procédure ────────

def test_communes_en_procedure_actives_seulement():
    """Le radar (point de calcul unique) ne remonte QUE les procédures actives servies : SOURCE,
    révision/élaboration, non dormantes. Chacune porte son type et sa date."""
    from labuse import veille_plu as V
    items = V.communes_en_procedure()
    insees = {it["insee"] for it in items}
    assert insees == {"97409", "97413", "97423"}       # Saint-André, Saint-Leu, Trois-Bassins
    assert "97417" not in insees                        # Saint-Philippe = prescrite_dormante → exclue
    for it in items:
        assert it["type"] and it["date_acte"] and it["etat"]


def test_simulplu_procedures_ne_leve_pas_sans_table_contexte(db_session):
    """L'endpoint ne 500 JAMAIS quand la table de contexte n'est pas matérialisée (base de test nue,
    même contrat data-gap que M136) : `to_regclass` garde, on retombe sur le nom registre. Le radar
    liste bien les 3 procédures actives, chacune avec son type et son état."""
    out = moteurs.simulplu_procedures(db=db_session)    # ne lève pas malgré commune_conso_enaf absente
    assert {c["insee"] for c in out["communes"]} == {"97409", "97413", "97423"}
    tb = next(c for c in out["communes"] if c["insee"] == "97423")
    assert tb["commune"] == tb["commune_radar"] == "Trois-Bassins"   # repli nom registre (table absente)
    assert tb["type"] and tb["etat"]
