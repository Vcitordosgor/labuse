"""Témoins PDF des deux découpages et des réponses documentaires de la reprise."""
import importlib.util
from pathlib import Path
import re

import pytest

from test_plu_fix15_decoupage import articles
from labuse.api import modules
from labuse.ingestion import plu_ingest as plu


def test_etang_limite_avant_le_titre_agricole():
    rows = articles("97404")
    reg = next(r for r in rows if r["article_ref"] == "AU 3.2")
    assert (reg["page_debut"], reg["page_fin"]) == (84, 85)
    assert "assainissement" in reg["texte"]
    assert "TITRE IV" not in reg["texte"]
    for zone, page in [("AU", 75), ("A", 89), ("N", 99)]:
        assert not any(r["article_ref"] == "ZONE " + zone and r["page_fin"] > page for r in rows)


def test_saint_benoit_colonnes_article_au_12():
    reg = next(r for r in articles("97410") if r["article_ref"] == "Article AU – 12.")
    texte = " ".join(reg["texte"].split())
    assert (reg["page_debut"], reg["page_fin"]) == (29, 31)
    assert "installations doit être assuré en dehors des voies publiques" in texte
    assert "2 emplacements par classe" in texte
    assert "Cette règle vise" not in texte
    assert "Explication des règles" not in texte


def test_saint_benoit_liste_emplacements_hors_articles_au():
    rows = articles("97410")
    assert not any(r["zone"] and 149 <= r["page_debut"] <= 152 for r in rows)
    assert any("chemin Impérial" in r["texte"] for r in rows if r["zone"] is None and r["page_debut"] >= 149)


@pytest.mark.parametrize("zone,pages", [("A", (32, 39)), ("Nta47", (40, 48))])
def test_carte_documentaire_sans_article_propre(monkeypatch, zone, pages):
    for nom, valeur in [("corpus_status", {"97410": {}}), ("count_reglement", 0),
                        ("search_reglement", []), ("zone_renvoi_note", None)]:
        monkeypatch.setattr(plu, nom, lambda *a, val=valeur, **kw: val)
    d = modules.plu_annuaire_search("stationnement", "97410", zone, 25, 0, None)
    carte = d.get("absence_article") or {}
    assert (carte.get("page_debut"), carte.get("page_fin")) == pages
    assert "article propre" in carte["texte"]
    assert carte["url"].endswith(f"#page={pages[0]}")


def test_mesure_sans_objet_et_titre_reellement_vide():
    spec = importlib.util.spec_from_file_location("mesure", Path(__file__).parents[1] / "scripts/plu_fix14_mesure.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    titre = "ARTICLE AUST 10 - HAUTEUR MAXIMALE DES CONSTRUCTIONS"
    assert m._is_title_only({"texte_verbatim": titre})
    assert not m._is_title_only({"texte_verbatim": titre + "\nSans objet."})


def test_etang_intertitres_de_secteurs_restant_dans_au_2_2():
    rows = articles("97404")
    reg = next(r for r in rows if r["article_ref"] == "AU 2.2")
    for secteur in ("AUc", "AUe", "AUs", "AUt"):
        assert f"Zone {secteur}" in reg["texte"]
    assert not any((r["article_ref"] or "").startswith("TITRE") and r["zone"] for r in rows)


def test_fiches_de_saint_benoit_conservent_leur_perimetre():
    rows = articles("97410")
    assert all(r["page_fin"] <= 86 for r in rows if r["zone"] == "NTA53")
    assert any(r["zone"] == "NTA53" and r["page_debut"] <= 86 <= r["page_fin"]
               and "plancher bas et le faîtage" in r["texte"] for r in rows)
    assert any(r["zone"] == "NTB57" and "stationnement" in r["texte"].lower()
               and r["page_debut"] == 94 for r in rows)
    assert any(r["zone"] == "UE" and "Petit Saint-Pierre" in (r["article_ref"] or "")
               and r["page_debut"] == 53 and "stationnement" in r["texte"].lower() for r in rows)
    assert not any(r["zone"] in ("NTB", "NTB57", "NTB59") and r["page_fin"] >= 97 for r in rows)
