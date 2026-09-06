"""CIRCUIT-5 lot 3 — le verrou des versions : une seule version servie, partout ; la sonde
écrit des ids. Chaque verrou prouvé CASSÉ sur un cas construit, puis VERT."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import circuit_verrous as CV, sonde_circuit
from labuse.registre import tables as T

pytestmark = pytest.mark.verrous


# ── V3a — une génération servie par réservoir ───────────────────────────────────────────

def test_v3a_prouve_casse_sur_une_generation_en_trop():
    """Une table `dvf_mutations__essai` posée exprès dans le schéma injecté (ni __attente ni
    __precedente) casse le verrou — deux millésimes côte à côte ne passent plus."""
    schema = T.tables_carte() | {"dvf_mutations__essai"}
    r = CV.verrou_versions_generations(schema=schema)
    assert r.verdict == "casse"
    assert any("dvf_mutations__essai" in d for d in r.details)


def test_v3a_l_echange_circuit3_reste_admis():
    schema = T.tables_carte() | {"dvf_mutations__attente", "dvf_mutations__precedente"}
    r = CV.verrou_versions_generations(schema=schema)
    assert r.verdict == "ok"


# ── V3b — zéro eau ancienne hors étiqueté ───────────────────────────────────────────────

def test_v3b_prouve_casse_et_nomme_la_donnee_et_le_robinet(monkeypatch):
    """Une eau ouverte posée exprès casse le verrou, et le détail NOMME la donnée et le
    robinet (l'exigence du mandat 3.2) ; la même eau étiquetée (gel assumé) le laisse vert."""
    ligne = ("dpe_connu", "payload fiche (bloc dpe_connu, non affiché)",
             "ingestion 2026-08-01", "amont vu 2026-09-01", "cron DPE : ré-ingérer", "ouvert")
    monkeypatch.setattr(sonde_circuit, "eau_lignes", lambda db: [ligne])
    r = CV.verrou_eau_ancienne(None)
    assert r.verdict == "casse"
    assert any("dpe_connu" in d and "payload fiche" in d for d in r.details)

    monkeypatch.setattr(sonde_circuit, "eau_lignes",
                        lambda db: [ligne[:5] + ("etiquete",)])
    r2 = CV.verrou_eau_ancienne(None)
    assert r2.verdict == "ok"
    assert "1 gel" in r2.preuve


# ── V3c — la sonde écrit des ids (dette CIRCUIT-P3) ─────────────────────────────────────

def test_robinet_id_de_resout_ids_correspondances_et_moteurs():
    assert sonde_circuit.robinet_id_de("fiche_commune_zonage") == "fiche_commune_zonage"
    assert sonde_circuit.robinet_id_de("http:/parcels") == "fiche_parcelle_entete"
    assert sonde_circuit.robinet_id_de("attrs.niveau (servi)") == "couche_alea_inondation"
    # un côté moteur/SQL n'est PAS un robinet : pas d'id, le libellé reste
    assert sonde_circuit.robinet_id_de("moteur:zonage") is None
    assert sonde_circuit.robinet_id_de("sql:parcels.surface_m2") is None
    # le bloc DPE n'est affiché par AUCUN robinet (Fiche.tsx:1492) : pas d'id non plus
    assert sonde_circuit.robinet_id_de("payload fiche (bloc dpe_connu, non affiché)") is None


@pytest.mark.db
def test_v3c_prouve_casse_sur_un_robinet_sans_id_puis_backfill(db_session):
    """PREUVE : une ligne d'écart écrite À L'ANCIENNE (libellé de robinet du registre, id
    NULL) casse V3c ; `ensure()` (backfill de la migration) la répare ; V3c repasse vert."""
    sonde_circuit.ensure(db_session)
    db_session.execute(text(
        "INSERT INTO circuit_ecarts (chiffre_id, cle, robinet_a, robinet_b, cause) "
        "VALUES ('part_zone_U_pct', 'zz-preuve-v3c', 'fiche_commune_zonage', 'moteur:zonage', 'table') "
        "ON CONFLICT DO NOTHING"))
    db_session.execute(text(
        "UPDATE circuit_ecarts SET robinet_a_id = NULL WHERE cle = 'zz-preuve-v3c'"))
    r = CV.verrou_sonde_ids(db_session)
    assert r.verdict == "casse"
    assert any("fiche_commune_zonage" in d for d in r.details)

    sonde_circuit.ensure(db_session)          # rejoue le backfill
    r2 = CV.verrou_sonde_ids(db_session)
    assert not any("zz-preuve-v3c" in d for d in r2.details)
    ligne = db_session.execute(text(
        "SELECT robinet_a_id, robinet_b_id FROM circuit_ecarts WHERE cle = 'zz-preuve-v3c'")).first()
    assert ligne[0] == "fiche_commune_zonage" and ligne[1] is None


@pytest.mark.db
def test_v3c_chiffre_hors_registre_casse(db_session):
    sonde_circuit.ensure(db_session)
    db_session.execute(text(
        "INSERT INTO circuit_eau_ancienne (chiffre_id, robinet, tampon, attendu, mecanisme, statut) "
        "VALUES ('(chiffres fantomes)', 'nulle part', 't', 'a', 'm', 'ouvert')"))
    r = CV.verrou_sonde_ids(db_session)
    assert r.verdict == "casse"
    assert any("chiffres fantomes" in d for d in r.details)


@pytest.mark.db
def test_upsert_ecart_ecrit_les_ids_a_l_insertion(db_session):
    """La sonde n'écrit plus jamais un libellé seul : l'upsert pose les ids lui-même."""
    sonde_circuit.ensure(db_session)
    sonde_circuit._upsert_ecart(db_session, "part_zone_U_pct", "zz-preuve-upsert",
                                "fiche_commune_zonage", 1, "moteur:zonage", 2, "table")
    row = db_session.execute(text(
        "SELECT robinet_a_id, robinet_b_id FROM circuit_ecarts WHERE cle = 'zz-preuve-upsert'")).first()
    assert row[0] == "fiche_commune_zonage" and row[1] is None


def test_eau_dpe_attribuable_au_registre():
    """FICHE-1 lot 2 — `dpe_connu` RÉTABLI : servi par le tiroir « Le bien »
    (fiche_parcelle_le_bien), plus en_attente, lit le réservoir dpe_ademe (non muet, V1d)."""
    from labuse.registre import ROBINETS
    from labuse.registre.donnees import DONNEES
    d = DONNEES["dpe_connu"]
    assert d.reservoirs == ("dpe_ademe",)
    assert d.en_attente is None       # rétabli : n'attend plus le chantier premium
    assert "dpe_connu" in ROBINETS["fiche_parcelle_le_bien"].chiffres
    r = CV.verrou_reservoirs_sans_lecteur()
    assert "dpe_ademe" not in r.details


# ── le passage complet sur la base réelle ───────────────────────────────────────────────

@pytest.mark.local
def test_verrous_lot3_passent_sur_la_base_reelle():
    import os

    from sqlalchemy.orm import sessionmaker

    from labuse import db as db_mod
    real = db_mod.make_engine(os.environ["LABUSE_APP_DATABASE_URL"])
    with sessionmaker(bind=real)() as s:
        for f in (CV.verrou_versions_generations, CV.verrou_eau_ancienne, CV.verrou_sonde_ids):
            r = f(s)
            assert r.verdict == "ok", (r.id, r.preuve, r.details[:5])
