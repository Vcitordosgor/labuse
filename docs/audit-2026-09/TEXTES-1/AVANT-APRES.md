# TEXTES-1 — capture avant / après (témoins)

Les textes corrigés sont des libellés/bulles générés par parcelle ou commune (tooltips PEB/EBC/SIS,
encarts fiscaux) : la capture d'écran dépend d'une parcelle porteuse de l'attribut. On documente ici
le **avant → après** verbatim de chaque correction (le témoin est la chaîne servie elle-même).
`tsc` 0 · `vitest` 225 vert · V6b vert · banc `--echantillon` sans écart nouveau.

## Famille FAUX / PÉRIMÉ (références juridiques)

### Témoin 1 — RAP « part logement » (moteur taxe, servi partout : fiche, Dossier, bilan)
`src/labuse/taxe_amenagement.py:194`
- **AVANT** : `code du patrimoine art. L524-7 (0,40 % de l'assiette de la taxe d'aménagement)`
- **APRÈS** : `redevance d'archéologie préventive — 0,40 % de l'assiette de la taxe d'aménagement (CGI, gestion DGFiP depuis l'ordonnance 2022-883 ; fait générateur art. 1635 quater F)`
- **Pourquoi** : le taux 0,40 % est bien en vigueur, mais depuis l'ord. 2022-883 (01/09/2022) cette
  part a été recodifiée au CGI ; l'art. L524-7 du code du patrimoine ne porte plus que le régime au
  m² (0,69 €/m² 2026), réservé aux travaux SANS permis. Réf. Légifrance L524-7 lue le 2026-09-29.

### Témoin 2 — RAP au pré-dossier PC (mauvais régime + millésime périmé)
`src/labuse/api/pre_dossier.py:360`
- **AVANT** : `Redevance d'archéologie préventive 0,68 €/m² de surface créée (art. L524-7 du Code du patrimoine) — chiffrée sur la SDP du projet`
- **APRÈS** : `Redevance d'archéologie préventive 0,40 % de l'assiette de la taxe d'aménagement pour les travaux soumis à permis (CGI, gestion DGFiP depuis l'ordonnance 2022-883) — chiffrée sur la SDP du projet, au Dossier financier`
- **Pourquoi** : un pré-dossier PC = travaux soumis à permis → régime 0,40 %, pas le tarif au m²
  (qui vise les aménagements sans permis). Le « 0,68 €/m² » était en outre le millésime 2024.

### Témoin 3 — isolement acoustique (pré-dossier PC, notice PCMI4)
`src/labuse/api/pre_dossier.py:837`
- **AVANT** : `Isolement acoustique renforcé obligatoire en catégorie élevée (art. R.571-32 du Code de l'environnement).`
- **APRÈS** : `Isolement acoustique minimal réglementaire obligatoire pour tout bâtiment situé dans un secteur affecté par le bruit (art. R.571-43 du Code de l'environnement et arrêté du 30 mai 1996) ; le niveau requis dépend de la catégorie de classement de l'infrastructure.`
- **Pourquoi** : R.571-32 = recensement/classement des infrastructures par le préfet, pas
  l'obligation d'isolement (R.571-43 + arrêté du 30/05/1996) ; « catégorie élevée » surqualifiait.

### Témoin 4 — SIS (bulle « i » fiche parcelle, section Risques)
`declarations/fiche/risques.yaml:33`
- **AVANT** : `La parcelle est dans un Secteur d'Information sur les Sols (Géorisques) — servitude OPPOSABLE aux autorisations d'urbanisme (art. L125-6 c. env.).`
- **APRÈS** : `La parcelle est dans un Secteur d'Information sur les Sols (Géorisques, art. L125-6 c. env.) : cette information est annexée au PLU et déclenche, en cas de projet de construction ou de lotissement, une obligation d'étude de sols (art. L556-2 c. env.).`
- **Pourquoi** : L125-6 ne crée pas une servitude « opposable » au sens d'un motif de refus ; il
  déclenche l'obligation d'étude de sols de L556-2.

### Témoins 5 & 6 — PEB zones C et D (tooltip fiche parcelle)
`frontend/src/components/fiche/constructibilite.tsx:911-912`
- **C — AVANT** : `isolement acoustique renforcé obligatoire (art. L112-10 CU)`
- **C — APRÈS** : `constructions d'habitation limitées, sans accroissement sensible de la population exposée (art. L112-10 CU)`
- **D — AVANT** : `zone d'information sur le bruit (art. L112-10 CU)`
- **D — APRÈS** : `constructions autorisées sous réserve d'isolation acoustique (art. L112-10 et L112-12 CU)`
- **Pourquoi** : l'obligation d'isolation relève de L112-12 (zones où la construction est permise) ;
  la zone C limite l'urbanisation, la zone D n'est pas une simple « zone d'information ».

### Témoins 7 & 8 — EBC (tooltip fiche + pré-dossier)
`frontend/src/components/fiche/constructibilite.tsx:935` · `src/labuse/api/pre_dossier.py:311`
- **AVANT** : `… (art. L113-1 CU)`
- **APRÈS** : `… (art. L113-1 et L113-2 CU)` (+ « boisée **classée** »)
- **Pourquoi** : L113-1 = pouvoir de classement ; l'interdiction/effet relève de L113-2.

## Famille PROMESSE (reformulations conditionnées)

### Témoin 9 — carence SRU (contexte commune)
`frontend/src/components/contexte/ContextePanel.tsx:29`
- **AVANT** : `Commune en carence SRU : forte pression de production de logement social — les programmes avec part LLS y sont attendus (et souvent facilités).`
- **APRÈS** : `Commune en constat de carence SRU (art. L302-9-1 CCH) : régime de rattrapage (prélèvement majoré, le préfet peut reprendre la délivrance des autorisations d'urbanisme) — forte pression à la production de logement social. La faisabilité d'un programme reste soumise au PLU et à l'instruction.`
- **Pourquoi** : L302-9-1 institue un régime de SANCTION, pas de « facilitation » des programmes.

### Témoins 10 & 11 — ZFANG renforcé / standard (fiscalité)
`src/labuse/territoire_fiscal.py:46-50`
- **renforcé AVANT** : `Régime renforcé (commune de l'Est, décret n° 2026-421 du 29 mai 2026) — abattements majorés : 80 % … 100 % … jusqu'en 2030.`
- **renforcé APRÈS** : `Régime renforcé (ZFANG, art. 44 quaterdecies CGI ; liste des communes éligibles fixée par le décret n° 2026-421 du 29 mai 2026) — sous réserve d'éligibilité de l'activité, abattements majorés pouvant atteindre 80 % … et 100 % sur la CFE, jusqu'en 2030 — à confirmer auprès d'un fiscaliste.`
- **standard AVANT** : `Régime standard — dispositif de plein droit dans les DOM (art. 44 quaterdecies CGI) : abattement d'environ 50 % sur les bénéfices.`
- **standard APRÈS** : `Régime standard (ZFANG, art. 44 quaterdecies CGI) — sous réserve d'éligibilité de l'activité, abattement d'environ 50 % sur les bénéfices — à confirmer auprès d'un fiscaliste.`
- **Pourquoi** : les taux/échéance viennent du CGI art. 44 quaterdecies (le décret ne fixe que la
  liste des communes) ; « de plein droit » / « commune de l'Est » affirmaient l'avantage sans la
  condition d'éligibilité de l'activité.
