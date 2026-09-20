"""COPILOTE-2 lot 2 — LE CHEMIN OUTIL. La table de routage question → outil est écrite et testable ;
chaque porte pointe vers un outil LIVE du registre front (plus de lien mort — constat COPILOTE-AUDIT-1) ;
le Copilote extrait les paramètres, ouvre l'outil pré-rempli et le DIT, sans afficher de résultat."""
from __future__ import annotations

import re
from pathlib import Path

from labuse.copilote_v2 import answering

REGISTRY = Path(__file__).resolve().parents[1] / "frontend/src/components/outils/registry.ts"


def _cles_registre() -> set[str]:
    """Les clés d'outil LIVE, lues du registre front (jamais une liste recopiée qui dériverait)."""
    txt = REGISTRY.read_text(encoding="utf-8")
    return set(re.findall(r"key:\s*'([a-z0-9-]+)'", txt))


def test_portes_outil_toutes_vivantes():
    """Chaque module cible de _OUTIL_MAP est une clé LIVE du registre — aucune porte morte."""
    cles = _cles_registre()
    assert cles, "registre front introuvable"
    for _kws, (module, *_r) in answering._OUTIL_MAP:
        assert module in cles, f"_OUTIL_MAP → porte morte : {module}"


def test_portes_concept_toutes_vivantes():
    cles = _cles_registre()
    for _kws, cible in answering._CONCEPT_MAP:
        module = cible[0]
        assert module in cles, f"_CONCEPT_MAP → porte morte : {module}"


def test_aucune_cle_morte_connue():
    """Les 6 clés mortes de l'audit ne routent plus nulle part."""
    mortes = {"plu-annuaire", "lettre-zonage", "verif-procedure", "duediligence", "o5-servitudes", "simulplu"}
    cibles = {c[0] for _k, c in answering._OUTIL_MAP} | {c[0] for _k, c in answering._CONCEPT_MAP}
    assert not (cibles & mortes), f"clés mortes encore routées : {cibles & mortes}"


def test_table_canonique():
    """La table de routage du mandat : chaque demande-type ouvre le bon outil."""
    cas = {
        "je veux comparer ces deux parcelles": "comparer",
        "quelle taxe d'amenagement sur ce terrain": "taxe-amenagement",
        "montre-moi le reglement de la zone": "plu",
        "quels sont les pieges et risques": "risques",
        "quelle charge fonciere je peux payer": "calculette-fonciere",
        "assembler les parcelles voisines": "assemblage",
        "quelle est la faisabilite / capacite constructible": "programme",
        "ecrire au proprietaire": "courriers",
        "remonter le temps sur ce site": "temps",
    }
    for message, attendu in cas.items():
        cible = answering._match_outil(message)
        assert cible is not None, f"aucune porte pour : {message}"
        assert cible[0] == attendu, f"{message} → {cible[0]} (attendu {attendu})"


def test_outil_annonce_et_ouvre_prerempli():
    """Le Copilote DIT qu'il ouvre l'outil (« Je vous ouvre… »), pose la porte + le préremplissage,
    et n'affiche AUCUN résultat de l'outil (juste la porte)."""
    rep = answering._outil(None, "quels sont les risques de cette parcelle", {"idu": "97411000BZ1065"})
    assert rep["porte"] == "risques"
    assert rep["prefill_idu"] == "97411000BZ1065"
    assert "ouvre l'outil" in rep["text"].lower()
    # aucune donnée de résultat servie (pas de sources/valeur — c'est une porte, pas une réponse)
    assert not rep.get("sources") and rep.get("intent") == "OUTIL"


def test_plu_prefill_correct():
    """Le hub PLU reçoit prefill_plu {insee, zone} (jamais prefill_idu, ignoré par Plu.tsx)."""
    rep = answering._outil(None, "le reglement de la zone", {"idu": "97411000BZ1065"})
    assert rep["porte"] == "plu"
    assert rep.get("prefill_plu") == {"insee": "97411", "zone": None}
    assert not rep.get("prefill_idu")
