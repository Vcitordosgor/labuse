#!/usr/bin/env python
"""M130-6 §D — Génère (de façon REPRODUCTIBLE) les 4 projets de QA du PDF projet et leurs PDF.

À exécuter chez Vic (Python 3.11, conda `labusedb`, la variable d'env de connexion PostgreSQL
habituelle de labuse doit être posée) :

    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
    LABUSE_DATABASE_URL="postgresql+psycopg://<user>@localhost:5432/labuse" \
    python qa/m130/generer_pdf_qa.py

Ce que le script fait, à partir d'une base où les projets N'EXISTENT PAS ENCORE :
  - (re)crée les 4 projets de QA (idempotent : supprime d'abord ceux du même nom) ;
  - fige les cadrages figeables (P1/P2/P3) avec une DATE DE FIGEAGE DÉTERMINISTE ;
  - laisse P4 SANS figeage ;
  - écrit les 4 PDF dans qa/m130/ sous le préfixe M130-6- ;
  - affiche les `pid` créés (visibles ensuite dans GET /projets pour le compte utilisé).

Les projets sont PERSISTÉS (aucun rollback) : ils restent dans la base et dans l'application.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# --- repo sur le path (src/) ---
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

from sqlalchemy import text  # noqa: E402

from labuse import models  # noqa: E402
from labuse.api.pdf_projet import render_projet_pdf  # noqa: E402
from labuse.api.projets import _figer_shortlist, _projet_dict, _shortlist_pdf  # noqa: E402
from labuse.db import session_scope  # noqa: E402

# Date de figeage DÉTERMINISTE (reproductibilité : même rendu d'un run à l'autre).
FIGE_LE = datetime(2026, 8, 22, tzinfo=timezone.utc)
OUT = _ROOT / "qa" / "m130"

# nom → (cadrage, identité, figer ?). Noms préfixés « QA M130 » pour un nettoyage idempotent.
PROJETS = [
    ("QA M130 · P1 large île", {}, {"type_logement": "logements"}, True),
    ("QA M130 · P2 étroit Tampon",
     {"communes": ["Le Tampon"], "surfaceMin": 3000},
     {"type_logement": "logements", "budget_eur": 800000}, True),
    ("QA M130 · P3 écartées Saint-Pierre",
     {"communes": ["Saint-Pierre"], "tiers": ["ecartee"]}, {"type_logement": "logements"}, True),
    ("QA M130 · P4 non figé", {"communes": ["Le Tampon"]}, {"type_logement": "logements"}, False),
]
# préfixe versionné du mandat courant (bump à chaque itération M130-x)
PREFIXE = "M130-11"
FICHIER = {
    "QA M130 · P1 large île": f"{PREFIXE}-projet-P1-large-ile.pdf",
    "QA M130 · P2 étroit Tampon": f"{PREFIXE}-projet-P2-etroit-tampon.pdf",
    "QA M130 · P3 écartées Saint-Pierre": f"{PREFIXE}-projet-P3-ecartees-stpierre.pdf",
    "QA M130 · P4 non figé": f"{PREFIXE}-projet-P4-non-fige.pdf",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with session_scope() as db:
        compte_id = db.execute(text(
            "SELECT compte_id FROM projets WHERE compte_id IS NOT NULL "
            "ORDER BY id LIMIT 1")).scalar()   # rattache la QA au 1er compte réel (visible dans l'app)
        # nettoyage idempotent : on repart d'un état propre pour ces 4 noms
        noms = [n for n, *_ in PROJETS]
        anciens = [r[0] for r in db.execute(text(
            "SELECT id FROM projets WHERE nom = ANY(:noms)"), {"noms": noms}).all()]
        if anciens:
            db.execute(text("DELETE FROM projet_parcelles WHERE projet_id = ANY(:ids)"), {"ids": anciens})
            db.execute(text("DELETE FROM projets WHERE id = ANY(:ids)"), {"ids": anciens})
            db.flush()
        pids = {}
        for nom, cadrage, identite, figer in PROJETS:
            p = models.Projet(compte_id=compte_id, nom=nom, filtres=cadrage, identite=identite)
            db.add(p)
            db.flush()
            pids[nom] = p.id
            if figer:
                _figer_shortlist(db, p, None)
                p.derniere_execution_at = FIGE_LE          # date DÉTERMINISTE (écrase le now() du figeage)
                db.flush()
            pdf = render_projet_pdf(_projet_dict(p), _shortlist_pdf(db, p))
            (OUT / FICHIER[nom]).write_bytes(pdf)
        db.flush()   # PERSISTÉ : session_scope commit à la sortie (aucun rollback)

    print("Projets de QA (re)créés et PDF générés dans qa/m130/ :")
    for nom, *_ in PROJETS:
        print(f"  pid {pids[nom]:>5}  ·  {nom}  →  {FICHIER[nom]}")
    print(f"\nCompte rattaché : compte_id={compte_id}. Visibles dans GET /projets pour ce compte.")
    print("Date de figeage déterministe :", FIGE_LE.date().isoformat())


if __name__ == "__main__":
    main()
