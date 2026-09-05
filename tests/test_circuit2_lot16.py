"""CIRCUIT-2 lot 1.6 — « un moteur nommé pour chaque chiffre ».

Verrous :
  1. `calcul="sql_propre"` a disparu du registre (0 donnée) — chaque calcul porte un moteur nommé ;
  2. chaque donnée `calcul="moteur"` déclare un `moteur` non vide qui EXISTE dans l'inventaire
     docs/CIRCUIT/inventaire/moteurs.csv (1re colonne) ;
  3. chaque `passe_plat` SERVI déclare la table (ou l'origine) lue dans `table=` — les cinq
     réglementaires `en_attente` (réservoir CIRCUIT-3 lot 6) sont exclues : leur réservoir
     n'existe pas encore, déclarer une table serait une invention ;
  4. les fonctions extraites représentatives sont importables et appelables sur la base de test
     (mêmes valeurs que le chemin endpoint quand la comparaison est simple).
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from labuse.registre.donnees import DONNEES

pytestmark = pytest.mark.db

RACINE = Path(__file__).resolve().parents[1]


# ─────────────────────────── 1-3 · le registre (pur code) ───────────────────────────

def test_plus_aucun_sql_propre():
    """Objectif du lot : `sql_propre` = 0 — chaque chiffre a un moteur nommé."""
    restants = [cid for cid, d in DONNEES.items() if d.calcul == "sql_propre"]
    assert restants == [], f"données encore en sql_propre : {restants}"


def _moteurs_inventaire() -> set[str]:
    with open(RACINE / "docs" / "CIRCUIT" / "inventaire" / "moteurs.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter=";"))
    return {r[0].strip() for r in rows[1:] if r and r[0].strip()}


def test_chaque_moteur_est_nomme_et_inventorie():
    """Une donnée `calcul="moteur"` porte un moteur non vide, présent dans moteurs.csv."""
    inventaire = _moteurs_inventaire()
    for cid, d in DONNEES.items():
        if d.calcul != "moteur":
            continue
        assert d.moteur, f"{cid} : calcul=moteur sans moteur nommé"
        assert d.moteur in inventaire, f"{cid} : moteur {d.moteur!r} absent de moteurs.csv"


def test_chaque_passe_plat_declare_sa_table():
    """Un passe-plat SERVI dit la table qu'il lit (`table=`) ; les `en_attente` (réservoir à
    venir, CIRCUIT-3 lot 6) sont exclues — pas de table inventée pour un réservoir absent."""
    for cid, d in DONNEES.items():
        if d.calcul != "passe_plat" or d.en_attente:
            continue
        assert d.table and str(d.table).strip(), f"{cid} : passe_plat sans table déclarée"


def test_fonction_toujours_declaree():
    """Chaque donnée moteur/passe_plat pointe un producteur (`fonction` non vide)."""
    for cid, d in DONNEES.items():
        if d.calcul in ("moteur", "passe_plat"):
            assert d.fonction and d.fonction.strip(), f"{cid} : fonction vide"


# ─────────────────────── 4 · fonctions extraites, sur la base de test ───────────────────────

def test_compte_parcelles_commune_meme_valeur(db_session):
    """n_parcelles_commune — le moteur rend LE même count que la requête directe."""
    from sqlalchemy import text
    from labuse.registre.moteurs.commune import compte_parcelles_commune
    direct = db_session.execute(
        text("SELECT count(*) FROM parcels WHERE commune = 'Saint-Paul'")).scalar() or 0
    assert compte_parcelles_commune(db_session, "Saint-Paul") == int(direct)


def test_mutations_12m_appelable(db_session):
    """mutations_12m_n — appelable, rend un entier ≥ 0 (0 si DVF vide : fenêtre sur max NULL)."""
    from labuse.registre.moteurs.commune import mutations_12m
    n = mutations_12m(db_session, "Saint-Paul")
    assert isinstance(n, int) and n >= 0


def test_indicateurs_et_composite_communes(db_session):
    """velocite/permis_5a + comparateur_composite — le SQL extrait tourne sur la base de test ;
    le composite garde ses invariants (axe manquant → null, jamais 0)."""
    from labuse import runs
    from labuse.registre.moteurs.commune import INDICATEURS, composite_communes, indicateurs_communes
    rows = indicateurs_communes(db_session, runs.current())
    assert isinstance(rows, list)
    # composite sur données synthétiques : mêmes règles que l'endpoint (test_comparateur)
    poids = {k: v[2] for k, v in INDICATEURS.items()}
    faux = [{k: None for k in INDICATEURS} | {"stock": 10},
            {k: None for k in INDICATEURS} | {"stock": 0}]
    out = composite_communes(faux, poids)
    assert out[0]["rang"] == 1 and out[0]["stock"] == 10
    assert out[0]["normalise"]["prix_neuf"] is None      # axe manquant : null, jamais 0


def test_qpv_et_pct_couche_appelables(db_session):
    """qpv_n · ppr_pct — appelables sur la base de test (liste / None si total nul)."""
    from labuse.registre.moteurs.commune import pct_parcelles_couche, qpv_commune
    assert isinstance(qpv_commune(db_session, "Saint-Paul"), list)
    assert pct_parcelles_couche(db_session, "Saint-Paul", "ppr", 0) is None   # total nul → None


def test_plus_proche_appelable(db_session):
    """distance_arret_m — KNN appelable ; parcelle inconnue → None (jamais une invention)."""
    from labuse.registre.moteurs.parcelle import plus_proche
    assert plus_proche(db_session, "974XX-INEXISTANTE", "transport_arret") is None


def test_cartes_par_colonne_meme_valeur(db_session):
    """crm_cartes_n · pipeline_entrees_n — même dict que la requête directe (bucket pilote)."""
    from sqlalchemy import text
    from labuse.registre.moteurs.plateforme import cartes_par_colonne
    direct = {r[0]: r[1] for r in db_session.execute(text(
        "SELECT status, count(*) FROM pipeline_entries WHERE compte_id IS NULL GROUP BY status"))}
    assert cartes_par_colonne(db_session, None) == direct


def test_compte_parcelles_ile_run_inconnu(db_session):
    """n_parcelles_ile — run inconnu → None ou 0 replié, jamais une exception ni une invention."""
    from labuse.registre.moteurs.plateforme import compte_parcelles_ile
    assert compte_parcelles_ile(db_session, "run_inexistant_lot16") in (None, 0)


def test_arithmetiques_commune_pures():
    """vacance_pct · autres_loges_pct — mêmes arrondis que les robinets d'origine."""
    from labuse.registre.moteurs.commune import autres_loges_pct, vacance_pct
    assert vacance_pct(1000, 125) == 12.5
    assert vacance_pct(None, 5) is None and vacance_pct(0, 5) is None
    assert autres_loges_pct(52.3, 41.2) == 6.5
    assert autres_loges_pct(60.0, 45.0) == 0.0     # plancher 0 (jamais négatif)
