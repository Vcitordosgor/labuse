"""MOTEUR-VERITE-FIX-1 — mesures après chaque lot, permis réels pour juge.

Compare le cache du lot (cache-<tag>/) au cache de RÉFÉRENCE de l'audit VERITE-TERRAIN-3
(moteur d'avant les correctifs) :
  · Test 1 : % de permis H où le moteur dit « constructible » (+ « capacité à vérifier » à part) ;
  · Test 2 : ratio autorisé/enveloppe max sur H mono-parcelle, dépassements > 1,10 ;
  · « terrain_exigu » restants (parcelles des permis de la cohorte rejouée) ;
  · CONTRÔLE INVERSE : les 30 plus fortes HAUSSES de capacité (ancien vs nouveau), à relire ;
    garde A/N : aucune parcelle passée de non-constructible à constructible en zone A/N sans règle
    (liste intégrale si ça arrive) ; garde des rubans : tests unitaires (cités, joués à part).

    PYTHONPATH=src python docs/audit-2026-11/moteur-verite-fix-1/scripts/mesures_fix.py lot1
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
FIX = RACINE / "docs" / "audit-2026-11" / "moteur-verite-fix-1"
VT3 = RACINE / "docs" / "audit-2026-11" / "verite-terrain-3"
CACHE_REF = VT3 / "cache" / "capacite"
COEF_PLANCHER = 1.15

tag = sys.argv[1] if len(sys.argv) > 1 else "lot1"
CACHE = FIX / f"cache-{tag}"


def lire(cache: Path, idu: str) -> dict | None:
    p = cache / f"{idu}.json"
    return json.loads(p.read_text()) if p.exists() else None


def main() -> None:
    h = list(csv.DictReader(open(VT3 / "cohortes" / "H.csv", newline="")))
    n_ok = n_non = n_averif = n_sans = 0
    exigu = set()
    t2 = []
    for p in h:
        idus = [i.strip() for i in p["idus"].split(",") if i.strip()]
        caps = [lire(CACHE, i) for i in idus]
        if any(c is None for c in caps):
            n_sans += 1
            continue
        constr = [bool(c.get("constructible")) for c in caps]
        for c in caps:
            if str(c.get("cause") or c.get("cause_moteur") or "").startswith("terrain_exigu"):
                exigu.add(c["idu"])
        averif = any("capacité à vérifier" in str(c.get("verdict") or "") for c in caps)
        if any(constr):
            n_ok += 1
        elif averif:
            n_averif += 1
        else:
            n_non += 1
        if p["mono"] == "t":
            c = caps[0]
            aut = float(p["surf_hab"] or 0) * COEF_PLANCHER
            emp, niv = c.get("emprise_constructible_m2"), c.get("niveaux_max")
            if emp is not None and niv and aut > 0:
                t2.append(aut / (float(emp) * int(niv)))
    n = n_ok + n_non + n_averif
    print(f"H évaluables : {n} (sans cache : {n_sans})")
    print(f"TEST 1 — constructible : {n_ok}/{n} ({100 * n_ok / n:.1f} %) ; "
          f"« capacité à vérifier » : {n_averif} ({100 * n_averif / n:.1f} %) ; "
          f"non : {n_non} ({100 * n_non / n:.1f} %)")
    dep = sum(1 for r in t2 if r > 1.10)
    print(f"TEST 2 — enveloppe mesurable : {len(t2)} ; dépassements >1,10 : {dep} "
          f"({100 * dep / max(1, len(t2)):.1f} %)")
    print(f"terrain_exigu restants (parcelles des permis H) : {len(exigu)}")

    # cohorte rejouée complète (VT-2) : causes « au-dessus » du CSV du lot si présent
    permis_csv = FIX / f"PERMIS-VS-CAPACITE-{tag.upper()}.csv"
    if permis_csv.exists():
        rows = list(csv.DictReader(open(permis_csv)))
        au = [r for r in rows if r["au_dessus"] == "True"]
        print(f"\nCohorte rejouée ({len(rows)} permis) — au-dessus : {len(au)} "
              f"({100 * len(au) / len(rows):.1f} %) ; "
              f"causes : {Counter(r['cause_si_au_dessus'] for r in au).most_common()}")

    # ── CONTRÔLE INVERSE ────────────────────────────────────────────────────────
    hausses, an_sans_regle = [], []
    for p in CACHE.glob("*.json"):
        new = json.loads(p.read_text())
        old = lire(CACHE_REF, p.stem)
        if old is None:
            continue
        d = float(new.get("sdp_max_m2") or 0) - float(old.get("sdp_max_m2") or 0)
        if d > 0:
            hausses.append((d, p.stem, old, new))
        if (new.get("constructible") and not old.get("constructible")
                and str(new.get("zone_fam") or "").upper() in ("A", "N")):
            an_sans_regle.append((p.stem, old.get("cause"), new.get("verdict")))
    hausses.sort(key=lambda x: -x[0])
    print(f"\nCONTRÔLE INVERSE — parcelles en hausse : {len(hausses)} ; les 30 plus fortes :")
    for d, idu, old, new in hausses[:30]:
        print(f"  {idu}  {old.get('sdp_max_m2') or 0:7.0f} → {new.get('sdp_max_m2') or 0:7.0f} m² "
              f"(+{d:.0f})  zone {new.get('zone')}  niveaux {old.get('niveaux_max')}→{new.get('niveaux_max')}")
    print(f"garde A/N : {len(an_sans_regle)} parcelle(s) passée(s) constructible(s) en zone A/N")
    for idu, oc, nv in an_sans_regle[:20]:
        print(f"  ⚠ {idu} : {oc} → {str(nv)[:80]}")
    with open(FIX / f"CONTROLE-INVERSE-{tag}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idu", "sdp_avant", "sdp_apres", "hausse", "zone", "niveaux_avant",
                    "niveaux_apres", "verdict_apres"])
        for d, idu, old, new in hausses[:30]:
            w.writerow([idu, old.get("sdp_max_m2"), new.get("sdp_max_m2"), round(d),
                        new.get("zone"), old.get("niveaux_max"), new.get("niveaux_max"),
                        str(new.get("verdict") or "")[:160]])
    print(f"→ CONTROLE-INVERSE-{tag}.csv (30 lignes, à relire une par une)")


if __name__ == "__main__":
    main()
