"""Rapport À BLANC AU-OUVERTURE (mandat GO RE-RUN). Les TROIS mesures demandées par Vic :
  (1) tiers avant/après par commune + total (écart par ligne, même de 1) ;
  (2) golden avant/après (ancres qui bougent, lesquelles, motif) ;
  (3) backfills : combien montent d'un tier, et par MÉRITE (signal en hausse : rang/contrib_d
      s'améliorent) vs par HÉRITAGE DE PLACE (rang + contrib_d inchangés, seul le seuil glisse) = dette #9.
Lecture seule. Aucune bascule.
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope

AVANT, APRES = "q_v8_au_avant", "q_v8_au_apres"
COMMUNES = {"97415": "Saint-Paul", "97408": "La Possession", "97413": "Saint-Leu", "97423": "Les Trois-Bassins"}
# ordinal de « hauteur » de tier — un backfill = l'ordinal monte
ORD = {"brulante": 5, "chaude": 4, "a_creuser": 3, "reserve_fonciere": 2,
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
        print(f"\n--- {titre}  (n={len(idus)}) ---")
        print(f"{'tier':30s} {'avant':>8s} {'après':>8s} {'écart':>7s}")
        ca = {t: 0 for t in TIERS_ORDER}; cp = {t: 0 for t in TIERS_ORDER}
        for i in idus:
            ca[av[i].tier] = ca.get(av[i].tier, 0) + 1
            cp[ap[i].tier] = cp.get(ap[i].tier, 0) + 1
        for t in TIERS_ORDER:
            d = cp[t] - ca[t]
            if ca[t] or cp[t]:
                print(f"{t:30s} {ca[t]:>8d} {cp[t]:>8d} {d:>+7d}")
    for ins, nom in COMMUNES.items():
        table([i for i in av if av[i].insee == ins], f"{nom} ({ins})")
    reste = [i for i in av if av[i].insee not in COMMUNES]
    table(reste, "RESTE DE L'ÎLE (hors 4 communes — capte le spillover N_e)")
    table(list(av), "TOTAL ÎLE")

    # ---- (2) golden avant/après --------------------------------------------------------------
    print("\n\n========== (2) GOLDEN AVANT / APRÈS ==========")
    g = json.load(open("reports/m6-audit/golden/golden-parcelles.json"))["parcelles"]
    bouge = []
    for idu, meta in g.items():
        if idu not in av:
            continue
        ta, tp = av[idu].tier, ap[idu].tier
        if ta != tp:
            bouge.append((idu, meta.get("commune"), ta, tp, meta.get("tier_v2"),
                          meta.get("anchor"), meta.get("motif")))
    print(f"ancres golden présentes : {sum(1 for i in g if i in av)} / {len(g)}")
    print(f"ancres qui BOUGENT avant→après : {len(bouge)}")
    for idu, com, ta, tp, tref, anc, motif in bouge:
        au = ap[idu]
        print(f"  {idu} ({com}) {ta} → {tp}  [ref golden tier_v2={tref}, anchor={anc}, motif={motif}]")

    # ---- (3) backfills : mérite vs héritage de place -----------------------------------------
    print("\n\n========== (3) BACKFILLS — MÉRITE vs HÉRITAGE DE PLACE (dette #9) ==========")
    risers = [i for i in av if ORD[ap[i].tier] > ORD[av[i].tier]]
    droppers = [i for i in av if ORD[ap[i].tier] < ORD[av[i].tier]]
    print(f"parcelles qui MONTENT d'un tier : {len(risers)}")
    print(f"parcelles qui DESCENDENT d'un tier : {len(droppers)}")
    merite = herit = 0; rang_moves = []
    for i in risers:
        dr = (av[i].rang or 0) - (ap[i].rang or 0)      # rang plus petit = mieux ; >0 = amélioration
        dd = float(ap[i].contrib_d or 0) - float(av[i].contrib_d or 0)
        if abs(dr) > 0 or abs(dd) > 1e-9:
            merite += 1; rang_moves.append((i, dr, dd, av[i].tier, ap[i].tier))
        else:
            herit += 1
    print(f"  par MÉRITE (rang/contrib_d bougent) : {merite}")
    print(f"  par HÉRITAGE DE PLACE (rang+contrib_d inchangés, seuil glissé) : {herit}")
    if rang_moves:
        print("  détail des 'mérite' (anomalie si non vide : au_statut ne touche ni p ni rang) :")
        for i, dr, dd, ta, tp in rang_moves[:20]:
            print(f"    {i} rangΔ={dr} contrib_dΔ={dd:+.5f} {ta}→{tp}")
    # ventilation des montées par transition
    from collections import Counter
    trans = Counter((av[i].tier, ap[i].tier) for i in risers)
    print("  transitions (montées) :")
    for (a, b), n in trans.most_common():
        print(f"    {a} → {b} : {n}")
    transd = Counter((av[i].tier, ap[i].tier) for i in droppers)
    print("  transitions (descentes, effet direct du déclassement) :")
    for (a, b), n in transd.most_common():
        print(f"    {a} → {b} : {n}")

    # n_entree avant/après (le seuil qui glisse)
    print("\n  seuils N_e (params du run) :")
    for lbl in (AVANT, APRES):
        p = s.execute(text("SELECT params FROM p_score_v2_runs WHERE run_id=:r"), {"r": lbl}).scalar()
        # AVANT a été supprimé de p_score_v2_runs ? on le remet pour la mesure si besoin
        print(f"    {lbl}: {p if p else 'ligne runs absente (supprimée pour hystérésis)'}")
