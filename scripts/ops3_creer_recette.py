#!/usr/bin/env python3
"""OPS-3 (C) — crée (ou met à jour) le COMPTE DE RECETTE dédié de la vérité permanente.

« Pas d'instance sans authentification » : les lots A/B/F de `verite_permanente` s'authentifient
avec ce compte. Compte NON administrateur (un vrai client), plan INTÉGRAL, statut ACTIF, titulaire.
Idempotent : si l'email existe déjà, on le remet au vert (plan intégral, actif) et on (ré)installe
le mot de passe fourni. Le mot de passe n'est JAMAIS écrit en clair ni commité — il vient de
l'argument `--password` ou de l'env `LABUSE_RECETTE_PASSWORD`.

    PYTHONPATH=src python scripts/ops3_creer_recette.py \
        --email victorlaganepro+recette@gmail.com --password "$LABUSE_RECETTE_PASSWORD"
"""
from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import text

from labuse import comptes
from labuse.config import get_settings
from labuse.db import session_scope

RECETTE_EMAIL = "victorlaganepro+recette@gmail.com"


def creer_ou_mettre_a_jour(db, email: str, password: str) -> dict:
    """Crée le compte de recette (plan intégral, actif, titulaire) ou le remet au vert. Renvoie un
    petit état {utilisateur_id, compte_id, cree: bool}."""
    comptes.ensure_tables(db)
    email = comptes._norm_email(email)
    h = comptes._ph.hash(password)
    cgv_v = get_settings().cgv_version
    u = db.execute(text("SELECT id, compte_id FROM utilisateurs WHERE email = :e"),
                   {"e": email}).mappings().first()
    if u:
        uid, cid = int(u["id"]), int(u["compte_id"])
        db.execute(text("UPDATE utilisateurs SET hash = :h, statut = 'actif', role = 'titulaire', "
                        "cgv_acceptees_at = COALESCE(cgv_acceptees_at, now()), cgv_version = :v, "
                        "updated_at = now() WHERE id = :i"), {"h": h, "v": cgv_v, "i": uid})
        db.execute(text("UPDATE comptes SET plan = 'integral', statut = 'actif', "
                        "essai_expire_at = NULL, paiement_requis_at = NULL, acces_fin_at = NULL, "
                        "updated_at = now() WHERE id = :c"), {"c": cid})
        db.commit()
        return {"utilisateur_id": uid, "compte_id": cid, "cree": False}
    cid = db.execute(text(
        "INSERT INTO comptes (nom, plan, statut, sieges) "
        "VALUES ('LABUSE (recette)', 'integral', 'actif', 1) RETURNING id")).scalar()
    uid = db.execute(text(
        "INSERT INTO utilisateurs (compte_id, email, hash, role, statut, cgv_acceptees_at, cgv_version) "
        "VALUES (:c, :e, :h, 'titulaire', 'actif', now(), :v) RETURNING id"),
        {"c": cid, "e": email, "h": h, "v": cgv_v}).scalar()
    comptes.audit(db, "recette_cree", cid, uid, "compte de recette vérité-permanente (OPS-3)")
    db.commit()
    return {"utilisateur_id": int(uid), "compte_id": int(cid), "cree": True}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default=os.environ.get("LABUSE_RECETTE_EMAIL") or RECETTE_EMAIL)
    ap.add_argument("--password", default=os.environ.get("LABUSE_RECETTE_PASSWORD"))
    args = ap.parse_args()
    if not args.password:
        print("ERREUR : mot de passe absent (--password ou LABUSE_RECETTE_PASSWORD).", file=sys.stderr)
        return 2
    with session_scope() as db:
        etat = creer_ou_mettre_a_jour(db, args.email, args.password)
    print(f"compte de recette {'CRÉÉ' if etat['cree'] else 'mis à jour'} : "
          f"{args.email} (compte {etat['compte_id']}, utilisateur {etat['utilisateur_id']}, "
          f"plan intégral, actif)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
