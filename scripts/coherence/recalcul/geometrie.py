"""Recalcul indépendant — surface, pente, % d'intersection (aléas / couches).

  · surface_m2 : ST_Area(geom_2975) recalculée vs la surface servie (la géométrie brute est
    la source ; ST_Area est PostGIS, pas du code LABUSE).
  · pente_bande : réimplémentation des bornes en degrés (_PENTE_BANDES) vs la bande servie —
    et la conversion degrés→% (round(tan(rad)·100)) testée en cas limite (socle).
  · % couche commune (ppr_pct, mouvement_terrain_pct) : round(100·intersectantes/total,1)
    recalculé indépendamment vs la valeur servie du contexte commune.
"""
from __future__ import annotations

import math

from . import socle

#: mêmes bornes que app.py:_PENTE_BANDES (réimplémentation indépendante, degrés).
_PENTE_BANDES = ((5.0, "plat"), (15.0, "modérée"), (30.0, "forte"))


def pente_bande(deg):
    if deg is None:
        return None
    for borne, lib in _PENTE_BANDES:
        if deg < borne:
            return lib
    return "très forte"


def verifier_surface(rec: socle.Recalc, conn, echantillon):
    for row in echantillon:
        idu = row["idu"]
        with conn.cursor() as cur:
            cur.execute("SELECT surface_m2, ST_Area(geom_2975) FROM parcels WHERE idu=%s", (idu,))
            r = cur.fetchone()
        if not r:
            continue
        servi, aire = r
        rec.compare("parcels.surface_m2 vs ST_Area(geom_2975)", "surface_parcelle_m2", idu,
                    servi=servi, recalc=aire, tol="1 %", cause="formule")


def verifier_pente(rec: socle.Recalc, conn, echantillon):
    for row in echantillon:
        idu = row["idu"]
        f = socle.fiche(idu)
        deg = socle.chemin(f, "terrain.pente_moy_deg")
        bande_servie = socle.chemin(f, "terrain.pente_bande")
        if deg is None or bande_servie is None:
            continue
        rec.compare("app.py:_pente_bande", "pente_bande", idu,
                    servi=bande_servie, recalc=pente_bande(deg), tol="0", cause="formule")


def verifier_couche_pct_commune(rec: socle.Recalc, conn, echantillon):
    """% de parcelles d'une commune intersectant PPR / mouvement de terrain : recalcul
    indépendant du ratio de comptage vs la valeur servie au contexte commune."""
    communes = sorted({r["commune"] for r in echantillon if r["commune"] not in ("", "?")})
    kinds = {"ppr_pct": ("ppr", None),
             "mouvement_terrain_pct": ("georisque_alea", "mouvement_terrain")}  # subtype réel
    for com in communes:
        f = None
        try:
            c = socle._client_en_process()
            import urllib.parse
            resp = c.get(f"/communes/{urllib.parse.quote(com)}/contexte")
            if resp.status_code == 200:
                import json
                f = json.loads(resp.content)
        except Exception:  # noqa: BLE001
            f = None
        if not isinstance(f, dict):
            continue
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM parcels WHERE commune=%s", (com,))
            total = cur.fetchone()[0]
        if not total:
            continue
        for champ, (kind, subtype) in kinds.items():
            servi = _chercher(f, champ)
            if servi is None:
                continue
            cond = "sl.kind=%(kind)s" + (" AND sl.subtype=%(subtype)s" if subtype else "")
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT round(100.0*count(DISTINCT p.idu)/%(total)s, 1)
                        FROM parcels p JOIN spatial_layers sl
                          ON sl.geom_2975 && p.geom_2975 AND ST_Intersects(sl.geom_2975, p.geom_2975)
                        WHERE p.commune=%(com)s AND {cond}""",
                    {"total": total, "com": com, "kind": kind, "subtype": subtype})
                recalc = cur.fetchone()[0]
            rec.compare(f"commune.pct_parcelles_couche[{kind}]", champ, com,
                        servi=servi, recalc=recalc, tol="0,1 abs", cause="formule")


def _chercher(obj, champ, prof=0):
    """Cherche récursivement une clé `champ` dans un dict/list imbriqué (contexte commune)."""
    if prof > 6:
        return None
    if isinstance(obj, dict):
        if champ in obj and isinstance(obj[champ], (int, float)):
            return obj[champ]
        for v in obj.values():
            r = _chercher(v, champ, prof + 1)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _chercher(v, champ, prof + 1)
            if r is not None:
                return r
    return None


def verifier(rec, conn, echantillon):
    verifier_surface(rec, conn, echantillon)
    verifier_pente(rec, conn, echantillon)
    verifier_couche_pct_commune(rec, conn, echantillon)
