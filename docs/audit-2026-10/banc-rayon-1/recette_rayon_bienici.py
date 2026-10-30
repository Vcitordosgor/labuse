#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RADAR-SOURCES-3 (Lot B) — RECETTE du rayon par source sur la capture réelle Bien'ici
`qa/radar-bienici/ECH-BIENICI-1.json` (100 annonces de vente, La Réunion), LECTURE SEULE sur la base
servie `labuse` (434 582 parcelles).

Mesure, AVANT (rayon 150 m partout, l'ancien comportement) vs APRÈS (60 m pour les positions à
l'adresse, 150 m pour les positions de quartier — le code actuel) :
  · la répartition des états (rattachee / piste / non_rattachee) ;
  · le nombre d'AMBIGUS (pistes à plusieurs candidates « à instruire ») ;
  · le nombre d'AUTO-RATTACHÉS, avec leur idu (pour la vérif ortho).

AVANT = on force `_rayon` à rendre 150 m (monkeypatch local), rien d'autre ne change.
APRÈS = le code tel quel.

Lancer : LABUSE_DATABASE_URL=postgresql+psycopg:///labuse PYTHONPATH=src \
         ~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/banc-rayon-1/recette_rayon_bienici.py
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

from labuse.db import session_scope
from labuse.pige import html_next, rattachement_html
from labuse.pige.intake import resoudre_commune

ECH = Path(__file__).resolve().parents[3] / "qa" / "radar-bienici" / "ECH-BIENICI-1.json"
ICI = Path(__file__).resolve().parent


def _mesure(db, recs, *, rayon_force: int | None):
    """Passe chaque rec rattachable dans la cascade ; si `rayon_force`, on impose ce rayon (AVANT)."""
    orig = rattachement_html._rayon
    if rayon_force is not None:
        rattachement_html._rayon = lambda rec: rayon_force
    etats = collections.Counter()
    ambigus = 0
    autos = []
    try:
        for r in recs:
            res = rattachement_html.rattacher(db, r)
            etats[res["etat"]] += 1
            if res["etat"] == "piste" and len([p for p in res.get("pistes", []) if p["n_criteres"] >= 2]) >= 2:
                ambigus += 1
            elif res["etat"] == "piste" and len(res.get("pistes", [])) >= 2:
                ambigus += 1
            if res["etat"] == "rattachee":
                autos.append((r, res))
    finally:
        rattachement_html._rayon = orig
    return etats, ambigus, autos


def main() -> None:
    recs = html_next.analyser(ECH.read_text(encoding="utf-8"))["records"]
    dans = [r for r in recs if resoudre_commune(r["commune"])]
    rattachables = [r for r in dans if r.get("type") in rattachement_html._TYPES_RATTACHABLES
                    and not r.get("est_copro")]
    adresse = [r for r in rattachables if r.get("source_position") == "address"]
    print(f"Annonces lues : {len(recs)} · périmètre : {len(dans)} · rattachables (maison/terrain/immeuble) : "
          f"{len(rattachables)} · dont position À L'ADRESSE : {len(adresse)}")

    with session_scope() as db:
        e_av, amb_av, autos_av = _mesure(db, rattachables, rayon_force=rattachement_html.RAYON_M)
        e_ap, amb_ap, autos_ap = _mesure(db, rattachables, rayon_force=None)

    def bloc(nom, etats, ambigus, autos):
        print(f"\n== {nom} ==")
        for k in ("rattachee", "piste", "non_rattachee"):
            print(f"  {k:<16} {etats.get(k, 0):3d}")
        print(f"  AMBIGUS (≥2 candidates, à instruire) : {ambigus}")
        print(f"  AUTO-RATTACHÉS : {len(autos)}")

    bloc("AVANT (rayon 150 m partout)", e_av, amb_av, autos_av)
    bloc("APRÈS (60 m à l'adresse, 150 m quartier)", e_ap, amb_ap, autos_ap)

    # liste des auto-rattachés APRÈS (pour la vérif ortho) + export JSON
    print("\n== AUTO-RATTACHÉS APRÈS (à vérifier à l'ortho) ==")
    export = []
    for r, res in autos_ap:
        crit = "+".join(sorted(c["critere"] for c in res["criteres"])) or res.get("etage")
        print(f"  {r['commune']:<16} {r['type']:<9} hab={r.get('surface_hab')} terr={r.get('surface_terrain')} "
              f"→ {res['idu']} [{res['niveau']}/{crit} conf={res.get('confiance')}] "
              f"pos={r.get('source_position')} r={r.get('brut', {}).get('blur_radius_m')}")
        export.append({
            "list_id": r.get("list_id"), "commune": r["commune"], "type": r["type"],
            "surface_hab": r.get("surface_hab"), "surface_terrain": r.get("surface_terrain"),
            "lat": r.get("lat"), "lng": r.get("lng"),
            "source_position": r.get("source_position"),
            "blur_radius_m": r.get("brut", {}).get("blur_radius_m"),
            "idu": res["idu"], "niveau": res["niveau"], "confiance": res.get("confiance"),
            "criteres": res["criteres"], "n_pistes": len(res.get("pistes", [])),
            "subject": r.get("subject"), "url": r.get("url"),
        })
    (ICI / "AUTO_RATTACHES.json").write_text(json.dumps(export, ensure_ascii=False, indent=2))
    print(f"\nécrit : {ICI/'AUTO_RATTACHES.json'}  ({len(export)} auto-rattachés)")


if __name__ == "__main__":
    main()
