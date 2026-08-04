"""REBUILD UNIQUE — Étape D : rapport consolidé (lecture seule).

Les 4 mesures du mandat :
  (1) tiers AVANT/APRÈS par commune + total (écart par ligne, total = 431 663) ;
  (2) golden : ancres qui bougent, lesquelles, motif ;
  (3) backfills : mérite (rang/contrib_d bougent) vs héritage de place (seuil glisse) = dette #9 ;
  (4) les 8 brûlantes Saint-Benoît : état final.
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope
from collections import Counter, defaultdict

AVANT, APRES = "q_v9_avant", "q_v9_apres"
COMMUNES = {"97415": "Saint-Paul", "97408": "La Possession", "97413": "Saint-Leu",
            "97423": "Les Trois-Bassins", "97410": "Saint-Benoît"}
ORD = {"brulante": 6, "chaude": 5, "a_creuser": 4, "reserve_fonciere": 3,
       "declasse_au_fermee": 1, "declasse_au_statut_inconnu": 1, "declasse_zone_fermee": 1,
       "declasse_non_constructible": 1, "ecartee": 0}
TIERS_ORDER = ["brulante", "chaude", "a_creuser", "reserve_fonciere",
               "declasse_au_fermee", "declasse_au_statut_inconnu",
               "declasse_zone_fermee", "declasse_non_constructible", "ecartee"]

def load(s, label):
    rows = s.execute(text("""
        SELECT parcelle_id AS idu, tier, rang, contrib_d,
               substring(parcelle_id from 1 for 5) AS insee
        FROM parcel_p_score_v2 WHERE run_id=:r"""), {"r": label}).all()
    return {r.idu: r for r in rows}

with session_scope() as s:
    av = load(s, AVANT); ap = load(s, APRES)
    print(f"AVANT n={len(av)}  APRÈS n={len(ap)}")
    assert set(av) == set(ap), "jeux d'idus divergents"

    # ---- (1) tiers avant/après par commune + total ------------------------------------------
    print("\n========== (1) TIERS AVANT / APRÈS ==========")
    def table(idus, titre):
        ca = Counter(); cp = Counter()
        for i in idus:
            ca[av[i].tier] += 1; cp[ap[i].tier] += 1
        lignes = [(t, ca[t], cp[t], cp[t]-ca[t]) for t in TIERS_ORDER if ca[t] or cp[t]]
        if not any(d for *_, d in lignes) and titre.startswith("  "):
            return  # commune sans mouvement, on l'omet du détail
        print(f"\n--- {titre}  (n={len(idus)}) ---")
        print(f"{'tier':30s} {'avant':>8s} {'après':>8s} {'écart':>7s}")
        for t, a, p, d in lignes:
            print(f"{t:30s} {a:>8d} {p:>8d} {d:>+7d}")
    for ins, nom in COMMUNES.items():
        table([i for i in av if av[i].insee == ins], f"{nom} ({ins})")
    reste = [i for i in av if av[i].insee not in COMMUNES]
    table(reste, "RESTE DE L'ÎLE (hors 5 communes — spillover N_e)")
    table(list(av), "TOTAL ÎLE")
    # écart net par tier (île)
    print("\n  bougés au total (île) :", sum(1 for i in av if av[i].tier != ap[i].tier))

    # ---- (2) golden -------------------------------------------------------------------------
    print("\n\n========== (2) GOLDEN AVANT / APRÈS ==========")
    g = json.load(open("reports/m6-audit/golden/golden-parcelles.json"))["parcelles"]
    present = sum(1 for i in g if i in av)
    bouge = []
    for idu, meta in g.items():
        if idu not in av: continue
        ta, tp = av[idu].tier, ap[idu].tier
        if ta != tp:
            bouge.append((idu, meta.get("commune"), ta, tp, meta.get("tier_v2"),
                          meta.get("anchor"), meta.get("motif")))
    print(f"ancres présentes : {present}/{len(g)} ; qui BOUGENT avant→après : {len(bouge)}")
    for idu, com, ta, tp, tref, anc, motif in bouge:
        print(f"  {idu} ({com}) {ta} → {tp}  [ref tier_v2={tref}, anchor={anc}, motif={motif}]")

    # ---- (3) backfills mérite vs héritage ---------------------------------------------------
    print("\n\n========== (3) BACKFILLS — MÉRITE vs HÉRITAGE (dette #9) ==========")
    risers = [i for i in av if ORD.get(ap[i].tier,0) > ORD.get(av[i].tier,0)]
    droppers = [i for i in av if ORD.get(ap[i].tier,0) < ORD.get(av[i].tier,0)]
    print(f"MONTENT d'un tier : {len(risers)} ; DESCENDENT : {len(droppers)}")
    merite = herit = 0; ex = []
    for i in risers:
        dr = (av[i].rang or 0) - (ap[i].rang or 0)
        dd = float(ap[i].contrib_d or 0) - float(av[i].contrib_d or 0)
        if abs(dr) > 0 or abs(dd) > 1e-9:
            merite += 1
            if len(ex) < 15: ex.append((i, dr, dd, av[i].tier, ap[i].tier))
        else:
            herit += 1
    print(f"  par MÉRITE (rang/contrib_d bougent) : {merite}")
    print(f"  par HÉRITAGE DE PLACE (rang+contrib_d inchangés, seuil glissé) : {herit}")
    for i, dr, dd, ta, tp in ex:
        print(f"    {i} rangΔ={dr} contrib_dΔ={dd:+.5f} {ta}→{tp}")
    print("  transitions (montées) :")
    for (a, b), n in Counter((av[i].tier, ap[i].tier) for i in risers).most_common():
        print(f"    {a} → {b} : {n}")
    print("  transitions (descentes) :")
    for (a, b), n in Counter((av[i].tier, ap[i].tier) for i in droppers).most_common():
        print(f"    {a} → {b} : {n}")
    for lbl in (AVANT, APRES):
        p = s.execute(text("SELECT params FROM p_score_v2_runs WHERE run_id=:r"), {"r": lbl}).scalar()
        print(f"  seuils {lbl}: {p if p else '(ligne runs absente — hystérésis)'}")

    # ---- (4) les 8 brûlantes Saint-Benoît ---------------------------------------------------
    print("\n\n========== (4) LES 8 BRÛLANTES SAINT-BENOÎT ==========")
    # identifiées comme brûlantes AUa5/AUb19 dans le run SERVI q_v7_defisc
    brul = s.execute(text("""
        SELECT sc.parcelle_id AS idu, b.zone_lib
        FROM parcel_p_score_v2 sc
        JOIN parcel_zone_plu_prebascule b ON b.idu=sc.parcelle_id
        WHERE sc.run_id='q_v7_defisc' AND substring(sc.parcelle_id from 1 for 5)='97410'
          AND sc.tier='brulante' AND (b.zone_lib LIKE 'AUa%' OR b.zone_lib LIKE 'AUb%')
        ORDER BY b.zone_lib, sc.parcelle_id""")).all()
    print(f"n = {len(brul)} (brûlantes servies en AUa/AUb)")
    # statut AU + zone_lib après rebuild
    for r in brul:
        au = s.execute(text("SELECT classe, motif FROM parcel_au_statut WHERE idu=:i"), {"i": r.idu}).first()
        znew = s.execute(text("SELECT zone_lib, zone_libelle FROM parcel_zone_plu WHERE idu=:i"), {"i": r.idu}).first()
        ta = av[r.idu].tier if r.idu in av else "?"
        tp = ap[r.idu].tier if r.idu in ap else "?"
        aucl = au.classe if au else "(aucune)"
        print(f"  {r.idu} {r.zone_lib:6s}→{(znew.zone_lib if znew else '?'):6s} | au_statut={aucl:24s} | tier {ta}→{tp}")
print("\nÉTAPE D FINIE")
