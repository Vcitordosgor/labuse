"""FIX-10. Exécuter population puis mesure sur chaque révision, enfin diff.

La population couvre chaque dominante qui intersecte l'intérieur d'une AU fermée.
Le bilan et la SDP proviennent du moteur servi. Une erreur de calcul interrompt la mesure.
"""
import argparse
import csv
import json
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.bilan import compute_bilan_servi
from labuse.faisabilite.db import parcel_faisabilite
from labuse.faisabilite.zonage import resolve_zone
from labuse.faisabilite.zone_servie import _TOK
from labuse.runs import current


def moteur():
    return create_engine(os.environ["LABUSE_APP_DATABASE_URL"], connect_args={
        "options": "-c default_transaction_read_only=on"
    })


def population(sortie):
    with Session(moteur()) as db:
        zones = db.execute(text(f"""
            SELECT z.id, z.commune, {_TOK} AS code FROM spatial_layers z
            WHERE z.kind='plu_gpu_zone' AND labuse_zone_famille(z.subtype)='AU'
        """))
        fermees = []
        for ident, commune, code in zones:
            regle = resolve_zone(code, commune)
            if regle and not regle.constructible_neuf:
                fermees.append(ident)
        lignes = db.execute(text("""
            SELECT DISTINCT p.id, p.idu, p.commune, zp.zone_lib, zp.zone_fam
            FROM spatial_layers z JOIN parcels p ON p.commune=z.commune
              AND p.geom_2975 && z.geom_2975
              AND ST_Relate(p.geom_2975, ST_MakeValid(z.geom_2975), '2********')
            LEFT JOIN parcel_zone_plu zp ON zp.idu=p.idu
            WHERE z.id=ANY(:ids) ORDER BY p.idu
        """), {"ids": fermees}).all()
        with sortie.open("w") as f:
            ecrivain = csv.writer(f)
            ecrivain.writerow(["pid", "idu", "commune", "zone", "fam"])
            ecrivain.writerows(lignes)
        print("Parcelles avec intersection de surface", len(lignes), sorted(Counter(r.zone_fam for r in lignes).items()))


def classement():
    with Session(moteur()) as db:
        run = current()
        nb, empreinte = db.execute(text("""
            SELECT count(*), md5(string_agg(md5(jsonb_build_array(parcelle_id, rang, tier,
                   percentile, mult_base, p_raw)::text), '' ORDER BY parcelle_id))
            FROM parcel_p_score_v2 WHERE run_id=:run
        """), {"run": run}).one()
        if not nb:
            raise ValueError(f"Classement vide pour {run}")
        print(f"{run} | {nb} | {empreinte}")


def mesurer_lot(lignes):
    with Session(moteur()) as db:
        for row in lignes:
            fz = parcel_faisabilite(db, int(row["pid"]))
            b, _ = compute_bilan_servi(db, int(row["pid"]), fz=fz)
            sdp = (fz[1].fourchette or {}).get("surface_plancher_m2") if fz else None
            montants = []
            for champ in ("ca", "charge_fonciere"):
                triplet = getattr(b, champ, None) or {}
                montants.extend(triplet.get(k) for k in ("bas", "central", "haut"))
            row.update(sdp=sdp, montants=montants)
            db.rollback()
    return lignes


def mesure(entree, sortie):
    with entree.open() as f:
        lignes = list(csv.DictReader(f))
    with ProcessPoolExecutor(max_workers=3) as pool, sortie.open("w") as f:
        for lot in pool.map(mesurer_lot, (lignes[i:i+15] for i in range(0, len(lignes), 15))):
            for row in lot:
                print(json.dumps(row, ensure_ascii=False), file=f)
            f.flush()
    print(f"{len(lignes)} parcelles mesurées")


def diff(avant, apres):
    def lire(path):
        return {r["idu"]: r for r in map(json.loads, path.read_text().splitlines())}
    a, b = lire(avant), lire(apres)
    if not a or a.keys() != b.keys():
        raise ValueError("Populations vides ou différentes")
    groupes = {}
    hors = []
    for idu, row in a.items():
        autre = b[idu]
        cle = (row["commune"], row["zone"])
        n = groupes.setdefault(cle, [0, 0, 0])
        n[0] += 1
        capacite = row["sdp"] != autre["sdp"]
        bilan = row["montants"] != autre["montants"]
        n[1] += capacite
        n[2] += bilan
        if (capacite or bilan) and row["fam"] not in ("A", "N"):
            r = resolve_zone(row["zone"], row["commune"])
            if row["fam"] != "AU" or not r or r.constructible_neuf:
                hors.append((idu, *cle, row["sdp"], autre["sdp"], row["montants"], autre["montants"]))
    print("commune | zone | mesurées | SDP modifiée | bilan modifié")
    for cle, n in sorted(groupes.items()):
        print(*cle, *n, sep=" | ")
    print("TOTAL", *map(sum, zip(*groupes.values())), sep=" | ")
    if hors:
        for cas in hors:
            print("HORS PÉRIMÈTRE", *cas, sep=" | ")
        raise SystemExit(f"ARRÊT avant commit : {len(hors)} parcelles hors périmètre")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sous = parser.add_subparsers(dest="mode", required=True)
    for nom, args in [("population", ["sortie"]), ("classement", []),
                      ("mesure", ["entree", "sortie"]), ("diff", ["avant", "apres"])]:
        p = sous.add_parser(nom)
        for arg in args:
            p.add_argument(arg, type=Path)
    options = vars(parser.parse_args())
    {"population": population, "classement": classement, "mesure": mesure, "diff": diff}[options.pop("mode")](**options)
