"""CALCULS-AUDIT-1 lot B — le RECALCUL INDÉPENDANT.

Chaque calcul du back qui produit un chiffre servi est ré-implémenté ICI, à la main, à
partir des ENTRÉES BRUTES (tables de base, géométrie), SANS importer une seule ligne du
code de production (`labuse.faisabilite`, `labuse.gabarit`, `labuse.registre`…). La valeur
recalculée est comparée à la valeur SERVIE (fiche JSON ou table de résultat) : une formule
fausse dans le back est fausse partout pareil — cohérente, donc invisible au banc de
COHERENCE-1 ; seul un recalcul indépendant la voit.

Rejoué sur deux corpus :
  · l'échantillon gelé de COHERENCE-1 (120 parcelles, 24 communes) ;
  · des cas limites construits (socle.CasLimites) : 0, absence, minuscule, géante, à cheval,
    bâti > emprise, hauteur LiDAR absente, AU fermée, « non réglementé », prix sans vente,
    taux de TA majoré, multi-propriétaires.

Sortie : docs/audit-2026-09/CALCULS-1/ECARTS-CALCUL.csv.
"""
