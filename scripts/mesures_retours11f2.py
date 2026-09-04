"""RETOURS-11F session F2 — mesures base réelle (labuse). Chaque chiffre du rapport vient d'ici.
Couvre M3 (prix secteur), M9 (score densifier), M12 (piscines confiance), M13 (colonnes)."""
from __future__ import annotations

import sys

from sqlalchemy import text

from labuse.db import engine, session_factory

PARCELLE = "97415000BS0086"   # parcelle des captures F4/F5 (Saint-Paul)


def m3_prix_secteur():
    """Divergence O1 : sector_price (bilan) vs _ref_local (pige) sur la MÊME parcelle."""
    S = session_factory(); db = S()
    from labuse.faisabilite.bilan import sector_price, Hypotheses, PERIODE_SECTEUR_ANS, MIN_N_SECTEUR
    from labuse.pige.signaux import _ref_local, SEUIL_REF_LOCAL
    pid = db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": PARCELLE}).scalar()
    print(f"[M3] parcelle {PARCELLE} (id={pid}) — constantes : PERIODE_SECTEUR_ANS={PERIODE_SECTEUR_ANS} "
          f"MIN_N_SECTEUR={MIN_N_SECTEUR} SEUIL_REF_LOCAL={SEUIL_REF_LOCAL}")
    if pid:
        sp = sector_price(db, pid, Hypotheses.charger())
        print(f"[M3] sector_price → €/m²={sp.get('eur_m2') if sp else None}  n={sp.get('n') if sp else None} "
              f"type={sp.get('type_retenu') if sp else None} rayon={sp.get('rayon_m') if sp else None} "
              f"fenetre={sp.get('fenetre') if sp else None}")
    for tb in ("maison", "appartement"):
        rl = _ref_local(db, PARCELLE, tb)
        print(f"[M3] _ref_local({tb}) → €/m²={rl.get('eur_m2') if rl else None}  n={rl.get('n') if rl else None} "
              f"rayon={rl.get('rayon_m') if rl else None} millesime={rl.get('millesime') if rl else None}")


def m9_score_densifier():
    """Saturation du score renouvellement : combien de parcelles à 100/100 ?"""
    with engine().connect() as c:
        tbl = c.execute(text("SELECT to_regclass('parcel_renouvellement')")).scalar()
        if not tbl:
            print("[M9] table parcel_renouvellement absente")
            return
        r = c.execute(text(
            "SELECT count(*) n, count(*) FILTER (WHERE renouv_score>=100) sat100, "
            "count(*) FILTER (WHERE renouv_score>=95) sat95, "
            "round(avg(renouv_score)::numeric,1) moy, max(renouv_score) mx, min(renouv_score) mn "
            "FROM parcel_renouvellement")).mappings().one()
        print(f"[M9] segment renouvellement n={r['n']} | score=100: {r['sat100']} "
              f"({100*r['sat100']/max(1,r['n']):.0f}%) | score>=95: {r['sat95']} | moy={r['moy']} min={r['mn']} max={r['mx']}")
        # distribution des têtes de liste (top 50) — combien à 100 ?
        top = c.execute(text("SELECT renouv_score FROM parcel_renouvellement ORDER BY renouv_score DESC LIMIT 50")).scalars().all()
        print(f"[M9] top 50 : {sum(1 for s in top if s>=100)} à 100 ; scores distincts dans le top 50 = {len(set(top))}")


def m12_piscines():
    """Confiance des piscines : distribution + total réel (R8c : 8 299 ?)."""
    with engine().connect() as c:
        tbl = c.execute(text("SELECT to_regclass('parcel_equipements')")).scalar()
        if not tbl:
            print("[M12] table parcel_equipements absente")
            return
        r = c.execute(text(
            "SELECT count(*) FILTER (WHERE piscine) n_pisc, "
            "count(*) FILTER (WHERE piscine AND piscine_confiance IS NULL) sans_conf, "
            "avg(piscine_confiance) FILTER (WHERE piscine) moy, "
            "min(piscine_confiance) FILTER (WHERE piscine) mn, max(piscine_confiance) FILTER (WHERE piscine) mx, "
            "count(*) FILTER (WHERE piscine AND piscine_confiance>=0.8) haute, "
            "count(*) FILTER (WHERE piscine AND piscine_confiance>=0.5 AND piscine_confiance<0.8) moyenne, "
            "count(*) FILTER (WHERE piscine AND piscine_confiance<0.5) basse "
            "FROM parcel_equipements")).mappings().one()
        _moy = f"{r['moy']:.3f}" if r['moy'] is not None else "None"
        print(f"[M12] piscines détectées={r['n_pisc']} | sans confiance={r['sans_conf']} | "
              f"conf moy={_moy} [{r['mn']}..{r['mx']}]")
        print(f"[M12] confiance : haute(>=.8)={r['haute']}  moyenne(.5-.8)={r['moyenne']}  basse(<.5)={r['basse']}")
        # corrections table existe ?
        corr = c.execute(text("SELECT to_regclass('piscine_corrections')")).scalar()
        print(f"[M12] table piscine_corrections : {'présente' if corr else 'ABSENTE (à créer)'}")


def m13_colonnes():
    """Table Communes : couverture €/m² terrain nu DVF + population."""
    S = session_factory(); db = S()
    from labuse.faisabilite.marche_commune import ligne2_terrain_zone
    communes = db.execute(text("SELECT DISTINCT commune FROM parcels ORDER BY commune")).scalars().all()
    ok = 0
    ex = []
    for com in communes:
        try:
            l = ligne2_terrain_zone(db, com)
            pz = (l.get("valeurs") or {}).get("par_zone") or {}
        except Exception:
            pz = {}
        cell = None
        for fam in ("U", "AU"):
            c0 = pz.get(fam) or {}
            if c0.get("calculable") and c0.get("median_eur_m2"):
                cell = (fam, c0["median_eur_m2"], c0.get("n")); break
        if cell:
            ok += 1
            if len(ex) < 8:
                ex.append((com, *cell))
    print(f"[M13] terrain nu DVF servable : {ok}/{len(communes)} communes")
    for com, fam, v, n in ex:
        print(f"      {com:20s} zone {fam}  {v} €/m²  n={n}")
    with engine().connect() as c:
        pop = c.execute(text("SELECT count(*) FROM commune_insee_logement")).scalar()
        print(f"[M13] population RP par commune : AUCUNE table dédiée ; commune_insee_logement (logements) n={pop}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("m3", m3_prix_secteur), ("m9", m9_score_densifier),
                     ("m12", m12_piscines), ("m13", m13_colonnes)):
        if which in ("all", name):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                print(f"[{name}] ERREUR: {e}")
