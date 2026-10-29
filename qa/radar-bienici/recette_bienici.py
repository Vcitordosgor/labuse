"""RADAR-SOURCES-2 — RECETTE Bien'ici, LECTURE SEULE sur la base servie `labuse`.

Mesure, sur la capture réelle `ECH-BIENICI-1.json` (100 annonces de vente, La Réunion) :
  1. combien d'annonces sont lues et dans le périmètre des 24 communes ;
  2. la présence de chaque champ par annonce (contrat du traducteur) ;
  3. **le taux de biens rattachés à une parcelle** — le résultat le plus important du mandat —, en
     appelant la cascade `rattachement_html.rattacher` (SELECT uniquement) contre les 434 582 parcelles ;
  4. combien d'annonces Bien'ici **fusionnent** avec un bien déjà en base (Leboncoin) via
     `html_ingest.bien_meme_physique` (`_est_meme_bien`, portail-agnostique) — SELECT uniquement.

AUCUNE ÉCRITURE : ni ingestion, ni rattachement posé. On appelle les fonctions de calcul directement.
Lancer : LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@/labuse PYTHONPATH=src python qa/radar-bienici/recette_bienici.py
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

from labuse.db import session_scope
from labuse.pige import html_ingest, html_next, rattachement_html
from labuse.pige.intake import resoudre_commune

ECH = Path(__file__).resolve().parent / "ECH-BIENICI-1.json"

CHAMPS = ("prix", "prix_m2", "surface_hab", "surface_terrain", "pieces", "chambres", "type",
          "commune", "zipcode", "district", "lat", "lng", "annee_construction", "dpe_classe",
          "owner_type", "first_publication_date")


def main() -> None:
    recs = html_next.analyser(ECH.read_text(encoding="utf-8"))["records"]
    print(f"Annonces lues : {len(recs)}")

    # 1 & 2 — périmètre + présence des champs
    dans = [r for r in recs if resoudre_commune(r["commune"])]
    print(f"Dans le périmètre (24 communes) : {len(dans)}/{len(recs)}  "
          f"(hors : {len(recs) - len(dans)})")
    print("\nPrésence des champs (sur les 100) :")
    for c in CHAMPS:
        n = sum(1 for r in recs if r.get(c) not in (None, ""))
        print(f"  {c:<22} {n:3d}/100")

    with session_scope() as db:
        # 3 — rattachement (lecture seule)
        etats = collections.Counter()
        niveaux = collections.Counter()
        rattaches = []
        for r in dans:
            res = rattachement_html.rattacher(db, r)
            etats[res["etat"]] += 1
            if res["etat"] == "rattachee":
                niveaux[res["niveau"]] += 1
                rattaches.append((r, res))
        print("\n== RATTACHEMENT (lecture seule, 434 582 parcelles) ==")
        for e, n in etats.most_common():
            print(f"  {e:<16} {n:3d}")
        print(f"  niveaux rattachés : {dict(niveaux)}")
        n_rat = etats.get("rattachee", 0)
        print(f"  → TAUX RATTACHÉ : {n_rat}/{len(dans)} = {100*n_rat/max(1,len(dans)):.1f} %")
        # détail des rattachements (preuve : critères convergents)
        for r, res in rattaches[:12]:
            crit = "+".join(sorted(c["critere"] for c in res["criteres"]))
            print(f"    · {r['commune']:<14} {r['type']:<11} {str(r.get('surface_terrain') or r.get('surface_hab')):>6} m²"
                  f"  → {res['idu']}  [{res['niveau']}/{crit} conf={res['confiance']}]")

        # type non rattachable (appartement = copro) : combien d'annonces concernées ?
        appart = sum(1 for r in dans if r["type"] == "appartement")
        rattachables = len(dans) - appart
        print(f"  (dont {appart} appartements — non rattachables par nature ; "
              f"assiette rattachable = {rattachables})")
        if rattachables:
            print(f"  → taux sur rattachables (maison/terrain/immeuble) : "
                  f"{n_rat}/{rattachables} = {100*n_rat/rattachables:.1f} %")

        # 4 — fusions avec un bien déjà en base (Leboncoin)
        print("\n== DÉDOUBLONNAGE INTER-PORTAILS (lecture seule) ==")
        base_biens = db.execute(
            __import__("sqlalchemy").text(
                "SELECT count(*) FROM pige_biens")).scalar()
        print(f"  biens déjà en base : {base_biens} (tous Leboncoin)")
        fusions = []
        for r in dans:
            meme = html_ingest.bien_meme_physique(db, r["commune"], r)
            if meme is not None:
                fusions.append((r, meme))
        print(f"  annonces Bien'ici qui FUSIONNENT avec un bien existant : {len(fusions)}/{len(dans)}")
        for r, bid in fusions[:15]:
            print(f"    · bien #{bid}  ← {r['commune']} {r['type']} "
                  f"{r.get('surface_hab') or r.get('surface_terrain')} m² {r['prix']} €")


if __name__ == "__main__":
    main()
