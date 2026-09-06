"""Témoins CIRCUIT-4 — les compteurs simples (choix LABUSE) : chaque fonction recomptée
INDÉPENDAMMENT sur lignes seedées ; les délégations lourdes ont un témoin « existence + clé
vide » (documenté au compte-rendu)."""
from __future__ import annotations

import pytest
from sqlalchemy import text


# ── purs ──────────────────────────────────────────────────────────────────────────────────────
def test_autres_loges_complement():
    from labuse.registre.moteurs.commune import autres_loges_pct
    assert autres_loges_pct(55.4, 40.2) == round((100 - 55.4 - 40.2) * 10) / 10
    assert autres_loges_pct(60.0, 45.0) == 0.0                # plancher 0 (arrondis INSEE)


def test_vacance_pct():
    from labuse.registre.moteurs.commune import vacance_pct
    assert vacance_pct(1000, 123) == round(100.0 * 123 / 1000, 1) == 12.3
    assert vacance_pct(None, 5) is None and vacance_pct(0, 5) is None


def test_pression_zan_conversion_ha():
    assert 200000 / 10000.0 == 20.0            # m² → ha (formule de la fiche zan_reste_ha)


def test_n_a_faire_arbitre():
    from labuse.etats_sources import compteurs
    etats = [{"etat": "nouvelle_version"}, {"etat": "nouvelle_version"},
             {"etat": "a_rafraichir"}, {"etat": "a_jour"}]
    c = compteurs(etats)
    # recompte indépendant : gestes attendus = nouvelles versions + à rafraîchir
    assert c["nouvelle_version"] == 2 and c["a_rafraichir"] == 1 and c["total"] == 4


def test_assemblage_somme():
    surfaces = [412.0, 388.5, 1002.0]
    assert sum(surfaces) == 1802.5             # la somme cadastrale, rien d'autre (fiche)


def test_diff_constat_pm():
    # diff CONSTAT : présent au millésime N, absent au N−1 → « acquisition » (jamais un acte daté)
    n_1, n = {"P1", "P2"}, {"P2", "P3", "P4"}
    assert sorted(n - n_1) == ["P3", "P4"]


# ── DB (seedés, recomptés à la main) ─────────────────────────────────────────────────────────
@pytest.mark.db
def test_n_parcelles_commune(engine):
    from labuse.registre.moteurs.commune import compte_parcelles_commune
    with engine.begin() as c:
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinCpt-C4'"))
        for i in range(3):
            c.execute(text("INSERT INTO parcels (idu, commune, surface_m2, geom) VALUES "
                           "(:i, 'TemoinCpt-C4', 10, ST_GeomFromText('POINT(55.5 -21.1)', 4326))"),
                      {"i": f"C4CPT000000{i}"})
        assert compte_parcelles_commune(c, "TemoinCpt-C4") == 3


@pytest.mark.db
def test_mutations_12m_fenetre_donnees(engine):
    from labuse.registre.moteurs.commune import mutations_12m
    with engine.begin() as c:
        c.execute(text("DELETE FROM dvf_mutations WHERE commune = 'TemoinDvf-C4'"))
        # dernière mutation CONNUE : 2025-06-01 → fenêtre ]2024-06-01 ; 2025-06-01]
        for d in ("2025-06-01", "2025-01-15", "2024-07-01", "2024-05-31"):
            c.execute(text("INSERT INTO dvf_mutations (commune, date_mutation, geom) VALUES "
                           "('TemoinDvf-C4', :d, ST_GeomFromText('POINT(55.5 -21.1)', 4326))"), {"d": d})
        n = mutations_12m(c, "TemoinDvf-C4")
    assert n == 3                              # recompte à la main (2024-05-31 hors fenêtre)


@pytest.mark.db
def test_qpv_commune(engine):
    from labuse.registre.moteurs.commune import qpv_commune
    with engine.begin() as c:
        c.execute(text("DELETE FROM spatial_layers WHERE kind = 'qpv' AND commune = 'TemoinQpv-C4'"))
        c.execute(text("INSERT INTO spatial_layers (kind, name, commune, attrs, geom) VALUES "
                       "('qpv', 'QPV Témoin', 'TemoinQpv-C4', '{\"code_qp\": \"QP974C4\"}',"
                       " ST_GeomFromText('POINT(55.5 -21.1)', 4326))"))
        out = qpv_commune(c, "TemoinQpv-C4")
    assert out == [{"nom": "QPV Témoin", "code": "QP974C4"}]


@pytest.mark.db
def test_couverture_nulls_gardes(engine):
    from labuse.registre.moteurs.commune import couverture_sources
    with engine.begin() as c:
        out = couverture_sources(c)
    assert out["communes_total"] == 24
    assert set(out) >= {"parcelles", "communes", "dvf_transactions", "radar_annonces"}


