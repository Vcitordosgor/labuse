import pytest

from labuse.ingestion import plu_ingest as plu


@pytest.mark.parametrize("code,label,zone,ref,texte,mention", [
    ("97403", "Nci", "N", "Article N3", "Implantation des constructions", "règle de la zone mère"),
    ("97403", "Nci", None, None, "DISPOSITIONS COMMUNES APPLICABLES À TOUTES LES ZONES", "disposition commune à toutes les zones"),
    ("97424", "Ub1", "UB", "Article Ub 12", "", "rattachement non établi dans le règlement écrit, à vérifier"),
    ("97423", "Nto1", "N", "Article N 10", "", "rattachement non établi dans le règlement écrit, à vérifier"),
    ("97424", "NtoPOS", "N", "Article N 10", "", "rattachement non établi dans le règlement écrit, à vérifier"),
])
def test_provenance_carte(code, label, zone, ref, texte, mention):
    row = {"zone": zone, "article_ref": ref, "texte_verbatim": texte, "insee": code}
    assert plu.mention_rattachement(row, label) == mention
