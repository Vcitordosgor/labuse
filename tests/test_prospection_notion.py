"""PROSPECTION-NOTION : tests des fonctions PURES (aucun réseau, aucune DB — données synthétiques).
Vérifie : en-têtes Notion EXACTS, séparateur virgule + BOM, checkbox true/false, tag « Entité publique »
(mot-clé ET flag officiel), suggestion de segment, dénomination normalisée, aucune coordonnée inventée.
"""
from __future__ import annotations

import csv

from labuse.ingestion import prospection_notion as pn


def test_colonnes_exactes_notion():
    # L'ordre et l'orthographe (casse + accents) doivent matcher la base pour un import sans retouche.
    assert pn.COLONNES_NOTION == [
        "Dénomination", "SIREN", "Segment", "Nb PC", "Nb PA", "Logements autorisés",
        "Parcelles détenues", "Communes", "Dirigeants", "Dernière autorisation", "Entité publique",
        "Adresse siège", "Ville siège", "Site web",
    ]


def test_segment_heuristique():
    assert pn._suggest_segment("SCI PROMOTION DES HAUTS") == "promoteur"
    assert pn._suggest_segment("AMENAGEMENT FONCIER OCEAN INDIEN") == "lotisseur"
    assert pn._suggest_segment("CONSTRUCTIONS TROPICALES") == "cmi"
    assert pn._suggest_segment("SIDR") == "bailleur"
    assert pn._suggest_segment("GARAGE DUPONT") == "autre_pro"


def test_entite_publique_mot_cle_et_faux_positif():
    # Marqué via mot-clé…
    rows = pn.build_notion_rows([{"siren": "111111111", "denomination": "COMMUNE DE SAINT-PAUL"}])
    assert rows[0]["Entité publique"] == "true"
    # …mais « SEM » ⊂ « ENSEMBLE » ne doit PAS déclencher (frontière de mot).
    rows = pn.build_notion_rows([{"siren": "222222222", "denomination": "ENSEMBLE IMMOBILIER DES ILES"}])
    assert rows[0]["Entité publique"] == "false"


def test_entite_publique_flag_officiel_api():
    # Une SEM au nom neutre reste taguée si l'API la déclare service public / nature juridique 7xxx.
    enr = {"333333333": {"adresse": "", "ville": "", "site_web": "", "nom_complet": "STRUCTURE X",
                         "public_officiel": True, "nature_juridique": "7210"}}
    rows = pn.build_notion_rows([{"siren": "333333333", "denomination": "STRUCTURE X"}], enr)
    assert rows[0]["Entité publique"] == "true"


def test_denomination_normalisee_et_aucune_coordonnee_inventee():
    enr = {"444444444": {"adresse": "1 RUE A 97400 SAINT-DENIS", "ville": "97400 SAINT-DENIS",
                         "site_web": "", "nom_complet": "PROMOTION REUNION SA", "public_officiel": False}}
    rows = pn.build_notion_rows([{"siren": "444444444", "denomination": "promotion reunion"}], enr)
    r = rows[0]
    assert r["Dénomination"] == "PROMOTION REUNION SA"   # nom normalisé INSEE/INPI privilégié
    assert r["Adresse siège"] == "1 RUE A 97400 SAINT-DENIS"
    assert r["Site web"] == ""                            # open data : jamais inventé


def test_csv_virgule_bom_et_quoting(tmp_path):
    rows = [{
        "siren": "555555555", "denomination": "ENEAL, HABITAT MODERE", "n_pc": 3, "n_pa": 0,
        "nb_logements": None, "n_parcelles_detenues": 0, "communes": "Bras-Panon",
        "dirigeants": "X ; Y", "dernier_depot": "2025-02-06",
    }]
    p = pn.write_notion_csv(pn.build_notion_rows(rows), tmp_path / "out.csv")
    raw = p.read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf"                     # BOM UTF-8
    text = raw.decode("utf-8-sig")
    assert text.splitlines()[0] == ",".join(pn.COLONNES_NOTION)   # en-tête séparé par des virgules
    # relecture : la virgule interne de la dénomination est protégée → 14 champs, pas de décalage
    parsed = list(csv.DictReader(text.splitlines()))
    assert len(parsed) == 1 and parsed[0]["Dénomination"] == "ENEAL, HABITAT MODERE"
    assert parsed[0]["Logements autorisés"] == ""        # None → champ vide
    assert parsed[0]["Dernière autorisation"] == "2025-02-06"
