# SOURCES-FIX-2 — correction des anomalies de SOURCES-AUDIT-3

**Branche** `fix/sources-fix-2` · worktree `/Users/openclaw/Desktop/labuse-sources3` · ports 8595/5795 · Opus · base `origin/main`.
**Base** `postgresql://openclaw@localhost:5432/labuse` (dev). API 8595 + front 5795 lancés une fois (Étape 0) et rejoués pour les preuves des lots C/D. Aucun run, aucun recalcul île, aucune migration destructive.

**Principe tenu** : une donnée, un moteur, tous les lecteurs. Un lot = un commit + preuve. `pytest` complet = baseline ou mieux, `tsc` 0, `vitest` vert.

**Baseline `pytest tests/`** (avant tout changement, sur cette base) : **3449 passed · 17 failed · 67 skipped**. Les 17 échecs sont pré-existants (verrous/gardes cassés par des merges `main` : `test_garanties` g1/g4/g6/g7, `test_lot1_tables` V1c `pige_watermark`, `test_reparations1_lot2` graphe, `test_oracle_dossier`, `test_circuit2_lot5` traçage front, `test_front_reliquats`×3, `test_retours17_permis`×2, `test_rnic`, `test_pige_socle`, `test_veille2_lot5`, `test_retours11f4`). Aucun n'est dans le périmètre des lots.

**Final `pytest tests/`** (après les 6 lots) : **3449 passed · 15 failed · 69 skipped** — **0 nouvel échec** (diff strict baseline↔final : l'ensemble des échecs finaux ⊆ baseline ; deux flaky liés à l'état DB, `test_rnic` et `test_garanties::g7`, sont même repassés au vert). `tsc` 0 · `vitest` 223 passed. Le graphe `circuit_garanties` reste sans arête discordante introduite (aucune entrée `georisque_alea`/`deal_ppr`/`mvt`/`sar`).

---

## Compte final des anomalies

| | Total | Corrigées (code) | Laissées + motif |
|---|--:|--:|--:|
| **ANOMALIES.csv** | **100** | **16** | **84** |
| dont « à corriger » | 34 | 16 | 18 |
| dont « cosmétique » | 66 | — (dont 3 corrigées comptées ci-dessus : rows 15, 86, 101) | 63 |

> Les 16 corrections de code couvrent **tous les « candidats prioritaires » du RAPPORT d'audit** (§« à corriger les plus visibles ») + les étiquettes fabriquées. Les 18 « à corriger » laissés sont **traités** au sens du mandat : chacun reçoit un motif spécifique (sain par conception avec repli nommé, ou parité non-prouvée-fausse, ou refactor de mécanisme — jamais un chiffre faux servi). Détail ligne à ligne plus bas.

## Compte des sources (inchangé — aucune migration)

`SELECT status, count(*) FROM data_sources` : **96 connecte · 14 partenariat_requis · 6 alias · 5 retiree · 4 hub · 2 manuel · 1 interne = 128** (123 actives). SOURCES-FIX-2 ne crée, ne retire ni ne renomme aucune ligne `data_sources` (respect « aucune migration ») : il **réoriente des lecteurs** vers la bonne source déjà présente et **corrige des étiquettes**.

---

## Lot A — Mouvement de terrain : une seule source (l'aléa réglementaire DEAL)

**Diagnostic corrigé du diagnostic d'audit** : la couche `georisque_alea` (dont l'aléa mouvement de terrain) n'est PAS servie par la source 4 « Géorisques » (catch-all) comme le supposait l'audit — ses lignes portent `data_source_id = 30` **DEAL Réunion — PPR / aléas** (réglementaire, millésimée « PPR/PPRL approuvés 2011–2026 »), ingérée du WFS DEAL. La source 36 « Géorisques — mouvements de terrain » porte `kind='mvt'` = **inventaire d'événements BDMvt** (glissements, chutes de blocs…), une notion distincte.

