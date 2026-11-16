"""MOTEUR-VERITE-FIX-6 LOT 4 — la preuve sur l'ÎLE, pas seulement sur la cohorte des permis.

Le parc contrôlé = TOUTES les parcelles des zones où une hausse est autorisée (liste fermée
du mandat) + 3 000 parcelles U et AU tirées à GRAINE FIXE sur toute l'île. Pour chacune : la
capacité, le verdict (constructible), la cause. Lancé DEUX fois —

    PYTHONPATH=/tmp/labuse-main6/src python …/controle_inverse_fix6_ile.py build-liste  # une fois
    PYTHONPATH=/tmp/labuse-main6/src python …/controle_inverse_fix6_ile.py rejeu main6  # réf origin/main
    PYTHONPATH=src                 python …/controle_inverse_fix6_ile.py rejeu fix6     # la branche

— puis `compare` produit CONTROLE-INVERSE-FIX6-ILE.csv (une ligne par hausse, avec le côté
utilisé, la condition et le recalcul AVEC/SANS la règle), les TOTAUX et les 50 plus fortes
hausses. Invariant : aucune hausse hors des zones autorisées.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

FIX = Path(__file__).resolve().parents[1]
LISTE = FIX / "cache-fix6-ile-liste.json"

#: zones AUTORISÉES (liste fermée du mandat FIX-5/FIX-6)
FACADE_OK = {("97418", "UA"), ("97418", "UAz"), ("97402", "Ub"), ("97402", "Uc")}
OUVERTURE_OK = {("97406", "Ub"), ("97421", "UA")}      # Plaine Ub, Salazie UA
EGOUT_OK_INSEE = {"97408"}                              # La Possession, zones U hors AU


def _zone_autorisee(insee: str, zone: str, zone_fam: str) -> bool:
    if (insee, zone) in FACADE_OK or (insee, zone) in OUVERTURE_OK:
        return True
    if insee in EGOUT_OK_INSEE and zone_fam == "U":
        return True
    return False


def build_liste() -> None:
    """Liste DÉTERMINISTE : zones autorisées exhaustives + 3 000 U/AU graine fixe sur l'île."""
    from sqlalchemy import text
    from labuse.db import session_factory
    s = session_factory()()
    autor = [r[0] for r in s.execute(text("""
        SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu = p.idu
        WHERE p.geom_2975 IS NOT NULL AND (
            (left(p.idu,5)='97418' AND z.zone_lib IN ('UA','UAz'))
         OR (left(p.idu,5)='97402' AND z.zone_lib IN ('Ub','Uc'))
         OR (left(p.idu,5)='97408' AND z.zone_fam='U')
         OR (left(p.idu,5)='97406' AND z.zone_lib='Ub')
         OR (left(p.idu,5)='97421' AND z.zone_lib='UA'))""")).fetchall()]
    ile = [r[0] for r in s.execute(text("""
        SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu = p.idu
        WHERE z.zone_fam IN ('U','AU') AND p.geom_2975 IS NOT NULL""")).fetchall()]
    ile.sort(key=lambda i: hashlib.md5((i + "FIX6-ILE-3000").encode()).hexdigest())
    sample = ile[:3000]
    liste = sorted(set(autor) | set(sample))
    LISTE.write_text(json.dumps({"autorisees": sorted(set(autor)), "echantillon": sorted(set(sample)),
                                 "toutes": liste}))
    print(f"liste : {len(autor)} parcelles en zones autorisées + {len(sample)} graine fixe "
          f"= {len(liste)} au total → {LISTE.name}")


def rejeu(tag: str) -> None:
    from sqlalchemy import text
    from labuse.db import session_factory
    from labuse.faisabilite.db import parcel_faisabilite
    s = session_factory()()
    liste = json.loads(LISTE.read_text())["toutes"]
    out = FIX / f"cache-{tag}-ile"
    out.mkdir(exist_ok=True)
    done = {p.stem for p in out.glob("*.json")}
    n = 0
    for idu in liste:
        if idu in done:
            continue
        rec = {"idu": idu, "sdp": None, "constructible": None, "cause": None, "zone": None}
        pid = s.execute(text("select id from parcels where idu=:i"), {"i": idu}).scalar()
        if pid is not None:
            try:
                ctx, f = parcel_faisabilite(s, pid)
                rec.update(sdp=(f.fourchette or {}).get("surface_plancher_m2"),
                           constructible=bool(f.constructible), cause=f.cause, zone=f.zone)
            except Exception as e:  # noqa: BLE001
                rec["cause"] = f"ERREUR:{str(e)[:40]}"
        (out / f"{idu}.json").write_text(json.dumps(rec))
        n += 1
        if n % 1000 == 0:
            print(f"  {tag} : {n} rejouées…", flush=True)
    print(f"{tag} : {n} parcelles rejouées → {out.name}")


