"""SCORING-3 · L4 — le potentiel du run candidat : valeur créée, indice
d'opportunité, accès. Vérifie les DÉFINITIONS (sources nommées), la sémantique
NULL (hors_plu / commune sans ventes → honnête, jamais un faux zéro) et le
cloisonnement du score (ni p_raw, ni rang, ni tier touchés)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.scoring.p_v2.potentiel import backfill_run

pytestmark = pytest.mark.db

RUN = "q_test_potentiel"


@pytest.fixture
def run_minimal(db_session):
    """Un run de 3 parcelles : SDP > 0 (valeur calculable), SDP 0 (valeur 0),
    hors_plu (NULL honnête) — avec un marché communal 2025 (med 2 000 €/m²)."""
    suf = uuid.uuid4().hex[:4].upper()
    idus = [f"97411000AA{i}{suf[:2]}0" for i in range(3)]
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS p_model_ext_mut_l2 ("
        " idu varchar(14), id_mutation text, date_mutation date,"
        " pm2_bati float, exclue_l2f boolean DEFAULT false)"))
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS parcel_residuel ("
        " parcel_id integer PRIMARY KEY REFERENCES parcels(id) ON DELETE CASCADE,"
        " taux_emprise_pct integer, pct_potentiel integer, sous_densite boolean,"
        " sdp_residuelle_m2 integer, capacite_estimee boolean,"
        " computed_at timestamptz NOT NULL DEFAULT now(), cause text)"))
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS parcel_adresse ("
        " idu varchar(14), ban_voie text, ban_cp text, ban_commune text)"))
    db_session.execute(text("DELETE FROM p_score_v2_runs WHERE run_id = :r"), {"r": RUN})
    db_session.execute(text(
        "INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, "
        " n_parcelles, computed_at) "
        "VALUES (:r, 'q_v12', 'x', '{\"annee_features\": 2026}', 3, now())"), {"r": RUN})
    pids = []
    for idu in idus:
        pid = db_session.execute(text(
            "INSERT INTO parcels (idu, commune, geom, created_at, updated_at) "
            "VALUES (:i, 'Saint-Paul', ST_GeomFromText('POINT(55.5 -21.1)', 4326), "
            "now(), now()) RETURNING id"), {"i": idu}).scalar()
        pids.append(pid)
    donnees = [(pids[0], 300, None), (pids[1], 0, "terrain_exigu"),
               (pids[2], None, "hors_plu")]
    for pid, sdp, cause in donnees:
        db_session.execute(text(
            "INSERT INTO parcel_residuel (parcel_id, sdp_residuelle_m2, cause) "
            "VALUES (:p, :s, :c)"), {"p": pid, "s": sdp, "c": cause})
    for i, (idu, p_raw) in enumerate(zip(idus, (0.10, 0.05, 0.02))):
        db_session.execute(text(
            "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, "
            " contrib_z, contrib_d, copro, model_version, computed_at, rang, tier) "
            "VALUES (:r, :i, :p, 1.0, 0, 0, false, 'q_v12', now(), :g, 'chaude')"),
            {"r": RUN, "i": idu, "p": p_raw, "g": i + 1})
    # marché communal 2025 (Y-1 du run 2026) : 3 ventes, médiane 2 000 €/m²
    for j, pm2 in enumerate((1500.0, 2000.0, 2500.0)):
        db_session.execute(text(
            "INSERT INTO p_model_ext_mut_l2 (idu, id_mutation, date_mutation, pm2_bati) "
            "VALUES (:i, :m, '2025-06-01', :v)"),
            {"i": idus[0], "m": f"m{j}-{suf}", "v": pm2})
    # accès : la 1re parcelle a une adresse BAN, aucune n'a de SIREN
    db_session.execute(text(
        "INSERT INTO parcel_adresse (idu, ban_voie) VALUES (:i, '12 rue des Aloès')"),
        {"i": idus[0]})
    return idus


def _lig(db_session, idu):
    return db_session.execute(text(
        "SELECT potentiel_sdp_m2, prix_secteur_eur_m2, valeur_creee_eur, "
        "       valeur_creee_min_eur, valeur_creee_max_eur, indice_opportunite, "
        "       acces_pm_siren, acces_courrier, p_raw, rang, tier "
        "FROM parcel_p_score_v2 WHERE run_id = :r AND parcelle_id = :i"),
        {"r": RUN, "i": idu}).mappings().first()


def test_backfill_potentiel_valeurs_et_intervalle(db_session, run_minimal):
    idus = run_minimal
    stats = backfill_run(db_session, RUN)
    assert stats["n"] == 3 and stats["n_valeur"] == 2 and stats["n_valeur_pos"] == 1
    a = _lig(db_session, idus[0])
    # 300 m² × médiane 2 000 = 600 000 € ; intervalle honnête = q1/q3 communaux
    assert a["potentiel_sdp_m2"] == 300 and a["prix_secteur_eur_m2"] == 2000.0
    assert a["valeur_creee_eur"] == 600_000
    assert a["valeur_creee_min_eur"] == 300 * 1750.0   # q1 (percentile_cont interpolé)
    assert a["valeur_creee_max_eur"] == 300 * 2250.0   # q3
    assert a["acces_courrier"] is True and a["acces_pm_siren"] is False
    # SDP 0 = réponse : valeur 0, jamais NULL
    b = _lig(db_session, idus[1])
    assert b["potentiel_sdp_m2"] == 0 and b["valeur_creee_eur"] == 0
    # hors_plu : NULL honnête partout (rien d'inventé)
    c = _lig(db_session, idus[2])
    assert c["potentiel_sdp_m2"] is None and c["valeur_creee_eur"] is None
    assert c["indice_opportunite"] is None


def test_backfill_ne_touche_pas_le_score(db_session, run_minimal):
    """Cloisonnement du score : p_raw / rang / tier STRICTEMENT inchangés."""
    idus = run_minimal

    def _score(i):
        return db_session.execute(text(
            "SELECT p_raw, rang, tier FROM parcel_p_score_v2 "
            "WHERE run_id = :r AND parcelle_id = :i"), {"r": RUN, "i": i}).first()

    avant = {i: _score(i) for i in idus}
    backfill_run(db_session, RUN)
    for i in idus:
        assert _score(i) == avant[i]


def test_backfill_ecrit_les_definitions_au_registre(db_session, run_minimal):
    backfill_run(db_session, RUN)
    pot = db_session.execute(text(
        "SELECT params -> 'potentiel' FROM p_score_v2_runs WHERE run_id = :r"),
        {"r": RUN}).scalar()
    assert pot and pot["annee_prix_secteur"] == 2025
    defs = pot["definitions"]
    # chaque terme NOMME sa source (traçabilité datée)
    assert "DVF" in defs["prix_secteur_eur_m2"]
    assert "parcel_residuel" in defs["potentiel_sdp_m2"]
    assert "jamais partagé entre comptes" in defs["deja_contacte"]
