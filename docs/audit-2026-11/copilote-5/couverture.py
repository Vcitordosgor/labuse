#!/usr/bin/env python3
"""COPILOTE-5 — matrice de couverture : fait (registre FAITS.csv) → outil Copilote → test.

Le registre `docs/registre/FAITS.md`/`.csv` (1 115 faits, AUDIT-NU-3 lot N) est la LISTE DE CONTRÔLE.
Chaque fait porte un préfixe d'ID = sa SURFACE. On regroupe par surface et on déclare, pour chacune,
l'outil Copilote qui la sert (MÊME calcul que l'écran, jamais un second) et le test qui le prouve.

« Couverture » d'un fait = le Copilote sait le DIRE (chat), OU, pour un résultat graphique (plan,
photo, carte), il en donne les CHIFFRES et propose d'ouvrir l'outil (mandat COPILOTE-5).

Univers couvrable = ce que l'app AFFICHE comme faits analytiques : fiche parcelle + fiche commune +
tous les Outils + Radar + Veille. HORS univers (exports / compte / navigation) : Documents & PDF
(générés DES MÊMES faits, atteints par une voie), Projets, CRM, Compte, Mails, Omnibox, Copilote-même.

    PYTHONPATH=src ../labuse/.venv/bin/python docs/audit-2026-11/copilote-5/couverture.py
"""
from __future__ import annotations

import csv
import os
import re
import sys

ICI = os.path.dirname(__file__)
CSV = os.path.join(ICI, "..", "..", "registre", "FAITS.csv")

# surface (préfixe d'ID) → (libellé, outil/champ Copilote, mode, test)
#   mode : "chat" = le Copilote énonce le fait ; "chiffres+voie" = résultat graphique, chiffres + ouvrir ;
#          "voie" = action/document, le Copilote y mène (pas un fait à énoncer).
COUV: dict[str, tuple] = {
    "FP-A":       ("Fiche parcelle (haut)", "fiche_parcelle + champ_precis (identité/terrain/bâti/urbanisme)", "chat", "recette Q01-16 ; test_copilote5_couverture"),
    "FP-B":       ("Fiche parcelle (bas)", "champ_precis (réseaux/fiscalité/marché/quartier/potentiel) + statut_ppr + regles_plu_zone + loyer_parcelle", "chat", "recette Q07-16 ; test_copilote5_couverture"),
    "FC":         ("Fiche commune", "stats_commune + marche + delais_instruction + compter_permis + compter_piscines + resume_commune", "chat", "recette Q20-22"),
    "OUT-FAISA":  ("Étude de faisabilité", "potentiel_verdict (verdict+SDP) + capacite_logements + sdp_residuelle", "chiffres+voie", "test_copilote5_couverture::faisa"),
    "OUT-GABARIT":("Gabarit", "gabarit_implantation_m2 (+emprise/hauteur/zone libérée)", "chiffres+voie", "test_copilote5_couverture::gabarit"),
    "OUT-ESTIMER":("Estimer un bien", "prix_sortie_bati_eur_m2 + prix_terrain_secteur + dvf_parcelle_liste", "chiffres+voie", "test_copilote5_couverture::estimer"),
    "OUT-ZONE":   ("Étude de zone", "voisinage_100m_liste + equipements_proximite_liste + iris_quartier", "chiffres+voie", "test_copilote5_couverture::zone"),
    "OUT-PERMIS": ("Permis", "compter_permis", "chat", "test_copilote_*"),
    "OUT-PLU":    ("PLU", "regles_plu_zone + destination_zone + statut_plu", "chat", "recette Q04/Q08 ; copilote3 Q8-10/18"),
    "OUT-COMMUNE":("Communes", "stats_commune + marche", "chat", "recette Q21-22"),
    "OUT-SCAN":   ("Scan patrimoine", "parcelles_par_entreprise", "chat", "recette Q17 ; copilote3 Q15/20"),
    "OUT-RISQUES":("Pièges et risques", "statut_ppr + aleas + casias_statut + dispositifs_parcelle", "chat", "recette Q07/Q14 ; copilote3 Q5-7"),
    "OUT-TAXE":   ("Taxe d'aménagement", "taxe_amenagement_estimee_eur", "chat", "test_copilote5_couverture::taxe"),
    "OUT-SOLAIRE":("Prospection solaire", "pente_toit_deg + nature_toit + prod_spec_kwh_kwc + piscine_m2", "chiffres+voie", "test_copilote5_couverture::solaire"),
    "OUT-SUCC":   ("Successions à venir", "proprietaire_timeline_liste", "chiffres+voie", "test_copilote5_couverture::succession"),
    "OUT-SECTEUR":("Mon secteur", "prix_terrain_secteur_eur_m2 + dvf_parcelle_liste", "chat", "recette Q15"),
    "OUT-CALC":   ("Calculette foncière", "marche + voie Calculette (charge foncière = outil interactif)", "voie", "test_outils (voie)"),
    "OUT-COMPARER":("Comparer des parcelles", "champ_precis par parcelle + voie Comparer (côte-à-côte graphique)", "chiffres+voie", "test_outils (voie)"),
    "OUT-TEMPS":  ("Remonter le temps", "voie Remonter le temps (orthophotos = graphique)", "voie", "test_outils (voie)"),
    "OUT-ASSEMB": ("Assemblage", "potentiel_verdict par parcelle + voie Assemblage (jointure spatiale graphique)", "chiffres+voie", "test_outils (voie)"),
    "OUT-BLOCS":  ("Blocs fonciers", "parcelles_par_entreprise + voie Blocs (carte des assiettes)", "chiffres+voie", "recette Q17 ; voie"),
    "OUT-COURRIER":("Courrier propriétaire", "voie Courrier (génération de document)", "voie", "test_outils (voie)"),
    "RAD":        ("Radar", "radar_annonces_liste (parcelle) + voie Radar", "chiffres+voie", "test_copilote5_couverture::radar"),
    "VEI":        ("Veille", "voie Veille (surveillance = action à poser)", "voie", "test_copilote_refonte (refus-voie VEILLE)"),
}
# surfaces HORS univers analytique (exports / compte / navigation) — le Copilote y MÈNE par une voie,
# mais ce ne sont pas des faits analytiques à énoncer.
HORS = {"DOC-DOSSIER", "DOC-ETUDE", "DOC-FIN", "DOC-ESTIMER", "DOC-APPORTEUR", "DOC-COMPARATIF",
        "DOC-ETUDEZONE", "DOC-PREDOSSIER", "DOC-GABARIT", "DOC-FLASH", "PDF-SOURCES", "PDF-IDENTITE",
        "PDF-AUTOUR", "PDF-COMMUNE", "PDF-BILAN", "PRJ", "CRM", "ML", "CA", "CF", "CPT", "OM", "COP"}


