"""PPR-UNIQUE-1 — classification UNIQUE des zones PPR (module `labuse.ppr` + fonction SQL
`labuse_ppr_couleur`), consommée par la fiche / l'Étude / le Gabarit / Pièges et risques / les PDF.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import ppr


# ── Classification pure (miroir Python de la fonction SQL) ────────────────────────────────────────
@pytest.mark.parametrize("subtype,code_degre,attendu", [
    ("INTERDICTION", "R1", ppr.ROUGE),          # DEAL rouge
    ("PRESCRIPTION", "B2", ppr.BLEU),            # DEAL bleu
    ("INTERDICTION", "R1B1", ppr.ROUGE),         # code mixte, subtype fait foi
    ("PRESCRIPTION", "RB1", ppr.BLEU),           # code mixte, subtype fait foi
    (None, "rR2", ppr.ROUGE),                    # repli code : variante r + R majuscule = rouge
    (None, "rB3", ppr.BLEU),                     # repli code : variante r + B majuscule = bleu
    (None, "Rg", ppr.ROUGE),
    (None, "Bg", ppr.BLEU),
    ("i", None, ppr.AUTRE),                      # code hérité PM1 Saint-Philippe → non classé
    (None, None, ppr.AUTRE),                     # rien → non classé
    ("ZONE_BIZARRE", "X9", ppr.AUTRE),           # inconnu → non classé
])
def test_classer(subtype, code_degre, attendu):
    assert ppr.classer(subtype, code_degre) == attendu


def test_autre_traite_en_rouge_et_interdit():
    # Un code non classé ('autre') est INTERDIT (traité en rouge par prudence), jamais ignoré.
    assert ppr.est_interdit(ppr.AUTRE) is True
    assert ppr.est_interdit(ppr.ROUGE) is True
    assert ppr.est_interdit(ppr.BLEU) is False
    assert ppr.COULEURS_INTERDITES == (ppr.ROUGE, ppr.AUTRE)


@pytest.mark.db
def test_sql_fonction_parite_avec_python(db_session):
    """La fonction SQL `labuse_ppr_couleur` rend EXACTEMENT ce que `ppr.classer` rend (une vérité)."""
    cas = [("INTERDICTION", '{"code_degre":"R1"}'), ("PRESCRIPTION", '{"code_degre":"B2"}'),
           (None, '{"code_degre":"rR2"}'), (None, '{"code_degre":"rB3"}'),
           ("i", '{"code_risque":"i"}'), (None, '{}')]
    import json
    for subtype, attrs in cas:
        sql = db_session.execute(text("SELECT labuse_ppr_couleur(:s, CAST(:a AS jsonb))"),
                                 {"s": subtype, "a": attrs}).scalar()
        a = json.loads(attrs)
        py = ppr.classer(subtype, a.get("code_degre"), a.get("code_risque"))
        assert sql == py, f"{subtype}/{attrs}: SQL={sql} Python={py}"


@pytest.mark.db
def test_code_i_classe_autre_jamais_ignore(db_session):
    """Un PPR au code non reconnu ('i') est bien classé 'autre' (interdit) par la fonction SQL."""
    c = db_session.execute(text(
        "SELECT labuse_ppr_couleur('i', '{\"code_risque\":\"i\"}'::jsonb)")).scalar()
    assert c == ppr.AUTRE
    assert ppr.est_interdit(c) is True
