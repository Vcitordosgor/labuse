"""MOTEUR-VERITE-FIX-4 LOT 5 — régénère LISTE-BLANCHE.md depuis les YAML (état FIX-4).

Changements vs FIX-3 : Salazie UA porte le nombre MESURÉ (2 latérales + 1 fond, articles
distincts) ; Plaine Ub et Le Port Uc portent des FERMOIRS par prescription GPU mesurée
(patrimoine ; RHI / linéaires commerciaux) ; La Possession AUAv retiré des références égout
(règle propre 3 m). Le fichier reste contrôlable EN ENTIER par le relecteur.

    python docs/audit-2026-11/moteur-verite-fix-1/scripts/liste_blanche_md_fix4.py
"""
from __future__ import annotations

import glob
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[4]
OUT = RACINE / "docs" / "audit-2026-11" / "moteur-verite-fix-1" / "LISTE-BLANCHE.md"

NOMS = {"97401": "Les Avirons", "97402": "Bras-Panon", "97403": "Entre-Deux",
        "97404": "L'Étang-Salé", "97405": "Petite-Île", "97406": "La Plaine-des-Palmistes",
        "97407": "Le Port", "97408": "La Possession", "97409": "Saint-André",
        "97410": "Saint-Benoît", "97411": "Saint-Denis", "97412": "Saint-Joseph",
        "97413": "Saint-Leu", "97414": "Saint-Louis", "97415": "Saint-Paul",
        "97416": "Saint-Pierre", "97418": "Sainte-Marie", "97419": "Sainte-Rose",
        "97420": "Sainte-Suzanne", "97421": "Salazie", "97422": "Le Tampon",
        "97423": "Les Trois-Bassins", "97424": "Cilaos"}


def main() -> None:
    ouvertes, egouts = [], []
    for f in sorted(glob.glob(str(RACINE / "config" / "plu_destinations" / "*.yaml"))):
        insee = Path(f).name[:5]
        doc = yaml.safe_load(open(f))
        for z, zd in ((doc or {}).get("zones") or {}).items():
            leaf = (((zd or {}).get("regles") or {}).get("retraits") or {}).get("limites_separatives")
            if not isinstance(leaf, dict):
                continue
            for cote in ("implantation_laterales", "implantation_fond"):
                s = leaf.get(cote)
                if isinstance(s, dict) and isinstance(s.get("liste_blanche"), dict):
                    lb = s["liste_blanche"]
                    ouvertes.append((insee, z, cote.replace("implantation_", ""), s, lb))
            if leaf.get("h_reference") == "egout" and str(leaf.get("formule") or "").strip():
                egouts.append((insee, z, leaf))

    md = ["# LISTE BLANCHE — MOTEUR-VERITE-FIX-4 (contrôlable EN ENTIER)", "",
          "Tout est FERMÉ par défaut. Une capacité ne dépasse main que pour les zones ci-dessous.",
          "",
          "Changements FIX-4 : Salazie UA — nombre de limites MESURÉ (deux latérales au plus,",
          "U 7.2 ; UN fond, U 7.3 — budgets séparés, articles distincts) ; La Plaine Ub — la",
          "protection patrimoniale (Ub 7.2) est MESURÉE (prescription GPU 07, fermoir par",
          "parcelle) ; Le Port Uc — périmètres RHI (ER 22-25) et linéaires commerciaux",
          "(prescription 22) MESURÉS (fermoirs), CES 60 % OAP Mascareignes MESURÉ, ZAC Rivière",
          "des Galets portée en règle non modélisée ; La Possession AUAv RETIRÉ des références",
          "égout (règle propre 3 m, p.68). Le budget se compte sur des CÔTÉS CADASTRAUX",
          "(FIX-4 LOT 1 : jamais une coupe interne, une ligne hors contour ou une polyligne).",
          "",
          f"## A. Implantation en limite (ouvertures chiffrées) — "
          f"{len({(i, z) for i, z, *_ in ouvertes})} zones, {len(ouvertes)} feuilles", ""]
    for insee, z, cote, s, lb in ouvertes:
        md += [f"### {NOMS.get(insee, insee)} — {z} ({cote})",
               f"- Article {s.get('article')} · page PDF {s.get('page_pdf')} · mode `{s.get('mode')}`"
               + (f" · `{s.get('condition_modelable')}`" if s.get("condition_modelable") else ""),
               f"- Citation : « {str(s.get('citation') or '')[:260]} »",
               f"- Justification : {str(lb.get('justification') or '').strip()[:500]}",
               "- Conditions : " + " ; ".join(f"{k}={v}" for k, v in (lb.get("conditions") or {}).items())]
        if s.get("ferme_si_prescription"):
            md += ["- Fermoirs MESURÉS : "
                   + " | ".join(str(r.get("motif"))[:90] for r in s["ferme_si_prescription"])]
        md += [""]
    md += [f"## B. H/2 à l'ÉGOUT prouvé (niveau par niveau) — {len(egouts)} zones", ""]
    for insee, z, leaf in egouts:
        md += [f"- **{NOMS.get(insee, insee)} {z}** — {leaf.get('article')} p.{leaf.get('page_pdf')} : "
               f"`{leaf.get('formule')}` · « {str(leaf.get('citation') or '')[:140]} »"]
    md += ["", "Toutes les autres zones : retrait prudent (minimum sourcé ; formule au faîtage",
           "PRUDENT quand la référence n'est pas l'égout) — aucune hausse admise au contrôle inverse.", ""]
    OUT.write_text("\n".join(md))
    print(f"→ {OUT.name} : {len(ouvertes)} feuilles ouvertes, {len(egouts)} zones égout")


if __name__ == "__main__":
    main()