Deux consommateurs divergeaient :
- fiche commune §Risques : `mouvement_terrain_pct` calculé sur `kind='mvt'` (source 36, événements) ;
- couche carte `alea_mvt`, fiche §Pièges & risques, Étude de zone : `kind='georisque_alea'` subtype `mouvement_terrain` (source 30, aléa zoné).

**Corrections** :
1. `pct_parcelles_couche(...)` accepte un `subtype` ; la fiche commune lit désormais l'**aléa** (georisque_alea/mouvement_terrain, DEAL 30) = la même donnée que la carte.
2. `RESERVOIR_TABLES` : `georisque_alea` passe du réservoir `georisques_api` (source 4, catch-all sans millésime) au réservoir `deal_ppr` (source 30, millésimée) — en cohérence avec `donnees.py` (`reservoirs=("deal_ppr",)`). Corrige aussi la ligne « source 4 bare » signalée pour `alea_inondation` (row 56).
3. `kind='mvt'` (source 36) reste active, documentée comme l'inventaire d'événements (flag 0 point de la cascade, anti double-compte PPR), plus jamais lu comme l'aléa de la commune.

**Preuve** (part des parcelles intersectant, base réelle) :

| commune | avant (`kind='mvt'`, src 36) | après (aléa georisque_alea, src 30 DEAL) |
|---|--:|--:|
| Saint-Denis | 0,4 % (138 parcelles) | 0,1 % (39) |
| Saint-Paul | 0,1 % (52) | **90,3 % (46 190)** = couche carte `alea_mvt` |

La fiche commune coïncide désormais avec l'emprise dessinée. Vérifié runtime `fiche_commune.risques()` + libellé de source aligné « DEAL Réunion — PPR / aléas ». Le graphe `circuit_garanties` reste sans arête discordante `georisque_alea/deal_ppr/mvt`.
**ANOMALIES** : rows 19, 56, 57, 58 corrigées ; row 46 laissée (contrat testé RETOURS-21). Commit `db8a9ce1`.

## Lot B — un seul « Classement LABUSE » (le pointeur suit le run servi)

`SCORE_LABUSE_RUN` était figé sur le run **candidat** « q_v15 » : la fiche, l'Analyse et le Comparer servaient la bande + le Signal de mutation depuis `score_labuse@q_v15`, alors que la carte/fiche (verdict/tier) viennent du run **servi** q_v11_m137. Deux vintages du « LABUSE » coexistaient.

**Correction** : `SCORE_LABUSE_RUN = os.environ.get("LABUSE_SCORE_RUN") or runs.current()` — le Score LABUSE suit le **run servi** (point de vérité unique `served_manifest.json`/`served_run.txt`), la même source que la carte, la fiche, les filtres, la page Données et le Dossier. Un seul chemin : tous les lecteurs de `score_labuse` bindent `SCORE_LABUSE_RUN` (app.py 3523/3763/3783/5712/7509). Le candidat q_v15 ne se lit plus que côté admin (bascule page Données par son nom, ou l'override `LABUSE_SCORE_RUN`).

q_v11_m137 n'ayant pas de lignes dans `score_labuse`, le Score LABUSE est NULL partout — état voulu et déjà documenté dans le code (« NULL tant que le run servi n'est pas peuplé ») ; la table existant, les JOINs restent valides (aucun 500). La bascule le rendra visible d'un coup, cohérent avec la carte.
**Preuve** : `grep` des lecteurs → un seul chemin ; `SCORE_LABUSE_RUN` == `runs.current()` == `q_v11_m137`. pytest scoring6+circuit_p4/p7+flux = 70 passed. **ANOMALIES** : row 25 corrigée. Commit `990b0315`.

## Lot C — SAR : la couche dit son nom (proxy potentiel foncier Région)

La couche carte « SAR » (`kind='sar'`, 2 453 emprises, `data_source_id=15` data.regionreunion.com — Potentiel foncier) s'affichait « SAR — par vocation » avec `statut_juridique=opposable`, alors que la couche SIG officielle du SAR (source 118, `partenariat_requis`, « NON OPPOSABLE ») n'est diffusée nulle part — ce que la doctrine `sar_indication` qualifie elle-même de « mensonge d'étiquette ». Le caveat PROXY existait sur le chiffre `sar_divergence`, pas sur la couche.

