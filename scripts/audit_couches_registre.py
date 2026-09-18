"""COUCHES-REGISTRE — audit du lien couche↔source (checks 1 Registre + 2 Réservoir réel) et sens
inverse. Lecture seule.

Check 1 (Registre) : la couche est déclarée avec un réservoir nommé — via DONNEES[cid].reservoirs
(front key) et/ou RESERVOIR_TABLES[rid].couches.
Check 2 (Réservoir réel) : le réservoir déclaré existe en data_sources, statut `connecte`, ET c'est
bien lui que la couche LIT :
  · couche `spatial_layers` → le `data_source_id` RÉEL des lignes servies pointe une source connecte ;
  · repère dérivé (mvt_parcels / mvt_communes / parcel_zone_plu) → le réservoir déclaré est connecte
    et la table dérivée porte des lignes (le `data_source_id` n'existe pas sur ces tables dérivées).
"""
import json
import re
from labuse.api.couches_tuyau import registre
from labuse.registre import tables
from labuse.registre.couverture import COUCHE_PAR_CLE_FRONT
from labuse.registre.donnees import DONNEES
from labuse.registre.valeur import _RESERVOIR_NAME_ILIKE
from labuse.db import session_scope
from sqlalchemy import text

RT = tables.RESERVOIR_TABLES
reg = registre()

# tuyau kind → clé front (pour retrouver le cid DONNEES via COUCHE_PAR_CLE_FRONT)
KIND2FRONT = {
    "plu_gpu_zone": "zonage", "limites_parcelles": "limites", "limites_communes": "communes",
    "safer": "rpg", "amenite": "equipements", "amenite_bpe": "equipements_bpe",
    "parc_national": "parc", "transport_ligne": "transport", "transport_arret": "transport",
    "pole_echange": "axes", "axe_structurant": "axes", "ligne_ht": "lignes_ht", "ligne_mt": "lignes_ht",
    "tcsp": "tcsp", "zonage_parcelle": "zonage_parcelle",
}
stocked_to_res: dict[str, list[str]] = {}
for rid, r in RT.items():
    for k in (getattr(r, "couches", None) or ()):
        stocked_to_res.setdefault(k, []).append(rid)


def declared_reservoirs(kind, c):
    stocked = [sk for sk, _ in (c.resolution or ())]
    resv = {rid for sk in stocked for rid in stocked_to_res.get(sk, [])}
    fk = KIND2FRONT.get(kind, kind)
    cid = COUCHE_PAR_CLE_FRONT.get(fk)
    if cid and cid in DONNEES:
        resv |= set(getattr(DONNEES[cid], "reservoirs", ()) or ())
    return sorted(resv), cid


with session_scope() as db:
    ds = {name: status for name, status in db.execute(text("SELECT name, status FROM data_sources")).all()}

    def res_status(rid):
        pat = _RESERVOIR_NAME_ILIKE.get(rid)
        if not pat:
            return (None, None)
        rx = re.compile("^" + re.escape(pat).replace("\\%", ".*").replace("%", ".*") + "$", re.I)
        for name, st in ds.items():
            if rx.match(name):
                return (name, st)
        return (None, "ABSENT")

    def real_source(c):
        """Source RÉELLE via data_source_id (couches spatial_layers) — (name, status, n)."""
        best = (None, None, 0)
        for sk, subs in (c.resolution or ()):
            q = ("SELECT ds.name, ds.status, count(*) n FROM spatial_layers sl "
                 "LEFT JOIN data_sources ds ON ds.id=sl.data_source_id WHERE sl.kind=:k")
            p = {"k": sk}
            if subs:
                q += " AND sl.subtype = ANY(:s)"; p["s"] = list(subs)
            q += " GROUP BY ds.name, ds.status ORDER BY n DESC"
            for n, s, cnt in db.execute(text(q), p).all():
                if cnt > best[2]:
                    best = (n, s, cnt)
        return best

    def derived_rows(c):
        if c.table in ("mvt_parcels", "mvt_communes"):
            return db.execute(text(f"SELECT count(*) FROM {c.table}")).scalar() or 0
        return 0

    rows = []
    c1 = c2 = 0
    for kind, c in sorted(reg.items()):
        resv, cid = declared_reservoirs(kind, c)
        check1 = bool(resv)
        if c.resolution:  # couche spatial_layers → vérité data_source_id
            nm, st, n = real_source(c)
            check2 = (st == "connecte" and n > 0)
            real = f"{nm} [{st}] ×{n}" if nm else f"— (aucune source) ×{n}"
        else:  # repère dérivé → réservoir déclaré connecte + table dérivée peuplée
            statuts = [(rid, *res_status(rid)) for rid in resv]
            conn = [x for x in statuts if x[2] == "connecte"]
            nd = derived_rows(c)
            check2 = bool(conn) and nd > 0
            real = f"{'/'.join(x[1] or x[0] for x in conn) or '—'} [dérivé {c.table} ×{nd}]"
        c1 += check1; c2 += check2
        rows.append({"kind": kind, "famille_table": c.table, "reservoirs": resv, "cid": cid,
                     "real": real, "check1_registre": check1, "check2_reservoir": check2})

    geo_no_couche = []
    for rid, r in sorted(RT.items()):
        tbls = getattr(r, "tables", None) or ()
        couches = getattr(r, "couches", None) or ()
        is_geo = any(("spatial_layers" in t or "mvt_" in t or "parcel" in t or t == "communes") for t in tbls)
        name, st = res_status(rid)
        if is_geo and not couches and st == "connecte":
            geo_no_couche.append((rid, name, list(tbls)))

import sys
print(f"CHECK 1 (Registre) : {c1}/56 | CHECK 2 (Réservoir réel) : {c2}/56", file=sys.stderr)
for r in rows:
    if not (r["check1_registre"] and r["check2_reservoir"]):
        print(f"  ✗ {r['kind']:22} reg={'O' if r['check1_registre'] else 'N'} "
              f"res={'O' if r['check2_reservoir'] else 'N'} | {r['reservoirs']} | {r['real']}", file=sys.stderr)
print(json.dumps({"rows": rows, "geo_no_couche": geo_no_couche, "check1": c1, "check2": c2},
                 ensure_ascii=False, default=str))
