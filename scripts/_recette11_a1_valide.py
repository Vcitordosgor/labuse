"""RECETTE-11 A1 — la méthode par dalles redonne-t-elle les valeurs de la méthode par parcelle ?

Sur 50 bâtiments de Saint-Denis, mesure faîtage/égout par les DEUX chemins :
- ANCIEN : `hauteur_lidar.hauteur_parcelle_lidar` (fetch WMS MNS+MNT HIGHRES par parcelle, la méthode
  validée RECETTE-8 W23 sur 20 bâtiments) ;
- NOUVEAU : dalle MNH téléchargée + lue en local (`hauteur_lidar_dalles`).
Écrit l'écart toléré et l'écart constaté (max, médian) sur faîtage et égout.

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src python scripts/_recette11_a1_valide.py
"""
from __future__ import annotations

import statistics

import httpx
import rasterio
from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite import hauteur_lidar_dalles as D
from labuse.faisabilite.hauteur_lidar import hauteur_parcelle_lidar

TOLERANCE_M = 0.5  # le rendu arrondit au 0,1 m ; ±0,5 m = même valeur pour l'usage (faîtage/égout)


def main() -> None:
    with session_scope() as db, httpx.Client() as client:
        D.ensure_grille(db); D.ensure_colonnes_survol(db); db.commit()
        D.charger_grille(db, client)
        # 50 parcelles bâties de Saint-Denis réparties sur quelques dalles
        idus = [r[0] for r in db.execute(text(
            "SELECT p.idu FROM parcels p JOIN spatial_layers b ON b.kind='batiment' "
            "AND b.geom_2975 IS NOT NULL AND ST_Intersects(b.geom_2975,p.geom_2975) "
            "WHERE p.commune='Saint-Denis' GROUP BY p.idu ORDER BY p.idu LIMIT 50")).all()]
        print(f"[A1] {len(idus)} parcelles de Saint-Denis")

        # NOUVEAU : mesure par dalle (regroupe par dalle pour ne télécharger qu'une fois)
        neuf: dict[str, dict] = {}
        # précalcule la grille utile
        dalles = {dict(r)["cle"]: dict(r) for r in db.execute(text("SELECT * FROM lidar_dalle_grille")).mappings().all()}
        for idu in idus:
            row = db.execute(text(
                "SELECT ST_X(ST_Centroid(pb.geom)) cx, ST_Y(ST_Centroid(pb.geom)) cy FROM parcels p "
                "JOIN LATERAL (SELECT b.geom_2975 geom FROM spatial_layers b WHERE b.kind='batiment' "
                "AND b.geom_2975 IS NOT NULL AND ST_Intersects(b.geom_2975,p.geom_2975) "
                "ORDER BY ST_Area(b.geom_2975) DESC LIMIT 1) pb ON true WHERE p.idu=:i"),
                {"i": idu}).mappings().first()
            if not row:
                continue
            for dd in dalles.values():
                if dd["x0"] <= row["cx"] < dd["x1"] and dd["y0"] <= row["cy"] < dd["y1"]:
                    neuf.setdefault(dd["cle"], dd)
                    break
        mesures_neuf: dict[str, dict] = {}
        for cle, dd in neuf.items():
            path = D._telecharger_mnh(client, dd["url_mnh"])
            try:
                with rasterio.open(path) as ds:
                    mnh = ds.read(1).astype("float64"); tr = ds.transform; nod = ds.nodata
                for r in D.parcelles_de_dalle(db, dd["x0"], dd["y0"], dd["x1"], dd["y1"]):
                    if r["idu"] not in idus:
                        continue
                    h = D._hauteurs_locales(mnh, tr, nod, r["gj"], (r["x0"], r["y0"], r["x1"], r["y1"]))
                    if h:
                        mesures_neuf[r["idu"]] = h
            finally:
                import os
                os.remove(path)

        # ANCIEN : mesure par parcelle
        ecarts_f, ecarts_e = [], []
        compares = 0
        for idu in idus:
            if idu not in mesures_neuf:
                continue
            pid = db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            anc = hauteur_parcelle_lidar(db, int(pid))
            if not anc or anc.get("faitage_m") is None:
                continue
            nf = mesures_neuf[idu]
            df = abs(nf["faitage_m"] - anc["faitage_m"])
            de = abs(nf["egout_m"] - anc["egout_m"])
            ecarts_f.append(df); ecarts_e.append(de); compares += 1
            flag = "" if (df <= TOLERANCE_M and de <= TOLERANCE_M) else "  <-- HORS TOL"
            print(f"  {idu}: faîtage dalle={nf['faitage_m']} parc={anc['faitage_m']} Δ={df:.2f} | "
                  f"égout dalle={nf['egout_m']} parc={anc['egout_m']} Δ={de:.2f}{flag}")

        print(f"\n[A1] comparés {compares} bâtiments · tolérance ±{TOLERANCE_M} m")
        if ecarts_f:
            print(f"  faîtage : Δ max={max(ecarts_f):.2f} m, médian={statistics.median(ecarts_f):.2f} m, "
                  f"≤tol={sum(1 for d in ecarts_f if d<=TOLERANCE_M)}/{len(ecarts_f)}")
            print(f"  égout   : Δ max={max(ecarts_e):.2f} m, médian={statistics.median(ecarts_e):.2f} m, "
                  f"≤tol={sum(1 for d in ecarts_e if d<=TOLERANCE_M)}/{len(ecarts_e)}")


if __name__ == "__main__":
    main()
