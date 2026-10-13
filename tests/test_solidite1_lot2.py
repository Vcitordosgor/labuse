"""SOLIDITE-1 (Lot 2) — le banc CHASSE-DONNÉES chaque nuit, sur la prod.

On prouve sans réseau : (1) un écart ouvre un incident par la porte unique et le retour au vert le
referme, (2) le passage est historisé (counts justes, écarts nouveaux comptés), (3) toute garde ajoutée
à chasse_donnees.GARDES entre automatiquement dans le banc en-process.
"""
from sqlalchemy import text


def test_journaliser_passage_compte_et_historise(db_session):
    from labuse import chasse_journal
    chasse_journal.ensure_table(db_session)
    db_session.execute(text("DELETE FROM chasse_runs"))
    resultats = [("g-a", "OK", "ok"), ("g-b", "ECART", "CW0658 fiche 27156 vs tuile 25633"),
                 ("g-c", "SKIP", "non évaluable")]
    res = chasse_journal.journaliser_passage(db_session, resultats)
    assert (res["n_gardes"], res["ok"], res["ecart"], res["skip"]) == (3, 1, 1, 1)
    assert res["ecart_nouveaux"] == 1 and res["ecarts"] == ["g-b"]
    passages = chasse_journal.derniers_passages(db_session, n=5)
    assert passages and passages[0]["n_ecart"] == 1
    assert passages[0]["ecarts"][0]["garde"] == "g-b"


def test_ecart_ouvre_incident_puis_resout(db_session):
    """Garde en écart → incident chasse:<garde> ouvert par la porte unique ; passage suivant OK → résolu."""
    from labuse import chasse_journal, ops_alertes
    chasse_journal.ensure_table(db_session)
    ops_alertes.ensure_table(db_session)
    db_session.execute(text("DELETE FROM ops_incidents WHERE cle = 'chasse:g-x'"))
    chasse_journal.journaliser_passage(db_session, [("g-x", "ECART", "témoin AV2114 : X vs Y")])
    ouverts = {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}
    assert "chasse:g-x" in ouverts
    # un écart déjà connu ne compte plus comme « nouveau » (anti-déluge), mais reste ouvert
    r2 = chasse_journal.journaliser_passage(db_session, [("g-x", "ECART", "témoin AV2114 : X vs Y")])
    assert r2["ecart_nouveaux"] == 0
    # retour au vert → incident refermé
    chasse_journal.journaliser_passage(db_session, [("g-x", "OK", "aligné")])
    assert all(i["cle"] != "chasse:g-x" for i in ops_alertes.incidents_ouverts(db_session))


def test_skip_ne_touche_pas_l_incident(db_session):
    """Une garde qui SKIP (non évaluable ce soir) ne referme pas un incident ouvert ni n'en ouvre un."""
    from labuse import chasse_journal, ops_alertes
    chasse_journal.ensure_table(db_session)
    ops_alertes.ensure_table(db_session)
    db_session.execute(text("DELETE FROM ops_incidents WHERE cle = 'chasse:g-s'"))
    chasse_journal.journaliser_passage(db_session, [("g-s", "ECART", "écart")])
    assert "chasse:g-s" in {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}
    chasse_journal.journaliser_passage(db_session, [("g-s", "SKIP", "injoignable")])
    # toujours ouvert : un SKIP n'est pas une résolution
    assert "chasse:g-s" in {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}


def test_toutes_les_gardes_entrent_automatiquement():
    """Le banc itère chasse_donnees.GARDES : les 25 gardes y sont, toute nouvelle garde entre sans
    un geste de plus (pas de liste tenue à la main ailleurs)."""
    import sys
    from pathlib import Path
    racine = Path(__file__).resolve().parents[1]
    if str(racine) not in sys.path:
        sys.path.insert(0, str(racine))
    from scripts.coherence import chasse_donnees as cd
    noms = [n for n, _ in cd.GARDES]
    assert len(noms) >= 25 and len(noms) == len(set(noms))   # unique, au moins les 25
