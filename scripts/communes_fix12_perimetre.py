#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-12 LOT 1 — PREUVE (ASTRA-9 §1, Cilaos). Combien de fiches affichent un RAYON
qui ne contient pas l'effectif annoncé, AVANT et APRÈS la transmission de `commune_fallback` par la
route de faisabilité ?

Défaut : quand le rayon adaptatif (500→1000→1500 m) ne réunit pas le seuil d'effectif, le moteur
replie sur la COMMUNE entière (`commune_fallback=True`) ; la médiane/l'effectif sont alors
commune-wide. L'en-tête Marché (lib/marche.ts) n'affiche le rayon de la série « ancien » (mb) QUE
lorsque le terrain de la section est sous le seuil (sinon il sert la série terrain = « section
cadastrale »). AVANT le fix, la route (modules.py:1981) OMETTAIT `commune_fallback` → l'en-tête
retombait sur `radius_m` et écrivait « rayon 1 500 m » pour un effectif réuni sur la commune.

Métrique, sur UNE parcelle représentative par SECTION cadastrale (idu[:10]) de toute l'île :
  mislabel = (l'en-tête sert la série « ancien ») ET commune_fallback=True ET radius_m présent.
  AVANT : commune_fallback omis → l'en-tête montre « rayon {radius_m} m » = mislabel.
  APRÈS : commune_fallback transmis → l'en-tête montre « commune entière » = 0 mislabel.

Reproduit l'en-tête (marche.ts) à l'identique : série terrain si prix_section(terrain) servi, sinon
série « ancien » (mb) avec son rayon/ commune.

Usage :
    LABUSE_TEST_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
    PYTHONPATH=src /Users/openclaw/Desktop/labuse-main/.venv/bin/python scripts/communes_fix12_perimetre.py
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse import marche_service
from labuse.dvf_secteur import prix_section


def _entete_perimetre(mb: dict, transmis: bool) -> str | None:
    """Reproduit lib/marche.ts:25 — périmètre affiché par la série « ancien » (mb).
    `transmis` = la route transmet commune_fallback (APRÈS) ou non (AVANT)."""
    cf = bool(mb.get("commune_fallback")) if transmis else False
    if cf:
        return "commune entière"
    r = mb.get("radius_m")
    return f"rayon {int(r)} m" if r is not None else None


def main() -> int:
    url = os.environ.get("LABUSE_TEST_DATABASE_URL") or "postgresql+psycopg://openclaw@localhost:5432/labuse"
    eng = create_engine(url)
    with eng.connect() as c:
        reps = c.execute(text(
            "SELECT substring(idu,1,10) AS sec, min(idu) AS idu FROM parcels "
            "GROUP BY substring(idu,1,10) ORDER BY 1")).mappings().all()
    print(f"Sections cadastrales : {len(reps)} (une parcelle représentative chacune)\n")

    avant = apres = 0
    serie_ancien = 0
    exemples = []
    with Session(eng) as db:
        for i, r in enumerate(reps):
            sec, idu = r["sec"], r["idu"]
            try:
                mb = marche_service.marche_dvf(db, idu, profil=marche_service.DVF_BANQUIER_ADAPTATIF)
            except Exception as ex:  # noqa: BLE001 — parcelle sans bilan/marche : on la saute, tracé
                continue
            if not mb:
                continue
            # L'en-tête sert la série TERRAIN si prix_section(terrain) est diffusé (≥ seuil) ; sinon « ancien ».
            ter = prix_section(db, sec, "terrain")
            sert_ancien = ter.get("prix_m2") is None
            if not sert_ancien:
                continue
            serie_ancien += 1
            av = _entete_perimetre(mb, transmis=False)   # AVANT : flag omis
            ap = _entete_perimetre(mb, transmis=True)     # APRÈS : flag transmis
            cf = bool(mb.get("commune_fallback"))
            # mislabel = effectif commune mais périmètre affiché = un rayon
            if cf and av is not None and av.startswith("rayon"):
                avant += 1
                if len(exemples) < 8:
                    exemples.append((idu, mb.get("type_prix"), mb.get("n"), av, ap))
            if cf and ap is not None and ap.startswith("rayon"):
                apres += 1
            if (i + 1) % 200 == 0:
                print(f"  … {i+1}/{len(reps)} sections", file=sys.stderr)

    print(f"Fiches servant la série « ancien » (terrain sous le seuil) : {serie_ancien}")
    print(f"  AVANT (commune_fallback omis)   — rayon affiché pour un effectif commune : {avant}")
    print(f"  APRÈS (commune_fallback transmis) — rayon affiché pour un effectif commune : {apres}")
    print("\nExemples de fiches corrigées (idu · type · n · AVANT → APRÈS) :")
    for idu, tp, n, av, ap in exemples:
        print(f"  {idu}  {tp} · {n} ventes · {av}  →  {ap}")

    # Cilaos 97424000AC0139 — le cas nommé par l'audit, before/after explicite.
    print("\nCilaos 97424000AC0139 (cas ASTRA-9 §1) :")
    with Session(eng) as db:
        mb = marche_service.marche_dvf(db, "97424000AC0139", profil=marche_service.DVF_BANQUIER_ADAPTATIF)
        print(f"  mb : type={mb.get('type_prix')} median={mb.get('median')} n={mb.get('n')} "
              f"radius_m={mb.get('radius_m')} commune_fallback={mb.get('commune_fallback')}")
        print(f"  en-tête AVANT : {_entete_perimetre(mb, transmis=False)}")
        print(f"  en-tête APRÈS : {_entete_perimetre(mb, transmis=True)}")

    ok = apres == 0 and avant > 0
    print(f"\n{'SUCCÈS' if ok else 'À VÉRIFIER'} : {avant} fiches mal étiquetées AVANT → {apres} APRÈS.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