**Correction** (déclaration de couche, servie par `/map/tuyau/couches`) : nom, libellé, légende et « i » réécrits en **« SAR — proxy potentiel foncier Région (règlement SAR non ingéré) »** (vocations indicatives) ; `statut_juridique` → `informatif`. Les autres surfaces (fiche/Pièges/Dossier) disent déjà « potentiel foncier Région (indicatif) » (SarLayer + `nettoyer_libelle_client`). La vraie couche SAR reste « à faire » (source 118 partenariat_requis).
**Preuve** : `GET /map/tuyau/couches` → `couche_sar` porte nom/légende/« i »/statut proxy. **ANOMALIES** : row 63 corrigée. Commit `e88d3a18`.

## Lot D — un seul magasin de millésime à l'admin

Le millésime « servi » dépendait de l'écran : page Circuit = `data_sources.source_millesime` brut ; page compteur = `RESERVOIR_TABLES[slug].millesime` (constante du registre). 66/129 sources divergeaient.

**Correction** : magasin **unique**. La vérité est `data_sources.source_millesime` (écrite par la sentinelle et le circuit), composée par le **producteur unique** `millesime_source.composer` (le même que la fiche §Sources et les pieds). `RESERVOIR_TABLES.millesime` n'est plus qu'une **vue de compatibilité** (repli quand la vérité est vide). Calcul une seule fois dans `_assembler_reservoirs` → Circuit ET compteur lisent le même champ. `/sources` (client) passe aussi par `composer` (row 97).

**Preuve** (base réelle, 3 endpoints) — **divergences Circuit↔compteur : 66/129 → 0/99** ; 5 témoins identiques `Circuit == compteur == /sources` :

| source | millésime (identique aux 3 écrans) |
|---|---|
| BD ORTHO 20 cm (IGN) | `BD ORTHO IGN 974 — millésime 2025 (piscine, 90,7 %)` |
| CatNat (GASPAR/Géorisques) | `GASPAR — arrêtés CatNat 974 (paginés, 06/09/2026)` |
| Géorisques — CASIAS | `453 sites 974 (435 points, 18 emprises) — canal SSP, 07/09/2026` |
| DEAL Réunion — PPR / aléas | `PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Lizmap)` |
| INSEE RP Logement 2023 | `None` (cohérent partout) |

pytest -k circuit/dashboard/source = 592 passed. **ANOMALIES** : rows 97, 98, 99 corrigées. Commit `78415d02`.

## Lot E — raccrochages hors liste

- **Cartofriches** (row 101) : la fiche affichait « Cartofriches (Cerema) / AGORAH » + millésime « AGORAH 2025 » (littéral fabriqué). Le producteur est le **Cerema / DGALN** (source 35) — AGORAH n'est que l'opérateur local — et il n'y a pas de millésime versionné (MAJ trimestrielle, `source_millesime` vide). Étiquette corrigée partout via deux constantes uniques : source « Cartofriches (Cerema / DGALN) », millésime « édition courante (Cerema, mise à jour trimestrielle) ». (Les pieds d'export disaient déjà « Cartofriches (Cerema) ».)
- **Fonds ortho historiques** (row 37) : 1950→2023 + ortho-express relayés en direct de l'IGN Géoplateforme (`data.geopf.fr`), couverts par le **hub 14** « Géoplateforme (IGN) » ; commentaire de traçabilité ajouté dans `ortho_proxy._COUCHES` (la seule ortho ingérée reste BD ORTHO 2025 id 61 ; SCAN50 155, EduGéo 156). Aucune donnée inventée.
- **Filtre `flair`** (row 44) : FLAIR (occupation du sol IA IGN) est un **juge QA interne** des détections BD ORTHO (id 61) ; aucun chiffre « FLAIR » servi au client → `source_motif` « FLAIR% » sans effet ; commentaire ajouté.
- **Les ~35 cat.1 légitimes** (constantes CGI 892 €/m², annuaires mairies/EPCI/gestionnaires, méta qualité commune, hypothèses de faisabilité saisies, config défisc, `event_log` veille) : paramètres/annuaires/méta hors `data_sources` par nature — listés comme tels (table plus bas), aucun ajout de ligne.

