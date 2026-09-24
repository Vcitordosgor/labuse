# COMPARER-2 — Correction des 4 écarts de l'outil Comparer

**Mandat d'exécution** (suite de COMPARER-1). Branche `fix/comparer-2` (worktree `~/Desktop/labuse-comparer2`, base main `1a6d58d0`), **non mergée**. Un commit par point.
**Preuves :** sonde read-only appelant les fonctions servies (`_compare_row`, `fiche_payload`, `compute_bilan`, `resolve_zone`, `build_marche_commune`) — les mêmes que l'endpoint `/compare`. Payloads réels dans `avant-payload.txt` / `apres-payload.json`. Témoins Saint-Paul : **CV1201 · CV1498 · CV1289**.

## Récapitulatif fait / non fait

| Point | Fait | Commit |
|---|---|---|
| §1 Emprise au sol — ne plus inventer une règle | ✅ | `77248dd1` |
| §2 Charge foncière — unité + VRD à la racine + LLS | ✅ | `3a8f6585` |
| §3 Badges — médiane ≠ fait cadastral | ✅ | `eb5803c0` |
| §4 Ligne « Classement LABUSE » | ✅ | `55922f73` |

**Tests :** `tsc` ✅, `build` ✅, `vitest` **176 passed / 2 failed** (les 2 = `admin/circuit/Detail.test.tsx`, **pré-existants**, identiques sur `main`). `pytest` bilan + consommateurs (bilan, decisions_1_3, lot_d, calibration, pente_exposition, mn_faisabilite, scoreur, exports2, shortlist, surface_c, retours11f3) **tous verts**, dont le **nouveau test VRD** et le test D3b (LLS) mis à jour.

---

## Capture avant / après du tableau (3 témoins)

> Le backend HTTP de ce poste (partagé avec d'autres sessions) restait bloqué au démarrage ; les tableaux ci-dessous sont **rendus fidèlement depuis les payloads réels** servis par les fonctions de `/compare` (fichiers `avant-payload.txt` / `apres-payload.json`). Chaque valeur est celle que l'écran affiche.

### AVANT (base `main`)

| Ligne (badge) | CV1201 | CV1498 | CV1289 |
|---|---|---|---|
| Surface `Sourcé` | 405 m² | 7 398 m² | 413 m² |
| Zone PLU `Sourcé` | U3c | AU3c | U3c |
| Constructible `Sourcé` | oui | oui | oui |
| SDP max · terrain libéré `Estimé` | 263 m² | 5 992 m² | 268 m² |
| SDP résiduelle · bâti conservé `Estimé` | 241 m² | 5 947 m² | 65 m² |
| **Emprise au sol max** `Sourcé` | 11 % | **1 %** | 51 % |
| Sous-densité `Estimé` | oui | oui | non |
| **Charge foncière /m²** `Estimé` *(titre : « …au m² de plancher »)* | +99 €/m² | **−143 €/m²** | +98 €/m² |
| **Prix terrain nu zone** `Sourcé` | 479 €/m² | 328 €/m² | 479 €/m² |
| **Prix bâti secteur** `Sourcé` | 3 652 €/m² | 3 652 €/m² | 3 652 €/m² |
| Logements possibles `Estimé` | 2–4 | 41–47 | 2–4 |
| Bâti existant `Sourcé` | 5 % | 1 % | 25 % |
| Gabarit max `Sourcé` | R+2 | R+2 | R+2 |
| Accès & réseaux `Sourcé` | Viabilisation confirmée… | Viabilisation confirmée… | Viabilisation confirmée… |
| **Assainissement** `Sourcé` | Tout-à-l'égout | 59 % du secteur non raccordés | Tout-à-l'égout |
| Propriétaire `Sourcé` | particulier | personne morale | particulier |
| Contrainte majeure `Sourcé` | bruit routier cat. 2 | PPR bleue ~24 % | SDP résiduelle 65 m² |

### APRÈS (`fix/comparer-2`) — les cases modifiées sont en gras

| Ligne (badge) | CV1201 | CV1498 | CV1289 |
|---|---|---|---|
| Surface `Sourcé` | 405 m² | 7 398 m² | 413 m² |
| Zone PLU `Sourcé` | U3c | AU3c | U3c |
| **Classement LABUSE** *(nouveau)* | **À étudier · Signal faible** | **Bonne · Signal faible** | **Faible · Signal faible** |
| Constructible `Sourcé` | oui | oui | oui |
| SDP max · terrain libéré `Estimé` | 263 m² | 5 992 m² | 268 m² |
| SDP résiduelle · bâti conservé `Estimé` | 241 m² | 5 947 m² | 65 m² |
| **Emprise au sol max (PLU)** `Sourcé` | **non réglementée** | **non réglementée** | **non réglementée** |
| **Taux d'occupation du gabarit** `Estimé` *(nouveau libellé)* | **11 %** | **1 %** | **51 %** |
| Sous-densité `Estimé` | oui | oui | non |
| **Charge foncière /m² terrain** `Estimé` | **+100 €/m²** | **−93 €/m²** | **+101 €/m²** |
| **Prix terrain nu zone** `Estimé` | 479 €/m² | 328 €/m² | 479 €/m² |
| **Prix bâti secteur** `Estimé` | 3 652 €/m² | 3 652 €/m² | 3 652 €/m² |
| Logements possibles `Estimé` | 2–4 | 41–47 | 2–4 |
| Bâti existant `Sourcé` | 5 % | 1 % | 25 % |
| Gabarit max `Sourcé` | R+2 | R+2 | R+2 |
| Accès & réseaux `Sourcé` | Viabilisation confirmée… | Viabilisation confirmée… | Viabilisation confirmée… |
| **Assainissement** `Estimé` | Tout-à-l'égout | 59 % du secteur non raccordés | Tout-à-l'égout |
| Propriétaire `Sourcé` | particulier | personne morale | particulier |
| Contrainte majeure `Sourcé` | bruit routier cat. 2 | PPR bleue ~24 % | SDP résiduelle 65 m² |

---

## §1 — Emprise au sol : ne plus déguiser un dérivé en règle PLU

L'ancienne ligne « Emprise au sol max » (badge **Sourcé**) servait `residuel.taux_emprise_pct` = **bâti existant ÷ emprise constructible** (un taux d'occupation), sous un titre prétendant citer le PLU — alors qu'U3c/AU3c **n'ont aucune CES** au règlement calibré.

