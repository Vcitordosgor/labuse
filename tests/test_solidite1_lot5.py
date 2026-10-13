"""SOLIDITE-1 (Lot 5) — la vérité face aux sources. Sans réseau : le job est au registre ; un écart
servi↔source ouvre un incident agrégé (parcelle + deux valeurs) et un passage propre le referme ; les
« non vérifiable » ne sonnent jamais ; l'échantillonneur stratifié est robuste (aucune écriture)."""
from sqlalchemy import text

from labuse.jobs import JOBS


def test_verite_sources_au_registre():
    j = JOBS.get("verite-sources")
    assert j is not None and j.cadence.startswith("mensuel") and j.cron_utc == "0 2 15 * *"


def test_faux_ouvre_incident_puis_se_referme(db_session):
    from labuse import verite_sources as vs, ops_alertes
    vs.ensure_table(db_session)
    ops_alertes.ensure_table(db_session)
    db_session.execute(text("DELETE FROM ops_incidents WHERE cle = 'verite-sources'"))
    faux = {"lignes": [{"notion": "contenance", "objet": "97415000CW0658",
                        "valeur_labuse": "100", "valeur_oracle": "120",
                        "source_oracle": "API Carto cadastre", "url": "", "verdict": "faux"}],
            "echantillon": [{"idu": "97415000CW0658", "commune": "Saint-Paul", "slot": "contenance_diff"}],
            "bilan": {"vrai": 0, "faux": 1, "non_verifiable": 0}}
    r = vs.journaliser_passage(db_session, faux)
    assert r["faux"] == 1
    assert "verite-sources" in {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}
    passages = vs.derniers_passages(db_session, n=3)
    assert passages and passages[0]["n_faux"] == 1 and passages[0]["faux"][0]["objet"] == "97415000CW0658"
    # passage propre → incident refermé
    propre = {"lignes": [{"notion": "contenance", "objet": "x", "valeur_labuse": "1",
                          "valeur_oracle": "1", "source_oracle": "s", "url": "", "verdict": "vrai"}],
              "echantillon": [{"idu": "x", "commune": "Y", "slot": "aleatoire"}],
              "bilan": {"vrai": 1, "faux": 0, "non_verifiable": 0}}
    vs.journaliser_passage(db_session, propre)
    assert all(i["cle"] != "verite-sources" for i in ops_alertes.incidents_ouverts(db_session))


def test_non_verifiable_ne_sonne_pas(db_session):
    from labuse import verite_sources as vs, ops_alertes
    vs.ensure_table(db_session)
    ops_alertes.ensure_table(db_session)
    db_session.execute(text("DELETE FROM ops_incidents WHERE cle = 'verite-sources'"))
    res = {"lignes": [{"notion": "surface_contenance_m2", "objet": "z", "valeur_labuse": "",
                      "valeur_oracle": "", "source_oracle": "API Carto injoignable",
                      "url": "", "verdict": "non_verifiable"}],
           "echantillon": [{"idu": "z", "commune": "Y", "slot": "aleatoire"}],
           "bilan": {"vrai": 0, "faux": 0, "non_verifiable": 1}}
    vs.journaliser_passage(db_session, res)
    assert all(i["cle"] != "verite-sources" for i in ops_alertes.incidents_ouverts(db_session))


def test_echantillon_stratifie_robuste(engine):
    """L'échantillonneur rend une liste (≤ n), stratifiée, sans jamais écrire ni lever — même si des
    strates sont vides. Chaque entrée porte idu, commune, slot."""
    from labuse import verite_sources as vs
    raw = engine.raw_connection()
    try:
        raw.driver_connection.autocommit = True        # psycopg3 : lectures indépendantes
        sample = vs.echantillon_stratifie(raw.driver_connection, n=10)
    finally:
        raw.close()
    assert isinstance(sample, list) and len(sample) <= 10
    for t in sample:
        assert set(t) >= {"idu", "commune", "slot"}
