"""CIRCUIT-1 lot 2.1 — LA part de zonage, définie UNE fois : la part de SURFACE.

Décision Vic (05/09/2026) : « Part de zonage : la surface partout. Le compte de parcelles par
zone survit uniquement dans les filtres, sous un autre nom, jamais affiché comme une part. »

Ids du registre : `part_zone_U_pct` / `AU` / `A` / `N` (surface, CE module, seul chemin) ;
`parcelles_par_zone_n` (un NOMBRE pour les filtres — libellé « parcelles en zone … », le mot
« part » n'y apparaît jamais).

Extraction de `_foncier_commune` (api/app.py, OUTILS-6 C1) — le commentaire d'origine reste la
définition : les parts de PARCELLES ne représentent pas le territoire (à La Réunion U domine en
nombre mais A+N couvrent l'essentiel de l'aire). Dénominateur = surface cadastrée ZONÉE de la
commune (parcel_zone_plu porte UNE zone par parcelle, PK idu — jamais de double comptage) ;
les parts somment à 100 %. Témoin (fuites_mesurees.csv, 05/09/2026) : Saint-Paul A = 35,8 %,
N = 47,2 % (les valeurs « parcelles » 17,8 %/6,8 % sont le constat Vic « 18 %/6 % »).
"""
from __future__ import annotations

from sqlalchemy import text


def parts_zonage_surface(db, commune: str) -> dict | None:
    """LES parts de zonage d'une commune (surface) — le SEUL chemin servi comme « part ».
    Rend {"base": "surface", "total_ha": …, "familles": {"U": {"ha", "pct", "n"}, …}} ou None
    si la commune n'a aucune parcelle zonée (RNU : Saint-Philippe)."""
    zon = {(r["fam"] or "").upper(): {"n": r["n"], "m2": float(r["m2"] or 0)} for r in db.execute(text(
        "SELECT z.zone_fam AS fam, count(*) n, sum(p.surface_m2) m2 FROM parcels p "
        "JOIN parcel_zone_plu z ON z.idu = p.idu "
        "WHERE p.commune = :c AND z.zone_fam IS NOT NULL GROUP BY 1"), {"c": commune}).mappings()}

    def _bucket(pred):
        return (sum(v["m2"] for k, v in zon.items() if pred(k)),
                sum(v["n"] for k, v in zon.items() if pred(k)))

    au_m2, au_n = _bucket(lambda k: k.startswith("AU"))
    a_m2, a_n = _bucket(lambda k: k.startswith("A") and not k.startswith("AU"))
    u_m2, u_n = _bucket(lambda k: k.startswith("U"))
    n_m2, n_n = _bucket(lambda k: k.startswith("N"))
    total = u_m2 + au_m2 + a_m2 + n_m2
    if not total:
        return None

    def _fam(m2, nn):
        return {"ha": round(m2 / 10000), "pct": round(100 * m2 / total, 1), "n": int(nn)}

    return {"base": "surface", "total_ha": round(total / 10000),
            "familles": {"U": _fam(u_m2, u_n), "AU": _fam(au_m2, au_n),
                         "A": _fam(a_m2, a_n), "N": _fam(n_m2, n_n)}}


def parcelles_par_zone(db, communes: list[str] | None = None) -> dict:
    """LE compte de parcelles par famille/zone — un NOMBRE pour les FILTRES (« parcelles en
    zone … »), JAMAIS servi comme une part (décision Vic 2.1). Extraction de /zones-plu."""
    join, where, params = "", "WHERE z.zone_filtre IS NOT NULL", {}
    if communes:
        join = "JOIN parcels p ON p.idu = z.idu"
        where += " AND p.commune = ANY(:coms)"
        params["coms"] = communes
    rows = db.execute(text(
        f"SELECT z.zone_fam AS fam, z.zone_filtre AS zone, count(*) AS n "
        f"FROM parcel_zone_plu z {join} {where} GROUP BY 1, 2"), params).mappings().all()
    fams: dict[str, dict] = {}
    for r in rows:
        f = fams.setdefault(r["fam"] or "autre", {"fam": r["fam"] or "autre", "n": 0, "zones": []})
        f["n"] += r["n"]
        f["zones"].append({"zone": r["zone"], "n": r["n"]})
    familles = sorted(fams.values(), key=lambda f: -f["n"])
    for f in familles:
        f["zones"].sort(key=lambda z: (-z["n"], z["zone"]))
    return {"portee": "commune" if communes else "ile", "communes": communes or [], "familles": familles}
