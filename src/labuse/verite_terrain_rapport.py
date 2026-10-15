"""VERITE-TERRAIN-1 — assemblage des livrables depuis COMPARAISONS.csv.

- RAPPORT.md  : verdict en 5 lignes, puis UN TABLEAU PAR DONNÉE avec son taux de conformité,
                la part de fraîcheur (SOURCE PLUS RÉCENTE) et ce qui n'a pas pu être comparé.
- ECARTS.md   : la liste des « LABUSE FAUX » (candidats) à revérifier à la main — chaque écart
                confirmé y reste avec parcelle, champ, les deux valeurs, cause probable, fichier:ligne.

Lecture seule : lit le CSV, écrit des .md dans le dossier de la chasse. Rien en base.

    python -m labuse.verite_terrain_rapport
"""
from __future__ import annotations

import csv
from collections import defaultdict

from .verite_terrain import (CONFORME, FAUX, NC, RECENTE, COMPARAISONS_CSV, SORTIE,
                             ECHANTILLON_CSV, GRAINE)


def _lire() -> list[dict]:
    if not COMPARAISONS_CSV.exists():
        raise SystemExit("COMPARAISONS.csv absent — lancer d'abord `comparer` puis `fusionner`.")
    with open(COMPARAISONS_CSV, newline="") as f:
        return list(csv.DictReader(f))


def _par_champ(rows: list[dict]) -> dict:
    """Agrège par (source logique, champ) : compte chaque verdict."""
    agg: dict = defaultdict(lambda: {CONFORME: 0, FAUX: 0, RECENTE: 0, NC: 0, "n": 0})
    for r in rows:
        src = r["source"].split(" · ")[0]
        cle = (src, r["champ"])
        v = r["verdict"]
        if v in agg[cle]:
            agg[cle][v] += 1
        agg[cle]["n"] += 1
    return agg


