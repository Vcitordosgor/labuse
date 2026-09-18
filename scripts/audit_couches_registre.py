"""COUCHES-REGISTRE-1 — audit lecture seule du lien couche↔source↔Circuit. Produit la matière
du rapport (checks 1 Registre + 2 Réservoir réel, + sens inverse). Aucune écriture."""
import json
from labuse.api.couches_tuyau import registre
from labuse.registre import tables
from labuse.registre.couverture import COUCHE_PAR_CLE_FRONT
from labuse.registre.donnees import DONNEES
from labuse.registre.valeur import _RESERVOIR_NAME_ILIKE
from labuse.db import session_scope
from sqlalchemy import text

RT = tables.RESERVOIR_TABLES
reg = registre()

# invert reservoir.couches → stocked_kind -> [rid]
stocked_to_res: dict[str, list[str]] = {}
for rid, r in RT.items():
    for k in (getattr(r, "couches", None) or ()):
        stocked_to_res.setdefault(k, []).append(rid)

# front key -> cid, invert to also find cid by stocked kind via DONNEES.table "kind=X"
cid_by_kind: dict[str, str] = {}
for cid, d in DONNEES.items():
    tbl = (getattr(d, "table", "") or "")
    if "kind=" in tbl:
        k = tbl.split("kind=")[1].split(",")[0].split(")")[0].strip()
        cid_by_kind.setdefault(k, cid)

with session_scope() as db:
    # data_sources name+status
    ds = {name: status for name, status in db.execute(text("SELECT name, status FROM data_sources")).all()}
    def res_status(rid):
        pat = _RESERVOIR_NAME_ILIKE.get(rid)
        if not pat:
            return (None, None)
        import re
        rx = re.compile("^" + re.escape(pat).replace("\\%", ".*").replace("%", ".*") + "$", re.I)
        for name, st in ds.items():
            if rx.match(name):
                return (name, st)
        return (None, "ABSENT")

    def touched_rows(kind, c):
        """Lignes réellement servies par la couche (table runtime, pas la déclaration)."""
        res = c.resolution
        try:
            if c.table == "mvt_parcels":
                return db.execute(text("SELECT count(*) FROM mvt_parcels")).scalar() or 0
            if c.table == "mvt_communes":
                return db.execute(text("SELECT count(*) FROM mvt_communes")).scalar() or 0
            if not res:
                return -1
            n = 0
            for sk, subs in res:
                if subs:
                    n += db.execute(text("SELECT count(*) FROM spatial_layers WHERE kind=:k AND subtype = ANY(:s)"),
                                    {"k": sk, "s": list(subs)}).scalar() or 0
                else:
                    n += db.execute(text("SELECT count(*) FROM spatial_layers WHERE kind=:k"), {"k": sk}).scalar() or 0
            return n
        except Exception as e:  # noqa
            return f"ERR:{e}"

    rows = []
    for kind, c in sorted(reg.items()):
        stocked = [sk for sk, _ in c.resolution] or ([] if c.resolution == () else [])
        reservoirs = sorted({rid for sk in stocked for rid in stocked_to_res.get(sk, [])})
        res_info = [(rid, *res_status(rid)) for rid in reservoirs]
        # check 1 : declared with a named reservoir
        check1 = bool(reservoirs)
        # check 2 : >=1 reservoir connecte AND runtime table has rows
        nrows = touched_rows(kind, c)
        connecte = [ri for ri in res_info if ri[2] == "connecte"]
        has_rows = isinstance(nrows, int) and (nrows > 0 or nrows == -1)
        check2 = bool(connecte) and (isinstance(nrows, int) and nrows > 0)
        # front key + cid (registre « i »)
        fk = [k for k, v in COUCHE_PAR_CLE_FRONT.items()]  # placeholder
        cid = cid_by_kind.get(kind) or cid_by_kind.get(stocked[0] if stocked else "")
        rows.append({
            "kind": kind, "table": c.table, "stocked": stocked,
            "reservoirs": res_info, "rows": nrows,
            "cid": cid, "check1_registre": check1,
            "check2_reservoir": check2,
        })

    # reverse : geographic reservoirs (tables include spatial_layers or map data) with no couche
    geo_no_couche = []
    for rid, r in sorted(RT.items()):
        tbls = getattr(r, "tables", None) or ()
        couches = getattr(r, "couches", None) or ()
        is_geo = any("spatial_layers" in t or "mvt_" in t or "parcel" in t for t in tbls)
        name, st = res_status(rid)
        if is_geo and not couches and st == "connecte":
            geo_no_couche.append((rid, name, tbls))

print(json.dumps({"rows": rows, "geo_no_couche": geo_no_couche}, ensure_ascii=False, default=str))
