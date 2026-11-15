"""MOTEUR-VERITE-FIX-4 LOT 5 — le contrôle inverse par la PREUVE, côté par côté.

Pour CHAQUE parcelle dont la capacité (cache-fix4final) dépasse origin/main (cache-main3),
y compris les hausses de 1 ou 2 m² (plus aucun filtre), le contrôle RETROUVE :

1. la LIMITE CADASTRALE effectivement utilisée — les arêtes réellement posées en limite 0 m
   par le scénario retenu (`ruleId == limite-sep-limite` du gabarit), avec type (latérale/
   fond), longueur, et drapeau cadastral (jamais une coupe interne, FIX-4 LOT 1) ;
2. la CONDITION réglementaire effectivement appliquée (`racc.implantation.appliques` +
   décision rejouée avec les mesures de la parcelle) ;
3. l'EFFET CHIFFRÉ de cette condition : la capacité est RE-CALCULÉE toutes ouvertures
   FERMÉES (monkeypatch de la décision) — delta = part de la hausse due à l'ouverture ; le
   reste relève de la formule H/2 à l'égout prouvé (niveau par niveau).

Une hausse HORS LISTE BLANCHE (ni ouverture `liste_blanche_ok` ni égout prouvé) = ÉCHEC
(alerte ⚠, exit 1). Les SDP « capacité à vérifier » restent « inconnu » — jamais 0.

    PYTHONPATH=src python docs/audit-2026-11/moteur-verite-fix-1/scripts/controle_inverse_fix4.py [tag]
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
FIX = RACINE / "docs" / "audit-2026-11" / "moteur-verite-fix-1"
TAG = sys.argv[1] if len(sys.argv) > 1 else "fix4final"
CACHE = FIX / f"cache-{TAG}"
REF = FIX / "cache-main3"
OUT = FIX / "CONTROLE-INVERSE-FIX4.csv"

COMMUNES = {"97401": "Les Avirons", "97402": "Bras-Panon", "97403": "Entre-Deux",
            "97404": "L'Étang-Salé", "97405": "Petite-Île", "97406": "La Plaine-des-Palmistes",
            "97407": "Le Port", "97408": "La Possession", "97409": "Saint-André",
            "97410": "Saint-Benoît", "97411": "Saint-Denis", "97412": "Saint-Joseph",
            "97413": "Saint-Leu", "97414": "Saint-Louis", "97415": "Saint-Paul",
            "97416": "Saint-Pierre", "97418": "Sainte-Marie", "97419": "Sainte-Rose",
            "97420": "Sainte-Suzanne", "97421": "Salazie", "97422": "Le Tampon",
            "97423": "Les Trois-Bassins", "97424": "Cilaos"}


def _sdp_fermee(session, pid: int) -> float | None:
    """Capacité recalculée TOUTES OUVERTURES FERMÉES (décision d'implantation neutralisée) —
    l'écart avec la capacité servie est l'EFFET CHIFFRÉ de la condition d'ouverture."""
    import labuse.gabarit.builder as B
    from labuse.faisabilite.db import parcel_faisabilite
    orig = B.analyser_condition_implantation

    def _fermee(imp, largeur_m, surface_m2):
        d = orig(imp, largeur_m, surface_m2)
        d.update(ouvre=False, zero=0, bande_m=None, lineaire_pct=None, detail=None, mention=None)
        return d

    B.analyser_condition_implantation = _fermee
    try:
        res = parcel_faisabilite(session, pid)
    except Exception:  # noqa: BLE001
        res = None
    finally:
        B.analyser_condition_implantation = orig
    if res is None:
        return None
    return (res[1].fourchette or {}).get("surface_plancher_m2")


def main() -> None:
    from sqlalchemy import text as _T

    from labuse.db import session_factory
    from labuse.gabarit.builder import (_fraction_hauteur_formule, build_gabarit_input,
                                        liste_blanche_ok)
    from labuse.faisabilite.zonage import resolve_zone
    from labuse.faisabilite.db import parcel_faisabilite

    session = session_factory()()
    lignes, echecs = [], 0
    for p in sorted(CACHE.glob("*.json")):
        new = json.loads(p.read_text())
        q = REF / p.name
        if not q.exists():
            continue
        old = json.loads(q.read_text())
        if new.get("sdp_max_m2") is None:
            continue                              # capacité à vérifier : INCONNUE, pas une hausse
        d = float(new.get("sdp_max_m2") or 0) - float(old.get("sdp_max_m2") or 0)
        if d <= 0:
            continue                              # TOUTES les hausses, 1-2 m² comprises
        idu = p.stem
        commune = COMMUNES.get(idu[:5], idu[:5])
        pid = session.execute(_T("select id from parcels where idu=:i"), {"i": idu}).scalar()
        if pid is None:
            continue

        # 1. la limite cadastrale effectivement utilisée (arêtes en limite 0 m du scénario)
        cotes, appliques, mentions = [], [], []
        try:
            gb = build_gabarit_input(session, idu)
            if gb is not None:
                for sb in gb.input.setbacks:
                    if sb.ruleId == "limite-sep-limite":
                        cotes.append(f"{'latérale' if sb.type == 'side' else 'fond'}")
                imp = (gb.raccordement or {}).get("implantation") or {}
                appliques = list(imp.get("appliques") or [])
                mentions = list(imp.get("mentions") or [])
        except Exception:  # noqa: BLE001
            pass
        # longueurs/cadastral des côtés réellement qualifiés (même pipeline que le moteur)
        cotes_mesures = ""
        try:
            from labuse.gabarit.builder import _multizone_split
            from labuse.gabarit.limites import classify_parcel_limits
            cons, noncons, _b = _multizone_split(session, pid)
            kw = {}
            if cons and len(cons) == 1 and cons[0].get("wkt"):
                kw = dict(sub_geom_wkt=cons[0]["wkt"],
                          extra_neighbors_wkt=[c["wkt"] for c in noncons if c["wkt"]])
            lim = classify_parcel_limits(session, pid, **kw)
            cotes_mesures = " ; ".join(
                f"{e.type} {e.length_m:.1f} m{' (NON cadastrale)' if not e.cadastrale else ''}"
                for e in lim.edges if e.type in ("side", "rear"))
        except Exception:  # noqa: BLE001
            pass

        # 2+3. condition appliquée + effet chiffré (capacité toutes ouvertures fermées)
        sdp_f = _sdp_fermee(session, pid)
        effet = (round(float(new["sdp_max_m2"]) - float(sdp_f))
                 if isinstance(sdp_f, (int, float)) else None)

        # liste blanche : ouverture whitelistée OU égout prouvé — sinon ÉCHEC
        zone = new.get("zone")
        sous_zone = None
        try:
            res = parcel_faisabilite(session, pid)
            if res is not None:
                sous_zone = (getattr(res[0], "uau_reelle", None) or {}).get("sous_zone")
        except Exception:  # noqa: BLE001
            pass
        z_eff = sous_zone or zone
        zr = resolve_zone(z_eff, commune) if z_eff else None
        lb_ok = egout_ok = False
        if zr is not None:
            lb_ok = any(liste_blanche_ok(i) for i in (zr.implantation_laterales,
                                                      zr.implantation_fond) if i)
            frac = _fraction_hauteur_formule(getattr(zr, "recul_limites_formule", None))
            egout_ok = (frac is not None and getattr(zr, "h_reference", None) == "egout"
                        and isinstance(zr.recul_limites_sep_m, (int, float)))
        ok = "" if (lb_ok or egout_ok) else "⚠"
        if ok:
            echecs += 1
        lignes.append({
            "idu": idu, "commune": commune, "zone": zone, "sous_zone": sous_zone or "",
            "sdp_main": old.get("sdp_max_m2"), "sdp_fix4": new.get("sdp_max_m2"),
            "delta": round(d),
            "cotes_en_limite": " + ".join(cotes) if cotes else "aucun (retrait partout)",
            "cotes_cadastraux": cotes_mesures,
            "condition_appliquee": " | ".join(appliques) or ("H/2 à l'égout prouvé, niveau "
                                                             "par niveau" if egout_ok else ""),
            "mentions": " | ".join(mentions),
            "sdp_toutes_fermees": sdp_f if sdp_f is not None else "inconnu",
            "effet_ouverture_m2": effet if effet is not None else "",
            "liste_blanche": "ouverture" if lb_ok else ("egout" if egout_ok else "HORS LISTE"),
            "alerte": ok})

    lignes.sort(key=lambda r: -r["delta"])
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]) if lignes else ["idu"], delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print(f"{len(lignes)} hausses (SEUIL 0 — 1-2 m² comprises) vs origin/main → {OUT.name} ; "
          f"HORS LISTE BLANCHE : {echecs}")
    for r in lignes[:14]:
        print(f"  {r['alerte']}{r['idu']} {r['zone'] or '?':7s} {r['sdp_main'] or 0:>7} → "
              f"{r['sdp_fix4']:>7} (+{r['delta']})  en limite: {r['cotes_en_limite'][:30]:32s} "
              f"effet: {r['effet_ouverture_m2']}")
    sys.exit(1 if echecs else 0)


if __name__ == "__main__":
    main()
