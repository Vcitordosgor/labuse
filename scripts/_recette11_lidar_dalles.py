"""RECETTE-11 A1 — ingestion LiDAR HD par DALLES sur TOUTE l'île, en arrière-plan, reprenable.

Une seule méthode pour les 24 communes (Saint-Denis compris). Pour chaque dalle 1 km de la grille
IGN : on télécharge MNS+MNT EN LOCAL, on mesure faîtage/égout de toutes les parcelles bâties de la
dalle, on écrit dans `batiment_hauteur_lidar` (avec la date de survol de la dalle), on SUPPRIME les
fichiers. Repris par l'état `lidar_dalle_grille.fait_le` : relancer SAUTE les dalles finies.

SEULS motifs d'arrêt : disque insuffisant ou taux d'échec anormal — JAMAIS la durée.

Usage (arrière-plan, nom de processus contient « lidar ») :
  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
      nohup python scripts/_recette11_lidar_dalles.py > /tmp/lidar_dalles.log 2>&1 &
Suivi : tail -f /tmp/lidar_dalles.log   ·   ou SQL : voir la requête d'avancement dans le rapport.
Env : COMMUNE (une seule commune d'abord), LIMIT (nb de dalles, test), DISQUE_MIN_GO (défaut 3).
"""
from __future__ import annotations

import os
import shutil
import time

import httpx
from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite import hauteur_lidar_dalles as D

COMMUNE = os.environ.get("COMMUNE")
LIMIT = int(os.environ["LIMIT"]) if os.environ.get("LIMIT") else None
DISQUE_MIN_GO = float(os.environ.get("DISQUE_MIN_GO", "3"))
ECHECS_MAX_CONSEC = int(os.environ.get("ECHECS_MAX_CONSEC", "25"))


def _disque_go() -> float:
    return shutil.disk_usage(os.path.expanduser("~")).free / 1e9


def dalles_a_faire(db) -> list[dict]:
    """Dalles pas encore finies. Si COMMUNE : seulement celles qui touchent son emprise."""
    if COMMUNE:
        sql = text(
            """SELECT g.* FROM lidar_dalle_grille g
               WHERE g.fait_le IS NULL AND EXISTS (
                 SELECT 1 FROM parcels p WHERE p.commune = :c
                   AND p.geom_2975 && ST_MakeEnvelope(g.x0,g.y0,g.x1,g.y1,2975))
               ORDER BY g.cle""")
        rows = db.execute(sql, {"c": COMMUNE}).mappings().all()
    else:
        rows = db.execute(text(
            "SELECT * FROM lidar_dalle_grille WHERE fait_le IS NULL ORDER BY cle")).mappings().all()
    return [dict(r) for r in rows]


def main() -> None:
    t0 = time.time()
    with session_scope() as db, httpx.Client() as client:
        D.ensure_grille(db); D.ensure_colonnes_survol(db); db.commit()
        n_grille = D.charger_grille(db, client)
        print(f"[LIDAR] grille : {n_grille} dalles connues (IGN LiDAR HD, mission par dalle)", flush=True)
        maj = D.backfill_dates(db)
        print(f"[LIDAR] backfill dates de survol sur mesures existantes : {maj} lignes", flush=True)
        todo = dalles_a_faire(db)
        print(f"[LIDAR] dalles à traiter : {len(todo)}"
              f"{' (commune '+COMMUNE+')' if COMMUNE else ''} · disque libre {_disque_go():.1f} Go", flush=True)
        if LIMIT:
            todo = todo[:LIMIT]
        ok_tot = vide_tot = err_consec = dalles_faites = dalles_avec_bati = 0
        for i, dalle in enumerate(todo, 1):
            if _disque_go() < DISQUE_MIN_GO:
                print(f"[LIDAR] STOP disque < {DISQUE_MIN_GO} Go (repris au prochain lancement)", flush=True)
                break
            try:
                res = D.mesurer_dalle(db, dalle, client)
                db.execute(text(
                    "UPDATE lidar_dalle_grille SET n_parcelles=:np, n_mesurees=:nm, fait_le=now() "
                    "WHERE cle=:c"),
                    {"np": res["n_parcelles"], "nm": res["ok"], "c": dalle["cle"]})
                db.commit()
                ok_tot += res["ok"]; vide_tot += res["vide"]
                dalles_faites += 1
                if res["n_parcelles"]:
                    dalles_avec_bati += 1
                err_consec = 0
            except Exception as exc:  # noqa: BLE001 — dalle non marquée finie → reprise ; on continue
                db.rollback()
                err_consec += 1
                print(f"[LIDAR] ERR dalle {dalle['cle']}: {str(exc)[:120]}", flush=True)
                if err_consec >= ECHECS_MAX_CONSEC:
                    print(f"[LIDAR] STOP {err_consec} échecs consécutifs (WMS indisponible ?) — "
                          f"repris au prochain lancement", flush=True)
                    break
            if i % 10 == 0 or i == len(todo):
                dt = time.time() - t0
                print(f"[LIDAR] {i}/{len(todo)} dalles · avec bâti={dalles_avec_bati} · "
                      f"parcelles mesurées={ok_tot} (vide={vide_tot}) · {dt:.0f}s "
                      f"({dt/max(1,dalles_faites):.1f}s/dalle) · disque {_disque_go():.1f} Go", flush=True)
        reste = db.execute(text("SELECT count(*) FROM lidar_dalle_grille WHERE fait_le IS NULL")).scalar()
        tot = db.execute(text("SELECT count(*) FROM batiment_hauteur_lidar WHERE methode='dalle'")).scalar()
        print(f"[LIDAR] FIN de ce lancement · dalles finies cette session={dalles_faites} · "
              f"reste≈{reste} dalles · total parcelles mesurées par dalle={tot} · {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
