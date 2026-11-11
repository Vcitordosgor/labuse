# Scan patrimoine

Clé interne : `patrimoine` (num M02) · composant : `frontend/src/components/outils/ScanPatrimoine.tsx` · endpoints : `/modules/patrimoine`, `/modules/patrimoine/search` (back `src/labuse/api/modules.py`) ; onglet « Construction » : `/outils/veille-promoteurs`, `/outils/veille-promoteurs/{siren}/frise`, `/outils/veille-promoteurs/{siren}/acquisitions` (back `src/labuse/api/veille_promoteurs.py`).

L'outil a DEUX chemins (deux onglets, propriétaire partagé) :
- **« Ce qu'il possède » (Possession)** — module M02, endpoint `/modules/patrimoine`.
- **« Ce qu'ils construisent » (Construction)** — ex-outil « Veille promoteurs » absorbé (alias caché `veille-promoteurs`, SECTEUR S3), endpoints `/outils/veille-promoteurs/*`.

L'accueil ouvre sur deux PORTES (`ScanPatrimoine.tsx:167-174`) : « Un propriétaire » (recherche → ses deux onglets) et « Toutes les opérations de l'île » (exploration générale, qui rend `<VeillePromoteurs embedded />` sans propriétaire ciblé, `ScanPatrimoine.tsx:179`).

---

## 1. À quoi il sert, et pour qui
Scan patrimoine montre, pour une PERSONNE MORALE (société, commune, bailleur…), tout le foncier qu'elle DÉTIENT à La Réunion (onglet Possession) et tout ce qu'elle CONSTRUIT, c'est-à-dire ses opérations de permis groupées (onglet Construction). Il vise les notaires, agences, apporteurs d'affaires et prospecteurs fonciers qui veulent cartographier un propriétaire ou un promoteur ; il ne touche JAMAIS un particulier (RGPD : `modules.py:297` « PM UNIQUEMENT (RGPD : jamais un particulier) »).

## 2. Le parcours
Un seul champ de saisie, en deux temps (`ScanPatrimoine.tsx:1-11`, `180-226`).

**Chemin Possession (M02)**
- L'utilisateur saisit un nom de société, un SIREN/SIRET, une adresse ou un IDU. La résolution (`resoudre`, `ScanPatrimoine.tsx:94-129`) : 9 chiffres → SIREN direct ; 14 chiffres (SIRET) → les 9 premiers ; IDU → propriétaire moral de la fiche (`ownerDeIdu`, lit `proprietaire_moral.siren`, `ScanPatrimoine.tsx:84-89`) ; sinon nom → `/modules/patrimoine/search` ; si le nom ne matche rien → repli adresse (BAN → parcelle → propriétaire).
- Si PLUSIEURS sociétés matchent un nom, l'écran liste `nom · SIREN · nb parcelles` et laisse choisir — plus d'auto-sélection du plus gros (`ScanPatrimoine.tsx:196-210`).
- Une fois le propriétaire retenu : encart en tête (raison sociale + SIREN + « changer »), onglets soulignés Possession / Construction.
- L'onglet Possession (`M02` dans `ModulePanel.tsx:179-379`) affiche un accordéon « Chiffres clés » (parcelles, surface totale, nus/bâtis, zone U ou AU), d'éventuels encarts d'approche (BODACC, « aucun dirigeant INPI »), les « Blocs contigus », puis la liste paginée des parcelles (commune · surface · SDP · « occupé par N établissements »), 200 par page. Un bouton « Voir ses parcelles → » replie les chiffres pour dérouler la liste.
- Si le SIREN est résolu mais ne détient rien à La Réunion : message explicite « ne détient aucune parcelle » (`ModulePanel.tsx:226-233`).