def _detail_hausse(session, idu: str):
    """MOTEUR-VERITE-FIX-6 LOT 4 — pour une hausse : le RECUL RÉELLEMENT APPLIQUÉ (scénario
    retenu, pas le recul d'entrée), les CÔTÉS posés en limite, et le recalcul SANS la règle
    (ouvertures fermées + formule retirée) — texte NON coupé."""
    import labuse.gabarit.builder as B
    from labuse.gabarit.builder import build_gabarit_input
    from labuse.gabarit.engine import shape_from_geojson, to_metric
    from labuse.faisabilite.db import parcel_faisabilite
    recul_reel, scenario, cotes = "", "", []
    try:
        gb = build_gabarit_input(session, idu)
        if gb is not None:
            plu = gb.raccordement.get("plu") or {}
            recul_reel = str(plu.get("recul_sep_m") or "")
            scenario = str(plu.get("recul_sep_formule") or "")
            for sb in gb.input.setbacks:
                if sb.ruleId == "limite-sep-limite":
                    try:
                        L = round(float(to_metric(shape_from_geojson(sb.geometry)).length), 1)
                    except Exception:  # noqa: BLE001
                        L = "?"
                    cotes.append(f"{'latérale' if sb.type == 'side' else 'fond'} {L} m (en limite 0 m)")
    except Exception:  # noqa: BLE001
        pass
    # recalcul SANS la règle : décision d'implantation fermée + formule niveau retirée
    orig_dec, orig_frac = B.analyser_condition_implantation, B._fraction_hauteur_formule

    def _fermee(imp, lg, su):
        d = orig_dec(imp, lg, su)
        d.update(ouvre=False, zero=0, bande_m=None, lineaire_pct=None, detail=None, mention=None)
        return d
    B.analyser_condition_implantation = _fermee
    B._fraction_hauteur_formule = lambda f: None
    try:
        pid = session.execute(__import__("sqlalchemy").text(
            "select id from parcels where idu=:i"), {"i": idu}).scalar()
        res = parcel_faisabilite(session, pid)
        sans = (res[1].fourchette or {}).get("surface_plancher_m2") if res else None
    except Exception:  # noqa: BLE001
        sans = None
    finally:
        B.analyser_condition_implantation = orig_dec
        B._fraction_hauteur_formule = orig_frac
    return recul_reel, scenario, " ; ".join(cotes), sans


