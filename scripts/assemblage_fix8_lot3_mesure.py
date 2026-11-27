"""OUTIL-ASSEMBLAGE-FIX-8 (LOT 3) — mesure de l'impact EURO du retrait de l'exemption automatique de
mixité attachée au LIBELLÉ de zone `AU3st` (prétendue « ZAC Savane des Tamarins »).

Contexte : aucun périmètre officiel de la ZAC Savane des Tamarins n'existe en base (spatial_layers :
seuls des POI « Tamarins », aucune géométrie de ZAC, aucune zone GPU dont le libellé la nomme). Le
règlement AU3st (PDF 97415, pp. 158-159) est une zone À URBANISER FERMÉE (« l'ouverture à l'urbanisation
de la zone est conditionnée à une modification du PLU »), n'admettant que réseaux, reconstruction à
l'identique et extensions ≤ 30 m² — aucun logement neuf. L'exemption de la clause de mixité au seul motif
du libellé AU3st n'est donc pas justifiée (consigne : sans périmètre géométrique, aucune exemption
automatique, le règlement s'applique tel qu'écrit).

Ce script compare, pour TOUTES les parcelles en zone AU3st, le bilan servi AVEC l'exemption (code actuel)
et SANS (exemption neutralisée). Il imprime les parcelles dont un MONTANT change (CA bas/central/haut,
charge foncière bas/central/haut). ARRÊT attendu : 0 parcelle si le retrait est euro-neutre.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import labuse.faisabilite.bilan as B

DBURL = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL") \
    or "postgresql+psycopg://openclaw@localhost:5432/labuse"
_ENGINE = create_engine(DBURL, future=True)


def _montants(b):
    """Tuple des montants euro suivis (None-safe)."""
    if b is None:
        return (None,) * 6
    ca = getattr(b, "ca", None) or {}
    cf = getattr(b, "charge_fonciere", None) or {}
    return (ca.get("bas"), ca.get("central"), ca.get("haut"),
            cf.get("bas"), cf.get("central"), cf.get("haut"))


def main():
    db = Session(_ENGINE)
    db.execute(text("SET default_transaction_read_only = on"))
    pids = db.execute(text("""
        SELECT DISTINCT p.id, p.idu
          FROM parcels p
          JOIN spatial_layers sl ON sl.kind = 'plu_gpu_zone' AND ST_Intersects(sl.geom_2975, p.geom_2975)
         WHERE p.commune = 'Saint-Paul'
           AND COALESCE(NULLIF(rtrim(split_part(btrim(sl.attrs->>'libelle'), ' ', 1), ':'), ''),
                        rtrim(split_part(btrim(sl.name), ' ', 1), ':')) = 'AU3st'
         ORDER BY p.idu
    """)).all()
    print(f"AU3st : {len(pids)} parcelles")

    orig = B._zac_savane_tamarins
    bouges = []
    n_exempt_now = 0
    for pid, idu in pids:
        db.rollback()
        # AVEC exemption (code actuel)
        B._zac_savane_tamarins = orig
        try:
            b_on, _ = B.compute_bilan_servi(db, pid)
        except Exception as ex:  # noqa: BLE001
            b_on = None
            print(f"  ERR ON {idu}: {ex!r}")
        m_on = _montants(b_on)
        mx_on = getattr(b_on, "mixite", None) if b_on else None
        if isinstance(mx_on, dict) and mx_on.get("detail") and "ZAC" in (mx_on.get("detail") or ""):
            n_exempt_now += 1
        # SANS exemption (neutralisée)
        db.rollback()
        B._zac_savane_tamarins = lambda *a, **k: False
        try:
            b_off, _ = B.compute_bilan_servi(db, pid)
        except Exception as ex:  # noqa: BLE001
            b_off = None
            print(f"  ERR OFF {idu}: {ex!r}")
        m_off = _montants(b_off)
        if m_on != m_off:
            bouges.append((idu, m_on, m_off))
    B._zac_savane_tamarins = orig

    print(f"Parcelles où l'exemption est AUJOURD'HUI affichée (detail ZAC) : {n_exempt_now}")
    print(f"Parcelles dont un MONTANT bouge en retirant l'exemption : {len(bouges)}")
    if bouges:
        print("\nIDU | CA(bas,cen,haut) AVEC -> SANS | ChargeF(bas,cen,haut) AVEC -> SANS")
        for idu, on, off in bouges:
            print(f"  {idu} | CA {on[0:3]} -> {off[0:3]} | CF {on[3:6]} -> {off[3:6]}")
    else:
        print("\n0 € d'écart : le retrait de l'exemption AU3st est EURO-NEUTRE.")


if __name__ == "__main__":
    main()