- Ligne renommée **« Taux d'occupation du gabarit »**, badge **Estimé**, sous-titre « bâti existant ÷ emprise constructible ».
- Nouvelle ligne **« Emprise au sol max (PLU) »**, badge **Sourcé** : la **vraie CES validée** dans `plu_destinations` (`resolve_zone(...).emprise_sol_pct` + citation au survol via `sources["emprise"]`). Quand la zone n'en fixe pas → **« non réglementée »** (jamais un chiffre dérivé sous ce titre). Sur les 3 témoins (U3c/AU3c) : `emprise_ces_pct = null` → **« non réglementée »** — conforme au règlement.
- **Fiche parcelle :** elle **n'affiche pas** ce champ (`taux_emprise_pct` n'est rendu nulle part dans `components/fiche/`) → rien à aligner côté fiche.

## §2 — Charge foncière : unité, VRD à la racine, LLS honnête

**Corrigé dans le moteur de bilan (`compute_bilan`), source unique fiche / Assemblage / Comparer — une seule fonction.**

**Règle VRD retenue (documentée dans le code) :**
> La VRD s'applique à l'**emprise réellement aménagée** du scénario, **plafonnée au terrain** :
> `emprise_aménagée = min( terrain , (empreinte_au_sol_programme + stationnement) × (1 + 40 % voirie interne) )`
> avec `empreinte_au_sol_programme = SDP retenue ÷ niveaux`, `stationnement = logements × places/logt × place_m2` (place_m2 = 25, places/logt lues du PLU de la zone, repli 2). Une **petite parcelle dense** sature déjà son terrain → aménagée = terrain (inchangée) ; une **grande parcelle sous-densifiée** ne fait plus payer la VRD des m² qu'elle n'aménage pas.

**LLS :** le prix affiché est désormais celui **réellement utilisé** (`prix_lls` résolu par secteur, p.ex. 2 900 €/m²), plus le « ×0 » trompeur qui lisait `hyp.prix_m2_lls` (placeholder brut). Quand le prix LLS **n'est pas** calibré (ni secteur ni saisi), la part LLS est **exclue du CA** avec mention **« LLS non chiffré »** — jamais un 0 silencieux ni un plein prix marché.

**Unité :** titre Comparer → **« Charge foncière /m² terrain »** (la valeur est `charge_fonciere.par_m2_terrain`) ; direction corrigée (`best='hi'` : la charge *supportable*, plus haut = mieux). Assemblage affichait **déjà** « €/m² de terrain » (moteurs.tsx). La fiche : l'étape de bilan disait déjà « ≈ X €/m² terrain ».

### Tableau des 4 cas de charge foncière

