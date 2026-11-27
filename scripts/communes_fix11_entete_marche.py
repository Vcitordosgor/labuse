#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-11 LOT 1 — PREUVE : l'en-tête Marché de la fiche tire son PRIX, son TYPE de bien,
son EFFECTIF et son PÉRIMÈTRE de la MÊME série (plus jamais le prix du bâti présenté avec l'effectif/
périmètre du terrain — défaut ASTRA-8 §1).

RÈGLE servie (marche.tsx) :
  · si le TERRAIN NU du secteur est diffusable (médiane ≥ seuil 8) → en-tête = terrain nu : prix du
    terrain · n ventes du terrain · section cadastrale ;
  · sinon → en-tête = l'ANCIEN (bâti) de `faisa.marche` : sa médiane · SON effectif (mb.n) · SON rayon
    (mb.radius_m, ou commune entière) · SON type (mb.type_prix) ; et le terrain sous le seuil est dit À
    PART (« terrain : échantillon insuffisant, N vente(s) »).

On interroge les ROUTES RÉELLES (/parcels/{idu} + /modules/faisabilite/{idu}) sur 30 fiches tirées (seed
fixe, reproductible) dans 10 communes, on reconstruit l'en-tête servi et on VÉRIFIE que ses 4 éléments
viennent d'une seule série — en contrastant avec l'ancien en-tête incohérent. Sortie brute.

Usage :
    LABUSE_TEST_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
    PYTHONPATH=src /Users/openclaw/Desktop/labuse-main/.venv/bin/python scripts/communes_fix11_entete_marche.py
"""
from __future__ import annotations

import json
import os
import random
import sys
import urllib.request

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

API = os.environ.get("LABUSE_API", "http://127.0.0.1:8000")
SEED = 1111  # tirage REPRODUCTIBLE (committé)
COMMUNES = {  # 10 communes
    "97412": "Saint-Joseph", "97415": "Saint-Paul", "97411": "Saint-Denis", "97422": "Le Tampon",
    "97416": "Saint-Pierre", "97409": "Saint-André", "97414": "Saint-Louis", "97410": "Saint-Benoît",
    "97401": "Les Avirons", "97408": "La Possession",
}
FORCES = ["97412000AY0082", "97415000CD0003"]  # les 2 exemples du rapport


def _get(path: str):
    try:
        with urllib.request.urlopen(f"{API}{path}", timeout=30) as r:
            return json.load(r)
    except Exception as ex:  # noqa: BLE001
        return {"__err__": f"{type(ex).__name__}: {ex}"}


def _terrain(fiche: dict) -> dict | None:
    sect = ((fiche.get("dvf_parcelle") or {}).get("secteur")) or []
    return next((s for s in sect if (s.get("type_bien") or "").lower() == "terrain"), None)


def _entete(fiche: dict, faisa: dict) -> dict:
    """Reconstruit l'en-tête SERVI (règle marche.tsx) + l'ancien en-tête INCOHÉRENT, pour contraste."""
    t = _terrain(fiche) or {}
    mb = (faisa.get("marche") or {}) if isinstance(faisa, dict) else {}
    t_prix, t_n, t_per = t.get("mediane_prix_m2"), t.get("n_ventes"), t.get("perimetre")
    mb_med, mb_n = mb.get("median"), mb.get("n")
    mb_ray = ("commune entière" if mb.get("commune_fallback")
              else (f"rayon {int(mb['radius_m'])} m" if mb.get("radius_m") is not None else None))
    mb_type = mb.get("type_prix")
    if t_prix is not None:   # terrain diffusable → série TERRAIN
        servi = {"serie": "terrain", "prix": t_prix, "type": "terrain nu", "effectif": t_n, "perimetre": t_per}
    elif mb_med is not None:  # repli ANCIEN (bâti) → série MB
        servi = {"serie": "ancien", "prix": round(mb_med), "type": mb_type, "effectif": mb_n, "perimetre": mb_ray}
    else:
        servi = {"serie": "aucune", "prix": None, "type": None, "effectif": None, "perimetre": None}
    # ancien en-tête (bug) : prix du bâti MAIS effectif/périmètre du terrain
    ancien_bug = {"prix": (round(mb_med) if mb_med is not None and t_prix is None else t_prix),
                  "effectif": t_n, "perimetre": t_per}
    return servi, ancien_bug, {"t_prix": t_prix, "t_n": t_n, "mb_med": (round(mb_med) if mb_med is not None else None),
                               "mb_n": mb_n, "mb_ray": mb_ray, "mb_type": mb_type}


def main() -> int:
    url = os.environ.get("LABUSE_TEST_DATABASE_URL")
    if not url:
        print("LABUSE_TEST_DATABASE_URL manquant", file=sys.stderr)
        return 2
    rng = random.Random(SEED)
    idus: list[str] = list(FORCES)
    with Session(create_engine(url)) as s:
        for insee in COMMUNES:
            rows = s.execute(text(
                "SELECT p.idu FROM parcels p "
                "WHERE p.idu LIKE :pfx AND EXISTS (SELECT 1 FROM dvf_secteur_medianes m "
                "  WHERE m.secteur = left(p.idu,10)) "
                "ORDER BY p.idu"), {"pfx": insee + "%"}).scalars().all()
            if rows:
                pick = rng.sample(rows, min(3, len(rows)))
                idus.extend(x for x in pick if x not in idus)
    idus = idus[:32]
    print(f"API={API} · seed={SEED} · {len(idus)} fiches\n")
    echecs = []
    for idu in idus:
        fiche = _get(f"/parcels/{idu}")
        faisa = _get(f"/modules/faisabilite/{idu}")
        if "__err__" in fiche or "__err__" in faisa:
            print(f"{idu}  ERREUR route : {fiche.get('__err__') or faisa.get('__err__')}")
            echecs.append(idu); continue
        servi, bug, raw = _entete(fiche, faisa)
        # COHÉRENCE : les 4 éléments servis viennent d'UNE série.
        if servi["serie"] == "terrain":
            coherent = servi["prix"] == raw["t_prix"] and servi["effectif"] == raw["t_n"] and (servi["perimetre"] or "") != ""
        elif servi["serie"] == "ancien":
            # le PRIX est celui de l'ancien (mb) ET l'effectif + le périmètre sont ceux de l'ANCIEN (mb),
            # jamais ceux du terrain — c'est exactement ce que le bug mélangeait.
            coherent = (servi["prix"] == raw["mb_med"] and servi["effectif"] == raw["mb_n"]
                        and servi["perimetre"] == raw["mb_ray"])
        else:
            coherent = servi["prix"] is None
        et = f"{servi['prix']} €/m² · {servi['type']} · {servi['effectif']} ventes · {servi['perimetre']}" if servi["prix"] is not None else "—"
        flag = "OK " if coherent else "INCOHÉRENT"
        print(f"[{flag}] {idu}  série={servi['serie']}")
        print(f"    EN-TÊTE SERVI : {et}")
        if servi["serie"] == "ancien":
            print(f"    (ancien en-tête BUGGÉ aurait montré : {bug['prix']} €/m² · {bug['effectif']} ventes · {bug['perimetre']}  → prix bâti + effectif/périmètre TERRAIN)")
        if not coherent:
            echecs.append(idu)
    print(f"\n{'='*84}")
    if echecs:
        print(f"INCOHÉRENTS / erreurs : {echecs}")
        return 1
    print(f"SUCCÈS : {len(idus)} en-têtes cohérents — prix, type, effectif, périmètre d'UNE SEULE série.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