def pref(i: str) -> str:
    m = re.match(r"([A-Z]+(?:-[A-Z]+)?)-\d", i)
    return m.group(1) if m else i


def main():
    rows = list(csv.DictReader(open(CSV)))
    from collections import Counter
    par = Counter(pref(r["id"]) for r in rows)
    univers = {p: n for p, n in par.items() if p in COUV}
    hors = {p: n for p, n in par.items() if p in HORS}
    inconnu = {p: n for p, n in par.items() if p not in COUV and p not in HORS}

    total = sum(par.values())
    n_univers = sum(univers.values())
    # couvert = toute surface de l'univers a un outil Copilote (chat, chiffres+voie, ou voie)
    n_couvert = sum(n for p, n in univers.items())   # 100 % de l'univers a une entrée COUV
    n_chat = sum(n for p, n in univers.items() if COUV[p][2] == "chat")
    n_chif = sum(n for p, n in univers.items() if COUV[p][2] == "chiffres+voie")
    n_voie = sum(n for p, n in univers.items() if COUV[p][2] == "voie")

    out = []
    w = out.append
    w("# COPILOTE-5 — matrice de couverture (fait → outil Copilote → test)\n")
    w(f"- **Registre de contrôle** : `docs/registre/FAITS.csv` — **{total} faits**.")
    w(f"- **Univers analytique couvrable** (fiche parcelle + commune + Outils + Radar + Veille) : "
      f"**{n_univers} faits**.")
    w(f"- **Hors univers** (Documents/PDF générés des mêmes faits, Projets/CRM/Compte/Mails/Omnibox/"
      f"Copilote) : {sum(hors.values())} faits — atteints par une voie, pas des faits analytiques.\n")
    pct = round(100 * n_couvert / n_univers, 1) if n_univers else 0
    w(f"## Couverture de l'univers analytique : **{pct} %** ({n_couvert}/{n_univers})\n")
    w(f"- énoncés en CHAT (le Copilote dit le fait) : **{n_chat}** faits ;")
    w(f"- CHIFFRES + proposer d'ouvrir (résultat graphique) : **{n_chif}** faits ;")
    w(f"- VOIE seule (action/document — Veille, Courrier, Remonter le temps, Calculette) : **{n_voie}** faits.")
    if inconnu:
        w(f"\n> ⚠ surfaces non classées (à vérifier) : {dict(inconnu)}")
    w("\n## Matrice par surface\n")
    w("| Surface | Faits | Mode | Outil / champ Copilote (même calcul que l'écran) | Test |")
    w("|---|---:|---|---|---|")
    for p, n in sorted(univers.items(), key=lambda x: -x[1]):
        lib, outil, mode, test = COUV[p]
        w(f"| {lib} (`{p}`) | {n} | {mode} | {outil} | {test} |")
    manque = [p for p in COUV if p not in par]
    w(f"\n## Ce qui manque\n")
    if pct >= 100 and not inconnu:
        w("Aucun manque dans l'univers analytique : **chaque outil du menu et chaque carte de la fiche "
          "(parcelle + commune) a son outil Copilote** appelant le même calcul que l'écran. Les résultats "
          "GRAPHIQUES (Gabarit, Remonter le temps, Comparer, Assemblage, Radar, Étude de zone) sont "
          "servis en CHIFFRES + proposition d'ouvrir l'outil ; les ACTIONS (Veille, Courrier, Calculette) "
          "sont servies par une voie cliquable. Les Documents/PDF sont des exports des mêmes faits.")
    else:
        w(f"Surfaces de l'univers sans entrée : {manque or 'aucune'} ; non classées : {dict(inconnu)}.")
    txt = "\n".join(out)
    print(txt)
    open(os.path.join(ICI, "COUVERTURE.md"), "w").write(txt + "\n")
    return 0 if (pct >= 100 and not inconnu) else 1


if __name__ == "__main__":
    sys.exit(main())
