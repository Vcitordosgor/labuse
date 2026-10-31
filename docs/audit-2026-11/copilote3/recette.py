#!/usr/bin/env python3
"""COPILOTE-3 — recette : 20 questions sur 6 parcelles témoins, réponse APRÈS (déterministe, sans IA)
et décision du VERROU qualitatif sur l'hallucination AVANT.

LECTURE SEULE. Se joue contre la base de DEV (les 6 témoins y vivent ; la base `labuse_test` du hook
est minimale) :

    PYTHONPATH=src LABUSE_DATABASE_URL=postgresql+psycopg:///labuse \
        python docs/audit-2026-11/copilote3/recette.py

AVANT (NU-E-046/047/048) : `fiche_parcelle` ne portait NI copropriété NI propriétaire ; la zone était
estampillée « cadastre » ; une question copro tombait dans le formuler (LLM) qui INVENTAIT, et le
verrou anti-invention — aveugle au qualitatif — laissait passer. On le PROUVE ici : le verrou refuse
désormais l'affirmation inventée sur la fiche LEGACY.
APRÈS : réponse déterministe, sourcée au bon producteur, ou refus honnête.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg:///labuse")

from labuse.copilote_v2 import answering as A          # noqa: E402
from labuse.copilote_v2 import outils                  # noqa: E402
from labuse.db import session_factory                  # noqa: E402

WITNESS = {
    "97404000AV0167": "L'Étang-Salé — copro=True (RNIC) · PPR rouge · zone UC  [témoin NU-E-046]",
    "97410000AN0347": "Saint-Benoît — zone N · PPR rouge · propriété communale",
    "97401000AC0575": "Les Avirons — zone A (agricole, à cheval N)",
    "97417000AT1496": "Saint-Philippe — RNU (pas de PLU servi)  [témoin NU-E-055]",
    "97411000AW0692": "Saint-Denis — zone Ud · propriétaire SCI ALOE (personne morale)",
    "97416000CD0448": "Saint-Pierre — zone Us · hors PPR",
}

QUESTIONS = [
    ("97404000AV0167", "La parcelle 97404000AV0167 est-elle en copropriété ?", "copro"),
    ("97410000AN0347", "La parcelle 97410000AN0347 est-elle en copropriété ?", "copro"),
    ("97411000AW0692", "La parcelle 97411000AW0692 est-elle en copropriété ?", "copro"),
    ("97417000AT1496", "La parcelle 97417000AT1496 est-elle en copropriété ?", "copro"),
    ("97404000AV0167", "La parcelle 97404000AV0167 est-elle en zone rouge PPR ?", "ppr"),
    ("97416000CD0448", "Y a-t-il un risque PPR sur la parcelle 97416000CD0448 ?", "ppr"),
    ("97410000AN0347", "La parcelle 97410000AN0347 est-elle en zone rouge au PPR ?", "ppr"),
    ("97401000AC0575", "Quelle est la zone PLU de la parcelle 97401000AC0575 ?", "zone"),
    ("97411000AW0692", "Quelle est la zone de la parcelle 97411000AW0692 ?", "zone"),
    ("97417000AT1496", "Quelle est la zone PLU de la parcelle 97417000AT1496 ?", "zone"),
    ("97401000AC0575", "La parcelle 97401000AC0575 est-elle constructible ?", "constructible"),
    ("97417000AT1496", "Peut-on construire sur la parcelle 97417000AT1496 ?", "constructible"),
    ("97416000CD0448", "La parcelle 97416000CD0448 est-elle constructible ?", "constructible"),
    ("97404000AV0167", "Peut-on construire sur la parcelle 97404000AV0167 ?", "constructible"),
    ("97411000AW0692", "À qui appartient la parcelle 97411000AW0692 ?", "proprietaire"),
    ("97410000AN0347", "Qui possède la parcelle 97410000AN0347 ?", "proprietaire"),
    ("97404000AV0167", "Quelle est la surface de la parcelle 97404000AV0167 ?", "surface"),
    ("97416000CD0448", "Quelle hauteur maximale en zone Us pour la parcelle 97416000CD0448 ?", "regle"),
    ("97404000AV0167", "Dis-moi tout sur la parcelle 97404000AV0167.", "resume"),
    ("97411000AW0692", "La parcelle 97411000AW0692 appartient-elle à une personne morale ?", "proprietaire"),
]


def _legacy_fiche_res(db, idu):
    """La forme AVANT COPILOTE-3 : `fiche_parcelle` sans copro ni PM, zone estampillée « cadastre »."""
    r = outils.fiche_parcelle(db, idu=idu)
    if not r.ok:
        return None
    return outils.ToolResult("fiche_parcelle", valeur=r.data.get("surface_m2"),
                             data={k: r.data[k] for k in ("idu", "commune", "surface_m2", "zone", "etage0")},
                             source="cadastre")


def main():
    db = session_factory()()
    out = []
    w = out.append
    w("=" * 100)
    w("COPILOTE-3 — RECETTE : 20 questions · 6 parcelles témoins · lecture seule")
    w("run servi : " + __import__("labuse").runs.current())
    w("=" * 100)
    w("\nTÉMOINS :")
    for idu, desc in WITNESS.items():
        w(f"  {idu}  —  {desc}")

    # Preuve NU-E-047 : le verrou refuse l'hallucination copro sur la fiche LEGACY (sans champ copro).
    w("\n" + "-" * 100)
    w("PREUVE DU VERROU (NU-E-047) — l'hallucination AVANT ne passe plus")
    w("-" * 100)
    leg = _legacy_fiche_res(db, "97404000AV0167")
    if leg is not None:
        hallu = "Non, cette parcelle n'est pas en copropriété."
        w(f"  fiche LEGACY (sans champ copro) · prose inventée : « {hallu} »")
        w(f"    → verrou qualitatif : {'REFUSÉ (invention)' if not A._verdicts_coherents(hallu, leg) else 'PASSÉ (bug)'}")
        w(f"    → source estampillée sur la zone (LEGACY) : « {leg.source} »  (NU-E-048 : faux pour un fait PLU)")
    cur = outils.fiche_parcelle(db, idu="97404000AV0167")
    if cur.ok:
        zsrc = {f["cle"]: f["source"] for f in cur.faits}["zone"]
        w(f"  fiche APRÈS · copro porté = {cur.data['copro']} · source de la zone = « {zsrc} »")

    w("\n" + "-" * 100)
    w("20 QUESTIONS — réponse APRÈS (déterministe, sans IA) + sources")
    w("-" * 100)
    for i, (idu, q, kind) in enumerate(QUESTIONS, 1):
        rep = A.answer(db, q)
        txt = (rep.get("text") or "").replace("\n", "\n        ")
        srcs = rep.get("sources") or []
        w(f"\nQ{i:02d} [{kind}] {q}")
        w(f"    → {txt}")
        if srcs:
            w(f"    sources : {srcs}")
        # garde-fous honnêteté
        if "cadastre" in " ".join(srcs).lower() and kind in ("zone", "ppr", "constructible", "proprietaire"):
            w("    ⚠ SOURCE SUSPECTE : « cadastre » sur un verdict non cadastral (NU-E-048) !")
    w("\n" + "=" * 100)
    print("\n".join(out))


if __name__ == "__main__":
    main()