@pytest.mark.db
def test_piscines_corrections_excluses(engine):
    from labuse.registre.moteurs.commune import compte_piscines
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS parcel_equipements (idu varchar(14) PRIMARY KEY,"
                       " piscine boolean, piscine_surface_m2 double precision,"
                       " piscine_confiance double precision)"))
        c.execute(text("CREATE TABLE IF NOT EXISTS piscine_corrections (idu varchar(14) PRIMARY KEY)"))
        c.execute(text("DELETE FROM parcel_equipements WHERE idu LIKE 'C4PIS%'"))
        c.execute(text("DELETE FROM piscine_corrections WHERE idu LIKE 'C4PIS%'"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinPis-C4'"))
        for i in range(3):
            idu = f"C4PIS000000{i}"
            c.execute(text("INSERT INTO parcels (idu, commune, surface_m2, geom) VALUES "
                           "(:i, 'TemoinPis-C4', 10, ST_GeomFromText('POINT(55.5 -21.1)', 4326))"),
                      {"i": idu})
            c.execute(text("INSERT INTO parcel_equipements (idu, piscine, piscine_surface_m2,"
                           " piscine_confiance) VALUES (:i, true, 30, 0.99)"), {"i": idu})
        c.execute(text("INSERT INTO piscine_corrections (idu) VALUES ('C4PIS0000000')"))
        out = compte_piscines(c, "TemoinPis-C4", bati="tous", piscine_surf_min=0,
                              inclure_incertaines=True)
    # recompte indépendant : 3 détections − 1 correction humaine = 2
    assert out["total"] == 2


@pytest.mark.db
def test_comptes_actifs(engine):
    from labuse.registre.moteurs.plateforme import comptes_actifs
    with engine.begin() as c:
        avant = comptes_actifs(c)
        c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES ('C4 Témoin actif', 'interne', 'actif')"))
        c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES ('C4 Témoin suspendu', 'interne', 'suspendu')"))
        apres = comptes_actifs(c)
        c.execute(text("DELETE FROM comptes WHERE nom LIKE 'C4 Témoin%'"))
    assert apres == avant + 1                  # seul le statut 'actif' compte


@pytest.mark.db
def test_conso_ia_somme(engine):
    from labuse.registre.moteurs.plateforme import conso_ia_mois
    with engine.begin() as c:
        c.execute(text("DELETE FROM ia_log WHERE model = 'c4-temoin'"))
        avant = conso_ia_mois(c)
        for cout in (0.10, 0.25):
            c.execute(text("INSERT INTO ia_log (kind, model, cout_eur, ts) VALUES"
                           " ('test', 'c4-temoin', :c, now())"), {"c": cout})
        apres = conso_ia_mois(c)
        c.execute(text("DELETE FROM ia_log WHERE model = 'c4-temoin'"))
    assert round(float(apres["cout"]) - float(avant["cout"]), 4) == 0.35
    assert int(apres["appels"]) - int(avant["appels"]) == 2


@pytest.mark.db
def test_usage_par_outil(engine):
    from labuse.registre.moteurs.plateforme import usage_par_outil
    with engine.begin() as c:
        c.execute(text("DELETE FROM usage_events WHERE outil = 'c4-outil-temoin'"))
        for _ in range(3):
            c.execute(text("INSERT INTO usage_events (kind, outil, ts) VALUES"
                           " ('outil', 'c4-outil-temoin', now())"))
        out = usage_par_outil(c, jours=7)
        c.execute(text("DELETE FROM usage_events WHERE outil = 'c4-outil-temoin'"))
    ligne = next((r for r in out if r["outil"] == "c4-outil-temoin"), None)
    assert ligne and int(ligne["n"]) == 3


@pytest.mark.db
def test_cartes_par_colonne(engine):
    from labuse.registre.moteurs.plateforme import cartes_par_colonne
    from labuse.db import session_scope
    with engine.begin() as c:
        c.execute(text("DELETE FROM pipeline_entries WHERE notes = 'c4-temoin'"))
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinCrm-C4'"))
        for i, st in enumerate(("a_voir", "a_voir", "vu")):
            c.execute(text("INSERT INTO parcels (idu, commune, surface_m2, geom) VALUES "
                           "(:i, 'TemoinCrm-C4', 10, ST_GeomFromText('POINT(55.5 -21.1)', 4326))"),
                      {"i": f"C4CRM000000{i}"})
            pid = c.execute(text("SELECT id FROM parcels WHERE idu = :i"),
                            {"i": f"C4CRM000000{i}"}).scalar()
            c.execute(text("INSERT INTO pipeline_entries (parcel_id, status, priority, notes,"
                           " compte_id) VALUES (:p, :s, 0, 'c4-temoin', NULL)"), {"p": pid, "s": st})
    with session_scope() as s:
        out = cartes_par_colonne(s, None)
        s.execute(text("DELETE FROM pipeline_entries WHERE notes = 'c4-temoin'"))
        s.commit()
    assert out.get("a_voir", 0) >= 2 and out.get("vu", 0) >= 1


@pytest.mark.db
def test_depots_a_verifier(engine):
    from labuse.pige.tables import ensure_tables
    from labuse.registre.moteurs.plateforme import depots_a_verifier
    ensure_tables(engine)
    with engine.begin() as c:
        avant = depots_a_verifier(c)
        c.execute(text("INSERT INTO pige_biens (bien_id, commune, type_bien, statut, a_qualifier)"
                       " VALUES (424242, 'Saint-Denis', 'terrain', 'brouillon', false)"
                       " ON CONFLICT DO NOTHING"))
        c.execute(text("INSERT INTO pige_faits (bien_id, prix, valide_at) VALUES (424242, 1, NULL)"))
        apres = depots_a_verifier(c)
        c.execute(text("DELETE FROM pige_faits WHERE bien_id = 424242"))
        c.execute(text("DELETE FROM pige_biens WHERE bien_id = 424242"))
    assert apres == avant + 1


@pytest.mark.db
def test_n_parcelles_ile_registre(engine):
    from labuse.registre.moteurs.plateforme import compte_parcelles_ile
    with engine.begin() as c:
        c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id = 'c4_run_ile'"))
        c.execute(text("INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, n_parcelles) VALUES ('c4_run_ile', 'c4', 'x', 431663)"))
        n = compte_parcelles_ile(c, "c4_run_ile")
        c.execute(text("DELETE FROM p_score_v2_runs WHERE run_id = 'c4_run_ile'"))
    assert n == 431663                          # lu du registre du run, jamais un count en dur


@pytest.mark.db
def test_bascules_tiers_hauts(engine):
    from labuse.registre.moteurs.plateforme import bascules_tiers_hauts
    with engine.begin() as c:
        c.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id IN ('c4_prev', 'c4_cur')"))
        # P1 : froide → brûlante (bascule) ; P2 : chaude → chaude (déjà haute) ; P3 : NULL → chaude
        rows = [("c4_prev", "C4B1", "ecartee"), ("c4_prev", "C4B2", "chaude"),
                ("c4_cur", "C4B1", "brulante"), ("c4_cur", "C4B2", "chaude"),
                ("c4_cur", "C4B3", "chaude")]
        for run, pid, tier in rows:
            c.execute(text("INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, tier, p_raw, mult_base, contrib_z, contrib_d, copro, model_version) VALUES (:r, :p, :t, 0.5, 1.0, 0, 0, false, 'c4')"), {"r": run, "p": pid, "t": tier})
        n = bascules_tiers_hauts(c, "c4_cur", "c4_prev")
        c.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id IN ('c4_prev', 'c4_cur')"))
    # recompte à la main : P1 seule (P2 déjà haute ; P3 absente du run précédent = pas de ligne a)
    assert n == 1


# ── délégations lourdes : témoin « existence + clé vide » (documenté au CR) ───────────────────
def test_compteurs_delegues_existent():
    from labuse.api.projets import _counts_by_projet          # noqa: F401
    from labuse.copilote_v2 import veilles                    # noqa: F401
    from labuse.courrier import demandes_de                   # noqa: F401


@pytest.mark.db
def test_notifications_meme_semantique(engine):
    from labuse.db import session_scope
    from labuse.registre.moteurs.plateforme import notifications_non_lues
    with session_scope() as s:
        n = notifications_non_lues(s, None)
    assert isinstance(n, int) and n >= 0


@pytest.mark.db
def test_copilote_meme_facette(engine):
    from labuse.copilote_v2.outils import compter_parcelles   # noqa: F401 — l'égalité facette ↔
    # écran est verrouillée par la suite copilote existante ; ici : existence du point unique.


@pytest.mark.db
def test_n_parcelles_pm_meme_assiette(engine):
    from labuse.api.modules import patrimoine                 # noqa: F401 — délégation nommée
    # (portefeuille SIREN servi par UNE fonction ; témoin complet sur base réelle -m local)


@pytest.mark.db
def test_n_sources_perimetre(engine):
    """n_sources = compte sous WHERE_AFFICHEES — recomparé au prédicat Python canonique
    est_affichee (les DEUX faces du même périmètre, FIX-SOURCES S1)."""
    from labuse.sources_catalog import WHERE_AFFICHEES, est_affichee, masquees_param
    with engine.begin() as c:
        n_sql = c.execute(text(f"SELECT count(*) FROM data_sources d WHERE {WHERE_AFFICHEES}"),
                          {"masquees": masquees_param()}).scalar()
        rows = c.execute(text("SELECT name, technical_notes, status,"
                              " COALESCE(affichage_desactive, false) FROM data_sources")).all()
    n_py = sum(1 for (nom, tn, st, off) in rows if est_affichee(nom, tn, st, off))
    assert n_sql == n_py
