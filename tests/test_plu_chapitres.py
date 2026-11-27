"""Les pages sont celles du lecteur des quatre éditions GPU, couverture comprise."""
from functools import lru_cache
import importlib.util
import os
from pathlib import Path
import re

import pytest

from labuse.ingestion import plu_ingest as plu

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = {
    "97405": "97405_reglement_20230609.pdf", "97418": "97418_reglement_20251126.pdf",
    "97412": "97412_Reglement_20251210.pdf", "97407": "97407_reglement_20241209.pdf",
}


@lru_cache
def articles(code):
    dossier = Path(os.environ.get("LABUSE_PLU_PDF_DIR", ROOT.parent / "labuse/data/plu_reglements")).expanduser()
    doc = dossier / DOCUMENTS[code]
    if not doc.is_file():
        pytest.skip(f"Règlement officiel absent : {doc.name}")
    return plu._split_articles(str(doc))[0]


def mesure():
    spec = importlib.util.spec_from_file_location("mesure", ROOT / "scripts/plu_fix14_mesure.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("code,label,ref,zone,p", [
    ("97405", "1AU", "ARTICLE 1AUZ.10", "1AU", 104),
    ("97405", "1AUz", "ARTICLE 1AU.10", "1AU", 94),
    ("97418", "UC1", "Article U8", "U", 35),
    ("97418", "UEm", "Article U9", "U", 22),
])
def test_mesure_refuse_une_carte_etrangere_meme_annoncee_propre(monkeypatch, code, label, ref, zone, p):
    m = mesure()
    card = dict(article_ref=ref, zone=zone, document=DOCUMENTS[code], cas="propre",
                texte_verbatim="Une construction doit respecter la hauteur maximale fixée dans cette zone.",
                page_debut=p, page_fin=p)
    monkeypatch.setattr(m.M, "plu_annuaire_search", lambda **kw: {"resultats": [card]})
    assert m.classify(None, code, label, "hauteur") == "X"


@pytest.mark.parametrize("code,label,pages,own,foreign", [
    ("97405", "1AU", (88, 98), 94, 104), ("97405", "1AUz", (99, 108), 104, 94),
    ("97418", "UC1", (16, 28), 21, 34), ("97418", "UEm", (29, 40), 34, 21),
])
def test_filtre_conserve_seulement_le_chapitre_pdf(code, label, pages, own, foreign):
    rows = [dict(a, insee=code, document=DOCUMENTS[code], texte_verbatim=a["texte"])
            for a in articles(code) if a["zone"] in plu.zone_candidats(label)
            and (a["article_ref"] or "").lower().startswith("article")]
    rows = [a for a in rows if "hauteur" in a["texte"].lower()]
    served = plu._filtre_scope(rows, label, plu.zone_candidats(label))
    assert any(a["page_debut"] == own for a in served)
    assert all(pages[0] <= a["page_debut"] <= a["page_fin"] <= pages[1] for a in served)
    for a in rows:
        if a["page_debut"] == foreign:
            assert not plu._filtre_scope([a], label, plu.zone_candidats(label))


def test_joseph_limites_et_hauteur_indicee():
    rows = articles("97412")
    assert all(a["page_fin"] <= 135 for a in rows if a["zone"] == "N")
    assert all(a["page_fin"] <= 71 for a in rows if a["zone"] == "U4")
    assert any(a["zone"] == "U5" and a["article_ref"] == "ARTICLE U5 1" and a["page_debut"] == 73 for a in rows)
    rule = next(a for a in rows if a["article_ref"] == "ARTICLE AUindicée 10")
    assert rule["zone"] == "AUINDICEE" and rule["page_debut"] == rule["page_fin"] == 110
    assert "12 mètres au faîtage" in rule["texte"] and "6 mètres à l’égout" in rule["texte"]


def test_port_articles_et_dispositions_generales():
    rows = articles("97407")
    assert not any(a["zone"] for a in rows if a["page_debut"] < 21)
    for zone, ref, page in [("UA", "Article Ua 13", 32), ("1AU", "Article 1AUindicée 12", 151),
                            ("1AU", "Article 1AUindicée 13", 154)]:
        rule = next(a for a in rows if a["article_ref"] == ref and a["zone"] == zone)
        assert rule["page_debut"] == page
        assert len(re.findall(r"(?m)^Article [^\n]+? \d+ [-–]", rule["texte"])) == 1
    assert not any(a["zone"] and (a["article_ref"] or "").startswith("Section") for a in rows)