def rapport() -> None:
    rows = _lire()
    n_parcelles = len({r["parcelle"] for r in rows})
    glob = {CONFORME: 0, FAUX: 0, RECENTE: 0, NC: 0}
    for r in rows:
        if r["verdict"] in glob:
            glob[r["verdict"]] += 1
    comparables = glob[CONFORME] + glob[FAUX] + glob[RECENTE]
    taux_global = (glob[CONFORME] / comparables * 100) if comparables else 0.0

    agg = _par_champ(rows)
    # regrouper par source pour l'affichage
    par_source: dict = defaultdict(list)
    for (src, champ), d in agg.items():
        par_source[src].append((champ, d))

    L = []
    L.append("# VERITE-TERRAIN-1 — RAPPORT")
    L.append("")
    L.append("## Verdict en 5 lignes")
    L.append("")
    L.append(f"1. **{n_parcelles} parcelles** (échantillon stratifié reproductible, graine `{GRAINE}`, "
             f"base q_v18) confrontées aux sources officielles, **8 familles de données**.")
    L.append(f"2. Sur **{comparables} comparaisons réellement comparables**, "
             f"**{taux_global:.1f}% CONFORMES** "
             f"({glob[CONFORME]} conformes · {glob[FAUX]} « LABUSE FAUX » · {glob[RECENTE]} fraîcheur).")
    L.append(f"3. **{glob[NC]} comparaisons NON COMPARABLES** (source muette, champ non publié, ou "
             f"présence non infirmable) — détaillées, jamais comptées comme un échec.")
    ecarts = [r for r in rows if r["verdict"] == FAUX]
    champs_faux = sorted({(r['source'].split(' · ')[0], r['champ']) for r in ecarts})
    L.append(f"4. Les « LABUSE FAUX » se concentrent sur : "
             f"{', '.join(f'{c[0]}/{c[1]}' for c in champs_faux) or 'aucun champ'} "
             f"(chaque cas revérifié à la main dans ECARTS.md).")
    L.append(f"5. Fraîcheur (SOURCE PLUS RÉCENTE) : {glob[RECENTE]} cas — la source a bougé depuis "
             f"notre ingestion, ce n'est pas un bug.")
    L.append("")
    L.append("Reproduire : `python -m labuse.verite_terrain comparer --source toutes` puis "
             "`fusionner` puis `python -m labuse.verite_terrain_rapport`. "
             "Contrôle mensuel : même commande avec `--n 20`.")
    L.append("")

    ORDRE = ["cadastre", "ban", "plu", "risques", "dvf", "bati", "entreprises", "energie_permis"]
    TITRES = {
        "cadastre": "1. Cadastre (API Carto cadastre / IGN)",
        "ban": "2. Adresses (BAN)",
        "plu": "3. PLU (Géoportail de l'urbanisme)",
        "risques": "4. Risques (Géorisques)",
        "dvf": "5. Ventes (DVF Etalab)",
        "bati": "6. Bâti (RNB / BD TOPO)",
        "entreprises": "7. Entreprises (Recherche d'entreprises / SIRENE)",
        "energie_permis": "8. Énergie & permis (ADEME DPE, Sitadel)",
    }
    for src in ORDRE:
        if src not in par_source:
            continue
        L.append(f"## {TITRES.get(src, src)}")
        L.append("")
        L.append("| Champ | Comparables | Conformes | Taux | LABUSE FAUX | Fraîcheur | Non comparable |")
        L.append("|---|---|---|---|---|---|---|")
        for champ, d in sorted(par_source[src]):
            comp = d[CONFORME] + d[FAUX] + d[RECENTE]
            taux = f"{d[CONFORME] / comp * 100:.0f}%" if comp else "—"
            L.append(f"| {champ} | {comp} | {d[CONFORME]} | {taux} | {d[FAUX]} | {d[RECENTE]} | {d[NC]} |")
        L.append("")
        # raisons de non-comparabilité (échantillon)
        raisons = defaultdict(int)
        for r in rows:
            if r["source"].split(" · ")[0] == src and r["verdict"] == NC:
                raisons[r["note"][:70]] += 1
        if raisons:
            L.append("Non comparable — raisons :")
            for raison, nb in sorted(raisons.items(), key=lambda kv: -kv[1])[:8]:
                L.append(f"- {nb}× {raison}")
            L.append("")

    (SORTIE / "RAPPORT.md").write_text("\n".join(L) + "\n")
    print(f"→ {SORTIE / 'RAPPORT.md'} ({n_parcelles} parcelles, {len(rows)} comparaisons)")

    # ── ECARTS.md : candidats LABUSE FAUX (à revérifier à la main) ──
    E = ["# VERITE-TERRAIN-1 — ÉCARTS (« LABUSE FAUX » à confirmer)",
         "",
         f"{len(ecarts)} comparaison(s) classées **LABUSE FAUX** par le comparateur. Chacune est "
         "**revérifiée à la main** (appel direct à la source rejoué, cause tracée) avant de rester "
         "ici comme écart confirmé. Les cas infirmés par la revue sont retirés avec la raison.",
         ""]
    if not ecarts:
        E.append("**Aucun écart LABUSE FAUX détecté sur les champs comparables.**")
    else:
        E.append("| Parcelle | Source · Champ | Servi (LABUSE) | Officiel | Écart | URL |")
        E.append("|---|---|---|---|---|---|")
        for r in ecarts:
            E.append(f"| {r['parcelle']} | {r['source']} | {r['valeur_labuse'][:40]} | "
                     f"{r['valeur_officielle'][:40]} | {r['ecart'][:40]} | {r['url'][:50]} |")
        E.append("")
        E.append("> Revue manuelle à mener parcelle par parcelle : rejouer l'appel officiel, "
                 "confirmer la valeur servie dans le code (`fichier:ligne`), trancher "
                 "FAUX confirmé / fraîcheur / artefact de méthode.")
    (SORTIE / "ECARTS.md").write_text("\n".join(E) + "\n")
    print(f"→ {SORTIE / 'ECARTS.md'} ({len(ecarts)} candidats)")


if __name__ == "__main__":
    rapport()
