"""FIX-PRIX-ET-OPPORTUNITES lot 2 — DIAGNOSTIC (lecture seule, aucune modification de règle).

Reprend les deux gisements de VERITE-TERRAIN-2 volet D (fichier committé `PERMIS-VS-CAPACITE.csv`) :
  · 913 permis « densité réelle > calibrage LABUSE » (parcelle servie, capacité positive mais dépassée) ;
  · 418 permis « non constructible LABUSE » (capacité nulle alors qu'un permis logements a été autorisé,
    cause générique « rédhibitoire » + sous-causes terrain_exigu / zone A·N / PPR / ER).

Classe CHAQUE cas en 4 familles demandées par Vic : réunion de parcelles · antérieur au PLU · dérogation ·
erreur réelle de LABUSE (règle mal calibrée / seuil trop strict). Les deux premières sont OBSERVABLES
dans la donnée (nombre de parcelles, date vs millésime). La « dérogation » n'est PAS un champ Sit@del :
elle se cache, avec l'erreur réelle et le redécoupage, dans le résidu mono-parcelle bien postérieur au
PLU — on la borne, on ne l'invente pas.

    PYTHONPATH=src python scripts/diagnostic_opportunites_lot2.py
→ écrit docs/audit-2026-10/opportunites-diagnostic/CLASSIFICATION-LOT2.csv + imprime le résumé.
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SRC = RACINE / "docs" / "audit-2026-10" / "verite-terrain-2" / "PERMIS-VS-CAPACITE.csv"
OUT_DIR = RACINE / "docs" / "audit-2026-10" / "opportunites-diagnostic"
OUT_CSV = OUT_DIR / "CLASSIFICATION-LOT2.csv"

#: autorisé ≤ ce nb de mois après l'entrée en vigueur du PLU → très probablement DÉPOSÉ/instruit sous
#: l'ancien règlement (l'instruction d'un PC prend des mois ; un projet autorisé dans l'année d'un PLU
#: neuf a presque toujours été conçu sous les règles précédentes). Sensibilité donnée à 6 et 24 mois.
SEUIL_PLU_MOIS = 12


def _d(s):
    try:
        return date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def _mois(a, b):
    return None if (not a or not b) else (a.year - b.year) * 12 + (a.month - b.month)


def _f(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _fam(zones: str) -> str:
    z = zones or ""
    if "(" in z:
        f = z.split("(", 1)[1].rstrip(")").split("|")[0].strip()
        if f and f != "?":
            return f
    z = z.split(" (")[0].split("|")[0].lstrip("0123456789").upper()
    for p in ("AU", "U", "A", "N"):
        if z.startswith(p):
            return p
    return z or "?"


def _ratio(r):
    xs = [_f(r["ratio_sdp"]), _f(r["ratio_log"])]
    xs = [x for x in xs if x is not None]
    return max(xs) if xs else None


def _ncodes(r):
    return len((r["idu_codes"] or "").split())


def classer(r: dict, bucket: str, seuil_mois: int = SEUIL_PLU_MOIS) -> tuple[str, str]:
    """(famille, détail). Priorité : grain (réunion) → temporel (antérieur PLU) → résidu métier."""
    npar = int(r["n_parcelles"] or 1)
    nserv = int(r["n_parcelles_servies"] or 0)
    m = _mois(_d(r["date_permis"]), _d(r["millesime_plu"]))
    note = r["note"] or ""
    fam = _fam(r["zones"])

    if npar > 1 and nserv < npar:
        return "réunion de parcelles", "somme incomplète (parcelle(s) disparue(s)/redécoupée(s))"
    if m is not None and m <= seuil_mois:
        return "antérieur au PLU", f"autorisé {m} mois après le millésime (instruit sous l'ancien règlement)"
    if npar > 1:
        return "réunion de parcelles", f"{npar} parcelles servies — gabarit mutualisé > somme des gabarits unitaires"

    # résidu mono-parcelle, bien postérieur au PLU
    if bucket == "dens":
        x = _ratio(r)
        if x is None:
            return "indéterminé", "ratio non mesurable"
        if x <= 1.2:
            return "dérogation ou bruit", f"ratio {x:.2f} — dans le bruit de conversion SDP (coef 1,15)"
        if x <= 2.0:
            return "erreur réelle LABUSE", f"gabarit trop bas (ratio {x:.2f}) — zone {fam}, calibrage hauteur/emprise"
        if x <= 3.0:
            return "dérogation ou densité réelle", f"écart fort (ratio {x:.2f}) — dérogation ou densité réelle > gabarit"
        return "dérogation ou redécoupage", f"écart très fort (ratio {x:.2f})"
    # bucket == "ncon"
    if "terrain_exigu" in note and not re.search(r"zone_non_constructible:[AN]", note):
        return "erreur réelle LABUSE", f"seuil terrain_exigu trop strict — permis logements en zone {fam}"
    if re.search(r"zone_non_constructible:[AN]", note):
        return "dérogation ou exception", f"zone {fam} non constructible — exception agricole/STECAL OU zonage à vérifier"
    if "ppr" in note.lower():
        return "dérogation ou exception", "PPR rouge — permis antérieur à la servitude ou prescriptions"
    if "emplacement" in note.lower():
        return "dérogation ou exception", "emplacement réservé"
    # rédhibitoire générique, sans sous-cause nommée
    if fam == "U":
        return "erreur réelle LABUSE", "exclusion « rédhibitoire » sur parcelle URBAINE constructible — règle trop agressive (reste à nommer via le détail cascade)"
    return "dérogation ou exception", f"« rédhibitoire » en zone {fam} (non urbaine) — plutôt légitime"


def main() -> None:
    rows = list(csv.DictReader(open(SRC)))
    buckets = {"densité réelle > calibrage LABUSE": "dens", "non constructible LABUSE": "ncon"}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tot = {}
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["permit_id", "commune", "insee", "zones", "date_permis", "millesime_plu",
                    "n_parcelles", "n_parcelles_servies", "ratio_sdp", "ratio_log",
                    "gisement", "famille", "detail", "n_parcelles_idu"])
        for cause, bucket in buckets.items():
            grp = [r for r in rows if r["cause_si_au_dessus"] == cause]
            fam_count = Counter()
            fam_parc = Counter()
            for r in grp:
                fam, detail = classer(r, bucket)
                fam_count[fam] += 1
                fam_parc[fam] += _ncodes(r)
                w.writerow([r["permit_id"], r["commune"], r["insee"], r["zones"], r["date_permis"],
                            r["millesime_plu"], r["n_parcelles"], r["n_parcelles_servies"],
                            r["ratio_sdp"], r["ratio_log"], bucket, fam, detail, _ncodes(r)])
            tot[cause] = (len(grp), fam_count, fam_parc)

    print(f"→ {OUT_CSV}\n")
    for cause, (n, fc, fp) in tot.items():
        print(f"===== {cause} = {n} permis =====")
        for fam in sorted(fc, key=lambda k: -fc[k]):
            print(f"  {fam:30s} : {fc[fam]:4d} permis · {fp[fam]:4d} parcelle(s) IDU")
        print()

    # sensibilité du seuil « antérieur au PLU »
    print("Sensibilité « antérieur au PLU » (permis ≤ N mois du millésime) :")
    for cause, bucket in buckets.items():
        grp = [r for r in rows if r["cause_si_au_dessus"] == cause]
        for s in (6, 12, 24):
            n = sum(1 for r in grp if (_mois(_d(r["date_permis"]), _d(r["millesime_plu"])) or 999) <= s)
            print(f"  {bucket} ≤{s:2d} mois : {n}")


if __name__ == "__main__":
    main()
