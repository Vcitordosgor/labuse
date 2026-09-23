# COMPARER-1 — L'outil « Comparer des parcelles » : données branchées, vraies, et outil à niveau

**Mandat :** audit court, lecture seule. Vérifier ligne par ligne que le pied de tableau (« chaque valeur vient du même point de calcul que la fiche, run servi ») est vrai, que les valeurs sont justes, et que les badges Sourcé/Estimé sont les bons.
**Branche :** `audit/comparer-1` (worktree `~/Desktop/labuse-comparer`, base main `1a6d58d0`). Rapport = seul livrable, aucun code touché.
**Preuves live :** backend du worktree (`:8285`, base `labuse`) — `GET /compare?idus=…` end-to-end + sonde read-only appelant `_compare_row(_q_v2_fiche, fiche_payload)` et `build_marche_commune`, les fonctions exactes de la fiche.
**Témoins :** CV1201 (U3c, 405 m²) · CV1498 (AU3c, 7 398 m²) · CV1289 (U3c, 413 m²), Saint-Paul 97415.

---

## Verdict

**Le raccordement est vrai.** L'endpoint `/compare` (`app.py:6975`) construit chaque ligne par `_compare_row(_q_v2_fiche(db, idu), fiche_payload(db, pid))` — **littéralement les fonctions servies de la fiche** (verdict/cascade/propriétaire/viabilisation/ANC/DVF secteur d'un côté ; zone/SDP/résiduel/bilan de l'autre), plus `build_marche_commune` pour le terrain de zone (la source de la §Marché). **Aucun second moteur.** Les valeurs sont donc identiques à la fiche par construction — vérifié en appelant les mêmes fonctions.

