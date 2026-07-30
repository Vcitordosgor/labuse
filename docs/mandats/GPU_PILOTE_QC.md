# GPU-PILOTE — CONTRÔLE QUALITÉ des planchers de densité (30/07)

> Re-scan de TOUTES les communes avec les 5 formulations de plancher (les « angles morts » du 1er
> passage), pour rattraper les planchers ratés par un scan « log/ha » seul. Avant le diff final.

## Les 5 angles morts du scan (recensés)
1. **Nom de dossier OAP** : `5_OAP` vs `5_Orientations_amenagement` (Saint-Denis).
2. **Plancher en TABLEAU** (colonnes « Densité minimale exigée ») — Entre-Deux.
3. **OAP GRAPHIQUE** (image, texte nul) — La Plaine, Cilaos (nécessite poppler/OCR).
4. **Format DEUX COLONNES** du règlement (Règles | Explication) — Saint-Benoît.
5. **Formulation** « X logements minimum PAR HECTARE » (≠ « X log/ha ») — Sainte-Suzanne, Les Avirons,
   Sainte-Rose. + variante « X ou équivalents-logements par hectare » (Le Tampon).

## Résultat — 2 FAUX NÉGATIFS corrigés
| commune | 1er passage | QC (corrigé) | source |
|---|---|---|---|
| **Les Avirons** | « aucun plancher » | **AUa/AUc 30, AUd 20 log/ha** | règlement p.26 |
| **Sainte-Rose** | « aucun plancher » | **20 log/ha (10 rural Bois Blanc)** | règlement p.55-56 |

Les deux étaient des entrées **compactes du Packet A** (1er passage rapide) — c'est là que le risque
était concentré.

## Conclusions CONFIRMÉES (pas de miss)
L'Étang-Salé 50/30/15 · Saint-Leu 30/15 · Sainte-Marie 50/25/25 · Saint-Pierre 50/60/80 ·
Les Trois-Bassins 35/30/20 · La Possession 30/50 · Le Port 50 · Bras-Panon 30/50 (TCSP) ·
Entre-Deux 20 (table) · Sainte-Suzanne 10/20/30 · Le Tampon 20/10 (c/d, phrasé « équivalents ») ·
Saint-Louis 30/50. **Sans plancher confirmé** : Saint-Paul (délégué PLH), Petite-Île (qualitatif),
Cilaos, Saint-Denis.

## Non vérifiables au QC (limites)
- **Saint-Benoît** : règlement DEUX COLONNES + PDF Desktop devenus inaccessibles → planchers
  `a_verifier` (poppler/OCR requis).
- **La Plaine, Cilaos** : OAP GRAPHIQUE (image) → `a_verifier` (poppler requis).
- **Saint-Louis, Salazie** : dossiers `Downloads` éphémères disparus → re-scan impossible (densités
  déjà captées au 1er passage : Saint-Louis 30/50 ; Salazie clause par zone `a_verifier`).
- **Saint-Joseph** : périmé, à la corbeille.

## Verdict
Le QC multi-formulation était indispensable : **2 corrections sur ~22 communes** (les 2 entrées
compactes non re-lues). Toutes les calibrations au format complet (lues soigneusement) ont tenu.
**Reste bloqué par l'OUTIL** (poppler) : Saint-Benoît (2 colonnes), La Plaine + Cilaos (OAP image).
