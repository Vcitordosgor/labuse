"""MISE-EN-LIGNE-1 (décision Vic, FRAICHEUR-PROD-3 §7) — la tâche mensuelle INPI RNE ne fige plus
l'existant : relecture ROULANTE des sociétés lues depuis plus de 90 jours (jamais lues d'abord,
puis les plus anciennes — le quota sert toujours les plus périmées), et retrait (actif=false) des
dirigeants que le RNE ne renvoie plus — jamais sur une réponse vide."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)


def _poser(s, siren, rid, ingested_at, actif=True):
    s.execute(text(
        "INSERT INTO pm_dirigeants (siren, representant_id, type_personne, nom, actif, ingested_at) "
        "VALUES (:s, :r, 'INDIVIDU', :n, :a, :t) "
        "ON CONFLICT (siren, representant_id) DO UPDATE SET ingested_at=EXCLUDED.ingested_at, "
        "actif=EXCLUDED.actif"),
        {"s": siren, "r": rid, "n": f"NOM-{rid}", "a": actif, "t": ingested_at})


@pytest.mark.db
def test_relecture_roulante_ordre_et_fenetre(db_session):
    from labuse.ingestion.inpi_rne import sirens_a_relire
    s = db_session
    s.execute(text("DELETE FROM pm_dirigeants WHERE siren IN ('100000001','100000002','100000003')"))
    # 1 = lu il y a 200 j (périmé), 2 = lu il y a 10 j (frais), 3 = jamais lu
    _poser(s, "100000001", "r1", NOW - timedelta(days=200))
    _poser(s, "100000002", "r2", NOW - timedelta(days=10))

    todo, n_recents = sirens_a_relire(
        s, ["100000001", "100000002", "100000003"], fraicheur_jours=90, now=NOW)

    assert todo == ["100000003", "100000001"]   # jamais lu D'ABORD, puis le périmé
    assert n_recents == 1                        # le frais est sauté
    # fenêtre resserrée : le « frais » de 10 j devient périmé avec une fenêtre de 5 j
    todo5, n5 = sirens_a_relire(
        s, ["100000001", "100000002", "100000003"], fraicheur_jours=5, now=NOW)
    assert "100000002" in todo5 and n5 == 0
    # ordre du quota : parmi les lus, le PLUS ANCIEN d'abord (200 j avant 10 j)
    assert todo5.index("100000001") < todo5.index("100000002")


class _ConnecteurFige:
    """Connecteur factice : rend des sociétés parsées, zéro réseau."""

    def __init__(self, companies):
        self._companies = companies

    def fetch_companies(self, sirens, throttle_s=None):
        voulus = set(sirens)
        for c in self._companies:
            if c["siren"] in voulus:
                yield c


def _dirigeant(rid, nom="DURAND"):
    return {"representant_id": rid, "type_personne": "INDIVIDU", "nom": nom, "prenoms": "A",
            "date_naissance": None, "role_entreprise": "30", "date_prise_fonction": None,
            "gerant_siren": None, "actif": True, "diffusible": True, "raw": {}}


@pytest.mark.db
def test_dirigeant_parti_desactive(db_session):
    from labuse.ingestion.inpi_rne import ingest_inpi_rne
    s = db_session
    s.execute(text("DELETE FROM pm_dirigeants WHERE siren = '200000001'"))
    ancien = NOW - timedelta(days=139)
    _poser(s, "200000001", "reste", ancien)
    _poser(s, "200000001", "parti", ancien)

    conn = _ConnecteurFige([{"siren": "200000001", "dirigeants": [_dirigeant("reste")]}])
    res = ingest_inpi_rne(s, ["200000001"], connector=conn)

    assert res["dirigeants_partis"] == 1
    etat = dict(s.execute(text(
        "SELECT representant_id, coalesce(actif, true) FROM pm_dirigeants "
        "WHERE siren='200000001'")).all())
    assert etat["reste"] is True and etat["parti"] is False


@pytest.mark.db
def test_reponse_vide_ne_desactive_rien(db_session):
    """« Jamais remplacer du réel par du vide » : une société rendue SANS représentant identifiable
    (diffusibilité, parsing partiel) ne désactive aucun dirigeant existant."""
    from labuse.ingestion.inpi_rne import ingest_inpi_rne
    s = db_session
    s.execute(text("DELETE FROM pm_dirigeants WHERE siren = '200000002'"))
    _poser(s, "200000002", "seul", NOW - timedelta(days=139))

    conn = _ConnecteurFige([{"siren": "200000002", "dirigeants": []}])
    res = ingest_inpi_rne(s, ["200000002"], connector=conn)

    assert res["dirigeants_partis"] == 0
    actif = s.execute(text(
        "SELECT coalesce(actif, true) FROM pm_dirigeants "
        "WHERE siren='200000002' AND representant_id='seul'")).scalar()
    assert actif is True
