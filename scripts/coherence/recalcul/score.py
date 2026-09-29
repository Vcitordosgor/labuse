"""Recalcul indépendant — Signal de mutation (mult_base) + paliers/bandes (frontières).

  · mult_base : le back sert `round(p_raw / taux_base, 2)` où taux_base = moyenne des p_raw du
    run servi HORS copropriété. On recalcule taux_base à la main (AVG SQL indépendant) puis
    mult_base par parcelle, comparé au STOCKÉ. C'est le seul « ×N vs la moyenne » servi client.
  · signal_niveau / paliers : réimplémentation des frontières 0,20 / 0,10 (fort/moyen/faible)
    et 80/50/30 (bandes A/B/C/D), testées sur les valeurs EXACTEMENT aux bornes — met en
    évidence l'effet d'arrondi-avant-bande signalé à l'inventaire (score 79,5 → round 80 → A).
"""
from __future__ import annotations

from . import socle


# ── réimplémentations indépendantes des frontières ──

def signal_niveau(p):
    if p is None:
        return None
    if p >= 0.20:
        return "fort"
    if p >= 0.10:
        return "moyen"
    return "faible"


def bande_de_score(score):
    if score is None:
        return "NC"
    if score == 0:
        return "0"
    for seuil, lib in ((80, "A"), (50, "B"), (30, "C")):
        if score >= seuil:
            return lib
    return "D"


#: cas limites aux bornes exactes (frontière inclusive/exclusive + arrondi avant bande).
CAS_SIGNAL = [(0.0, "faible"), (0.099, "faible"), (0.10, "moyen"), (0.199, "moyen"),
              (0.20, "fort"), (0.50, "fort")]
CAS_BANDE = [(0, "0"), (29, "D"), (30, "C"), (49, "C"), (50, "B"), (79, "B"),
             (80, "A"), (100, "A"), (None, "NC")]


def verifier(rec: socle.Recalc, conn, echantillon):
    # 1) frontières de palier (formule pure, oracle = intention documentée)
    for p, attendu in CAS_SIGNAL:
        rec.compare("signal_mutation.signal_niveau", "palier", f"p={p}",
                    servi=attendu, recalc=signal_niveau(p), tol="0", cause="formule")
    for s, attendu in CAS_BANDE:
        rec.compare("score_labuse.bande_de_score", "bande", f"score={s}",
                    servi=attendu, recalc=bande_de_score(s), tol="0", cause="formule")

    # 2) mult_base recalculé depuis taux_base (moyenne p_raw hors copro du run servi)
    run = socle.RUN
    with conn.cursor() as cur:
        cur.execute("SELECT avg(p_raw) FROM parcel_p_score_v2 WHERE run_id=%s AND NOT copro", (run,))
        taux_base = cur.fetchone()[0]
    if taux_base:
        taux_base = float(taux_base)
        for row in echantillon:
            idu = row["idu"]
            with conn.cursor() as cur:
                cur.execute("SELECT p_raw, mult_base FROM parcel_p_score_v2 "
                            "WHERE parcelle_id=%s AND run_id=%s", (idu, run))
                r = cur.fetchone()
            if not r or r[0] is None or r[1] is None:
                continue
            p_raw, mult_stocke = float(r[0]), float(r[1])
            mult_recalc = round(p_raw / taux_base, 2)
            rec.compare("pipeline.mult_base", "mult_base", idu,
                        servi=mult_stocke, recalc=mult_recalc, tol="0,01 abs", cause="formule")
