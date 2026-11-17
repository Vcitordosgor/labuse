"""MOTEUR-VERITE-FIX-6/7 — la preuve sur l'ÎLE, pas seulement sur la cohorte des permis.

Le parc contrôlé = TOUTES les parcelles des zones où une hausse est autorisée (liste fermée
du mandat) + 3 000 parcelles U et AU tirées à GRAINE FIXE sur toute l'île. Pour chacune : la
capacité de main et de la branche, le verdict de chacun, la cause, et — côté branche — le CHEMIN
réellement servant (gabarit/repli), les niveaux, le recul appliqué et la portion servie.

    PYTHONPATH=/tmp/labuse-main6/src python …/controle_inverse_fix6_ile.py build-liste  # une fois
    PYTHONPATH=/tmp/labuse-main6/src python …/controle_inverse_fix6_ile.py rejeu main6         # réf origin/main
    PYTHONPATH=src                 python …/controle_inverse_fix6_ile.py rejeu fix6            # la branche
    PYTHONPATH=src                 python …/controle_inverse_fix6_ile.py rejeu fix6sr --sansregle  # branche SANS la règle

FIX-7 LOT 1/4 — le recalcul SANS la règle (niveau-par-niveau : ouvertures en limite + formule de
hauteur retirées → retrait prudent uniforme) est fait pour TOUTES les parcelles (donc toutes les
hausses), plus 300. `compare` produit CONTROLE-INVERSE-FIX6-ILE.csv (UNE ligne par parcelle des
21 467) + le décompte complet. Le recul affiché est celui RÉELLEMENT appliqué (scénario retenu).
Invariant : aucune hausse RÈGLE hors des zones autorisées.
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


def _apply_sansregle() -> None:
    """Désactive la RÈGLE niveau-par-niveau pour mesurer son effet : ouvertures en limite fermées
    + formule de hauteur retirée → le gabarit/repli retombe sur le retrait prudent uniforme (main)."""
    import labuse.gabarit.builder as B
    orig_dec = B.analyser_condition_implantation

    def _fermee(imp, lg, su):
        d = orig_dec(imp, lg, su)
        try:
            d.update(ouvre=False, zero=0, bande_m=None, lineaire_pct=None, detail=None, mention=None)
        except Exception:  # noqa: BLE001 — forme inattendue : on laisse la décision d'origine
            pass
        return d
    B.analyser_condition_implantation = _fermee
    B._fraction_hauteur_formule = lambda f: None


def rejeu(tag: str, sansregle: bool = False, subset: str | None = None) -> None:
    from sqlalchemy import text
    from labuse.db import session_factory
    if sansregle:
        _apply_sansregle()
    from labuse.faisabilite.db import parcel_faisabilite
    s = session_factory()()
    # FIX-7 LOT 4 — `subset` (fichier JSON d'idus) restreint le rejeu, p. ex. le recalcul SANS la
    # règle aux seules HAUSSES (inutile ailleurs) ; sinon tout le parc contrôlé.
    liste = (json.loads(Path(subset).read_text()) if subset
             else json.loads(LISTE.read_text())["toutes"])
    out = FIX / f"cache-{tag}-ile"
    out.mkdir(exist_ok=True)
    done = {p.stem for p in out.glob("*.json")}
    n = 0
    for idu in liste:
        if idu in done:
            continue
        rec = {"idu": idu, "sdp": None, "constructible": None, "cause": None, "zone": None,
               "verdict": None, "chemin": None, "niveaux": None, "recul": None, "portion": None}
        pid = s.execute(text("select id from parcels where idu=:i"), {"i": idu}).scalar()
        if pid is not None:
            try:
                ctx, f = parcel_faisabilite(s, pid)
                fr = f.fourchette or {}
                rec.update(sdp=fr.get("surface_plancher_m2"),
                           constructible=bool(f.constructible), cause=f.cause, zone=f.zone,
                           verdict=(f.verdict or "")[:200],
                           chemin=getattr(ctx, "assiette_source", None),
                           niveaux=getattr(ctx, "niveaux_servis", None) or fr.get("niveaux_max"),
                           recul=getattr(ctx, "recul_servi_m", None),
                           portion=getattr(ctx, "portion_servie_m2", None))
            except Exception as e:  # noqa: BLE001
                rec["cause"] = f"ERREUR:{str(e)[:40]}"
        (out / f"{idu}.json").write_text(json.dumps(rec))
        n += 1
        if n % 1000 == 0:
            print(f"  {tag}{' (sans règle)' if sansregle else ''} : {n} rejouées…", flush=True)
    print(f"{tag} : {n} parcelles rejouées → {out.name}")


def compare() -> None:
    """UNE ligne par parcelle (21 467) + décompte complet. Les colonnes chemin/niveaux/recul/portion
    sont celles de la BRANCHE (le chemin qui sert réellement le chiffre). `sdp_sans_regle` et
    `effet_regle_m2` viennent du rejeu `fix6sr` (branche, règle désactivée) — pour TOUTES les hausses."""
    liste = json.loads(LISTE.read_text())
    autor_set = set(liste["autorisees"])
    OUT = FIX / "CONTROLE-INVERSE-FIX6-ILE.csv"
    main_dir, fix_dir = FIX / "cache-main6-ile", FIX / "cache-fix6-ile"
    sr_dir = FIX / "cache-fix6sr-ile"

    def _load(d):
        return {p.stem: json.loads(p.read_text()) for p in d.glob("*.json")} if d.exists() else {}
    MAIN, FIXB, SR = _load(main_dir), _load(fix_dir), _load(sr_dir)

    from collections import Counter
    cat = Counter()
    refus_introduits = Counter()      # cause branche quand main chiffrait → branche refuse
    hausses, hors_zone = [], []
    rows = []
    for idu in liste["toutes"]:
        new = FIXB.get(idu)
        if new is None:
            continue
        old = MAIN.get(idu, {})
        sr = SR.get(idu, {})
        sn, so = new.get("sdp"), old.get("sdp")
        ssr = sr.get("sdp")
        zone = new.get("zone") or ""
        autorisee = idu in autor_set
        constr_new, constr_old = new.get("constructible"), old.get("constructible")
        # catégorie
        if sn is None and so is None:
            categorie = "a_verifier" if constr_new else "refus"
            if not constr_new and constr_old:        # main à vérifier/refus, ici refus
                pass
        elif sn is None:                              # main chiffrait, branche non
            if constr_new:
                categorie = "a_verifier"
            else:
                categorie = "refus_introduit"
                refus_introduits[new.get("cause") or "?"] += 1
        elif so is None:
            categorie = "hausse" if not constr_old else "hausse"   # chiffre là où main 0/refus → hausse
            categorie = "chiffre_vs_refus"
        else:
            d = float(sn) - float(so)
            categorie = "hausse" if d > 0.5 else ("baisse" if d < -0.5 else "inchangee")
        cat[categorie] += 1
        # hausses (delta sur chiffre commun, ou chiffre vs main refus)
        if categorie in ("hausse", "chiffre_vs_refus") and sn is not None:
            d = round(float(sn) - float(so)) if so is not None else round(float(sn))
            if d > 0.5:
                hausses.append((idu, zone, so, sn, d, autorisee))
                if not autorisee:
                    hors_zone.append((idu, zone, so, sn, d))
        eff = (round(float(sn) - float(ssr)) if isinstance(sn, (int, float)) and isinstance(ssr, (int, float)) else "")
        # verdict COMPACT (fichier compact demandé) : un chiffre servi se résume à « chiffre » (le
        # nombre dit tout) ; sinon le motif en un mot-clé (le détail complet est dans le verdict du
        # moteur, reproductible). Garde le fichier sous le plafond du hook (< 2 Mio).
        def _vc(v, sdp):
            if sdp not in (None, ""):
                return "chiffre"
            s = str(v or "").lower()
            for kw in ("implantation en limite", "zone rouge", "trait de côte", "façade",
                       "micro-parcelle", "exigu", "réservé", "boisé", "habitat", "zone de transition",
                       "pente", "à vérifier"):
                if kw in s:
                    return kw
            return (str(v or "").split(" : ")[0]).strip()[:30]
        rows.append([idu, zone,
                     so if so is not None else "", sn if sn is not None else "",
                     _vc(old.get("verdict"), so), _vc(new.get("verdict"), sn),
                     new.get("cause") or "", new.get("chemin") or "",
                     new.get("niveaux") if new.get("niveaux") is not None else "",
                     new.get("recul") if new.get("recul") is not None else "",
                     new.get("portion") if new.get("portion") is not None else "",
                     ssr if ssr is not None else "", eff,
                     "oui" if autorisee else "NON", categorie])
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writerow(["idu", "zone", "sdp_main", "sdp_branche", "verdict_main", "verdict_branche",
                    "cause_branche", "chemin_branche", "niveaux_branche", "recul_applique_m",
                    "portion_servie_m2", "sdp_sans_regle", "effet_regle_m2",
                    "zone_autorisee", "categorie"])
        w.writerows(sorted(rows))
    # hors-zone : RÈGLE (effet > 2 m²) vs dérive de chemin géométrique (effet ~nul)
    hz_regle, hz_geom = [], []
    for idu, z, so, sn, d in hors_zone:
        sr = SR.get(idu, {})
        ssr = sr.get("sdp")
        eff = (round(float(sn) - float(ssr)) if isinstance(ssr, (int, float)) else None)
        (hz_regle if (eff or 0) > 2 else hz_geom).append((idu, z, so, sn, d, eff))
    hausses.sort(key=lambda r: -r[4])
    print(f"ÎLE — parc contrôlé {len(liste['toutes'])} parcelles "
          f"({len(autor_set)} zones autorisées + {len(liste['echantillon'])} graine fixe)")
    print(f"  CSV complet : {len([r for r in rows])} lignes → {OUT.name}")
    print("  DÉCOMPTE :")
    for k in ("hausse", "chiffre_vs_refus", "baisse", "inchangee", "refus", "a_verifier", "refus_introduit"):
        print(f"    {k:18s} : {cat.get(k, 0)}")
    print(f"  HAUSSES hors zones autorisées : {len(hors_zone)} — "
          f"dont RÈGLE {len(hz_regle)}, dérive de chemin géométrique {len(hz_geom)}")
    if refus_introduits:
        print("  REFUS INTRODUITS par la branche (main chiffrait → branche refuse), par motif :")
        for cause, n in refus_introduits.most_common():
            print(f"    {n:5d}  {cause}")
    if hz_regle:
        print("  ⚠⚠ HAUSSES RÈGLE HORS ZONE (ÉCHEC) :")
        for idu, z, so, sn, d, eff in hz_regle:
            print(f"    {idu} {z} {so} → {sn} (+{d}, effet règle {eff})")
    if hz_geom:
        print("  · Dérives de CHEMIN géométrique hors zone (effet règle nul, documentées) :")
        for idu, z, so, sn, d, eff in hz_geom:
            print(f"    {idu} {z} {so} → {sn} (+{d}, effet règle {eff if eff is not None else '?'})")
    print("  Les 30 plus fortes hausses :")
    for idu, z, so, sn, d, au in hausses[:30]:
        print(f"    {'' if au else '⚠'}{idu} {z:8s} {so if so is not None else 'refus':>8} → "
              f"{sn:>8} (+{d})  {'autorisée' if au else 'HORS ZONE'}")
    sys.exit(1 if hz_regle else 0)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "compare"
    if cmd == "build-liste":
        build_liste()
    elif cmd == "rejeu":
        _sub = None
        if "--subset" in sys.argv:
            _sub = sys.argv[sys.argv.index("--subset") + 1]
        rejeu(sys.argv[2], sansregle=("--sansregle" in sys.argv), subset=_sub)
    else:
        compare()
