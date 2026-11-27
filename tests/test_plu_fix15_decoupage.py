"""Régressions constatées dans les règlements écrits, numéros du lecteur PDF."""
from functools import lru_cache
import os
from pathlib import Path
import re

import pytest

from labuse.ingestion import plu_ingest as plu


@lru_cache
def articles(insee):
    directory = Path(os.environ.get("LABUSE_PLU_PDF_DIR", "~/Desktop/labuse/data/plu_reglements")).expanduser()
    files = sorted(directory.glob(f"{insee}_*reglement*.pdf"))
    if not files:
        pytest.skip(f"Règlement officiel {insee} absent")
    return plu._split_articles(str(files[-1]))[0]


@pytest.mark.parametrize("insee,page_implantation,page_parking", [
    ("97402", 79, 80), ("97414", 109, 110),
])
def test_au_indicee_titre_et_renvoi(insee, page_implantation, page_parking):
    for num, page in [(6, page_implantation), (7, page_implantation), (8, page_implantation), (12, page_parking)]:
        matches = [a for a in articles(insee) if a["zone"] == "AUINDICEE"
                   and a["page_debut"] == page and re.search(rf"AUINDICEE\s*{num}\b", a["article_ref"] or "", re.I)]
        assert len(matches) == 1
        body = " ".join(matches[0]["texte"].split())
        assert "Se reporter au règlement de la zone U indiquée en indice" in body
        if num == 12:
            assert "STATIONNEMENT" in body
            assert "ARTICLE AUINDICEE 13" not in body


def test_etang_sale_stationnement_ua_2_7():
    cards = [a for a in articles("97404") if a["zone"] == "UA" and a["page_debut"] == 21
             and (a["article_ref"] or "").startswith("UA 2.7")]
    assert len(cards) == 1
    assert "en dehors des voies publiques" in cards[0]["texte"]
    assert "UA 3.1" not in cards[0]["texte"]


def test_entre_deux_sommaire_et_article_12():
    rows = articles("97403")
    assert not [a for a in rows if a["page_debut"] in (2, 3, 4) and a["zone"]]
    assert any(a["article_ref"] == "Article U12" and a["page_debut"] == 27
               and "séparation effective" in a["texte"] for a in rows)


def test_saint_benoit_intertitre_et_article_12():
    rows = articles("97410")
    assert not [a for a in rows if a["page_debut"] == 23 and a["article_ref"] == "Section 2"
                and "implantation" in a["texte"]]
    assert any(a["article_ref"] == "Article AU – 12." and a["page_debut"] == 29
               and "doit être assuré en dehors des voies publiques" in a["texte"] for a in rows)


def test_reingestion_donnees_seules_ne_prepare_pas_le_schema():
    from unittest.mock import Mock

    session = Mock(info={"plu_data_only": True})
    plu.ensure_ddl(session)
    session.execute.assert_not_called()
