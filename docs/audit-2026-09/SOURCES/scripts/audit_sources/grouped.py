"""SOURCES-AUDIT.md — les 116 sources par famille, verdict en tête de ligne, lisible."""
from __future__ import annotations

from pathlib import Path

FAMILLES_ORDRE = [
    "Parcelles et propriété", "Urbanisme et règles", "Risques, nature, patrimoine",
    "Marché, logement, permis", "Énergie, réseaux, assainissement",
    "Économie, équipements, accès", "Terrain, sol, imagerie", "Hubs et catalogues",
    "Voulues, absentes", "Autres",
]

# emoji par grande classe de verdict, pour le repérage
VERDICT_MARQUE = {
    "PLEINE": "🟢", "PARTIELLE": "🟡", "BRANCHÉE INVISIBLE": "🔵",
    "SERVIE HORS REGISTRE": "🟠", "PÉRIMÉE": "⚫", "RETIRÉE": "⚫", "À RETIRER": "🔴",
    "À DEMANDER": "⬜", "MANUELLE": "🟣", "ALIAS": "🔗", "HUB": "🏛",
}


def _marque(verdict: str) -> str:
    for k, m in VERDICT_MARQUE.items():
        if verdict.startswith(k):
            return m
    return "·"


def ecrire(records, out: Path):
    par_fam: dict[str, list] = {}
    for r in records:
        par_fam.setdefault(r["famille"], []).append(r)

    L = ["# SOURCES-AUDIT — les 116 sources par famille\n",
         "\n> Généré par `scripts/audit_sources` (lecture seule, rejouable). "
         "Verdict en tête de ligne. Détail : `fiches/<id>.md`. Données : `SOURCES-AUDIT.csv`.\n",
         "\n**Légende** : 🟢 PLEINE · 🟡 PARTIELLE · 🔵 BRANCHÉE INVISIBLE · "
         "🟠 SERVIE HORS REGISTRE · ⚫ RETIRÉE/PÉRIMÉE · 🔴 À RETIRER · ⬜ À DEMANDER/BRANCHER · "
         "🟣 MANUELLE · 🔗 ALIAS · 🏛 HUB\n"]

    # tableau récap des verdicts
    from collections import Counter
    cnt = Counter()
    for r in records:
        cnt[_classe(r["verdict"])] += 1
    L.append("\n## Compte des verdicts\n\n| Verdict | Nombre |\n|---|---|\n")
    for k in ["PLEINE", "PARTIELLE — champs manquants", "PARTIELLE — couverture incomplète",
              "BRANCHÉE INVISIBLE", "SERVIE HORS REGISTRE", "PÉRIMÉE", "À RETIRER",
              "À DEMANDER / À BRANCHER", "MANUELLE", "RETIRÉE (déjà)", "ALIAS (doublon)",
              "HUB (catalogue)"]:
        if cnt.get(k):
            L.append(f"| {k} | {cnt[k]} |\n")
    L.append(f"| **Total** | **{len(records)}** |\n")

    for fam in FAMILLES_ORDRE:
        rs = par_fam.get(fam)
        if not rs:
            continue
        L.append(f"\n## {fam}\n\n")
        L.append("| | Source | Verdict | Millésime base | Sentinelle | Filtre | "
                 "Chiffres | Où (résumé) |\n|---|---|---|---|---|---|---|---|\n")
        for r in sorted(rs, key=lambda x: x["id"]):
            ou = _resume_ou(r)
            L.append(f"| {_marque(r['verdict'])} | **{r['nom']}** (`{r['id']}`) | "
                     f"{r['verdict']} | {r['millesime_base'] or '—'} | "
                     f"{r['sous_sentinelle']} | {r['filtre_etat']} | "
                     f"{r['alimente_chiffres']} | {ou} |\n")
        # notes verdict par source (raison)
        for r in sorted(rs, key=lambda x: x["id"]):
            if r["verdict_raison"]:
                L.append(f"\n- **{r['nom']}** — {r['verdict_raison']}")
        L.append("\n")

    (out / "SOURCES-AUDIT.md").write_text("".join(L), encoding="utf-8")


def _classe(verdict: str) -> str:
    return verdict


def _resume_ou(r) -> str:
    bits = []
    if r["viz_fiche"]:
        bits.append("fiche")
    if r["viz_couche"]:
        bits.append("carte")
    if r["viz_outil"]:
        bits.append("outil")
    if r["viz_pdf"]:
        bits.append("PDF")
    if r["viz_copilote"]:
        bits.append("copilote")
    if r["viz_scoring"] == "oui":
        bits.append("scoring")
    return ", ".join(bits) or "—"