def test_petite_ile_croquis_uea_et_croquis_commun(monkeypatch):
    rows = articles("97405")
    assert any(a["zone"] == "UEA" and a["page_debut"] == 167 for a in rows)
    m = mesure()
    for page, expected in [(166, "T"), (167, "X")]:
        card = dict(document=DOCUMENTS["97405"], page_debut=page, page_fin=page)
        monkeypatch.setattr(m.M, "plu_annuaire_search", lambda **kw: {"dispositions_communes": [card]})
        assert m.classify(None, "97405", "1AU", "implantation") == expected


@pytest.mark.parametrize("code,label,own,other", [("97418", "1AUep", "U", "A"),
                                                  ("97412", "1AU3a", "U3", "U5")])
def test_le_renvoi_indice_conserve_le_detail_de_la_zone_u(monkeypatch, code, label, own, other):
    # Le chapitre V p. 41 à Sainte-Marie et AUindicée 10 p. 110 à Saint-Joseph
    # demandent de consulter aussi le règlement U de même indice.
    class Zones:
        def execute(self, *args):
            return self

        def scalars(self):
            return self

        def all(self):
            return [own, other, "AUINDICEE"]

    monkeypatch.setattr(plu, "_chapitre_propre", lambda *args: False)
    monkeypatch.setattr(plu, "_a_chapitre_auindicee", lambda *args: True)
    zones = plu.zones_apparentees(Zones(), label, code)
    assert set(zones) == {"AUINDICEE", own}


@pytest.mark.parametrize("code,chapitres", [
    ("97412", [("U1", 14, 27), ("U2", 28, 42), ("U3", 43, 57), ("U4", 58, 71),
               ("U5", 72, 87), ("U6", 88, 100), ("AUST", 102, 105),
               ("AUINDICEE", 106, 111), ("A", 113, 123), ("N", 125, 135)]),
    ("97407", [("UA", 21, 34), ("UB", 35, 49), ("UC", 50, 64), ("UD", 65, 78),
               ("UE", 79, 90), ("UMI", 91, 102), ("UOAP", 103, 106), ("UP", 107, 118),
               ("US", 119, 130), ("UV", 131, 141), ("1AU", 142, 156), ("2AU", 157, 161),
               ("A", 162, 169), ("N", 170, 177)]),
])
def test_chaque_chapitre_contient_ses_quatorze_articles_entiers(code, chapitres):
    rows = articles(code)
    for zone, debut, fin in chapitres:
        zone_pdf = {"AUINDICEE": "AUINDICÉE", "1AU": "1AUINDICÉE"}.get(zone, zone)
        titre = re.compile(rf"ARTICLE\s+{zone_pdf}\s*(\d+)\b", re.I)
        numeros = []
        for a in rows:
            ref = titre.fullmatch(a["article_ref"] or "")
            if not ref:
                continue
            assert a["zone"] == zone and debut <= a["page_debut"] <= a["page_fin"] <= fin
            assert len(titre.findall(a["texte"].splitlines()[0])) == 1
            assert len(re.findall(r"(?im)^\s*article\s+\w+\s*\d+\s*[-–—]", a["texte"])) == 1
            numeros.append(int(ref[1]))
        assert numeros == list(range(1, 15)), (zone, numeros)


def test_mesure_article_multilignes_du_port_et_vrai_bloc_fusionne():
    m = mesure()
    row = next(a for a in articles("97407") if a["page_debut"] == 151 and "stationnement" in a["texte"])
    card = dict(row, article_ref="Article 1AUindicée 12", document=DOCUMENTS["97407"], texte_verbatim=row["texte"])
    assert not m._is_chapter_block(card)
    card["texte_verbatim"] += "\nArticle 1AUindicée 13 - Desserte par les voies publiques ou privées"
    assert m._is_chapter_block(card)


def test_joseph_page_de_titre_avant_le_chapitre_u1():
    rows = articles("97412")
    assert all(a["page_debut"] >= 14 for a in rows if a["zone"] == "U1")
    assert any(a["zone"] == "U1" and a["page_debut"] == 14 and
               "indicatif" in a["texte"].lower() for a in rows)


@pytest.mark.parametrize("code,ref,titre", [
    ("97412", "ARTICLE AUindicée 10", "Hauteur maximale des constructions"),
    ("97407", "Article 1AUindicée 12", "Obligation de réalisation d’aires de stationnement"),
])
def test_titre_lisible_dans_la_carte_au_indicee(code, ref, titre):
    from labuse.api.modules import plu_titre_corps
    row = next(a for a in articles(code) if a["article_ref"] == ref)
    heading, body = plu_titre_corps(row["texte"])
    assert heading == titre
    assert body.startswith("Se reporter au règlement")
