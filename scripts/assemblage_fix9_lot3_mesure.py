"""OUTIL-ASSEMBLAGE-FIX-9 (LOT 3) — mesure avant/après du retrait de la capacité FANTÔME des zones à
urbaniser FERMÉES (`constructible_neuf=False`, famille AU : AU*st / 2AU…), sur TOUTES les communes.

Cause : le moteur SOLO (`parcel_faisabilite`) comptait toute la famille U/AU — AU fermée comprise — comme
assiette bâtissable, et appliquait les règles d'un éclat U constructible à toute l'assiette (CP1639 :
AU3st 99,95 % + éclat U3c 7 m² → 11 299 m² fantômes). Le moteur UNION (`estimate_capacity` par zone) zéro
déjà l'AU fermée. Correctif : `_uau_constructible_reelle` exclut les zones AU fermées de la portion
bâtissable — une seule règle lue par les deux moteurs.

Ce script compare, pour TOUTES les parcelles dont la zone DOMINANTE est une zone AU fermée, le bilan servi
(`compute_bilan_servi`) AVANT et APRÈS le correctif (via le drapeau d'environnement de mesure). Lancé 2×
(code AVANT = fichiers de `main` ; code APRÈS = HEAD). Il écrit un JSON keyé par idu : capacité (sdp) et
montants (CA bas/central/haut). Le diff final (par un second script) donne : parcelles dont la capacité
passe à zéro, par commune×zone ; bilans dont le montant change.
"""
from __future__ import annotations

import json
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.bilan import compute_bilan_servi
from labuse.faisabilite.zonage import resolve_zone

DBURL = os.environ["LABUSE_APP_DATABASE_URL"]
out_path = sys.argv[1]
e = create_engine(DBURL, future=True)
db = Session(e)
db.execute(text("SET default_transaction_read_only = on"))

# Parcelles dont la zone DOMINANTE (parcel_zone_plu) est de famille AU — on résout `constructible_neuf`
# en Python et on garde les FERMÉES. (Les parcelles à dominante A/N avec un éclat AU fermé sont
# couvertes par le contrôle séparé `assemblage_fix9_controle_non_fermees.py`.)
rows = db.execute(text("""
    SELECT p.id, p.idu, p.commune, z.zone_lib
    FROM parcels p JOIN parcel_zone_plu z ON z.idu = p.idu
    WHERE z.zone_fam = 'AU'
    ORDER BY p.idu
""")).all()

# cache constructible_neuf par (commune, zone)
cn_cache = {}
def _fermee(commune, zone):
    k = (commune, zone)
    if k not in cn_cache:
        r = resolve_zone(zone, commune)
        cn_cache[k] = (r is not None and r.constructible_neuf is False)
    return cn_cache[k]

res = {}
n = 0
for pid, idu, commune, zone in rows:
    if not _fermee(commune, zone):
        continue
    n += 1
    db.rollback()
    try:
        b, _ = compute_bilan_servi(db, pid)
    except Exception as ex:  # noqa: BLE001
        res[idu] = {"err": repr(ex), "commune": commune, "zone": zone}
        continue
    ca = (getattr(b, "ca", None) or {}) if b else {}
    cf = (getattr(b, "charge_fonciere", None) or {}) if b else {}
    res[idu] = {"commune": commune, "zone": zone,
                "ca": [ca.get("bas"), ca.get("central"), ca.get("haut")],
                "cf": [cf.get("bas"), cf.get("central"), cf.get("haut")]}
json.dump(res, open(out_path, "w"))
print(f"{n} parcelles en zone AU fermée mesurées -> {out_path}")
