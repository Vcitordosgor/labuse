"""CIRCUIT-5 lot 1 — le verrou des tables : chaque verrou est PROUVÉ CASSÉ sur un cas
construit (une table orpheline posée exprès, une fonction témoin qui la lit), puis VERT
une fois la garde en place (règle 3 du mandat — preuve avant affirmation).

Les tests sont hermétiques : le schéma est INJECTÉ (pas de dépendance au contenu accumulé
de labuse_test) ; seuls V1b (capture des requêtes) et le passage complet (`-m local`)
touchent une base.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import circuit_verrous as CV
from labuse.registre import tables as T

pytestmark = pytest.mark.verrous


# ── V1a — analyse statique ──────────────────────────────────────────────────────────────

def test_v1a_prouve_casse_sur_fonction_temoin(tmp_path):
    """Une fonction témoin qui lit une table orpheline (posée exprès dans le schéma injecté)
    CASSE le verrou — et le message nomme le fichier et la table."""
    temoin = tmp_path / "moteur_temoin.py"
    temoin.write_text(
        'def lire(db):\n'
        '    return db.execute("SELECT v FROM zz_orpheline_temoin JOIN parcels USING (idu)")\n',
        encoding="utf-8")
    schema = {"zz_orpheline_temoin", "parcels"}
    r = CV.verrou_tables_statique(sources=[temoin], schema=schema)
    assert r.verdict == "casse"
    assert any("zz_orpheline_temoin" in d for d in r.details)


def test_v1a_vert_quand_le_temoin_ne_lit_que_la_carte(tmp_path):
    temoin = tmp_path / "moteur_temoin.py"
    temoin.write_text(
        'def lire(db):\n'
        '    return db.execute("SELECT count(*) FROM parcels JOIN dvf_mutations USING (idu)")\n',
        encoding="utf-8")
    r = CV.verrou_tables_statique(sources=[temoin], schema={"parcels", "dvf_mutations"})
    assert r.verdict == "ok"


def test_v1a_passe_plats_du_registre_sont_dans_la_carte():
    """Chaque `Donnee.table` du registre qui EST une relation existante appartient à la carte
    (le schéma injecté = exactement les tables déclarées → aucun hors-carte possible, et le
    parseur ne se laisse pas piéger par `parcels.surface_m2` ou `spatial_layers (kind=…)`)."""
    r = CV.verrou_tables_statique(sources=[], schema=T.tables_carte())
    assert r.verdict == "ok", r.details


def test_v1a_injouable_sans_schema_est_un_verrou_casse():
    r = CV.verrou_tables_statique(sources=[])
    assert r.verdict == "casse"
    assert "injouable" in r.preuve


def test_table_declaree_comprend_les_formats_du_registre():
    assert CV.table_declaree("parcels.surface_m2") == "parcels"
    assert CV.table_declaree("commune_contexte_sru (objectif_pct, taux_lls)") == "commune_contexte_sru"
    assert CV.table_declaree("spatial_layers (kind=znieff, subtype=type I/II)") == "spatial_layers"
    assert CV.table_declaree("(web — aucun réservoir, marquage obligatoire)") is None
    assert CV.table_declaree("dvf_mutations__precedente") == "dvf_mutations"


# ── V1b — lecture à l'exécution (journal des requêtes de la session) ───────────────────

@pytest.mark.db
def test_v1b_prouve_casse_si_la_sonde_touche_une_orpheline(db_session, monkeypatch):
    """Une sonde qui lit une table orpheline (posée exprès) casse le verrou ; la même sonde
    restreinte à la carte le laisse vert. Même mécanisme de capture que la commande."""
    db_session.execute(text("CREATE TABLE IF NOT EXISTS zz_orpheline_v1b (v int)"))

    from labuse import sonde_circuit

    def _sonde_infidele(db):
        db.execute(text("SELECT count(*) FROM zz_orpheline_v1b")).scalar()
        return {}

    monkeypatch.setattr(sonde_circuit, "verifier_robinets", _sonde_infidele)
    r = CV.verrou_tables_execution(db_session)
    assert r.verdict == "casse"
    assert "zz_orpheline_v1b" in r.details

    def _sonde_fidele(db):
        db.execute(text("SELECT 1")).scalar()
        return {}

    monkeypatch.setattr(sonde_circuit, "verifier_robinets", _sonde_fidele)
    r2 = CV.verrou_tables_execution(db_session)
    assert r2.verdict == "ok"


def test_journal_requetes_normalise_l_echange_circuit3():
    """`x__attente` / `x__precedente` appartiennent au réservoir de `x` — jamais des
    orphelines de passage pendant un échange."""
    assert CV.tables_citees("SELECT * FROM dvf_mutations__attente") == {"dvf_mutations"}
    assert CV.tables_citees("DELETE FROM public.sitadel_permits__precedente") == {"sitadel_permits"}


# ── V1c — les orphelines sont listées, avec une action, jamais un DROP ──────────────────

def test_v1c_prouve_casse_sur_orpheline_sans_action(monkeypatch):
    """Une table orpheline posée exprès SANS action proposée casse le verrou (trou de
    curation) ; avec une action proposée, elle redevient « à décider » (le geste de Vic)."""
    relations = T.tables_carte() | {"zz_perdue_expres"}
    monkeypatch.setattr(CV, "relations_schema", lambda db: relations)
    r = CV.verrou_tables_orphelines(None)
    assert r.verdict == "casse"
    assert "zz_perdue_expres" in r.details

    monkeypatch.setitem(T.ACTIONS_PROPOSEES, "zz_perdue_expres", "purger (posée exprès)")
    r2 = CV.verrou_tables_orphelines(None)
    assert r2.verdict == "a_decider"
    assert "zz_perdue_expres" in r2.details


def test_v1c_vert_quand_le_schema_egale_la_carte(monkeypatch):
    monkeypatch.setattr(CV, "relations_schema", lambda db: T.tables_carte())
    r = CV.verrou_tables_orphelines(None)
    assert r.verdict == "ok"


def test_orphelines_est_calcule_jamais_en_dur():
    """La liste des orphelines est une DIFFÉRENCE (schéma − carte) : une table nouvelle
    inconnue sort orpheline sans qu'aucune liste n'ait à être tenue à la main."""
    assert T.orphelines(T.tables_carte() | {"zz_nouvelle"}) == {"zz_nouvelle"}
    assert T.orphelines(T.tables_carte()) == set()


# ── V1d — réservoirs sans lecteur ───────────────────────────────────────────────────────

def test_v1d_prouve_un_reservoir_muet(monkeypatch):
    """Un réservoir posé exprès (avec table servie, sans note) qu'aucune donnée ne lit sort
    dans « à décider » — la question est nommée."""
    carte = dict(T.RESERVOIR_TABLES)
    carte["zz_reservoir_muet"] = T.ReservoirTables(("zz_table_que_personne_ne_lit",))
    monkeypatch.setattr(T, "RESERVOIR_TABLES", carte)
    r = CV.verrou_reservoirs_sans_lecteur()
    assert r.verdict == "a_decider"
    assert "zz_reservoir_muet" in r.details


def test_v1d_un_reservoir_lu_via_table_declaree_n_est_pas_muet():
    """Le registre lit certains réservoirs par `table=`/`kind=` plutôt que `reservoirs=` :
    ils ne sont PAS muets (gpu_plu via zone_plu_famille, znieff via kind=znieff…)."""
    r = CV.verrou_reservoirs_sans_lecteur()
    assert "gpu_plu_api_carto" not in r.details
    assert "znieff_inpn" not in r.details
    assert "bd_topo" not in r.details


# ── cohérence de la carte elle-même ─────────────────────────────────────────────────────

def test_carte_couvre_les_reservoirs_du_registre():
    """Chaque réservoir nommé par une donnée du registre existe dans la carte — aucun slug
    fantôme d'un côté ni de l'autre."""
    from labuse.registre.donnees import DONNEES
    references = {res for d in DONNEES.values() for res in d.reservoirs}
    assert references <= set(T.RESERVOIR_TABLES), sorted(references - set(T.RESERVOIR_TABLES))


def test_carte_familles_disjointes():
    """Une table appartient à UNE famille : réservoir, fabrication ou exploitation — jamais
    deux (le doublon rendrait le « qui la sert » illisible)."""
    familles = [set(T.TABLES_FABRIQUEES), set(T.TABLES_EXPLOITATION), set(T.POSTGIS)]
    for i, a in enumerate(familles):
        for b in familles[i + 1:]:
            assert not (a & b), sorted(a & b)
    # les tables de réservoirs peuvent être partagées entre réservoirs (ortho/IRC), mais pas
    # avec les fabrications ni l'exploitation
    assert not (T.tables_reservoirs() & set(T.TABLES_FABRIQUEES))
    assert not (T.tables_reservoirs() & set(T.TABLES_EXPLOITATION))


# ── le passage complet sur la BASE RÉELLE (hors CI — CIRCUIT-P3 3.2) ────────────────────

@pytest.mark.local
def test_verrous_lot1_passent_sur_la_base_reelle():
    """`labuse circuit verrous` ne doit trouver AUCUN verrou cassé sur la base servie locale
    (les « à décider » — orphelines, réservoirs muets — sont admis : c'est le geste de Vic).
    Même motif que CIRCUIT-P3 3.2 : engine reconstruit sur LABUSE_APP_DATABASE_URL."""
    import os

    from sqlalchemy.orm import sessionmaker

    from labuse import db as db_mod
    app_url = os.environ.get("LABUSE_APP_DATABASE_URL")
    assert app_url, "LABUSE_APP_DATABASE_URL absent (base réelle inconnue)"
    real = db_mod.make_engine(app_url)
    with sessionmaker(bind=real)() as s:
        resultats = CV.jouer_tous(s)
    casses = [r for r in resultats if r.verdict == "casse"]
    assert not casses, [(r.id, r.preuve, r.details[:5]) for r in casses]