**Chemin Construction (Veille promoteurs embarquée, `VeillePromoteurs.tsx`)**
- Mode STRICT quand un propriétaire est ciblé (`strict = embedded && focusSiren`, `VeillePromoteurs.tsx:111`) : ni filtres, ni total de l'île — seulement SES opérations.
- Affiche « N opérations · M logements — construit ou en cours, permis depuis AAAA · Sitadel au JJ/MM/AAAA » (`VeillePromoteurs.tsx:260`). Une carte par promoteur (regroupée par SIREN), dépliable : liste des opérations (commune · logements · permis · date · état), programmes rattachés (nom + lien externe), et deux boutons « Voir son patrimoine → » (bascule d'onglet) / « Sa frise ».
- La « frise » (`/{siren}/frise`) : opérations et logements année par année + encart « En pétitionnaire : N permis » + filiales INPI + renvoi vers le patrimoine foncier.
- Porte « Toutes les opérations » : filtres commune / catégorie / période ; chaque opération est un POINT sur la carte.

## 3. Les données lues

| Source (catalogue) | Table SQL réellement lue | Millésime servi | Cadence |
|---|---|---|---|
| DGFiP — parcelles des personnes morales | `parcelle_personne_morale` (colonnes `siren`, `denomination`, `groupe`, `millesime`, `idu`) ; JOIN `parcels` | `millesime = '2025'` (uniforme, confirmé psql) | annuelle (panel 2019→2025, situation 1er janvier) |
| SITADEL (autorisations d'urbanisme) | `sitadel_permits` (`idu_codes`, `raw->>'nb_lgt'`, `etat`, `daact`, `date_depot`, `geom`, `petitioner_siren`) | `max(date_depot) = 2026-08-31` (servi comme « millesime ») | mensuelle |
| INPI RNE (dirigeants) | `pm_dirigeants` (`siren`, `gerant_siren`, `actif`) — 27 037 lignes | — (batch, non versionné) | — |
| BODACC (procédures collectives) | vue `v_foncier_sous_pression` (`modules.py:325`) | — | — |
| BODACC dépôts de comptes | `bodacc_depots` (`date_cloture`, `date_parution`) — 14 078 lignes (`modules.py:266`) | — | — |
| DVF / valeurs foncières | `dvf_mutations_parcelle` × `parcel_zone_plu` via `ligne2_terrain_zone` (`marche_commune.py:100`) — pour la valorisation du foncier nu | géo-DVF Etalab 2026-S1 | semestriel |
| SIRENE établissements géolocalisés | `etablissement_parcelle` (`modules.py:490`) — « occupé par N établissements » | mensuelle | mensuelle |
| Radar (annonces) | `pige_biens` (`veille_promoteurs.py:153`) — « annonce neuve Radar rattachée » | — | — |
| Programmes collectés | `programmes` (`veille_promoteurs.py:165, 236`) | — | — |
| Blocs fonciers | `parcel_blocs` / `parcel_bloc_membres` (`modules.py:448`) | — | — |

**Zonage / scoring secondaires** (onglet Possession) : `parcel_zone_plu` (zone_fam U/AU), `p_model_bati` (emprise bâtie → nu/bâti), `parcel_residuel` (SDP résiduelle), `parcel_p_score_v2` (tier/rang), `dryrun_parcel_evaluations` (étage 0 cascade).

**Source listée au brief mais NON lue par ces endpoints : « DFI — documents de filiation ».** `grep` sur `modules.py` et `veille_promoteurs.py` ne trouve aucune lecture de table de filiation. Ces endpoints ne reconstruisent donc pas de chaîne de filiation.

## 4. Les calculs
L'outil est presque entièrement des COMPTES SQL (sourcé). Les rares calculs :

- **Surface totale détenue** (Possession) : somme des CONTENANCES cadastrales (acte), pas des surfaces de dessin (`modules.py:388-390`, via `_surface.surface_terrain(surface_m2, contenance_m2)`). Arrondi à l'entier.
- **Terrains nus / bâtis** : `emprise_bati_m2 > 0` → bâti, sinon nu (`modules.py:391-392`, source `p_model_bati`).
- **N actionnables** : parcelles dont `tier_v2 ∈ _TIERS_ACTIONNABLES` (`brulante, chaude, reserve_fonciere, a_creuser, priorite, a_suivre, sans_signal`, `modules.py:244-245`), hors étage 0, hors écartées par le compte courant (`modules.py:380-381`).
- **Valorisation indicative du foncier nu** (`val_nu`, `modules.py:405-413`) : pour les seules parcelles en zone U/AU, `surface_terrain × prix médian €/m² de la zone` (référentiel `ligne2_terrain_zone`, un prix par commune×zone, issu de DVF terrain nu). **ESTIMÉ** (c'est une médiane de marché appliquée à la surface, pas un prix observé de la parcelle). Rendu `None` si aucune parcelle valorisable.
- **Assiette contiguë / blocs** : plus gros ensemble de parcelles du portefeuille à contact cadastral (`ST_DWithin(geom_2975, ADJ_BUFFER_M)`, `modules.py:419-443`) ; blocs = table pré-bâtie `parcel_blocs`.
- **Dépôt de comptes muet** : `depuis_ans ≥ SEUIL_DEPOT_MUET_ANS` (valeur **3**, codée en dur `modules.py:251`, origine : seuil interne, ex-front Successions) → « société en sommeil probable ».

**Opérations (Construction)** — un regroupement algorithmique (`_operations`, `veille_promoteurs.py:65-173`) :
- Candidats = permis SITADEL avec ≥ 1 logement (`nb_lgt ~ '^[0-9]+$'` et `≥ 1`), dont une parcelle appartient à une PM de groupe MAJIC 0/5/6 (`veille_promoteurs.py:70-71`).
- Deux permis sont dans la MÊME opération s'ils ont le même SIREN, des centroïdes à **≤ 250 m** (`OP_CONTIG_M`, codé en dur `veille_promoteurs.py:34`) ET des dépôts dans **≤ 24 mois** (`OP_PERIODE_MOIS`, `veille_promoteurs.py:35`). Agrégation par union-find.
- Distance : conversion deg→m approchée à la latitude ~-21° (`veille_promoteurs.py:103-106`) — **estimé** (pas de vraie géodésie PostGIS ici).
- Logements de l'opération = somme des `nb_lgt` membres ; état = « travaux achevés » si DAACT présente ou `etat=6` sur un membre, sinon `etat_libelle` du permis le plus récent (`veille_promoteurs.py:128-134`, source unique `ingestion/permits.py:100`).
- Plafond de service : **200** (`PLAFOND`, `veille_promoteurs.py:36`).

Catégories MAJIC : groupe 0 = promoteur, 5 = bailleur social, 6 = SEM (`veille_promoteurs.py:23-28`, origine : labels de la base MAJIC).

## 5. Chaque chiffre affiché

**Onglet Possession**
| Libellé à l'écran | D'où il vient | Sourcé / estimé |
|---|---|---|
| « N parcelles » | `count(*)` de `parcelle_personne_morale JOIN parcels` | sourcé |
| « surface totale » (m²) | Σ contenances cadastrales | sourcé |
| « terrains nus / bâtis » | emprise bâtie `p_model_bati` | sourcé |
| « en zone U ou AU » | `zone_fam` `parcel_zone_plu` | sourcé |
| « N actionnables » | compte sur `tier_v2` (scoring) | sourcé (dérivé du scoring LABUSE) |
| « valorisation nu » (€) | surface × médiane €/m² DVF zone | **estimé** |
| « Fichiers fonciers DGFiP · situation 2025 » | `parcelle_personne_morale.millesime` | sourcé |
| « Dépôt de comptes — dernier exercice AAAA » / « aucun dépôt depuis N ans » | `bodacc_depots` | sourcé (le « sommeil probable » = interprétation du seuil 3) |
| « ● BODACC — procédure » | `v_foncier_sous_pression` | sourcé |
| « Aucun dirigeant au registre INPI » | absence dans `pm_dirigeants` | sourcé (le « succession / sommeil » = interprétation) |
| « Blocs contigus : N » | `parcel_blocs` | sourcé |
| par parcelle : commune · surface · SDP · « occupé par N établissements » | `parcels`, `parcel_residuel`, `etablissement_parcelle` | sourcé |

**Onglet Construction**
| Libellé à l'écran | D'où il vient | Sourcé / estimé |
|---|---|---|
| « N opérations » | `n_total` = nb de groupes union-find | sourcé (mais regroupement = heuristique) |
| « M logements » | Σ `nb_lgt` SITADEL | sourcé |
| « permis depuis AAAA » | plus ancienne `date_min` des opérations servies | sourcé |
| « Sitadel au JJ/MM/AAAA » | `max(date_depot)` | sourcé |
| par opération : commune · N lgt · N permis · date · état | SITADEL agrégé | sourcé ; état décodé (`etat_libelle`) |
| frise : N op / N lgt par année | agrégat des opérations | sourcé |
| « En pétitionnaire : N permis · M logements » | `sitadel_permits.raw->>'petitioner_siren'` (2013+) | sourcé |
| « +N permis via K filiales identifiées » | `pm_dirigeants.gerant_siren` × SITADEL | sourcé (lien de gérance INPI) |
| « Patrimoine foncier détenu : N parcelles » | `count(*) parcelle_personne_morale` (SANS JOIN parcels) | sourcé — **mais compte ≠ onglet Possession** (voir Doutes) |
| « annonce neuve Radar rattachée » | `pige_biens` | sourcé |

## 6. Les limites
- **Un seul propriétaire à la fois, PM uniquement.** Jamais un particulier. Une parcelle détenue par un particulier ou non renseignée → « pas de propriétaire personne morale » (cas des témoins BZ1065 et DH0076 ci-dessous).
- **Le linkage « qui construit » est INDIRECT.** L'open SITADEL n'identifie le pétitionnaire que sur ~18 % des permis (note `veille_promoteurs.py:207`). L'outil rattache donc le permis au **propriétaire foncier** de la parcelle, pas au vrai maître d'ouvrage s'il diffère (promoteur via SCI/SNC d'opération non détenue, terrain d'un tiers…).
- **Les opérations livrées puis revendues sortent du compte** (`perimetre_note`, `veille_promoteurs.py:263`) : un promoteur qui a vendu après livraison « perd » ses opérations dans le décompte, qui porte sur les parcelles encore détenues.
- **Regroupement en opérations = heuristique** (250 m / 24 mois, distance approchée) : deux chantiers distincts proches peuvent fusionner ; un chantier étalé > 24 mois peut se scinder. Aucune validation contre une liste officielle d'opérations.
- **La valorisation nu est indicative** (médiane de zone, seules zones U/AU), jamais un prix de la parcelle.
- **Source DFI (filiation) listée au brief mais non exploitée** par ces endpoints.
- **Fraîcheur SITADEL :** le flux s'arrête au 2026-08-31 ; « permis depuis » et les totaux s'arrêtent là.

## 7. Les tests
- `tests/test_patrimoine.py` (backend) garantit : `patrimoine_search` ne lève jamais et retourne nom·SIREN·n (`:37-42`) ; `n_actionnables` exclut les parcelles « écartées par vous » (`:45-74`) ; l'endpoint ne lève pas, pagine, et nettoie les vestiges `q_score/a_score` (`:77-99`) ; une entreprise sans foncier ne déclenche PAS le faux signal INPI (`:102-111`) ; le signal INPI n'apparaît que sur un propriétaire résolu (`:114-123`). La clé `valorisation_nu_eur` existe mais sa VALEUR n'est pas vérifiée (`None` en base de test, `:88-89`).
- Front : `ScanPatrimoine.test.tsx` — deux portes, liste de choix sans auto-sélection, choix de la plus petite société (`:47-93`). `VeillePromoteurs.test.tsx` — une carte par promoteur, compteurs = somme des opérations (`:46-66`).
- **Non couvert :** l'endpoint `/outils/veille-promoteurs/*` n'a pas de test unitaire dédié (grep ne trouve que des références indirectes dans `test_retours13_lot3.py`, `test_dashboard.py`) ; la RÈGLE de regroupement (250 m / 24 mois, union-find) n'est vérifiée par aucun test ; l'écart entre `n_parcelles` de l'onglet Possession (JOIN parcels) et celui de la frise (sans JOIN) n'est testé nulle part ; la valorisation nu n'a pas de test de valeur.

## 8. Les documents liés (PDF, exports)
- **Export CSV** : `/modules/patrimoine?fmt=csv` (`modules.py:462-481`). Colonnes `idu;commune;tier_v2;rang_v2;surface_m2;sdp_residuelle_m2;siren;raison_sociale`. Il lit **exactement les mêmes lignes `rows`** que l'écran (plafonné à 5 000, notice si au-delà) — donc mêmes valeurs. Rejoué : COMMUNE DE SAINT ANDRE (219740099) → 890 lignes + en-tête, valeurs cohérentes avec l'écran.
- **Pas de PDF pour cet outil.** Le « patrimoine » qui apparaît dans `exports/miroir.py` et `api/pre_dossier.py` concerne le PATRIMOINE BÂTI/ABF d'une parcelle (monuments historiques), pas le portefeuille d'un propriétaire — sans rapport avec M02.

## 9. Trois cas rejoués
Deux des trois parcelles témoins n'ont PAS de propriétaire personne morale, donc l'outil (par propriétaire) ne peut rien afficher pour elles. Je les documente comme cas « pas de PM », puis j'ajoute **CBO TERRITORIA** (SIREN 452038805, l'exemple canonique du front) comme témoin adapté pour montrer les deux onglets peuplés.

**Cas 1 — `97411000BZ1065` (Saint-Denis)** — psql : aucune ligne dans `parcelle_personne_morale`. Résultat outil : « Cette parcelle n'a pas de propriétaire personne morale connu (particulier, ou non renseigné). » (`PAS_DE_PM`, `ScanPatrimoine.tsx:38, 106`).

**Cas 2 — `97409000AK0804` (Saint-André)** — psql : `siren 219740099 · COMMUNE DE SAINT ANDRE` (892 lignes PM). L'outil résout donc la commune comme propriétaire. Export CSV `fmt=csv` rejoué : HTTP 200, 890 lignes, 1re ligne `97409000AX0343;Saint-André;sans_signal;672;423;130;219740099;COMMUNE DE SAINT ANDRE`.

**Cas 3 — `97415000DH0076` (Saint-Pierre/sud)** — psql : aucune ligne PM. Même sortie que le cas 1 (« pas de PM »).

**Témoin adapté — CBO TERRITORIA (452038805), promoteur groupe MAJIC 0.**
- `/modules/patrimoine?siren=452038805` (HTTP 200) : `n_parcelles 1833`, `surface_totale_m2 25 718 185`, `n_terrains_nus 1000`, `n_terrains_batis 833`, `n_constructible_u_au 952`, `n_actionnables 690`, `sdp_residuelle_m2 776 815`, `valorisation_nu_eur 590 828 388` (`n_valorisables 945`), `millesime_majic "2025"`, `depot_comptes {annee 2025, muet false}`, `bodacc null`, `inpi_sans_dirigeant false`, `blocs_contigus.n 210`, `assiette_contigue` 118 parcelles.
- `/outils/veille-promoteurs?siren=452038805` (HTTP 200) : `n_total 21` opérations, `n_logements_total 247`, `millesime 2026-08-31`, règle « ≤ 250 m / ≤ 24 mois ». Op 0 : Sainte-Marie · 15 lgt · 15 permis · 2022-01-04→2026-07-29 · « travaux achevés ».
- `/outils/veille-promoteurs/452038805/frise` (HTTP 200) : `n_operations 21`, `n_logements 247`, en pétitionnaire **108 permis / 1197 logements** (2013+), **2 filiales** identifiées, `scan_patrimoine.n_parcelles 1871`. Frise dès 2013.
- `/outils/veille-promoteurs/452038805/acquisitions` (HTTP 200) : `n_parcelles 1871`, top communes Saint-Paul 857 · Sainte-Marie 453 · Saint-Leu 333.

## 10. Tes doutes
1. **Trois comptes de « parcelles détenues » pour le même SIREN.** `/modules/patrimoine` sert **1833** (JOIN `parcels`), tandis que la frise et `/acquisitions` servent **1871** (`count(*)` brut sur `parcelle_personne_morale`, `veille_promoteurs.py:229, 292`), et la recherche affiche **1833**. Un utilisateur qui passe de l'onglet Possession (« 1833 parcelles ») à l'encart « Patrimoine foncier détenu : 1871 parcelles » (`VeillePromoteurs.tsx:74`) voit deux chiffres contradictoires pour la même société. Aucun test ne verrouille cet écart.
2. **Le linkage « qui construit » peut attribuer des permis au mauvais acteur.** Comme l'opération est rattachée au propriétaire FONCIER de la parcelle (et non au pétitionnaire, absent à ~82 %), un permis sur un terrain détenu par CBO mais construit par un tiers (ou l'inverse) sera compté à CBO. Le périmètre est honnêtement noté, mais l'écran affiche quand même « N opérations » comme un fait.
3. **La règle de regroupement en opérations (250 m / 24 mois, distance deg→m approchée, union-find) n'a aucun test** et peut fusionner/scinder des opérations ; le « net » d'opérations est donc une construction non validée.
4. **La valorisation nu (590 M€ pour CBO) peut être lue comme une estimation de valeur réelle** alors que c'est surface × médiane de zone (DVF) sur les seules zones U/AU — potentiellement très au-dessus ou en dessous du prix réel ; l'étiquette « indicative » est discrète.
5. **Interprétations (« sommeil probable », « succession ») tirées de seuils internes** (dépôt muet ≥ 3 ans, absence INPI) : factuelles sur la donnée mais présentées comme signaux d'approche — le seuil de 3 ans est codé en dur, non délibéré ni configurable.
