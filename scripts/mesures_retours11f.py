"""RETOURS-11F — mesures base réelle (labuse). Chaque chiffre du rapport vient d'ici."""
from __future__ import annotations
import sys
from sqlalchemy import text
from labuse.db import engine, session_factory

VEFA = "Vente en l'état futur d'achèvement"


def m2_couverture():
    with engine().connect() as c:
        r = c.execute(text("""
          WITH mut AS (
            SELECT id_mutation, code_commune,
                   sum(COALESCE(surface_reelle_bati,0)) AS bati, max(valeur_fonciere) AS valeur
            FROM dvf_mutations_parcelle
            WHERE nature_mutation = :vefa AND date_mutation >= (now() - interval '36 months')::date
            GROUP BY id_mutation, code_commune)
          SELECT count(*) n, count(*) FILTER (WHERE bati>0 AND valeur>1000 AND valeur/bati BETWEEN 50 AND 20000) ex
          FROM mut"""), {"vefa": VEFA}).one()
        n, ex = int(r[0]), int(r[1])
        print(f"[M2] VEFA 36 mois — mutations distinctes: {n} | exploitables: {ex} ({100*ex/n:.0f}%) | sans surface: {n-ex} ({100*(n-ex)/n:.0f}%)")
        perc = c.execute(text("""
          WITH mut AS (
            SELECT id_mutation, code_commune, sum(COALESCE(surface_reelle_bati,0)) bati, max(valeur_fonciere) valeur
            FROM dvf_mutations_parcelle
            WHERE nature_mutation=:vefa AND date_mutation >= (now() - interval '36 months')::date
            GROUP BY id_mutation, code_commune)
          SELECT code_commune, count(*) n, count(*) FILTER (WHERE bati>0 AND valeur>1000 AND valeur/bati BETWEEN 50 AND 20000) ex
          FROM mut GROUP BY code_commune ORDER BY n DESC"""), {"vefa": VEFA}).all()
        print(f"[M2] communes avec VEFA: {len(perc)} | ≥8 mutations: {sum(1 for x in perc if x[1]>=8)} | ≥8 exploitables (servable): {sum(1 for x in perc if x[2]>=8)}")
        for x in perc[:12]:
            print(f"      {x[0]}  mut={x[1]:>4}  exploit={x[2]:>4}")
        for mois in (60, 120):
            r2 = c.execute(text(f"""
              WITH mut AS (SELECT id_mutation, sum(COALESCE(surface_reelle_bati,0)) bati, max(valeur_fonciere) valeur
                FROM dvf_mutations_parcelle WHERE nature_mutation=:vefa
                  AND date_mutation >= (now() - interval '{mois} months')::date GROUP BY id_mutation)
              SELECT count(*), count(*) FILTER (WHERE bati>0 AND valeur>1000 AND valeur/bati BETWEEN 50 AND 20000) FROM mut"""),
              {"vefa": VEFA}).one()
            print(f"[M2] fenêtre {mois} mois — mutations: {r2[0]} | exploitables: {r2[1]} ({100*int(r2[1])/max(1,int(r2[0])):.0f}%)")


def m5_charge(n_sample=400):
    """Distribue la charge foncière calibrée sur un échantillon de parcelles U, compare à DVF terrain nu."""
    from labuse.faisabilite.bilan import compute_bilan_servi
    S = session_factory(); db = S()
    ids = db.execute(text("""
        SELECT p.id FROM parcels p
        JOIN parcel_zone_plu z ON z.idu = p.idu
        WHERE z.zone_fam = 'U'
        ORDER BY p.id
        LIMIT :n"""), {"n": n_sample}).scalars().all()
    charges = []
    fiables = 0
    for pid in ids:
        try:
            bilan, _ = compute_bilan_servi(db, pid)
        except Exception:
            continue
        if bilan is None:
            continue
        cf = getattr(bilan, "charge_fonciere", None)
        if not cf or cf.get("par_m2_terrain") is None:
            continue
        charges.append(cf["par_m2_terrain"])
        if getattr(bilan, "fiable", False):
            fiables += 1
    charges.sort()
    if charges:
        import statistics
        med = statistics.median(charges)
        neg = sum(1 for x in charges if x < 0)
        print(f"[M5] {len(charges)} bilans (sur {len(ids)} parcelles U), {fiables} fiables | charge foncière €/m² terrain médiane={med:,.0f} | négatives={neg} ({100*neg/len(charges):.0f}%)")
        print(f"[M5] €/m² terrain: min={charges[0]:,.0f}  p25={charges[len(charges)//4]:,.0f}  med={med:,.0f}  p75={charges[3*len(charges)//4]:,.0f}  max={charges[-1]:,.0f}")
    else:
        print("[M5] aucun bilan calculable sur l'échantillon")
    # DVF terrain nu médian par zone (référence marché)
    ref = db.execute(text("""
        WITH tn AS (
          SELECT id_mutation, sum(COALESCE(surface_terrain,0)) terr, max(valeur_fonciere) val,
                 bool_or(COALESCE(surface_reelle_bati,0)>0) bati
          FROM dvf_mutations_parcelle
          WHERE nature_mutation IN ('Vente','Vente terrain à bâtir')
            AND date_mutation >= (now() - interval '5 years')::date
          GROUP BY id_mutation)
        SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY val/terr)::int, count(*)
        FROM tn WHERE NOT bati AND terr>0 AND val>1000 AND val/terr BETWEEN 20 AND 4000"""), {}).one()
    print(f"[M5] DVF terrain nu médian (5 ans, île): {ref[0]} €/m²  (n={ref[1]})")


def m6_compteurs():
    with engine().connect() as c:
        # PLU: en révision vs en procédure — lu du registre
        pass


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "m2"):
        m2_couverture()
    if which in ("all", "m5"):
        m5_charge()
