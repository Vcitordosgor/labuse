# COHERENCE-1 lot H — sémantique (« un mot = un sens »), scan du 28/09/2026

## Seuils faible/moyen/fort
UNE définition front (`frontend/src/lib/status.ts:134-138`, signal de mutation) ; seuils
de calcul centralisés back (`src/labuse/pige/signaux.py:19-29` : SEUIL_N=5,
SOUS_MARCHE=−15 %, REF_TYPE=30, REF_LOCAL=8). Bandes A/B/C/D/0/NC distinctes
(status.ts:116-123). **Pas de double définition trouvée** — sain.

## « Secteur » — la vraie faille sémantique (confirmée par le banc, 85/120 parcelles)
- Fiche `dvf_parcelle.secteur` : fenêtre 2021-2025, médiane locale.
- Outil Mon secteur : rayon ADAPTATIF 500→1000→1500 m→commune, `MIN_N_SECTEUR=8`,
  5 % extrêmes exclus (`src/labuse/faisabilite/bilan.py:109-117`) — rayons AFFICHÉS dans
  l'outil, PAS dans le tableau comparateur (`blocB.tsx:141-142` : la colonne « Prix ancien »
  = commune entière n≥100, le tooltip avoue « c'est normal qu'il diffère »).
- Mesure banc : BZ1065 maison 3 494 (fiche) vs 3 821 €/m² (Mon secteur) — deux « secteurs »
  sans rayon dans le libellé de la fiche. Gravité ÉTIQUETTE (chiffres justes, périmètres
  non nommés côte à côte).
- `voisinage_proche` (100 m) et `secteur_lieu_dit` (600 m) : rayons dits — sains.

## Badges Sourcé/Estimé/Dérivé (`primitives.tsx:368`)
- Azimut du bâti (Prospection solaire, `ProspectionSolaire.tsx:333`) : badge « Estimé »
  alors que l'orientation vient du bâti mesuré (dérivée LiDAR/BD TOPO) — étiquette à
  instruire (OUTILS-S1 avait tranché conf. basse : vérifier la cohérence avec ce choix).
- Hauteur LiDAR `hauteur_nature='sourcé'` : conforme (mesuré).

## Millésimes EN DUR dans le front (risque de mensonge à la prochaine mise à jour)
- `ProspectionSolaire.tsx:167` « IGN FLAIR et CoSIA, 2025 » ;
- `EtudeZone.tsx:570` « OLL 2024 » ;
- `frontend/src/lib/layers.ts:109` « ANCT — quartiers de génération 2024 ».
(Le reste lit `millesime` dynamique — sain.)

## Mots à plusieurs sens
- « opportunité » : palier de classement / bloc scoring « M opportunités » / bien Radar
  actif — trois acceptions sans définition UI unique.
- « constructible » : zone U vs potentiel constructible vs morceau constructible du
  gabarit — contextes distincts mais clairs ; « zone bleue » : UNE définition
  (`servitudes.py:257-261`) — sain ; « non modélisé » : trois contextes, pas de lexique.

## Formats
Virgule décimale systématique via `format.ts` — aucun mélange détecté.

## ANOMALIES retenues pour le rapport
1. ÉTIQUETTE — « secteur » à périmètres multiples non nommés (fiche vs Mon secteur vs
   comparateur) — mesuré 85/120.
2. ÉTIQUETTE — azimut bâti badgé « Estimé » (source mesurée).
3. ÉTIQUETTE — 3 millésimes en dur (FLAIR/CoSIA 2025, OLL 2024, ANCT 2024).
4. COSMÉTIQUE — « opportunité » polysémique ; « non modélisé » sans définition unique.
5. (Recoupe ABSENCES-FRONT) trois idiomes d'absence : « — » vs « n.c. » vs « non chiffré ».