| Cas | Avant | Après | VRD avant → après | Lecture |
|---|---|---|---|---|
| **CV1201** (U3c, 405 m²) | **+99 €/m²** | **+100 €/m²** | ~56 k€ → ~45 k€ | aménagée ≈ terrain → **quasi inchangée** ✅ |
| **CV1289** (U3c, 413 m²) | **+98 €/m²** | **+101 €/m²** | ~58 k€ → ~46 k€ | aménagée ≈ terrain → **quasi inchangée** ✅ |
| **CV1498** (AU3c, 7 398 m²) | **−143 €/m²** | **−93 €/m²** | ~1 032 k€ → ~661 k€ (aménagée ~4 736 m²) | voir ci-dessous |
| **Assemblage** CV0724+CV1506+CV1507 | **−11 841 €** (−3 €/m²) | **+158 406 €** (+42 €/m²) | — | le négatif **disparaît → positif** ✅ |

**CV1498 reste à −93 €/m² — clairement justifié (pas un artefact).** La VRD n'était que le symptôme visible : le **plancher de rentabilité** de cette parcelle est déjà à ≈ −3 €/m² **même à VRD nulle**, parce que sur ce **grand programme** (SDP 5 992 ≥ 1 500 m²) la **clause de mixité sociale s'enclenche** (30 % LLS à 2 900 €/m²), ce qui rabote le prix de sortie de 4 730 à 4 181 €/m² pondéré — et à ce prix le CA×0,76 couvre tout juste la construction. Le −93 €/m² restant = la **VRD réelle des 4 736 m² effectivement aménagés** (empreinte + stationnement + voirie), plus les 2 662 m² de terrain que le programme ne touche pas. C'est un **signal économique réel** (obligation LLS sur une grande assiette), plus l'artefact d'avant qui viabilisait 7 398 m² pour 2 478 m² vendables. À l'inverse, l'**assemblage** (petits programmes AU sous le seuil des 1 500 m² → pas de clause LLS) repasse **franchement positif**.

## §3 — Badges : une médiane n'est pas un fait cadastral

Passés de **Sourcé** à **Estimé** : **Prix terrain nu de zone** et **Prix bâti secteur** (médianes DVF = calcul sur des ventes), **Assainissement** (souvent une statistique de secteur, ex. « 59 % non raccordés », pas un raccordement vérifié à la parcelle). **Restent Sourcé** : surface cadastre, zone PLU, constructible, propriétaire DGFiP, contrainte majeure GPU/DEAL, **Emprise au sol max (PLU)** (§1).

**Divergence signalée, non corrigée (hors mandat refonte fiche) :** le **bilan de la fiche** marque encore le prix DVF `prov="sourcee"` sur ses *steps* (`bilan.py`), donc la fiche présente la médiane DVF comme « sourcée ». L'aligner toucherait fiche / Banquier / Argumentaire / exports (grande surface) — à traiter dans un mandat dédié.

## §4 — Ligne « Classement LABUSE »

Nouvelle **2e ligne** (sous Zone PLU) : la **bande** du moteur candidat **q_v15** (Excellente / Bonne / À étudier / Faible / Non retenue / Analyse incomplète) + le **Signal de mutation** en badge (Fort / Moyen / Faible), **même source** (`score_labuse`) et **mêmes couleurs** (`BANDE_META` / `SIGNAL_META`) que l'écran Analyse (ANALYSE-1/2/3). Témoins : **CV1201 = À étudier (C)**, **CV1498 = Bonne (B)**, **CV1289 = Faible (D)**, tous Signal faible.

**Servi tel quel depuis la table candidate q_v15** (comme l'Analyse) — donc **cohérent avec l'Analyse dès aujourd'hui**, avant même la bascule du run servi (qui, elle, rendra tout l'app cohérent). Si la table candidate est absente (base nue) → « — » (jamais un score inventé). Le score ne s'affiche que sur la fiche, l'Analyse et cet outil de comparaison — **jamais la carte** (doctrine M120).

---

## Ce qui a été aligné au passage (fiche / Assemblage)

- **Assemblage** : consomme le même `aggregate_assiette` → `compute_bilan` ; le correctif VRD/LLS s'y **propage sans code dédié** (assemblage témoin −11 841 € → +158 406 €). Son libellé « €/m² de terrain » était déjà correct.
- **Fiche** : même `compute_bilan` → l'étape VRD y montre désormais « emprise aménagée », et le CA pondéré affiche le **vrai prix LLS** (2 900) au lieu de « ×0 ». La charge foncière /m² de la fiche est cohérente à l'euro avec Comparer et Assemblage (source unique).
- **Fiche** : ne rendant pas `taux_emprise_pct`, aucun libellé « Emprise au sol max » à corriger côté fiche.

## Hors mandat (non fait)
Refonte de la fiche/Assemblage au-delà de l'unité et des libellés touchés ; alignement du badge « sourcée » des prix DVF dans le bilan de la fiche (signalé §3) ; autres lignes ; scoring ; merge.