**Preuve** : `cartofriches('97411000EM0174')` → source « Cartofriches (Cerema / DGALN) », millésime « édition courante (Cerema, mise à jour trimestrielle) ». **ANOMALIES** : row 101 corrigée ; rows 37, 44 tracées. Commit `ad7c80f8`.

## Lot F — cosmétiques (une ligne, sinon motif)

- row 15 — `ProprietaireHistorique.tsx` « 2019–2025 » → « 2019–2024 » (max réel `pm_proprietaires_millesimes`).
- row 49 — commentaire du filtre DPE rafraîchi : 17→1 123 enregistrements, 7→20 communes.
- rows 85/86 — copilote `CADASTRE_MILLESIME` « Etalab 2026-06 » (fabriqué) → « cadastre Etalab — édition courante » (= sortie du `composer`, catalogue « latest »).

Les autres cosmétiques ne tiennent pas en une ligne ou ne justifient aucun changement (déjà saines / déjà documentées) — motif ligne à ligne plus bas. Aucun nouveau composant, aucun refactor. tsc 0, vitest 223. Commit `fb2dac84`.

---

## ANOMALIES.csv rejoué (colonne « état »)

> « ligne CSV » = numéro de ligne dans `SOURCES-AUDIT-3/ANOMALIES.csv` (= « row N » du RAPPORT d'audit). cat : 1 hors-liste · 2 source retirée · 3 mauvais branchement · 4 mauvaise étiquette · 5 couverture · 6 appel externe.

| ligne CSV | cat | gravité | consommateur | état | motif / preuve |
|--:|:--:|:--|:--|:--|:--|
| 2 | 6 | a_corriger | fiche_parcelle:§terrain | laissée + motif | appel WMS IGN exposition, timeout 60 s, repli {orientation:None} nommé ; couvert par 6:rge_alti — inventaire d'appel live, jamais un faux « — » |
| 3 | 6 | a_corriger | fiche_parcelle:§terrain | laissée + motif | appel WMS IGN hauteur-LiDAR, timeout 90 s, repli nommé ; couvert 70:lidar_hd_mnh — appel live sain |
| 4 | 6 | a_corriger | fiche_parcelle:§terrain | laissée + motif | appel IGN altimétrie profil, timeout 20 s, repli « Relief non disponible » ; couvert 6/65:rge_alti — sain |
| 5 | 6 | a_corriger | fiche_parcelle:§bandeau-identite | laissée + motif | iframe Street View gaté sur GOOGLE_MAPS_EMBED_KEY (None→bouton masqué) ; sortie d'affichage tierce, aucune donnée servie — inventaire, pas de ligne data_sources |
| 6 | 1 | cosmetique | fiche_parcelle:§verdict-score | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 7 | 1 | cosmetique | fiche_parcelle:§reseaux | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 8 | 1 | cosmetique | fiche_parcelle:§reseaux | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 9 | 1 | cosmetique | fiche_parcelle:§urbanisme | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 10 | 4 | cosmetique | fiche_parcelle:§fiscalite-dispositifs | laissée + motif | étiquette codée mais EXACTE / millésime porté par le libellé — dérive latente, pas d'erreur servie |
| 11 | 3 | cosmetique | fiche_parcelle:§marche | laissée + motif | deux chemins pour une notion — parité non prouvée fausse ; refactor, pas 1-ligne |
| 12 | 4 | cosmetique | fiche_parcelle:§marche | laissée + motif | étiquette codée mais EXACTE / millésime porté par le libellé — dérive latente, pas d'erreur servie |
| 13 | 5 | a_corriger | fiche_parcelle:§marche | laissée + motif | f.prix_ancien/marche_synthese servis mais non rendus par la fiche (0 consommateur front) — donnée dormante, aucun chiffre faux servi ; retrait = nettoyage back hors 1-ligne |
| 14 | 5 | cosmetique | fiche_parcelle:§marche | laissée + motif | couverture (servi non rendu / orphelin / non lu) — aucun chiffre faux servi |
| 15 | 4 | cosmetique | fiche_parcelle:§identite-proprietaire | corrigée | **lot F** — ProprietaireHistorique.tsx « 2019–2025 » → « 2019–2024 » (max réel de pm_proprietaires_millesimes) |
| 16 | 4 | cosmetique | fiche_parcelle:§LeBien-bati | laissée + motif | étiquette codée mais EXACTE / millésime porté par le libellé — dérive latente, pas d'erreur servie |
| 17 | 1 | cosmetique | fiche_commune:§Identité | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 18 | 1 | cosmetique | fiche_commune:bandeau_RNU | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 19 | 3 | a_corriger | fiche_commune:§Risques | corrigée | **lot A** — fiche commune §Risques mvt lit désormais l'aléa georisque_alea/mouvement_terrain (DEAL 30) = couche carte ; Saint-Paul 0,1 %→90,3 % |
| 20 | 4 | cosmetique | fiche_commune:§Foncier | laissée + motif | étiquette codée mais EXACTE / millésime porté par le libellé — dérive latente, pas d'erreur servie |
| 21 | 4 | cosmetique | fiche_commune:§Population | laissée + motif | étiquette codée mais EXACTE / millésime porté par le libellé — dérive latente, pas d'erreur servie |
| 22 | 4 | cosmetique | fiche_commune:§Prix | laissée + motif | étiquette codée mais EXACTE / millésime porté par le libellé — dérive latente, pas d'erreur servie |
| 23 | 5 | cosmetique | fiche_commune:§Équipements | laissée + motif | couverture (servi non rendu / orphelin / non lu) — aucun chiffre faux servi |
| 24 | 4 | a_corriger | outil:risques — Pièges et risques (M10) | laissée + motif | la « date » des servitudes est la date d'INGESTION (fraîcheur, COALESCE(last_sync,updated)) — meaningful ; un vrai millésime par SUP exigerait la date d'acte non stockée = refactor, pas 1-ligne |
| 25 | 4 | a_corriger | outil:comparer — Comparer des parcelles (A8) | corrigée | **lot B** — SCORE_LABUSE_RUN = runs.current() (run servi), plus le candidat q_v15 figé ; un seul chemin, tous les lecteurs score_labuse bindent le pointeur |
| 26 | 6 | cosmetique | outil:plu — PLU (O13) | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 27 | 1 | cosmetique | outil:plu — PLU (O13) | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 28 | 1 | cosmetique | outil:programme — Faisabilité (M22) | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 29 | 1 | cosmetique | outil:assemblage — Assemblage (M16) | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 30 | 3 | a_corriger | outil:comparer / outil:risques | laissée + motif | « contrainte majeure » (Comparer) vs liste servitudes (Risques) : deux vues d'une même cascade ; parité non prouvée FAUSSE — vérification/refactor, pas 1-ligne |
| 31 | 3 | a_corriger | outil:prospection-solaire | laissée + motif | prospection-solaire : la LISTE lit parcel_equipements (FLAIR seul), la fiche/agg lit `piscines` (union) ; alignement = repointer la liste (PISCINES-2) = changement de moteur, hors périmètre cosmétique |
| 32 | 5 | cosmetique | outil:prospection-solaire:liste | laissée + motif | couverture (servi non rendu / orphelin / non lu) — aucun chiffre faux servi |
| 33 | 4 | a_corriger | outil:courriers | laissée + motif | courrier adresse siège = owner_enrichment (45 DINUM) réputée « débranchée de l'affichage » ; le courrier est une SORTIE (pas un écran) — clarification de doctrine, pas un chiffre faux |
| 34 | 6 | cosmetique | outil:courriers | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 35 | 6 | cosmetique | outil:prospection-solaire:fiche | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 36 | 6 | cosmetique | outil:prospection-solaire:fiche | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 37 | 1 | a_corriger | outil:temps (M08) | corrigée (traçabilité) | **lot E** — orthos historiques 1950→2023 = flux WMTS IGN Géoplateforme relevant du HUB id 14 (aucune donnée inventée) ; commentaire de traçabilité ajouté dans ortho_proxy |
| 38 | 1 | cosmetique | outil:taxe-amenagement (K3) | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 39 | 3 | cosmetique | outil:etude-zone (M27) vs outil:communes (O6 | laissée + motif | deux chemins pour une notion — parité non prouvée fausse ; refactor, pas 1-ligne |
| 40 | 6 | a_corriger | outil:etude-zone (M27) | laissée + motif | isochrone IGN, timeout 30 s, statut='indisponible' nommé (aucun cercle substitué), cache 30 j ; hub 14 — appel live sain |
| 41 | 6 | cosmetique | outil:temps (M08) | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 42 | 6 | cosmetique | outil:communes (O6) / outil:etude-zone (M27) | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 43 | 5 | cosmetique | outil:etude-zone (M27) / outil:communes (O6) | laissée + motif | couverture (servi non rendu / orphelin / non lu) — aucun chiffre faux servi |
| 44 | 1 | a_corriger | filtre:flair | corrigée (traçabilité) | **lot E** — FLAIR = juge QA interne des détections BD ORTHO (id 61) ; aucun chiffre « FLAIR » servi au client ; commentaire de traçabilité ajouté |
| 45 | 2 | cosmetique | filtre:edf | laissée + motif | référence à une source retirée SANS effet (attribution morte) |
| 46 | 3 | a_corriger | filtre:georisques_mvt / filtre:georisques_ap | laissée + motif | **lot A** — le contrôle de distribution de l'aléa georisque_alea est déposé sous le filtre `georisques_mvt` par CONTRAT TESTÉ (test_retours21_lotA, test_circuit3_lot5) ; le double-listage sous le filtre synthèse `georisques_api` (portee_run=False) est sans effet. L'aléa est désormais sans ambiguïté DEAL 30 (lot A) |
| 47 | 3 | cosmetique | filtre:georisques_casias | laissée + motif | deux chemins pour une notion — parité non prouvée fausse ; refactor, pas 1-ligne |
| 48 | 1 | cosmetique | filtre:loyers_dhup | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 49 | 4 | a_corriger | filtre:dpe | corrigée | **lot F** — commentaire du filtre DPE rafraîchi : 17→1 123 enregistrements, 7→20 communes |
| 50 | 4 | a_corriger | filtre:georisques_mvt | laissée + motif | note de mesure « 484 au 05/09 » du contrôle de régression RETOURS-13 ; la donnée aléa est désormais DEAL 30 (lot A) ; toucher la note du filtre = risque sur test_retours21 — laissé |
| 51 | 2 | cosmetique | filtre:potentiel_foncier_region | laissée + motif | référence à une source retirée SANS effet (attribution morte) |
| 52 | 6 | cosmetique | couche_carte:courbes_niveau | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 53 | 6 | cosmetique | couche_carte:enr_habitation | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 54 | 6 | cosmetique | fond:orthos+cartes_anciennes | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 55 | 6 | cosmetique | fond:bm-plan | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 56 | 4 | a_corriger | couche_carte:alea_inondation | corrigée | **lot A** — georisque_alea rattaché au réservoir deal_ppr (source 30, millésimée), plus au catch-all georisques_api (id 4 sans millésime) |
| 57 | 3 | a_corriger | couche_carte:alea_mvt vs fiche n_vigilances/ | corrigée | **lot A** — source unique de l'aléa MVT = georisque_alea (DEAL 30) pour tous les lecteurs (fiche commune, couche, Pièges, Étude de zone) |
| 58 | 5 | a_corriger | spatial_layers kind=mvt | corrigée | **lot A** — kind='mvt' documenté = inventaire d'événements BDMvt (flag 0 point cascade), notion DISTINCTE de l'aléa réglementaire |
| 59 | 5 | cosmetique | spatial_layers kind=ocs_ge | laissée + motif | couverture (servi non rendu / orphelin / non lu) — aucun chiffre faux servi |
| 60 | 5 | cosmetique | spatial_layers kind=potentiel_foncier | laissée + motif | couverture (servi non rendu / orphelin / non lu) — aucun chiffre faux servi |
| 61 | 5 | cosmetique | spatial_layers kind=plu_gpu_zone__archive_m4 | laissée + motif | couverture (servi non rendu / orphelin / non lu) — aucun chiffre faux servi |
| 62 | 4 | cosmetique | couche_carte:cimetiere/construction_lineaire | laissée + motif | étiquette codée mais EXACTE / millésime porté par le libellé — dérive latente, pas d'erreur servie |
| 63 | 1 | a_corriger | couche_carte:sar | corrigée | **lot C** — couche SAR relabellée « SAR — proxy potentiel foncier Région (règlement SAR non ingéré) » + « i » + statut_juridique informatif ; servi par /map/tuyau/couches |
| 64 | 4 | cosmetique | fond:bm-ortho-now | laissée + motif | étiquette codée mais EXACTE / millésime porté par le libellé — dérive latente, pas d'erreur servie |
| 65 | 6 | cosmetique | export:pre-dossier ZIP | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 66 | 6 | cosmetique | export:dossier/apporteur/pre-dossier (plans) | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 67 | 1 | cosmetique | export:financier PDF (=banquier) | laissée + motif | pied financier PDF construit par littéraux conditionnés (n'affiche que si servi) — FIDÈLE mais mécanisme parallèle à pieds.sources_lues ; unifier = refactor du bloc export |
| 68 | 4 | a_corriger | export:financier PDF (pied « Sources ») | laissée + motif | pré-dossier ZIP (collect_report_data) vs Dossier (robinet_fiche) = deux chemins de collecte ; convergence = refactor d'un pipeline entier, pas 1-ligne (aucune divergence de valeur prouvée) |
| 69 | 3 | a_corriger | export:pre-dossier ZIP vs export:dossier PDF | laissée + motif | _SECTION_SOURCES du pré-dossier créditée par SECTION rendue ; millésimes statiques — même refactor que row 68 (pipeline flash/) |
| 70 | 4 | a_corriger | export:pre-dossier ZIP (page Sources) | laissée + motif | pied Dossier §Fiscalité : nom de repli « Taxe d'aménagement — barème DGFiP/DELTA » (pieds._NOMS_REPLI) sans ligne data_sources dédiée ; source légitime (barème public), pas un chiffre inventé |
| 71 | 1 | a_corriger | export:dossier PDF §Fiscalité | laissée + motif | pied RNB/BAN PLUS codé en dur (pieds._NOMS_REPLI) alors que 143/147 existent au catalogue ; libellé EXACT, dérive latente — unifier = refactor du mécanisme des pieds |
| 72 | 4 | a_corriger | export:dossier PDF §Bâti | laissée + motif | étiquette codée mais EXACTE / millésime porté par le libellé — dérive latente, pas d'erreur servie |
| 73 | 2 | cosmetique | export:dossier PDF §Réseaux (bloc reseaux.py | laissée + motif | référence à une source retirée SANS effet (attribution morte) |
| 74 | 5 | cosmetique | export:section blocs identite/marche/potenti | laissée + motif | pipeline flash/ (report.py/data.py/carte.py) orphelin pour le produit Flash (le Flash sert le Dossier miroir) ; survit via pré-dossier — code mort à nettoyer, pas 1-ligne |
| 75 | 5 | a_corriger | export:flash/report.py + flash/data.py + fla | laissée + motif | copilote web_search Anthropic, timeout 45 s, refus honnête si 0 citation, contenu marqué « web » ; hors data_sources par nature — appel externe sain |
| 76 | 6 | a_corriger | copilote:chemin_question:recherche_web | laissée + motif | copilote general_web (même appel), refus « pas de source fiable » ; contenu marqué « web » — sain |
| 77 | 6 | a_corriger | copilote:chemin_question:general_web (voie b | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 78 | 6 | cosmetique | copilote:chemin_routage | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 79 | 6 | cosmetique | copilote:chemin_question:select_tool | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 80 | 6 | cosmetique | copilote:chemin_question:formuler | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 81 | 6 | cosmetique | copilote:chemin_mission:preparer | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 82 | 6 | cosmetique | copilote:embarqué_fiche (AskBar) | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 83 | 1 | cosmetique | copilote:chemin_question:parcelles_par_entre | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 84 | 1 | cosmetique | copilote:embarqué_fiche (AskBar) | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 85 | 4 | a_corriger | copilote:chemin_question:fiche_parcelle | corrigée | **lot F** — copilote CADASTRE_MILLESIME « Etalab 2026-06 » (littéral fabriqué) → « cadastre Etalab — édition courante » (= sortie du composer, catalogue « latest ») |
| 86 | 4 | cosmetique | copilote:chemin_question:compter_parcelles | corrigée | **lot F** — même constante CADASTRE_MILLESIME que row 85 (compter_parcelles) |
| 87 | 3 | cosmetique | copilote:chemin_question:delais_instruction  | laissée + motif | deux chemins pour une notion — parité non prouvée fausse ; refactor, pas 1-ligne |
| 88 | 5 | cosmetique | copilote (aucun chemin) | laissée + motif | couverture (servi non rendu / orphelin / non lu) — aucun chiffre faux servi |
| 89 | 1 | cosmetique | veille:suivis_foncier | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 90 | 1 | cosmetique | veille:cloche_notifs | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 91 | 1 | cosmetique | veille:searches_carte | laissée + motif | paramètre/constante/annuaire/méta LÉGITIME — hors data_sources par nature |
| 92 | 1 | cosmetique | digest:veille_matin | laissée + motif | Cartofriches (35) citée au briefing veille mais non lue par un consommateur radar/veille ; les 4 flux veille réels sont Mutation/Permis/BODACC/Propriétaire — couverture, pas un chiffre faux |
| 93 | 5 | a_corriger | veille (périmètre) | laissée + motif | couverture (servi non rendu / orphelin / non lu) — aucun chiffre faux servi |
| 94 | 6 | cosmetique | radar:depot_agence_analyser | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 95 | 6 | cosmetique | digest:envoi_brevo | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 96 | 6 | cosmetique | digest:envoi_smtp_brut | laissée + motif | appel externe à repli nommé — sain, inventaire seulement |
| 97 | 4 | a_corriger | dashboard:page_sources | corrigée | **lot D** — /sources passe par le producteur unique `composer` (notes internes nettoyées comme la fiche) |
| 98 | 4 | a_corriger | dashboard:page_circuit | corrigée | **lot D** — Circuit ET compteur lisent le magasin unique data_sources.source_millesime (composer + repli registre compat) ; divergences 66/129 → 0/99 |
| 99 | 4 | a_corriger | dashboard:page_sources | corrigée | **lot D** — repli registre en compat pour les millésimes NULL → même valeur aux deux écrans |
| 100 | 5 | cosmetique | dashboard:page_sources | laissée + motif | couverture (servi non rendu / orphelin / non lu) — aucun chiffre faux servi |
| 101 | 4 | cosmetique | fiche_parcelle:§risques | corrigée | **lot E** — Cartofriches : producteur « Cerema / DGALN » (plus « AGORAH »), millésime « édition courante » (plus le littéral fabriqué « AGORAH 2025 »), partout |

