"""MOTEUR-VERITE-FIX-5 LOT 4 — le contrôle inverse : AVEC et SANS la règle, reculs par côté.

Référence : origin/main 049dbcf7f rejoué (cache-main5). Pour CHAQUE hausse (seuil 0) :

1. le RECUL RÉELLEMENT APPLIQUÉ, côté par côté, lu dans LA classification du scénario servi
   (les setbacks du gbuild : ruleId, type latérale/fond/voie, longueur, recul en m — une seule
   classification, jamais une seconde qui divergerait, grief FIX-4) ;
2. le recalcul AVEC et SANS la règle qui justifie la hausse : ouvertures fermées (monkeypatch
   de la décision d'implantation) ET formule niveau-par-niveau retirée — l'écart de chaque
   rejeu isole l'EFFET de chaque règle ;
3. la hausse n'est admise QUE sur la liste du mandat (ouverture liste blanche / égout
   La Possession hors AU / façade Sainte-Marie UA-UAz, Bras-Panon Ub-Uc) — sinon ÉCHEC (exit 1).

En tête : parcelles en HAUSSE / en BAISSE / INCHANGÉES vs main, puis la liste complète.

    PYTHONPATH=src python docs/audit-2026-11/moteur-verite-fix-1/scripts/controle_inverse_fix5.py [tag]
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
FIX = RACINE / "docs" / "audit-2026-11" / "moteur-verite-fix-1"
TAG = sys.argv[1] if len(sys.argv) > 1 else "fix5"
CACHE = FIX / f"cache-{TAG}"
REF = FIX / "cache-main5"
OUT = FIX / "CONTROLE-INVERSE-FIX5.csv"

COMMUNES = {"97401": "Les Avirons", "97402": "Bras-Panon", "97403": "Entre-Deux",
            "97404": "L'Étang-Salé", "97405": "Petite-Île", "97406": "La Plaine-des-Palmistes",
            "97407": "Le Port", "97408": "La Possession", "97409": "Saint-André",
            "97410": "Saint-Benoît", "97411": "Saint-Denis", "97412": "Saint-Joseph",
            "97413": "Saint-Leu", "97414": "Saint-Louis", "97415": "Saint-Paul",
            "97416": "Saint-Pierre", "97418": "Sainte-Marie", "97419": "Sainte-Rose",
            "97420": "Sainte-Suzanne", "97421": "Salazie", "97422": "Le Tampon",
            "97423": "Les Trois-Bassins", "97424": "Cilaos"}

#: hausses ADMISES par le mandat FIX-5 (liste fermée)
FACADE_OK = {("97418", "UA"), ("97418", "UAz"), ("97402", "Ub"), ("97402", "Uc")}
OUVERTURE_OK_INSEE = {"97406", "97421"}          # Plaine Ub, Salazie UA (portes du moteur)
EGOUT_OK_INSEE = {"97408"}                       # La Possession hors AU


def _rejouer(session, pid: int, *, sans_ouvertures: bool, sans_formule: bool):
    import labuse.gabarit.builder as B
    from labuse.faisabilite.db import parcel_faisabilite
    orig_dec = B.analyser_condition_implantation
    orig_frac = B._fraction_hauteur_formule

    def _fermee(imp, largeur_m, surface_m2):
        d = orig_dec(imp, largeur_m, surface_m2)
        d.update(ouvre=False, zero=0, bande_m=None, lineaire_pct=None, detail=None, mention=None)
        return d

    if sans_ouvertures:
        B.analyser_condition_implantation = _fermee
    if sans_formule:
        B._fraction_hauteur_formule = lambda f: None
    try:
        res = parcel_faisabilite(session, pid)
    except Exception:  # noqa: BLE001
        res = None
    finally:
        B.analyser_condition_implantation = orig_dec
        B._fraction_hauteur_formule = orig_frac
    if res is None:
        return None
    return (res[1].fourchette or {}).get("surface_plancher_m2")


def main() -> None:
    from sqlalchemy import text as _T

    from labuse.db import session_factory
    from labuse.gabarit.builder import build_gabarit_input

    session = session_factory()()
    hausses, baisses, inchangees, inconnues = [], 0, 0, 0
    for p in sorted(CACHE.glob("*.json")):
        new = json.loads(p.read_text())
        q = REF / p.name
        if not q.exists():
            continue
        old = json.loads(q.read_text())
        s_new, s_old = new.get("sdp_max_m2"), old.get("sdp_max_m2")
        if s_new is None:
            inconnues += 1                      # « capacité à vérifier » : jamais une hausse
            continue
        d = float(s_new or 0) - float(s_old or 0)
        if d > 0:
            hausses.append((p.stem, new, old, d))
        elif d < 0:
            baisses += 1
        else:
            inchangees += 1

    print(f"vs origin/main (cache-main5) : {len(hausses)} HAUSSES ; {baisses} baisses ; "
          f"{inchangees} inchangées ; {inconnues} « capacité à vérifier » (inconnu, hors hausse)")

    lignes, echecs = [], 0
    for idu, new, old, d in sorted(hausses, key=lambda x: -x[3]):
        insee = idu[:5]
        commune = COMMUNES.get(insee, insee)
        zone = new.get("zone")
        pid = session.execute(_T("select id from parcels where idu=:i"), {"i": idu}).scalar()
        if pid is None:
            continue
        # 1. reculs RÉELLEMENT appliqués, côté par côté — LA classification du scénario servi
        cotes = []
        try:
            gb = build_gabarit_input(session, idu)
            if gb is not None:
                from labuse.gabarit.engine import shape_from_geojson, to_metric
                for sb in gb.input.setbacks:
                    t = {"side": "latérale", "rear": "fond", "road": "voie"}.get(sb.type, sb.type)
                    try:
                        L = round(float(to_metric(shape_from_geojson(sb.geometry)).length), 1)
                    except Exception:  # noqa: BLE001
                        L = None
                    cotes.append(f"{t}[{sb.ruleId}] {L if L is not None else '?'} m → "
                                 f"recul {sb.setbackM:g} m")
        except Exception:  # noqa: BLE001
            pass
        # 2. AVEC et SANS la règle : trois rejeux (servie / sans ouvertures / sans formule)
        sdp_sans_ouv = _rejouer(session, pid, sans_ouvertures=True, sans_formule=False)
        sdp_sans_form = _rejouer(session, pid, sans_ouvertures=False, sans_formule=True)
        eff_ouv = (round(float(new["sdp_max_m2"]) - float(sdp_sans_ouv))
                   if isinstance(sdp_sans_ouv, (int, float)) else None)
        eff_form = (round(float(new["sdp_max_m2"]) - float(sdp_sans_form))
                    if isinstance(sdp_sans_form, (int, float)) else None)
        # 3. admissibilité (liste fermée du mandat)
        # la LICENCE d'une hausse est la zone/l'article approuvés par le mandat — pas l'effet
        # mécanique d'un seul levier (AC3589 : hausse via la correction du recul D-024 dans une
        # zone égout approuvée — effet-formule nul, hausse ADMISE par « La Possession, zones où
        # l'article dit H/2 à l'égout, hors AU »).
        admise = ""
        _est_au5 = str(zone or "").upper().startswith(("AU", "1AU", "2AU"))
        _zr5 = None
        try:
            from labuse.faisabilite.zonage import resolve_zone as _rz5
            _zr5 = _rz5(zone, commune) if zone else None
        except Exception:  # noqa: BLE001
            _zr5 = None
        _egout_article = bool(_zr5 is not None and getattr(_zr5, "h_reference", None) == "egout"
                              and str(getattr(_zr5, "recul_limites_formule", "") or "").strip())
        if (insee, zone) in FACADE_OK and eff_form:
            admise = "facade_projet"
        elif insee in EGOUT_OK_INSEE and _egout_article and not _est_au5:
            admise = "egout_hors_AU"
        elif insee in OUVERTURE_OK_INSEE and eff_ouv:
            admise = "ouverture_liste_blanche"
        alerte = "" if admise else "⚠"
        if alerte:
            echecs += 1
        lignes.append({"idu": idu, "commune": commune, "zone": zone,
                       "sdp_main": s_old if (s_old := old.get("sdp_max_m2")) is not None else "inconnu",
                       "sdp_fix5": new.get("sdp_max_m2"), "delta": round(d),
                       "reculs_par_cote": " ; ".join(cotes)[:400],
                       "sdp_sans_ouvertures": sdp_sans_ouv if sdp_sans_ouv is not None else "inconnu",
                       "effet_ouvertures_m2": eff_ouv if eff_ouv is not None else "",
                       "sdp_sans_formule": sdp_sans_form if sdp_sans_form is not None else "inconnu",
                       "effet_formule_m2": eff_form if eff_form is not None else "",
                       "hausse_admise": admise or "HORS LISTE", "alerte": alerte})

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]) if lignes else ["idu"], delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print(f"→ {OUT.name} ; HORS LISTE : {echecs}")
    for r in lignes:
        print(f"  {r['alerte']}{r['idu']} {r['zone'] or '?':6s} {r['sdp_main']:>7} → "
              f"{r['sdp_fix5']:>7} (+{r['delta']})  ouv:{r['effet_ouvertures_m2'] or 0:>5} "
              f"form:{r['effet_formule_m2'] or 0:>5}  {r['hausse_admise']}")
    sys.exit(1 if echecs else 0)


if __name__ == "__main__":
    main()
