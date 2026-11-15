"""ETUDE-STATIONNEMENT-FIX-1 (LOT 3) — couverture du stationnement, zone constructible par zone.

Pour CHAQUE zone U/AU de chaque commune : la règle ingérée (mode + synthèse), OU la raison précise de
son absence (habitat interdit · renvoi à une zone mère · texte non servi en base · à ingérer). Jamais
« None » : une raison explicite partout. Sert à produire les TABLEAUX DE COUVERTURE du livrable et à
repérer les zones où l'habitat est permis mais la règle manque.

Usage : PYTHONPATH=src python scripts/stationnement_couverture.py [docs_out.md]
"""
from __future__ import annotations

import re
import sys

import yaml

from labuse.implantation import regles as R
from labuse.plu import destinations as D

CFG = "config/plu_destinations/"
PILOTES = {"97401", "97407", "97410", "97416", "97422"}
TEXTE_ABSENT = {"97404": "extraction partielle (12 p./97)", "97409": "règlement absent de la base",
                "97413": "règlement absent de la base", "97406": "barème en annexe non ingérée",
                "97411": "barème en dispositions générales XVII non ingéré"}


def _is_c(z):
    return re.match(r'^\d*(U|AU)', z or "", re.I) is not None


def _habitat_possible(zv: dict) -> bool:
    """Habitat (logement OU hébergement) permis dans la zone ? interdit explicite → non ; sinon (autorisé /
    sous condition / non mentionné avec silence « autorise ») → oui."""
    sd = zv.get("sous_destinations") or {}
    sil = zv.get("silence")
    for slug in ("logement", "hebergement"):
        st = (sd.get(slug) or {}).get("statut") if isinstance(sd.get(slug), dict) else None
        if st in ("autorise", "sous_condition"):
            return True
        if st in (None, "non_mentionne") and sil == "autorise":
            return True
    return False


def _synthese(b: R.BaremeStationnement) -> str:
    if b.mode == "par_logement":
        s = f"{b.flat_places:g} place/logt (arr. {b.arrondi})"
    elif b.mode == "par_m2_sdp":
        s = f"1 place / {b.m2_par_place:g} m² (arr. {b.arrondi})"
    elif b.mode == "par_typologie":
        s = "typologie [" + " ; ".join(
            f"{l.destination} {(format(l.places,'g')+'/logt') if l.places is not None else '1/'+format(l.par_m2,'g')+'m²'}"
            + (f"·{l.role}" if l.role != "base" else "") for l in b.lignes if l.destination == "collectif" or l.role != "base") + f"] (retenue {b.retenue})"
    else:
        s = b.mode
    extra = []
    if b.visiteurs:
        base = f"{b.visiteurs.par_logements} logts" if b.visiteurs.par_logements else f"{b.visiteurs.par_m2_sdp:g} m²"
        extra.append(f"visiteur {b.visiteurs.places:g}/{base}")
    for dest in ("social", "senior", "etudiant"):
        if b.has_destination(dest):
            extra.append(dest)
    if b.integ_pct:
        extra.append(f"intégrées {b.integ_pct:g}%>{b.integ_seuil_m2:g}m²")
    return s + ((" · " + " · ".join(extra)) if extra else "")


def couverture(insee: str):
    """[(zone, etat, detail)] pour toutes les zones U/AU. etat ∈ {ingérée, à ingérer, habitat interdit,
    renvoi, texte absent, propose}."""
    path = None
    import glob
    hits = glob.glob(CFG + f"{insee}_*.yaml")
    if not hits:
        return []
    doc = yaml.safe_load(open(hits[0], encoding="utf-8")) or {}
    zones = doc.get("zones") or {}
    rows = []
    for z in sorted(zones):
        if not _is_c(z):
            continue
        zv = zones[z] or {}
        if zv.get("renvoi") and not zv.get("regles"):
            rows.append((z, "renvoi", f"règles de la zone {zv['renvoi']}"))
            continue
        b = R.charger(insee, z).stationnement
        if b.validee:
            rows.append((z, "ingérée", _synthese(b)))
        elif not _habitat_possible(zv):
            rows.append((z, "habitat interdit", "zone d'activité/équipement — pas de norme d'habitation à servir"))
        elif insee in TEXTE_ABSENT:
            rows.append((z, "texte absent", TEXTE_ABSENT[insee]))
        else:
            rows.append((z, "à ingérer", "habitat permis, barème non encore servi — à lire au texte"))
    return rows


def main():
    communes = sorted({p.split("/")[-1].split("_")[0] for p in __import__("glob").glob(CFG + "974*_*.yaml")})
    out = ["# Couverture du stationnement — zone constructible par zone (24 communes)\n",
           "ETUDE-STATIONNEMENT-FIX-1 (LOT 3). Chaque zone U/AU : règle ingérée (synthèse) OU raison précise "
           "de son absence. Jamais « None ».\n"]
    manque = []
    for insee in communes:
        rows = couverture(insee)
        if not rows:
            continue
        slug = [p for p in __import__("glob").glob(CFG + f"{insee}_*.yaml")][0].split("/")[-1][6:-5]
        ing = sum(1 for _z, e, _d in rows if e == "ingérée")
        out.append(f"\n## {insee} — {slug} ({ing}/{len(rows)} zones servies)\n")
        out.append("| Zone | État | Détail |\n|---|---|---|")
        for z, e, d in rows:
            out.append(f"| {z} | {e} | {d} |")
            if e == "à ingérer":
                manque.append((insee, z))
    out.append("\n## Zones « à ingérer » (habitat permis, barème manquant)\n")
    out.append(", ".join(f"{i}/{z}" for i, z in manque) if manque else "— aucune —")
    txt = "\n".join(out)
    if len(sys.argv) > 1:
        open(sys.argv[1], "w", encoding="utf-8").write(txt)
        print("écrit:", sys.argv[1], "·", len(manque), "zones à ingérer")
    else:
        print(txt)
    return manque


if __name__ == "__main__":
    main()
