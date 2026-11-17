"""MOTEUR-VERITE-FIX-3 LOT 4 — contrôle inverse contre ORIGIN/MAIN ACTUEL, avec MESURES.

Compare cache-fix3 (branche d'intégration) à cache-main3 (origin/main 9058a8f55 rejoué dans un
worktree propre — plus l'ancien cache e269abaa0). Pour CHAQUE parcelle au-dessus de main :

* on recompute la décision du moteur SUR LA PARCELLE : sous-zone réellement servie, LARGEUR SUR
  VOIE mesurée (somme des arêtes voie), surface, et la décision d'implantation
  (`analyser_condition_implantation`) avec ces mesures — pas un contrôle de syntaxe des
  paramètres de zone (grief du relecteur sur controle_inverse_vrai.py:34) ;
* une hausse n'est JUSTIFIÉE que par : (a) une feuille d'implantation SUR LISTE BLANCHE dont la
  décision OUVRE avec les mesures de la parcelle, ou (b) la formule H/2 à l'ÉGOUT (h_reference
  'egout' prouvé à l'article) servie niveau par niveau ;
* toute hausse HORS LISTE BLANCHE est un ÉCHEC (alerte ⚠, compteur, code retour ≠ 0) — la règle
  FIX-3 l'interdit par construction, ce script le PROUVE sur le stock.

    PYTHONPATH=src python docs/audit-2026-11/moteur-verite-fix-1/scripts/controle_inverse_fix3.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
FIX = RACINE / "docs" / "audit-2026-11" / "moteur-verite-fix-1"
CACHE = FIX / "cache-fix3"
REF = FIX / "cache-main3"
OUT = FIX / "CONTROLE-INVERSE-FIX3.csv"

COMMUNES = {"97401": "Les Avirons", "97402": "Bras-Panon", "97403": "Entre-Deux",
            "97404": "L'Étang-Salé", "97405": "Petite-Île", "97406": "La Plaine-des-Palmistes",
            "97407": "Le Port", "97408": "La Possession", "97409": "Saint-André",
            "97410": "Saint-Benoît", "97411": "Saint-Denis", "97412": "Saint-Joseph",
            "97413": "Saint-Leu", "97414": "Saint-Louis", "97415": "Saint-Paul",
            "97416": "Saint-Pierre", "97418": "Sainte-Marie", "97419": "Sainte-Rose",
            "97420": "Sainte-Suzanne", "97421": "Salazie", "97422": "Le Tampon",
            "97423": "Les Trois-Bassins", "97424": "Cilaos"}


def _largeur_sur_voie(session, pid: int) -> float | None:
    """Largeur SUR VOIE de la parcelle = somme des longueurs des arêtes classées voie (la même
    mesure que le moteur depuis FIX-3 LOT 2 — jamais le petit côté du rectangle englobant)."""
    from labuse.gabarit.limites import classify_parcel_limits
    try:
        lim = classify_parcel_limits(session, pid)
        tot = sum(float(e.geom.length) for e in lim.edges if e.type == "voie")
        return round(tot, 1) if tot > 0 else None
    except Exception:  # noqa: BLE001
        return None


def main() -> None:
    from sqlalchemy import text as _T

    from labuse.db import session_factory
    from labuse.faisabilite.db import parcel_faisabilite
    from labuse.faisabilite.zonage import resolve_zone
    from labuse.gabarit.builder import (_fraction_hauteur_formule,
                                        analyser_condition_implantation, liste_blanche_ok)

    session = session_factory()()
    lignes, echecs = [], 0
    for p in sorted(CACHE.glob("*.json")):
        new = json.loads(p.read_text())
        q = REF / p.name
        if not q.exists():
            continue
        old = json.loads(q.read_text())
        d = float(new.get("sdp_max_m2") or 0) - float(old.get("sdp_max_m2") or 0)
        if d <= 2:
            continue
        idu = p.stem
        commune = COMMUNES.get(idu[:5], idu[:5])
        zone = new.get("zone")

        # mesures de LA parcelle + sous-zone réellement servie par le moteur
        pid = session.execute(_T("select id from parcels where idu=:i"), {"i": idu}).scalar()
        largeur = surface = sous_zone = None
        if pid is not None:
            largeur = _largeur_sur_voie(session, pid)
            surface = session.execute(_T(
                "select coalesce(contenance_m2, ST_Area(geom_2975)) from parcels where id=:p"),
                {"p": pid}).scalar()
            try:
                res = parcel_faisabilite(session, pid)
                if res is not None:
                    sous_zone = (getattr(res[0], "uau_reelle", None) or {}).get("sous_zone")
            except Exception:  # noqa: BLE001
                sous_zone = None
        z_eff = sous_zone or zone
        zr = resolve_zone(z_eff, commune) if z_eff else None

        justifs = []
        if zr is not None:
            # (a) implantation en limite : feuille SUR LISTE BLANCHE dont la décision OUVRE avec
            #     les MESURES de la parcelle (largeur sur voie, surface).
            for cote, imp in (("latérales", zr.implantation_laterales),
                              ("fond", zr.implantation_fond)):
                if not imp or not liste_blanche_ok(imp):
                    continue
                dec = analyser_condition_implantation(
                    imp, largeur, float(surface) if surface else None)
                if dec["ouvre"]:
                    justifs.append((
                        f"implantation en limite ({cote}, zone {z_eff}) OUVERTE avec les mesures "
                        f"de la parcelle : largeur sur voie {largeur if largeur is not None else '?'} m, "
                        f"surface {round(float(surface)) if surface else '?'} m² — "
                        f"{dec['detail'] or 'sans condition au règlement'}",
                        imp.get("article") or "?", str(imp.get("citation") or "")[:140]))
            # (b) H/2 à l'égout prouvé : formule + h_reference 'egout' à l'article.
            frac = _fraction_hauteur_formule(getattr(zr, "recul_limites_formule", None))
            if (frac is not None and getattr(zr, "h_reference", None) == "egout"
                    and isinstance(zr.recul_limites_sep_m, (int, float))):
                justifs.append((
                    f"retrait relatif H×{frac:.3g} (min {zr.recul_limites_sep_m:g} m) à l'ÉGOUT "
                    f"(h_reference prouvé à l'article), niveau par niveau — zone {z_eff}",
                    zr.sources.get("recul_limites", "Art. 7"),
                    str(zr.recul_limites_formule)[:140]))

        if justifs:
            art = " ; ".join(sorted({j[1] for j in justifs}))
            preuve = " | ".join(j[0] for j in justifs)
            cit = justifs[0][2]
            ok = ""
        else:
            art, preuve, cit, ok = "?", "HAUSSE HORS LISTE BLANCHE — ÉCHEC", "", "⚠"
            echecs += 1
        lignes.append({"idu": idu, "commune": commune, "zone": zone, "sous_zone": sous_zone or "",
                       "largeur_voie_m": largeur if largeur is not None else "",
                       "surface_m2": round(float(surface)) if surface else "",
                       "sdp_main": old.get("sdp_max_m2"), "sdp_fix3": new.get("sdp_max_m2"),
                       "delta": round(d), "article": art, "preuve_mesuree": preuve,
                       "citation": cit, "alerte": ok})

    lignes.sort(key=lambda r: -r["delta"])
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]) if lignes else ["idu"], delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print(f"{len(lignes)} parcelles au-dessus d'origin/main (9058a8f55) → {OUT.name} ; "
          f"HORS LISTE BLANCHE : {echecs}")
    for r in lignes[:12]:
        print(f"  {r['alerte']}{r['idu']} {r['zone'] or '?':8s} {r['sdp_main'] or 0:>7} → "
              f"{r['sdp_fix3']:>7} (+{r['delta']})  {r['article'][:60]}")
    sys.exit(1 if echecs else 0)


if __name__ == "__main__":
    main()
