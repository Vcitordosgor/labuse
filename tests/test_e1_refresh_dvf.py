"""CORRECTIFS-1 E1 — refresh_dvf recharge bien `dvf_mutations` (la table servie), pas une table
aux colonnes inexistantes ; la date de livraison n'est gravée qu'après un rechargement réussi."""
from sqlalchemy import text


def test_refresh_dvf_recharge_dvf_mutations(db_session, monkeypatch):
    from labuse.ingestion import fraicheur, layers_ingest
    s = db_session
    fraicheur._ensure(s)
    s.execute(text("DELETE FROM dvf_mutations WHERE mutation_id LIKE 'E1TEST%'"))
    # une ancienne ligne 2024 à remplacer
    s.execute(text("INSERT INTO dvf_mutations (mutation_id, date_mutation, valeur_fonciere, commune, geom) "
                   "VALUES ('E1TEST-OLD', '2024-03-01', 100000, 'Saint-Paul', ST_SetSRID(ST_MakePoint(55.3,-21.0),4326))"))

    # détection : le millésime 2024 a une nouvelle livraison
    monkeypatch.setattr(fraicheur, "check_dvf_livraison",
                        lambda session, timeout=20.0: {"modifies": [
                            {"annee": 2024, "lastmod": "NEW-2024", "connu": "OLD"}]})

    # chargement simulé : insère 2 lignes fraîches 2024 DANS dvf_mutations (colonnes qui EXISTENT)
    def fake_load(session, target="dvf_mutations", years=()):
        assert target == "dvf_mutations", "E1 : refresh_dvf doit cibler dvf_mutations"
        for i in (1, 2):
            session.execute(text(
                f"INSERT INTO {target} (mutation_id, date_mutation, valeur_fonciere, commune, geom) "
                "VALUES (:m, '2024-06-01', 200000, 'Saint-Paul', ST_SetSRID(ST_MakePoint(55.3,-21.0),4326))"), {"m": f"E1TEST-NEW{i}"})
        return 2
    monkeypatch.setattr(layers_ingest, "load_dvf_geo", fake_load)

    res = fraicheur.refresh_dvf(s, commit=False)

    assert res["no_op"] is False
    assert res["recharges"][0]["annee"] == 2024 and res["recharges"][0]["apres"] == 2
    # l'ancienne 2024 est partie, les 2 neuves sont là (RECHARGEMENT, pas seulement détection)
    assert s.execute(text("SELECT 1 FROM dvf_mutations WHERE mutation_id='E1TEST-OLD'")).scalar() is None
    n = s.execute(text("SELECT count(*) FROM dvf_mutations WHERE mutation_id LIKE 'E1TEST-NEW%'")).scalar()
    assert n == 2
    # la date de livraison n'est gravée qu'APRÈS le succès
    assert fraicheur._etat_get(s, "dvf:lastmod:2024") == "NEW-2024"


def test_refresh_dvf_lastmod_pas_grave_si_load_leve(db_session, monkeypatch):
    """Si le rechargement lève, la date de livraison n'est PAS enregistrée (re-tenté au prochain run)."""
    from labuse.ingestion import fraicheur, layers_ingest
    s = db_session
    fraicheur._ensure(s)
    monkeypatch.setattr(fraicheur, "check_dvf_livraison",
                        lambda session, timeout=20.0: {"modifies": [
                            {"annee": 2099, "lastmod": "BOOM", "connu": None}]})

    def boom(session, target="dvf_mutations", years=()):
        raise RuntimeError("téléchargement coupé")
    monkeypatch.setattr(layers_ingest, "load_dvf_geo", boom)

    try:
        fraicheur.refresh_dvf(s, commit=False)
    except RuntimeError:
        pass
    assert fraicheur._etat_get(s, "dvf:lastmod:2099") is None
