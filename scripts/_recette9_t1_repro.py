"""RECETTE-9 T1 — reproduction du blocage « Programme constructible » du Financier.
Lecture seule (sauf écriture du questionnaire de TEST sous compte_id=None, sur le worktree local).
Usage : PYTHONPATH=src python scripts/_recette9_t1_repro.py <idu>
"""
import sys

from labuse.db import session_factory
from labuse.api.app import parcel_fiche
from labuse import financier_questionnaire as qf
from labuse.exports import builder

idu = sys.argv[1] if len(sys.argv) > 1 else "97411000BD0527"
S = session_factory()
db = S()

fiche = parcel_fiche(idu, db=db, request=None)
pot = fiche.get("potentiel_transformation") or {}
print(f"=== {idu} ===")
print("surface_m2 :", fiche.get("surface_m2"))
print("potentiel_transformation keys :", list(pot.keys()))
print("  surface_vendable_m2 :", pot.get("surface_vendable_m2"))
print("  surface_plancher_m2 :", pot.get("surface_plancher_m2"))
print("  capacite_estimee    :", pot.get("capacite_estimee"))

# Vic remplit : nombre de logements + typologie + les 2 obligatoires
reponses = {
    "logements_vises_saisi": 8,
    "typologie_moyenne_saisi": "T3",
    "prix_sortie_saisi_eur_m2": 4500,
    "regime_tva_saisi": "assujetti_recuperation",
}
qf.enregistrer(db, idu, None, reponses)
db.commit()

ctx = builder._financier_contexte(db, idu, fiche, None)
print("\n--- après saisie logements=8 + typologie=T3 + prix_sortie + TVA ---")
print("program :", ctx.get("program"))
print("manques :", [m["libelle"] for m in ctx.get("manques") or []])
print("bilan établi ?", bool(ctx.get("bilan")))

db.close()
