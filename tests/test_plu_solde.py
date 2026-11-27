"""Témoins des pages physiques des éditions GPU contrôlées en novembre 2026."""
from functools import lru_cache
from pathlib import Path
import os
import re

import pytest
from labuse.ingestion import plu_ingest as plu

DOCS = {"97406": "20230527", "97408": "20260625", "97410": "20200206",
        "97411": "20260805", "97420": "20250929", "97422": "20230811", "97423": "20220602"}


@lru_cache
def articles(code):
    directory = Path(os.environ.get("LABUSE_PLU_PDF_DIR", "~/Desktop/labuse/data/plu_reglements")).expanduser()
    pdf = directory / f"{code}_reglement_{DOCS[code]}.pdf"
    assert pdf.is_file(), pdf
    return plu._split_articles(str(pdf))[0]


def test_plaine_glyphes_imprimes_dans_le_dossier_de_2023():
    rows = articles("97406")
    row = next(a for a in rows if a["article_ref"] == "ARTICLE UB 12" and a["page_debut"] == 147)
    assert row["zone"] == "UB" and row["page_fin"] == 148
    assert "12.3 - En cas d’impossibilité" in " ".join(row["texte"].split())
    assert not any(a["zone"] == "UR" and 118 <= a["page_debut"] <= 149 for a in rows)


def test_plaine_le_plan_de_zonage_ne_fait_pas_partie_de_la_hauteur():
    rows = articles("97406")
    assert all(not a["zone"] for a in rows if 169 <= a["page_debut"] <= 176)
    ub = next(a for a in rows if a["page_debut"] == 168 and a["article_ref"] == "ARTICLE UB 10")
    assert ub["page_fin"] == 168 and "hauteur" in ub["texte"].lower()
    assert any(a["page_debut"] >= 169 and "plan de zonage modifié" in a["texte"].lower() for a in rows)


def test_saint_denis_intitule_a_urbaniser():
    rows = articles("97411")
    assert not any(a["zone"] == "A" and 106 <= a["page_debut"] <= 111 for a in rows)
    assert any(a["zone"] == "AUA" and a["page_debut"] == 106 and "Chemin Neuf" in a["texte"].title()
               for a in rows)


def test_sainte_suzanne_chapitre_au_et_rubriques_urbaines():
    rows = articles("97420")
    assert not any(a["zone"] and (a["article_ref"] or "").startswith("Section ") for a in rows)
    indexed = [a for a in rows if re.fullmatch(r"Article AUindicée \d+", a["article_ref"] or "", re.I)]
    assert [int(a["article_ref"].split()[-1]) for a in indexed] == list(range(1, 18))
    assert all(a["zone"] == "AUINDICEE" and 29 <= a["page_debut"] <= a["page_fin"] <= 31 for a in indexed)
    for num in (4, 8, 15):
        assert "Se reporter au règlement" in indexed[num-1]["texte"]


def test_tampon_deux_articles_avec_la_fin_de_phrase():
    rows = articles("97422")
    trois = next(a for a in rows if a["article_ref"] == "ARTICLE Ue3")
    assert trois["page_debut"] == trois["page_fin"] == 73
    assert "présent règlement)." in " ".join(trois["texte"].split())
    quatre = next(a for a in rows if a["article_ref"] == "ARTICLE Ue4")
    assert quatre["page_debut"] == quatre["page_fin"] == 74 and "Alimentation en eau potable" in quatre["texte"]


def test_trois_bassins_fiches_patrimoniales_distinctes_du_chapitre_n():
    rows = articles("97423")
    assert all(a["page_fin"] <= 94 for a in rows if a["zone"] == "N")
    for n in (97, 98, 99, 100, *range(102, 109)):
        assert any(a["page_debut"] == a["page_fin"] == n and a["zone"] is None
                   and "ADRESSE POSTALE" in a["texte"].upper() for a in rows)


def test_inventaire_et_rapport_modificatif_ne_sont_pas_des_regles_communes():
    for doc, page in [("97423_reglement_20220602.pdf", 97), ("97406_reglement_20230527.pdf", 171)]:
        card = dict(document=doc, page_debut=page, zone=None, secteurs=None,
                    article_ref="Inventaire", texte_verbatim="Description de l’implantation")
        for zones in (["N"], ["AUINDICEE"]):
            assert not plu._filtre_scope([card], zones[0], zones)


def test_les_26_fiches_de_patrimoine_ne_fusionnent_pas_les_adresses():
    rows = [a for a in articles("97423") if 96 <= a["page_debut"] <= 108 and "ADRESSE POSTALE" in a["texte"]]
    assert len(rows) == 26
    assert all(a["texte"].count("ADRESSE POSTALE") == 1 for a in rows)
