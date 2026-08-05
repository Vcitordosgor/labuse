# M32 — Bilan des ré-extractions (file des partielles, 9/9)

Arbitrage Vic (a) : ré-extraction sur la **version OPPOSABLE GPU uniquement**, idurba + date
d'approbation ancrés. Toutes les archives re-téléchargées du GPU (data.geopf.fr), règlement + OAP
relus au texte. Limites v1 respectées (graphique/scanné = `non_extrait`, jamais deviné).

## Les 9 ré-extractions (par ordre de traitement)

| # | Commune | Opposable | Densité (confirmée/résolue) | Apport de la ré-extraction |
|---|---|---|---|---|
| 1 | Saint-Louis (97414) | 20251218 | OAP 30/50 log/ha | **écart de version LEVÉ** (opposable = 20250926) |
| 2 | Le Port (97407) | 20241209 | OAP 50 log/ha | **annulation lue** : Uppp/Up2 seul, AU intactes → **VALIDE** |
| 3 | Petite-Île (97405) | 20230609 | densité = objectif SAR (pas de plancher dur) | **`a_verifier` ouverture LEVÉ** (1AU opé. d'ens., 2AU phasage) |
| 4 | Sainte-Suzanne (97420) | 20250929 | OAP 10/20/30 log/ha par site | **2AU date-butoir 2031** (nouveau) |
| 5 | Les Avirons (97401) | 20241206 | règlt 30/30/20 log/ha (AUa/AUc/AUd) | **correction** : OAP porte le social par site (47 LLS…) |
| 6 | La Plaine (97406) | 20230527 | 10 LLS/opération | confirmé ; OAP graphique → `non_extrait` (limite v1) |
| 7 | Sainte-Rose (97419) | 20190504 | 20 log/ha (10 rural Bois Blanc) | confirmé ; phasage 2AU→1AU |
| 8 | Salazie (97421) | 20220524 | **20/20/10 log/ha (AUa/AUb/AUc)** | **densité a_verifier LEVÉE** ; social OAP 50% |
| 9 | Bras-Panon (97402) | 20260428 | 30/20/10 log/ha + modulation TCSP | confirmé (ouverture→modif PLU) |

## Ce que la campagne a produit (au-delà de « confirmer »)

- **3 questions ouvertes résolues** : écart de version (Saint-Louis), `a_verifier` ouverture
  (Petite-Île), valeurs de densité `a_verifier` (Salazie).
- **1 blocage levé** : Le Port — portée d'annulation lue (jugements TA 1900330 + CAA 22BX01470),
  limitée au secteur Uppp/Up2 (concession portuaire), **AU intactes** ; 0 parcelle Up/Uppp servie
  en tête → aucun effet servi. Le Port passe candidat Phase C.
- **1 correction** : Les Avirons — l'OAP porte bien le social par site (le 30/07 disait « sans »).
- **2 découvertes de limite v1 consignées** : 2ᵉ date-butoir (Sainte-Suzanne 2031, après Sainte-Marie) ;
  dépendances de phasage inter-zones (Petite-Île, Sainte-Rose, Bras-Panon).

## Limites v1 (jamais approximées, consignées yaml)

- **Densité PAR SITE** = calque graphique OAP → `non_extrait` au site près ; la valeur globale (log/ha)
  est servie, pas la ventilation site.
- **OAP tout-image** (La Plaine) → `non_extrait` (poppler/OCR NON, par décision Vic : un calque se lit
  à l'œil ou pas du tout).
- **Dépendance inter-zones** et **date-butoir** : non portées par le schéma `au_ouverture` v1.

## État de la file Phase A

- **9 partielles : ré-extraites** (ce bilan). Écarts/vigilances soldés (Le Port validé, Salazie/
  Petite-Île/Saint-Louis résolus).
- **8 exhaustives** (Entre-Deux, L'Étang-Salé, La Possession, Saint-Leu, Saint-Pierre, Sainte-Marie,
  Le Tampon, Les Trois-Bassins) : déjà sourcées → **candidates à l'intégration moteur Phase C**.
- **3 scans négatifs** (Saint-Denis, Saint-Joseph, Cilaos) : `sans_objet` consigné.
- **Saint-Philippe** RNU · **Saint-André** attente opposabilité · **Saint-Benoît** 19 fiches → v2.

**Rien n'est intégré au moteur `au_ouverture_planchers.yaml`** : l'intégration est un geste de
**rebuild (Phase C)**, sur **GO Vic explicite** uniquement.
