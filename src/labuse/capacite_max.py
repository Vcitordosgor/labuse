"""FIX-PRIX-ET-OPPORTUNITES (lot 3) — la capacité constructible est un MAXIMUM réglementaire.

Suite de VERITE-TERRAIN-2 volet D : face à 6 601 permis réellement autorisés post-PLU, la capacité
servie par LABUSE (SDP max du gabarit, logements estimés) est un PLAFOND — les projets déposés en
utilisent **en médiane environ la moitié** :

  · ratio médian autorisé / LABUSE = **0,46 en surface de plancher**, **0,40 en logements**.

Partout où une capacité constructible (SDP, logements) est affichée — fiche, Gabarit, exports,
Copilote — on le dit : c'est le maximum que la parcelle peut porter selon les règles, pas le programme
qui sera déposé. Mention courte et vraie, fondée sur la mesure (jamais « cette parcelle fera N logements »).

POINT DE TEXTE UNIQUE (Python). Miroir TypeScript : `frontend/src/lib/capaciteMax.ts` — à garder synchrone.
"""
from __future__ import annotations

#: ratios médians mesurés autorisé / capacité LABUSE (volet D). ≈ « la moitié ».
RATIO_MEDIAN_SDP = 0.46
RATIO_MEDIAN_LOGEMENTS = 0.40

#: mention complète (survol / détail / PDF / Copilote).
MENTION = (
    "Maximum réglementaire (gabarit) : le total que la parcelle peut porter selon les règles, pas le "
    "programme qui sera déposé. Face aux permis réellement autorisés (volet D VERITE-TERRAIN-2), les "
    "projets en utilisent en médiane environ la moitié (0,46 en surface, 0,40 en logements)."
)
#: mention courte (chip / inline).
MENTION_COURTE = "maximum réglementaire — les permis réels en utilisent ~½ en médiane (volet D)"

# LOGEMENTS-SOURCE-UNIQUE (décision Vic 18/10/2026, généralisée) — le NOMBRE de logements n'est
# plus jamais tiré de l'ancien calcul de capacité (`estimate_capacity` : SDP ÷ logement moyen) :
# seul le moteur d'implantation de l'Étude de faisabilité compte des logements (dessinés, contrôlés).
# PARTOUT où une surface affichait ce nombre (fiche, Comparatif, Dossier, Financier, Flash,
# Copilote, Assemblage, calculette), elle imprime CE renvoi — un seul texte, le même que la fiche.
#: renvoi unique (valeur de ligne) — « Nombre de logements : voir l'Étude de faisabilité ».
RENVOI_ETUDE = "voir l'Étude de faisabilité"
#: renvoi en phrase (prose Copilote / notes).
RENVOI_ETUDE_PHRASE = "nombre de logements : voir l'Étude de faisabilité"
