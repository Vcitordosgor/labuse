#!/usr/bin/env python
"""COMPTE-2 · Lot 2 — envoi RÉEL des 16 templates, par la file, vers la SEULE adresse autorisée.

À jouer À LA MAIN, avec l'accord de Vic (le harnais bloque l'envoi sortant automatique) :

    cd ~/Desktop/labuse-compte
    . ~/Desktop/labuse/.venv/bin/activate
    PYTHONPATH=$PWD/src SSL_CERT_FILE=/etc/ssl/cert.pem python scripts/recette_compte2_envoi.py

Règle dure (mandat) : destinataire UNIQUE, jamais une autre adresse. Un envoi par template. La sortie
imprime les seize message-id (à coller au compte-rendu). Passe `contactlabuse` en argument pour viser
l'autre adresse autorisée.
"""
from __future__ import annotations

import sys
import time

from labuse import brevo, mailfile
from labuse.db import engine

AUTORISEES = {"victor": "victorlaganepro@gmail.com", "contactlabuse": "contactlabuse@gmail.com"}


def main() -> int:
    cible = sys.argv[1] if len(sys.argv) > 1 else "victor"
    if cible not in AUTORISEES:
        print(f"cible inconnue : {cible!r} (attendu : {', '.join(AUTORISEES)})")
        return 2
    dest = AUTORISEES[cible]
    assert dest in AUTORISEES.values(), "garde-fou : adresse non autorisée"

    base = "https://app.labuse.immo"
    P = {
        "essai": {"PRENOM": "Victor", "EMAIL": dest, "MDP_PROVISOIRE": "Ab3-9xKp2Q",
                  "FIN_ESSAI": "le 12/09/2026 à 18h00 (heure Réunion)"},
        "souscription": {"PRENOM": "Victor", "LIEN_SOUSCRIPTION": f"{base}/souscrire?t=demo"},
        "onboarding1": {"PRENOM": "Victor", "EMAIL": dest, "MDP_PROVISOIRE": "Ab3-9xKp2Q"},
        "onboarding2": {"PRENOM": "Victor", "JAMAIS_CONNECTE": True},
        "onboarding3": {"PRENOM": "Victor"},
        "relance_carte": {"PRENOM": "Victor", "LIEN_PAIEMENT": f"{base}/facturation"},
        "suspension": {"PRENOM": "Victor", "LIEN_PAIEMENT": f"{base}/facturation"},
        "retablissement": {"PRENOM": "Victor"},
        "radar_digest": {"PRENOM": "Victor", "DATE": "jeudi 11 septembre 2026", "NB_BIENS": 7,
                         "CARTES": "<p>974 411 000 AB 0123 — Saint-Paul, 812 m²</p>"},
        "radar_alerte": {"PRENOM": "Victor", "VEILLE": "Saint-Denis · terrains &gt; 800 m²",
                         "NB_BIENS": 3, "CRITERES": "Saint-Denis, &gt; 800 m², zone U",
                         "CARTES": "<p>974 411 000 CD 0456 — 905 m²</p>"},
        "mdp_oublie": {"PRENOM": "Victor", "LIEN_RESET": f"{base}/reset?token=demo", "VALIDITE": "1 heure"},
        "mdp_modifie": {"PRENOM": "Victor", "DATE_HEURE": "le 07/09/2026 à 21h40 (heure Réunion)"},
        "resiliation": {"PRENOM": "Victor", "DATE_FIN_ACCES": "le 30/09/2026"},
        "flash_pret": {"LIEN_PDF": f"{base}/flash/demo.pdf", "VALIDITE": "48 heures",
                       "IDU": "974 411 000 AB 0123", "COMMUNE": "Saint-Paul"},
        "email_change": {"PRENOM": "Victor", "ANCIEN_EMAIL": "ancien@labuse.test", "NOUVEL_EMAIL": dest},
        "retour_traite": {"PRENOM": "Victor",
                          "SON_MESSAGE": "La surface résiduelle semble fausse sur cette parcelle.",
                          "REPONSE": "Corrigé — résiduel bâti non déduit. Merci du signalement."},
    }
    assert set(P) == set(brevo.REGISTRE), set(P) ^ set(brevo.REGISTRE)

    mailfile.ensure_tables(engine())
    print(f"Envoi des 16 vers {dest} (par la file mail_queue)…\n")
    print(f"{'ID':>3}  {'clé':<15} {'état':<10} message-id / raison")
    recu = 0
    for key in brevo.REGISTRE:                       # ordre 4→19
        r = mailfile.envoyer_mail(engine(), key=key, to=dest, params=P[key],
                                  compte_id=None, demandeur="job:compte2-recette",
                                  dedup=f"recette:{cible}:{key}")
        recu += (r.get("etat") == "recu")
        print(f"{brevo.template_id(key):>3}  {key:<15} {r.get('etat'):<10} "
              f"{r.get('message_id') or r.get('erreur')}")
        time.sleep(0.4)
    print(f"\n{recu}/16 reçus par Brevo → {dest}")
    return 0 if recu == 16 else 1


if __name__ == "__main__":
    raise SystemExit(main())