**Deux réserves, toutes deux d'affichage (pas de source divergente) :**
1. **Ligne « Emprise au sol max » : libellé faux.** La valeur servie est `residuel.taux_emprise_pct` = **emprise bâtie ÷ emprise constructible** (taux d'occupation du gabarit **déjà** bâti), pas la CES que le PLU autorise. Le titre (« Part **maximale** du terrain que le PLU autorise à couvrir ») décrit une règle qui, pour **U3c et AU3c, n'existe pas** (aucune CES au règlement). Badge **Sourcé** de surcroît, alors que c'est un ratio dérivé.
2. **Badges Sourcé sur des médianes DVF** (prix terrain nu de zone, prix bâti secteur) et sur une **statistique de secteur** (assainissement CV1498 « 59 % du secteur… ») : ce sont des estimés/observés, pas des faits cadastraux — le mandat a raison de le relever.

**Les valeurs sont justes.** SDP, résiduel, logements, charges, prix : tout se reproduit à l'euro. La charge foncière **−143 €/m² sur CV1498 est arithmétiquement exacte** — mais c'est un scénario pessimiste piloté par la VRD au m² de terrain sur une grande parcelle sous-densifiée (même famille qu'ASSEMBLAGE-1), pas la valeur du foncier.

---

## 1. Ligne par ligne — même source que la fiche ?

Comparer ne lit **que** `_q_v2_fiche` (fiche servie) + `fiche_payload` (faisabilité, même point de calcul que la fiche) + `build_marche_commune` (§Marché). Donc « même source » = **oui** partout ; les valeurs Comparer = valeurs fiche par construction. Le tableau ci-dessous donne source, valeurs des 3 témoins (live), et l'anomalie éventuelle.

| # | Ligne (badge) | Fonction/table lue par Comparer (= fiche) | CV1201 | CV1498 | CV1289 | OK/écart |
|---|---|---|---|---|---|---|
| 1 | Surface `Sourcé` | `_q_v2_fiche`→`parcels.surface_m2` | 405 m² | 7 398 m² | 413 m² | ✅ |
| 2 | Zone PLU `Sourcé` | `fiche_payload.zone` (`parcel_zone_plu` calibré) | U3c | AU3c | U3c | ✅ |
| 3 | Constructible `Sourcé` | `fiche_payload.constructible` | oui | oui | oui | ✅ |
| 4 | SDP max · terrain libéré `Estimé` | `fourchette.surface_plancher_m2` | 263 m² | 5 992 m² | 268 m² | ✅ |
| 5 | SDP résiduelle · bâti conservé `Estimé` | `residuel.sdp_residuelle_m2` | 241 m² | 5 947 m² | 65 m² | ✅ |
| 6 | **Emprise au sol max** `Sourcé` | `residuel.taux_emprise_pct` = **bâti ÷ emprise constructible** | 11 % | **1 %** | 51 % | ⚠ **E1 libellé faux** |
| 7 | Sous-densité `Estimé` | `residuel.sous_densite` (= taux_emprise < 40 %) | oui | oui | non | ✅ (cohérent avec E1) |
| 8 | Charge foncière /m² `Estimé` | `bilan.charge_fonciere.par_m2_terrain` | +99 €/m² | **−143 €/m²** | +98 €/m² | ✅ calcul, ⚠ **E2 unité titre** |
| 9 | Prix terrain nu zone `Sourcé` | `build_marche_commune`→`ligne2_terrain_zone` (médiane DVF/zone) | 479 €/m² | 328 €/m² | 479 €/m² | ✅ valeur · ⚠ **E5 badge** |
| 10 | Prix bâti secteur `Sourcé` | `dvf_parcelle.secteur` → **max n_ventes, hors terrain** | 3 652 €/m² | 3 652 €/m² | 3 652 €/m² | ✅ (même secteur) · ⚠ **E5 badge + sélection** |
| 11 | Logements possibles `Estimé` | `fourchette` : paire (au sol/sous-sol) au plus haut plafond | 2–4 | 41–47 | 2–4 | ✅ |
| 12 | Bâti existant `Sourcé` | `residuel.emprise_batie_m2 ÷ surface` | 5 % | 1 % | 25 % | ✅ (⚠ E6 redondant avec #6) |
| 13 | Gabarit max `Sourcé` | `residuel.niveaux_max` (hauteur PLU) | R+2 | R+2 | R+2 | ✅ (règle réelle, voir §2) |
| 14 | Accès & réseaux `Sourcé` | `_q_v2_fiche.viabilisation.libelle` | Viabilisation confirmée… | Viabilisation confirmée… | Viabilisation confirmée… | ✅ |
| 15 | Assainissement `Sourcé` | `_q_v2_fiche.anc.libelle` | Tout-à-l'égout | **59 % du secteur non raccordés** | Tout-à-l'égout | ✅ valeur · ⚠ E5 (stat secteur en « Sourcé ») |
| 16 | Propriétaire `Sourcé` | `proprietaire_moral` → morale/particulier (DGFiP) | particulier | **morale** | particulier | ✅ |
| 17 | Contrainte majeure `Sourcé` | cascade `qv2.lines` (HARD_EXCLUDE puis SOFT_FLAG) | bruit routier cat. 2 | PPR bleue inondation ~24 % | « SDP résiduelle 65 m² — rien à construire » | ✅ (⚠ #17 CV1289 = note de capacité, pas un risque) |

**Badges — verdict.** Le mandat pose le bon critère (« une médiane DVF n'est pas *sourcé* au sens d'un fait cadastral »). Faux/discutables :
- **#6 Emprise au sol max — faux deux fois** : c'est un ratio dérivé (donc *Estimé*, pas *Sourcé*) ET le libellé décrit une CES PLU inexistante en U3c/AU3c. **À corriger en priorité.**
- **#9 / #10** (`Sourcé`) sont des **médianes DVF** — données observées, mais statistiques, pas des faits. Un badge « Marché/Observé » ou *Estimé* serait plus honnête.
- **#15** sert pour CV1498 une **statistique de secteur** (« 59 % … ») sous badge *Sourcé*.
- Justes : #1, #2, #16, #17 (faits), #4/#5/#7/#8/#11 (*Estimé* correct).

---

## 2. Valeurs suspectes — explications sur données réelles

### Charge foncière −143 €/m² sur CV1498 — **juste au calcul, faux de sens**
Bilan servi de la parcelle (mono-parcelle, pas une somme), reproduit à l'euro :

| Poste | Valeur | Détail servi |
|---|---|---|
| SHAB vendable | 2 478 m² | scénario **R+2 au sol** retenu (34–35 logts) — pas les 5 992 m² de SDP max |
| Prix de sortie | 4 730 €/m² → **4 181 pondéré** | **clause mixité DÉCLENCHÉE** (SDP 5 992 ≥ 1 500) : 30 % × **0 €/m² LLS (placeholder)** ⇒ CA raboté |
| CA | 10,36 M€ | 2 478 × 4 181 |
| − marge + frais | ×0,76 | 24 % du CA (marge 9 % + honoraires 12 % + frais fin. 3 %) |
| − construction | 7,90 M€ | 3 098 m² SDP (2 478/0,80) × 2 550 €/m² |
| − **VRD** | **1,03 M€** | **90 €/m² × 7 398 m² de terrain × 1,55** (pente 17 % + assainissement autonome) |
| = charge foncière | **−1,06 M€ = −143 €/m² terrain** | 10,36×0,76 − 7,90 − 1,03 ≈ −1,06 M€ ✅ |

**Le calcul est exact ; trois hypothèses le poussent au négatif, toutes structurelles :**
1. **VRD facturée sur les 7 398 m² de terrain entiers** (×1,55) alors que le scénario retenu ne vend que 2 478 m² de logements ⇒ **416 €/m² vendable de VRD**. C'est **l'hypothèse dominante** que le mandat soupçonnait : plus la parcelle est grande et peu dense, plus la VRD au m² de terrain écrase le résiduel. (Preuve : les deux petites parcelles U — 405/413 m² — ressortent **+99 / +98 €/m²**, positives ; seule la grande AU plonge.)
2. **Sous-densification du scénario retenu** : SDP max 5 992 m² mais vendable 2 478 m² (ratio 0,41). Un R+2 au sol de 34 logements sur 7 398 m² laisse peu de CA pour absorber une VRD à l'échelle du terrain. Une opération réelle densifierait.
3. **LLS valorisé à 0 €/m² (placeholder non calibré)** : la clause de mixité rabote le prix de 4 730 à 4 181 €/m².

**Phrase nette : le −143 €/m² n'est pas un bug ni une valeur par défaut aberrante — il est arithmétiquement juste, mais c'est un scénario pessimiste dont la valeur dépend d'hypothèses à revoir (VRD au m² de terrain sur grande parcelle + faible densité + LLS à 0), pas la valeur du foncier** (marché AU = 328 €/m²). Même symptôme qu'ASSEMBLAGE-1. *Réserve d'unité* : le titre front dit « ramené au m² de **surface de plancher** » alors que la valeur est **par m² de terrain** (E2).

### Emprise au sol max 1 % sur CV1498 — **ni la règle AU3c, ni une CES**
Le règlement calibré (`config/plu_destinations/97415_saint_paul.yaml`) : **U3c n'a AUCUNE règle d'emprise au sol** (seulement hauteur faîtage 12 m / égout 9 m, retraits voie 4 m / séparatives 3 m, stationnement 2 pl./logt, pleine-terre 40 %) ; **AU3c = `renvoi: U3c`** (« se reporter au règlement de la zone U3 de même indice », p. 158) ⇒ pas de CES non plus. La « 1 % » servie est `taux_emprise_pct = 100 × emprise_bâtie (45 m²) ÷ emprise constructible (4 439 m²)` — un **taux d'occupation du gabarit déjà bâti**, pas une CES. **La règle citée par le libellé n'existe pas ; la valeur est un dérivé mal étiqueté.**

### Sous-densité « oui » sur CV1498 — **cohérent avec le champ réel (mais pas avec le libellé)**
`sous_densite = taux_emprise (1 %) < seuil (40 %)` ⇒ oui. C'est cohérent avec le **vrai** sens du champ (occupation du gabarit). Idem CV1201 (11 % < 40 → oui), CV1289 (51 % > 40 → non). Le raisonnement est bon ; seul le libellé de la ligne #6 trompe.

### Prix bâti secteur 3 652 €/m² identique sur les 3 — **normal (même secteur), pas un défaut**
Les 3 parcelles partagent le **même secteur DVF** (triplet identique : maison 3 652 €/m² n=55, appart 4 273 n=14, terrain 295 n=10). `_compare_row` retient le type le plus documenté hors terrain (**maison, n=55**) ⇒ 3 652 partout. Ce n'est pas une valeur par défaut. *Nuance* : la fiche §Marché montre maison **et** appartement ; Comparer n'en sert qu'un (E5b, sélection propre à l'outil).

### Gabarit max R+2 sur les 3 (dont AU3c) — **la vraie règle de chaque zone**
`niveaux_max = 3` (R+2) dérivé de la hauteur PLU : **U3c faîtage 12 m / égout 9 m** ; **AU3c `renvoi: U3c`** ⇒ même 12/9 m. À ~3 m/niveau, 9 m à l'égout ⇒ 3 niveaux (R+2). Identique et **réel**, pas un défaut commun.

---

## 3. L'outil est-il à niveau ? (constats, pas de maquette)

1. **Manque le classement LABUSE / bande** : `tier_v2`, `label`, `rang` sont **récupérés** mais la puce a été volontairement retirée (`OUTILS-FIX-3 C1`, « l'Analyse n'a pas été demandée ici »). Pour un comparateur, une bande (Excellente/Bonne/À étudier…) serait la ligne la plus utile — actuellement absente.
2. **Manque un rang lisible** : le rang global (ex. 271 141/431 663) ne parle pas ; un **rang dans la commune** serait parlant mais n'est pas dans le payload (déjà noté dans le code).
3. **Manque le signal de mutation daté** : seuls la raison dominante (« secteur qui bouge ») et la fraction M135 (« 1/5 sous 1 an ») apparaissent ; pas de **dernière vente DVF** ni de date.
4. **Manque le risque en %** : CV1498 a « PPR bleue ~24 % » mais **noyé dans le texte** de « Contrainte majeure », pas une ligne numérique comparable.
5. **Manque la surface exploitable clippée** (part U/AU réellement constructible d'une parcelle à cheval A/N) — la SDP est servie sur le contour, le clipping n'est pas une ligne.
6. **Ligne #6 fausse (voir §1/§2)** — le pire défaut de lisibilité/véracité : un « max PLU » qui n'existe pas.
7. **Redondance #6 vs #12** : deux ratios du même numérateur (emprise bâtie ÷ gabarit vs ÷ terrain) — source de confusion.
8. **« Contrainte majeure » parfois hors-sujet** : CV1289 y affiche une **note de capacité** (« SDP résiduelle 65 m² — rien à construire »), pas une contrainte réglementaire.
9. **Ergonomie** : « Tout vider » ✅, « Retour à la carte » ✅, ✕/Échap ferment le tableau ✅ ; la sélection **persiste 15 min** (store `compareTouchedAt`) mais le **tableau se ferme** dès qu'on quitte l'outil — il faut le rouvrir. Pas d'export (retiré volontairement).
10. **Badges** : deux médianes DVF et un ratio dérivé estampillés *Sourcé* (§1) — à requalifier.

---

## 4. Verdict & écarts

| Question | Réponse |
|---|---|
| « Même point de calcul que la fiche » (17 lignes) ? | **OUI** — `_q_v2_fiche` + `fiche_payload` + `build_marche_commune`, valeurs identiques par construction |
| Valeurs justes sur les 3 témoins ? | **OUI** — reproduites à l'euro (SDP, résiduel, logements, charges, prix) |
| Badges Sourcé/Estimé corrects ? | **NON pour #6** (dérivé mal étiqueté), **discutables #9/#10/#15** (médianes/stat en *Sourcé*) |
| Charge foncière −143 €/m² (CV1498) ? | **Juste au calcul, faux de sens** (VRD terrain-entier × faible densité × LLS 0) |

**Écarts (non corrigés) :**
- **E1 — Ligne « Emprise au sol max » mal libellée** : sert `taux_emprise_pct` (occupation du gabarit bâti), présentée comme la CES max que le PLU autorise — or U3c/AU3c n'ont **aucune CES**. Badge *Sourcé* à tort.
- **E2 — Titre « Charge foncière /m² » indique « m² de surface de plancher »** alors que la valeur est **par m² de terrain**.
- **E3 — Charge foncière −143 €/m²** : exacte mais dominée par la **VRD au m² de terrain (×1,55) sur 7 398 m² sous-densifiés** + LLS à 0 (placeholder) ; ne reflète pas la valeur du foncier.
- **E4 — Classement/bande LABUSE et rang commune absents** du tableau (récupérés mais non affichés) ; risque PPR %, dernière vente, surface clippée absents.
- **E5 — Badges** : #9/#10 médianes DVF et #15 statistique de secteur estampillés *Sourcé*.
- **E6 — Redondance #6/#12** (deux ratios de l'emprise bâtie) ; **#17** peut afficher une note de capacité au lieu d'une contrainte.

**3 recommandations pour le mandat de correction (max) :**
1. **Réparer la ligne #6** : soit la renommer « Emprise bâtie / gabarit (taux d'occupation) » en badge *Estimé*, soit servir la **vraie CES** quand elle existe et afficher « non réglementée » en U3c/AU3c. Corriger aussi le titre unité de #8 (terrain, pas plancher).
2. **Ajouter la ligne « Classement LABUSE » (bande + rang commune)** — la donnée est déjà dans le payload ; c'est la comparaison la plus attendue.
3. **Requalifier les badges** des médianes DVF (#9/#10) et de la stat secteur (#15) en *Estimé* / *Marché* — réserver *Sourcé* aux faits (surface, zone, propriétaire, contrainte).

---

## 5. Hors mandat (non fait)
Aucune correction, aucun ajout de ligne, aucune modif de la fiche/Assemblage/autres outils, aucun merge. Rapport seul, committé sur `audit/comparer-1`.
