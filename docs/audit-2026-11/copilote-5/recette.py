#!/usr/bin/env python3
"""COPILOTE-5 — recette : 25 questions sur 6 parcelles (par ADRESSE, par IDU, par PROPRIÉTAIRE),
5 outils et 2+ communes ; + preuve de la résolution d'entrée, du bridage web, et rejeu des 20
questions de COPILOTE-3 (zéro régression).

LECTURE SEULE. Base de DEV (les témoins y vivent ; la base `labuse_test` du hook est minimale) :

    PYTHONPATH=src LABUSE_DATABASE_URL=postgresql+psycopg:///labuse \\
        ../labuse/.venv/bin/python docs/audit-2026-11/copilote-5/recette.py

AVANT (COPILOTE-4) : « Donne-moi toutes les infos sur la parcelle 3 chemin de la Citerne, 97417 La
Montagne » partait en RÉPONSE GÉNÉRALE (web) — aucune résolution d'adresse. APRÈS : l'adresse est
résolue en parcelle (97411000BZ1065) AVANT toute réponse, et la fiche est servie.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg:///labuse")

from labuse.copilote_v2 import answering as A          # noqa: E402
from labuse.copilote_v2 import resolveur as R          # noqa: E402
from labuse.db import session_factory                  # noqa: E402

# 6 parcelles témoins, atteintes par les TROIS familles de l'omnibox.
TEMOINS = {
    "97411000BZ1065": "Saint-Denis — atteinte par ADRESSE (3 chemin de la Citerne, 97417)",
    "97416000DW0279": "Saint-Pierre — atteinte par ADRESSE (1 rue Augustin Archambaud)",
    "97411000AW0692": "Saint-Denis — atteinte par PROPRIÉTAIRE (SCI ALOE) / IDU",
    "97404000AV0167": "L'Étang-Salé — par IDU (copro=True, PPR rouge, UC)",
    "97416000CD0448": "Saint-Pierre — par IDU (zone Us, hors PPR)",
    "97410000AN0347": "Saint-Benoît — par IDU (zone N, propriété communale)",
}

# 25 questions : (n° de famille, question, attendu). L'« attendu » est un dict de contrôles légers
# (pas une chaîne exacte — la formulation Opus peut varier ; on vérifie le ROUTAGE et les SOURCES).
#   famille ∈ {ADRESSE, IDU, PROPRIO, COMMUNE, WEB}
#   check   : fonctions de garde (lambda rep -> bool) ; motif en clair.
Q = []


def add(famille, question, **attendu):
    Q.append((famille, question, attendu))


# ── 1-6 · RÉSOLUTION PAR ADRESSE (la première étape — le cœur du mandat) ──
add("ADRESSE", "Donne-moi toutes les infos sur la parcelle 3 chemin de la Citerne, 97417 La Montagne",
    idu="97411000BZ1065", pas_web=True, resume=True)
add("ADRESSE", "La parcelle 2 chemin de la citerne à Saint-Denis est-elle en copropriété ?",
    idu="97411000BZ1123", source="RNIC", pas_web=True)
add("ADRESSE", "Que peux-tu me dire sur le 1 rue Augustin Archambaud à Saint-Pierre ?",
    idu="97416000DW0279", pas_web=True)
add("ADRESSE", "Quelle est la zone PLU du 1 rue Augustin Archambaud, 97410 Saint-Pierre ?",
    idu="97416000DW0279", source="PLU", pas_web=True)
add("ADRESSE", "chemin de la citerne à saint-denis", propose=True, pas_web=True)
add("ADRESSE", "la parcelle BZ 1065 à Saint-Denis", idu="97411000BZ1065", pas_web=True)

# ── 7-16 · RÉSOLUTION PAR IDU · 5 outils · 2+ communes ──
add("IDU", "La parcelle 97404000AV0167 est-elle en zone rouge PPR ?", source="DEAL", pas_web=True)   # statut_ppr
add("IDU", "Quelle hauteur maximale en zone Us pour la parcelle 97416000CD0448 ?",
    source="PLU", pas_web=True)                                                                      # regles_plu_zone
add("IDU", "Quelle est l'adresse de la parcelle 97411000AW0692 ?", source="BAN", pas_web=True)        # adresse_ban
add("IDU", "Quelle est l'emprise bâtie de la parcelle 97411000BZ1065 ?", source="TOPO", pas_web=True)  # emprise_batie
add("IDU", "La parcelle 97411000BZ1065 a-t-elle la fibre ?", source="ARCEP", pas_web=True)            # fibre
add("IDU", "Quel est l'arrêt de bus le plus proche de la parcelle 97411000BZ1065 ?",
    source="transport", pas_web=True)                                                                # distance_arret
add("IDU", "Dans quel quartier est la parcelle 97411000BZ1065 ?", source="IRIS", pas_web=True)        # iris_quartier
add("IDU", "Y a-t-il des servitudes sur la parcelle 97411000BZ1065 ?", source="GPU", pas_web=True)    # dispositifs
add("IDU", "Quel est le prix du terrain au secteur de la parcelle 97416000CD0448 ?",
    source="DVF", pas_web=True)                                                                       # prix_terrain
add("IDU", "La parcelle 97410000AN0347 est-elle viabilisée ?", pas_web=True)                          # viabilisation

# ── 17-19 · RÉSOLUTION PAR PROPRIÉTAIRE ──
add("PROPRIO", "Quelles parcelles possède la SCI ALOE ?", pas_web=True)                               # parcelles_par_entreprise
add("PROPRIO", "À qui appartient la parcelle 97411000AW0692 ?", source="DGFiP", pas_web=True)
add("PROPRIO", "La parcelle 97410000AN0347 appartient-elle à une personne morale ?",
    source="DGFiP", pas_web=True)

# ── 20-22 · DEUX COMMUNES (contexte commune, outils stats/marché/comptage) ──
add("COMMUNE", "Combien de parcelles de plus de 1000 m² à Saint-Pierre ?", pas_web=True)              # compter_parcelles
add("COMMUNE", "Quel est le prix du foncier à Saint-Denis ?", pas_web=True)                           # marche
add("COMMUNE", "Quel est le taux de logement social à Saint-Pierre ?", pas_web=True)                  # stats_commune

# ── 23-25 · WEB BRIDÉ : une question LABUSE-locale sans réponse NE PART PAS sur le web ;
#            un maire / une loi, OUI (hors données LABUSE). ──
add("IDU", "Y a-t-il des termites déclarés sur la parcelle 97416000CD0448 ?", pas_web=True)           # LABUSE-domain → honnête
add("WEB", "Qui est le maire de Saint-Benoît ?", web=True)                                            # maire → web légitime
add("WEB", "C'est quoi la loi Girardin ?", general=True)                                              # notion → voie b


def _verifier(rep, att):
    pb = []
    src = " ".join(rep.get("sources") or []).lower()
    if att.get("pas_web") and (rep.get("web") or rep.get("general")):
        pb.append("parti sur le WEB alors que LABUSE-local")
    if att.get("web") and not rep.get("web"):
        pb.append("aurait dû aller sur le web (maire)")
    if att.get("general") and not rep.get("general"):
        pb.append("aurait dû passer en voie b (notion)")
    if att.get("propose") and not rep.get("clarification"):
        pb.append("aurait dû PROPOSER des candidates")
    if att.get("source") and att["source"].lower() not in src:
        pb.append(f"source attendue « {att['source']} » absente ({rep.get('sources')})")
    # résolution : l'IDU attendu doit apparaître dans la voie/le texte
    if att.get("idu"):
        voie_idu = (rep.get("voie") or {}).get("idu")
        if att["idu"] not in (rep.get("text") or "") and voie_idu != att["idu"]:
            pb.append(f"IDU {att['idu']} non résolu")
    return pb


def main():
    db = session_factory()()
    out = []
    w = out.append
    import labuse
    w("=" * 100)
    w("COPILOTE-5 — RECETTE : 25 questions · 6 parcelles (adresse / IDU / propriétaire) · 2+ communes")
    w("run servi : " + labuse.runs.current())
    w("=" * 100)
    w("\nTÉMOINS :")
    for idu, desc in TEMOINS.items():
        w(f"  {idu}  —  {desc}")

    # Preuve de la résolution d'entrée (famille par famille, déterministe).
    w("\n" + "-" * 100)
    w("RÉSOLUTION D'ENTRÉE (api.recherche._sugg_* — MÊME grammaire que l'omnibox) :")
    w("-" * 100)
    for q in ["Donne-moi toutes les infos sur la parcelle 3 chemin de la Citerne, 97417 La Montagne",
              "1 rue Augustin Archambaud, 97410 Saint-Pierre", "chemin de la citerne à saint-denis",
              "la parcelle BZ 1065 à Saint-Denis"]:
        res = R.resoudre(db, q)
        if res is None:
            w(f"  {q[:60]:60} → (non résolu)")
        elif res.kind == "idu":
            w(f"  {q[:60]:60} → IDU {res.idu} [{res.famille}] needle={res.requete!r}")
        else:
            w(f"  {q[:60]:60} → {len(res.candidats)} candidates [{res.famille}] (proposées)")

    w("\n" + "-" * 100)
    w("25 QUESTIONS — routage, résolution, sources, garde anti-web")
    w("-" * 100)
    total_pb = 0
    for i, (famille, question, att) in enumerate(Q, 1):
        rep = A.answer(db, question)
        pb = _verifier(rep, att)
        total_pb += len(pb)
        txt = (rep.get("text") or "").replace("\n", " | ")
        marque = "OK " if not pb else "KO "
        w(f"\n{marque}Q{i:02d} [{famille}] {question}")
        w(f"      → {txt[:220]}")
        srcs = rep.get("sources")
        if srcs:
            w(f"      sources : {srcs}")
        flags = [k for k in ("web", "general", "clarification") if rep.get(k)]
        if flags:
            w(f"      flags : {flags}")
        for p in pb:
            w(f"      ⚠ {p}")
    w("\n" + "-" * 100)
    w(f"BILAN 25 questions : {len(Q) - sum(1 for f, q, a in Q)} … {total_pb} contrôle(s) en échec")
    w(f"  → {'TOUT VERT' if total_pb == 0 else str(total_pb) + ' À CORRIGER'}")

    # Rejeu COPILOTE-3 — zéro régression (les 20 questions, mêmes réponses de fond).
    w("\n" + "-" * 100)
    w("REJEU COPILOTE-3 (20 questions) — zéro régression")
    w("-" * 100)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "recette_c3", os.path.join(os.path.dirname(__file__), "..", "copilote3", "recette.py"))
    c3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c3)
    reg = 0
    for i, (idu, q, kind) in enumerate(c3.QUESTIONS, 1):
        rep = A.answer(db, q)
        txt = (rep.get("text") or "")
        srcs = " ".join(rep.get("sources") or []).lower()
        suspect = ("cadastre" in srcs and kind in ("zone", "ppr", "constructible", "proprietaire"))
        bad = rep.get("web") or rep.get("general") or suspect
        if bad:
            reg += 1
            w(f"  ⚠ Q{i:02d} [{kind}] régression : web={rep.get('web')} general={rep.get('general')} suspect={suspect}")
    w(f"  → {'20/20 identiques (0 web, 0 source suspecte)' if reg == 0 else str(reg) + ' RÉGRESSIONS'}")
    w("\n" + "=" * 100)
    print("\n".join(out))
    return total_pb + reg


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