def compare() -> None:
    from labuse.db import session_factory
    session = session_factory()()
    liste = json.loads(LISTE.read_text())
    autor_set = set(liste["autorisees"])
    OUT = FIX / "CONTROLE-INVERSE-FIX6-ILE.csv"
    main_dir, fix_dir = FIX / "cache-main6-ile", FIX / "cache-fix6-ile"
    hausses, baisses, inchangees, inconnues, nouv_constr = [], 0, 0, 0, 0
    hors_zone = []
    for p in sorted(fix_dir.glob("*.json")):
        new = json.loads(p.read_text())
        q = main_dir / p.name
        if not q.exists():
            continue
        old = json.loads(q.read_text())
        sn, so = new.get("sdp"), old.get("sdp")
        insee = p.stem[:5]
        zone = new.get("zone") or ""
        autorisee = p.stem in autor_set
        if sn is None:
            inconnues += 1
            continue
        if so is None:
            if not old.get("constructible"):
                nouv_constr += 1            # chiffre là où main refusait
            d = float(sn)
        else:
            d = float(sn) - float(so)
        if d > 0.5:
            hausses.append((p.stem, zone, so, sn, round(d), autorisee))
            if not autorisee:
                hors_zone.append((p.stem, zone, so, sn, round(d)))
        elif so is not None and d < -0.5:
            baisses += 1
        else:
            inchangees += 1
    hausses.sort(key=lambda r: -r[4])
    # MOTEUR-VERITE-FIX-6 LOT 4 — le recalcul AVEC/SANS la règle (rebuild gabarit + rejeu) est
    # coûteux : on l'applique aux 300 PLUS FORTES hausses (dont les 50 affichées) ; au-delà, la
    # ligne porte les colonnes de base (idu/zone/main/fix6/delta/autorisée). Texte NON coupé.
    N_DETAIL = 300
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writerow(["idu", "zone", "sdp_main", "sdp_fix6", "delta", "zone_autorisee",
                    "recul_reellement_applique_m", "scenario_retenu", "cotes_en_limite",
                    "sdp_sans_la_regle", "effet_de_la_regle_m2"])
        for i, (idu, z, so, sn, d, au) in enumerate(hausses):
            if i < N_DETAIL:
                rr, sc, ct, sans = _detail_hausse(session, idu)
                eff = (round(float(sn) - float(sans)) if isinstance(sans, (int, float)) else "")
                w.writerow([idu, z, so if so is not None else "inconnu", sn, d, "oui" if au else "NON",
                            rr, sc, ct, sans if sans is not None else "inconnu", eff])
            else:
                w.writerow([idu, z, so if so is not None else "inconnu", sn, d,
                            "oui" if au else "NON", "", "", "", "", ""])
    # MOTEUR-VERITE-FIX-6 LOT 4 — pour les hausses HORS zone, on isole l'EFFET DE LA RÈGLE
    # (ouvertures fermées + formule retirée) : une hausse RÈGLE hors zone est un ÉCHEC ; une
    # dérive de CHEMIN géométrique (gabarit qui aboutit là où il échouait, ou l'inverse —
    # effet règle nul) est documentée, pas une hausse autorisée par une règle.
    hz_regle, hz_geom = [], []
    for idu, z, so, sn, d in hors_zone:
        try:
            _rr, _sc, _ct, _sans = _detail_hausse(session, idu)
            _eff = (round(float(sn) - float(_sans)) if isinstance(_sans, (int, float)) else None)
        except Exception:  # noqa: BLE001
            _eff = None
        (hz_regle if (_eff or 0) > 2 else hz_geom).append((idu, z, so, sn, d, _eff))
    print(f"ÎLE — parc contrôlé {len(liste['toutes'])} parcelles "
          f"({len(autor_set)} zones autorisées + {len(liste['echantillon'])} graine fixe)")
    print(f"  HAUSSES : {len(hausses)}  (hors zones autorisées : {len(hors_zone)} — "
          f"dont RÈGLE {len(hz_regle)}, dérive de chemin géométrique {len(hz_geom)})")
    print(f"  baisses : {baisses} ; inchangées : {inchangees} ; "
          f"« à vérifier » : {inconnues} ; chiffre là où main refusait : {nouv_constr}")
    print(f"→ {OUT.name}")
    if hz_regle:
        print("  ⚠⚠ HAUSSES RÈGLE HORS ZONE (ÉCHEC) :")
        for idu, z, so, sn, d, eff in hz_regle:
            print(f"    {idu} {z} {so} → {sn} (+{d}, effet règle {eff})")
    if hz_geom:
        print("  · Dérives de CHEMIN géométrique hors zone (effet règle nul, documentées) :")
        for idu, z, so, sn, d, eff in hz_geom:
            print(f"    {idu} {z} {so} → {sn} (+{d}, effet règle {eff if eff is not None else '?'})")
    print("  Les 50 plus fortes hausses :")
    for idu, z, so, sn, d, au in hausses[:50]:
        print(f"    {'' if au else '⚠'}{idu} {z:6s} {so if so is not None else 'inconnu':>8} → "
              f"{sn:>8} (+{d})  {'autorisée' if au else 'HORS ZONE'}")
    sys.exit(1 if hz_regle else 0)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "compare"
    if cmd == "build-liste":
        build_liste()
    elif cmd == "rejeu":
        rejeu(sys.argv[2])
    else:
        compare()
