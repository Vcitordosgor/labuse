# RAPPORT M55-D stage 6 — PHASE 1 : volumétrie des Signaux de vie (STOP)

Branche `feat/m55-d-stage6` (base `main` 5ee4157e, **stage 5 mergé — précondition vérifiée**).
**MESURE SEULE — aucun code. STOP : validation Vic de la liste finale avant la phase 2.**
Mesures sur le run servi `q_v8_calibre` (431 663 parcelles). « brûl+chaude » = tiers brûlante+chaude ;
« servables » = + réserve foncière + à creuser.

## ⚠ Le fait à voir AVANT le tableau — la « requête reine »

**« Brûlantes × sortie de défisc » = 0 brûlante, 3 chaudes aujourd'hui, île entière.**
Ventilation des 797 fenêtres actives : écartée 666 · déclassée bâti saturé 85 · à creuser 18 ·
déclassée inconstructible 14 · bâti révélé 8 · zone fermée 3 · **chaude 3**. C'est logique — une
sortie de défisc est par nature un bien **bâti** (appartement neuf d'il y a 9-15 ans), que
l'étage 0 / le déclassement bâti écarte du classement « terrain ». Le signal est bon, le
croisement avec les tiers hauts est structurellement rare. À savoir avant de bâtir l'UI autour :
la composition ET reste juste, mais la requête reine rendra des unités, pas des dizaines.

## Le tableau (9 candidats)

| # | Signal | n île | brûl+chaude | servables | Millésime | Coût requête | Verdict reco |
|---|--------|-------|-------------|-----------|-----------|--------------|--------------|
| 1 | **Procédure collective en cours** (dernier jugement ≠ clôture) | **518** (658 si « toute procédure ») | 3 | 73 | BODACC 02/07/2026 | léger (jointure siren, tables minuscules ; ~équivaut au `etat_societe=procedure` existant) | **GARDER** (version « en cours ») |
| 2 | **Permis actif** (PC < 3 ans, hors caducs) | **8 003** | **573** | 1 660 | Sitadel 30/06/2026 | ⚠ parse JSON `idu_codes` par appel → **pré-calcul requis** (table/flag au build — `build_permits`/`p_model_permits` existe déjà côté features, à exposer) | **GARDER** (pré-calculé) |
| 3 | **Permis abandonné/caduc** | **2 161** | 42 | 565 | calcul 08/08/2026 (PC ≤ 2022) | nul — **param `/filtre` `pc_caduc` EXISTE déjà** | **GARDER** (gratuit) |
| 4 | **Sortie de défiscalisation** (fenêtre active) | **797** | 3 | 21 | 21/07/2026 | nul — **param `defisc_active` EXISTE déjà** | **GARDER** (gratuit ; attentes cadrées ↑) |
| 5 | **Dormance longue** | **357 766** | 612 | 29 246 | DVF 31/12/2025 | anti-jointure 213 k lignes → pré-calcul obligatoire si gardé | **ÉCARTER** — double motif : > 100 k (83 % de l'île = pas un signal) ET **resserrer à 20/30 ans est IMPOSSIBLE : les DVF commencent en 2014** (12 ans de profondeur max). « Aucune vente depuis 2014 » est la seule version honnête, et elle ne discrimine rien. |
| 6 | **Terrain nu détenu par une société** | 9 741 (toutes PM) / **3 082 (privées, groupe 0)** | 170 | 2 275 | MAJIC 2025 | léger (EXISTS indexés, comme les filtres proprio actuels) | **GARDER en version PRIVÉE** — « toutes PM » compte communes/État/HLM, ce n'est pas le signal cherché |
| 7 | **Friche recensée** | **1 801** | 2 | 164 | Cartofriches 05/07/2026 (372 périmètres) | ⚠ jointure SPATIALE par appel → **pré-calcul obligatoire** : ajouter `friche` à `parcel_flags` (l'infra flags existe, `/filtre` la sert déjà à coût nul) | **GARDER** (pré-calculé flag) |
| 8 | **Cession de fonds récente** (< 12 mois) | **2 078** (2 434 à < 24 mois) | 36 | 348 | BODACC 03/07/2026 | léger (jointure siren) | **GARDER** (< 12 mois) |
| 9 | **Assemblage même propriétaire** | ≥2 privé : **27 328** · ≥3 privé : 22 813 (toutes PM ≥2 : 75 053, dominé par 415 gros porteurs = 60 871 parcelles) | 199 | 3 122 | MAJIC 2025 | ⚠ GROUP BY 34 k lignes par appel → **pré-calcul requis** (colonne `n_parcelles_meme_siren` ou table au build) | **GARDER resserré : privé (groupe 0) ≥ 3 parcelles** |

*(Exclusions Vic déjà actées : dirigeant âgé (RGPD), passoire thermique (15 DPE).)*

**Aucun signal < 50 (pas de gadget).** Un seul > 100 k : la dormance (à écarter, resserrage
impossible faute de profondeur DVF).

## Coût requête — synthèse
- **Gratuits** (params `/filtre` existants) : #3 `pc_caduc`, #4 `defisc_active` ; #1 ≈ `etat_societe=procedure` (à affiner « en cours »).
- **Légers** (EXISTS indexés, patron actuel) : #1, #6, #8.
- **Pré-calcul OBLIGATOIRE au build** (jamais de jointure lourde par appel) : **#2** (parse JSON Sitadel → table permis actifs, `build_permits` existe côté features), **#7** (spatial → flag `parcel_flags`), **#9** (GROUP BY → colonne/table). Chacun avec test d'idempotence en phase 2.

## Libellés « i » proposés (sourcés, datés, honnêtes sur le partiel)
1. « Le propriétaire (société) est en procédure collective — sauvegarde, redressement ou liquidation, dernier jugement connu non clôturé (BODACC, maj 07/2026). Ne couvre que les propriétaires personnes morales identifiés. »
2. « Un permis de construire accordé depuis moins de 3 ans, non repéré caduc (Sitadel, arrêté 06/2026 — rattachement à la parcelle tel que déclaré au permis). »
3. « Permis accordé jamais suivi de travaux repérés — caducité ESTIMÉE par LABUSE (croisement Sitadel × bâti, calcul 08/2026) ; à vérifier en mairie. »
4. « La fenêtre de revente fiscale (défiscalisation estimée sur l'année d'achat neuf) est ouverte — le propriétaire peut vendre sans reprise d'avantage (ESTIMATION LABUSE, maj 07/2026). »
6. « Parcelle quasi nue (emprise bâtie < 5 %) détenue par une société privée (fichiers fonciers MAJIC 2025). »
7. « La parcelle touche une friche de l'inventaire national Cartofriches (maj 07/2026) — inventaire NON exhaustif : l'absence du signal ne prouve rien. »
8. « Le propriétaire (société) a vendu ou cédé un fonds dans les 12 derniers mois (BODACC, maj 07/2026). Propriétaires personnes morales identifiés seulement. »
9. « Le propriétaire (société privée) détient 3 parcelles ou plus sur l'île (MAJIC 2025) — négociation groupée possible. »

## Recommandation de liste finale (7 signaux)
**#1 procédure en cours · #2 permis actif · #3 permis caduc · #4 sortie de défisc · #6 nu-société
(privée) · #7 friche · #8 cession de fonds · #9 assemblage privé ≥3** → 8 gardés, dormance écartée.
Si Vic veut exactement 7 : le moins discriminant des gardés est **#7 friche** (2 brûl+chaude, et
inventaire non exhaustif) — candidat à la coupe.

**STOP — j'attends la liste finale (et les arbitrages : #1 « en cours » vs « toute », #6 privée vs
toutes PM, #8 12 vs 24 mois, #9 seuil ≥2 vs ≥3, dormance vraiment écartée ?) avant la phase 2.**

## Périmètre
Phase 1 : lecture seule (SQL + code). CC ne merge jamais.
