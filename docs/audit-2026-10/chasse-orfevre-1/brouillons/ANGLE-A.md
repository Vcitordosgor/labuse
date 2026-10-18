# CHASSE-ORFEVRE-1 — Angle A : constats bruts (table par table)

Audit du 18/10/2026, base `labuse` (rôle `openclaw`, lecture seule), 274 tables public.
Toutes les requêtes sont rejouables via `scripts/angle_a_tables.py` (68 contrôles, 0 erreur à l'exécution de référence).
Gravités proposées : BLOQUANT / GÊNANT / COSMÉTIQUE / À SURVEILLER. Aucune correction appliquée.

Rappel des cas CONNUS re-signalés (état en base inchangé, voulus) :
- hauteurs LiDAR aberrantes (bornées à la lecture par `labuse_hauteur_lidar_m`, FIX-2 non mergé) → A-03 ;
- année DPE 1761 (<1800, garde à la lecture FIX-2) → A-04 ;
- 38 lignes `[GB-TEST]` dans `pipeline_entries.notes` (purge SQL fournie, non exécutée) → A-17.

---

## A-01 — score_labuse_runs.n_parcelles faux (métadonnée de run)
- **Table** : `score_labuse_runs` (3 lignes) vs `score_labuse` (1 298 121 lignes).
- **Requête** : `select r.run_label, r.n_parcelles, (select count(*) from score_labuse s where s.run_label=r.run_label) from score_labuse_runs r;`
- **Compte** : 3/3 runs faux.
- **Exemples** : q_v16 → meta 1663 / réel 431 663 ; q_v18 → meta 1229 / réel 433 229 ; q_v19 (SERVI) → meta 1229 / réel 433 229.
- **Gravité** : GÊNANT (métadonnée de pilotage mensongère ; quiconque lit le registre des runs croit à un run de 1 229 parcelles).
- **Cause** : `src/labuse/scoring/score_labuse_combine.py::persister()` est appelé par lot et upsert `n_parcelles=len(lignes)` du **dernier lot** (`ON CONFLICT … DO UPDATE SET n_parcelles=EXCLUDED.n_parcelles`). 1229/1663 = taille du dernier chunk.
- **Correction proposée (non appliquée)** : cumuler (`n_parcelles = score_labuse_runs.n_parcelles + EXCLUDED.n_parcelles` à l'insert initial du run, ou recompter en fin de run `UPDATE … SET n_parcelles=(select count(*) …)`).

## A-02 — parcel_residuel_runs : taux_emprise_pct et pct_potentiel > 100 %
- **Table** : `parcel_residuel_runs` (run servi 16 = q_v19).
- **Requête** : `select count(*) … where run_seq=16 and taux_emprise_pct not between 0 and 100;` idem `pct_potentiel`.
- **Compte** : run 16 : **61 555** taux_emprise_pct > 100 (max **19 569**) ; **64 475** pct_potentiel > 100 (max **20 140**). Mêmes ordres sur runs 13/15 ; run 1 (legacy) : 106 106 / 110 980. Aucune valeur négative, aucun sdp < 0.
- **Exemples** (run 16) : `97411000AY0015` taux 19569/pct 20140 sdp 0 ; `97421000BO0198` 8843/4620 ; `97411000AY0338` 7765/16280 ; `97421000AM0087` 7224/4003 ; `97422000EN0671` 6816/12307.
- **Gravité** : À SURVEILLER (sémantiquement : bâti existant > assiette clippée minuscule → sur-densité, sdp=0 cohérent ; mais si un écran affiche « taux d'emprise 19 569 % » c'est gênant).
- **Cause probable** : ratio emprise bâtie / assiette clippée quand l'assiette U-AU est un confetti de la parcelle.
- **Correction proposée** : plafonner l'affichage à 100 % (ou « >100 % ») au servi, pas en base ; ou stocker NULL au-delà d'un seuil avec motif.

## A-03 — batiment_hauteur_lidar : hauteurs impossibles (CONNU)
- **Table** : `batiment_hauteur_lidar` (303 452 lignes).
- **Requête** : `select count(*) filter (where faitage_m<=0), count(*) filter (where faitage_m>60), max(faitage_m), count(*) filter (where egout_m<=0) …;`
- **Compte** : 56 faîtage ≤ 0 ; 2 faîtage > 60 m dont **max 53 401,6 m** ; 1 507 égout ≤ 0 ; 0 égout > faîtage.
- **Gravité** : GÊNANT en base / neutralisé à la lecture — **CONNU** (CHASSE-INVARIANTS-FIX-2 : fonction SQL `labuse_hauteur_lidar_m` NULL si ≤0 ou >60, poussée non mergée ; le précalcul q_v19 a été fait avec).
- **Correction proposée** : rien de plus que FIX-2 ; option : purge/correction à la prochaine ré-ingestion LiDAR.

## A-04 — Années de construction 1761 (DPE) (CONNU)
- **Tables** : `dpe_records` (1 123) et `parcel_filtre_bati` (294 942).
- **Requête** : `… where annee_construction < 1800 …`
- **Compte** : 1 ligne chacune. Exemple : `dpe_records.numero_dpe=2568E0569173B`, annee 1761, parcelle `97418000AW0434` ; propagée dans `parcel_filtre_bati` (min=1761).
- **Gravité** : COSMÉTIQUE — **CONNU** (FIX-2 : « année inconnue » à la lecture ; `dpe_records` volontairement non réécrit).
- **Cause** : donnée source ADEME.

## A-05 — dvf_mutations_parcelle : doublons exacts, orphelins, valeurs ≤ 1 €
- **Table** : `dvf_mutations_parcelle` (102 551 lignes).
- **a) Doublons exacts métier** — requête : `group by id_mutation,id_parcelle,date_mutation,valeur_fonciere,type_local,surface_reelle_bati,surface_terrain,nature_culture having count(*)>1` → **7 082 groupes**. Exemples : mutation `2021-1677346` × `97411000AE0129` : 197 lignes « Dépendance » identiques (+ lignes « Appartement » identiques, ids 11247-…) ; `2024-1188637` × `97415000CT2791` : 170 lignes. **Gravité : À SURVEILLER** — c'est la structure même du DVF open-data (un lot par ligne, lots identiques indiscernables) ; ne PAS dédupliquer sans analyse (fausserait les comptes de lots), mais tout agrégat « nombre de ventes » doit compter `distinct id_mutation`.
- **b) Orphelins id_parcelle** — `not exists (parcels.idu)` → **1 128 lignes**. Exemples : id 99380 `97416000HN0670` (2025-10-21, 220 775 €), id 99385 `97416000HN0671`, id 98522 `97413000AV2316`, id 98954 `97416000HY0198`, id 98095 `97412000AM0765`. **Gravité : GÊNANT** (la vente ne peut pas s'accrocher à une fiche parcelle). **Cause** : parcelles filles récentes (divisions) absentes du millésime cadastre chargé, ou parcelles remembrées. **Correction** : rattacher via `dfi_filiation`/`cadastre_historique` au parent, ou re-millésimer le cadastre.
- **c) Valeurs** — 698 `valeur_fonciere` NULL ; **1 351 ≤ 1 €** (ex. ids 454-459, mutation 2021-1672853, « Vente » à 1 €). **Gravité : À SURVEILLER** (euro symbolique réel dans la source DGFiP ; à exclure des médianes — vérifier que `dvf_secteur_medianes` les filtre : ses bornes sont saines, 0 médiane ≤ 0).
- 0 date hors [1800, aujourd'hui], 0 coordonnée hors Réunion, 0 id_parcelle NULL.

## A-06 — dvf_mutations_histo / dvf_mutations : euro symbolique
- `dvf_mutations_histo` (110 477) : **2 289** valeur_fonciere ≤ 1 €, 0 date hors bornes, 0 recouvrement (id_mutation,id_parcelle) avec `dvf_mutations_parcelle` (bonne partition histo/récent).
- `dvf_mutations` (29 566, géolocalisées servies) : **16** vf ≤ 1 €, 0 doublon `mutation_id`, 0 geom NULL.
- **Gravité** : À SURVEILLER (source) ; `dvf_mutation_detail` : 0 orphelin vers `dvf_mutations_parcelle`.

## A-07 — parcelle_personne_morale : 601 idu orphelins
- **Table** : `parcelle_personne_morale` (82 701).
- **Requête** : `not exists (select 1 from parcels p where p.idu=x.idu)` → **601**.
- **Exemples** : `97411000CE0471` (SOVIPRO), `97411000HP0645`/`HP0421`/`HP0539`/`HP0549` (SIDR), tous millésime 2025.
- **Gravité** : GÊNANT (ces propriétés PM n'apparaissent sur aucune fiche ; le bloc propriétaire est incomplet là où la parcelle a changé d'idu).
- **Cause** : millésime MAJIC 2025 plus frais que le millésime cadastre des `parcels` (divisions/remembrements).
- **Correction proposée** : rattacher par filiation (`dfi_filiation`) ou purger au prochain chargement cadastre.

## A-08 — SIREN « U… » MAJIC dans parcelle_personne_morale et parcel_blocs (by design)
- **Tables** : `parcelle_personne_morale` : **10 145** siren non `^[0-9]{9}$` (ex. `U23691569` = ÉTAT/DIE, `U30823743`, `U14841558` Association diocésaine…) ; `parcel_blocs` : **1 197**.
- **Gravité** : COSMÉTIQUE / documenté — ce sont les numéros personne MAJIC quand le SIREN est inconnu ; le code filtre systématiquement `siren ~ '^[0-9]{9}$'` (`ingestion/bodacc.py:84`, `ingestion/inpi_rne.py:40`, `filtres/sources.py:170`…).
- **À noter** : **0** SIREN/SIRET numérique avec clé de Luhn fausse sur TOUTES les tables testées (`sirene_etablissements` 173 524, `pm_dirigeants`, `etablissement_parcelle` 131 187, `parcelle_personne_morale`, `bodacc_depots`) — remarquablement propre.

## A-09 — sirene_etablissements : 10 dates de création impossibles
- **Requête** : `date_creation > current_date or date_creation < '1800-01-01'`.
- **Compte** : **9 futures** (jusqu'à 2027-08-17) + **1 en l'an 26** (`79821632100025`, date_creation `0026-02-02` — année tronquée à la source).
- **Exemples** : `10816323900016` 2026-10-28 ; `99405053200013` « SANS OBJET » 2026-11-17 ; `10671837200019` LE CENTRAL GOURMAND 2027-01-01 ; `52503169600046` ATELIER MOURY ADELE 2027-03-13.
- **Gravité** : COSMÉTIQUE (données INSEE source ; « SANS OBJET » = non-diffusion). Correction : garde à l'affichage si la date est montrée.

## A-10 — piscines : 380 sans idu (dont 15 servies), 4 359 sans commune (dont 6 servies), 28 surfaces ≤ 0
- **Table** : `piscines` (50 516).
- **Requêtes** : `idu is null` → 380 (288 ecartee / 77 a_confirmer / **15 servie**) ; `commune is null or commune=''` → 4 359 (4 339 ecartee / 14 a_confirmer / **6 servie**) ; `surface_m2 <= 0` → 28 (toutes ecartee).
- **Exemples servies sans idu** : ids 8461, 8419 (aussi sans commune), 8451, 8479, 8482 — classe `cosia_confirmee`, confiance NULL.
- **Gravité** : GÊNANT pour les 15 servies sans idu + 6 servies sans commune (piscine « servie » introuvable depuis une parcelle) ; COSMÉTIQUE pour le reste (écartées).
- **Cause probable** : détection CoSIA hors emprise parcellaire (voirie/limite) ou rattachement non rejoué après chargement cadastre.
- **Correction proposée** : rejouer le rattachement spatial pour `statut in ('servie','a_confirmer') and idu is null` ; backfill commune par ST_Within.

## A-11 — m10_permit_delais : 7 633 délais négatifs (date_depot fausse)
- **Table** : `m10_permit_delais` (50 290).
- **Requête** : `delai_mois < 0` → **7 633** (min −157), tous `valide=false` ; `date_autorisation < date_depot` → **7 760**, dont **127 avec valide=true** (écarts de quelques jours, delai_mois clampé à 0).
- **Exemples** : `97441512A0616` Saint-Paul dépôt **2026-03-02** / autorisation **2013-02-22** (permis « 12A » = 2012 !) ; `97441512A0569` ; `97441612A0600` ; `9744121220197` ; exemples valide=t : `97440316A0026` Entre-Deux dépôt 24/08 / autorisation 03/08/2016, delai 0.
- **Gravité** : GÊNANT (mais contenu : les 7 633 grossiers sont `valide=false`, donc exclus si les stats filtrent sur `valide` — à vérifier côté consommateur M10) ; les 127 valide=true à quelques jours près sont COSMÉTIQUES (bruit source Sitadel).
- **Cause probable** : `date_depot` reconstruite/écrasée par une autre source (la date ressemble à une date de traitement 2025-2026, pas de dépôt) pour les vieux permis 2012-2013.
- **Correction proposée** : recalculer date_depot depuis le permit_id/Sitadel brut, ou NULLer date_depot quand autorisation < dépôt de plus de 1 mois.

## A-12 — comptes : doublons de nom = résidus de recette en base
- **Table** : `comptes` (47).
- **Requête** : `group by lower(nom) having count(*)>1`.
- **Compte** : 2 groupes : « compte de test vic » ids {4,5} (résiliés ×2) ; « recette onb » ids {61,62} (**actifs** ×2).
- **Gravité** : GÊNANT (comptes de test actifs dans la base vivante, en plus des `[GB-TEST]` connus ; « recette onb » ×2 actifs = vraisemblablement RECETTE-GENERALE-1).
- **Correction proposée** : étendre la purge SQL déjà fournie (GB-TEST) aux comptes de recette 61/62 (+ leurs utilisateurs/événements), après accord Vic.

## A-13 — utilisateurs : 1 compte « actif » sans hash de mot de passe
- **Table** : `utilisateurs` (29).
- **Requête** : `(hash is null or hash='') and statut='actif'`.
- **Compte** : 1 — id 30, `qa-m23@labuse.test`, compte 30, titulaire, créé 2026-07-26 (les 7 autres sans hash sont `invite`, normal).
- **Gravité** : GÊNANT (incohérence d'état : actif = peut se connecter, sans hash = ne peut pas ; résidu QA ; vérifier qu'aucun chemin de login n'accepte un hash vide).
- **Correction proposée** : passer en `invite`/supprimer avec la purge recette. Sinon la table est saine : 0 doublon email (même à la casse près), 0 format invalide, 0 orphelin compte.

## A-14 — mail_queue : 12 mails « a_rejouer » dont 3 vers un compte supprimé
- **Table** : `mail_queue` (17 : 5 recu, 12 a_rejouer).
- **Requête** : `etat='a_rejouer'` ; orphelins : `compte_id not in comptes` → **3** (ids 57/58/59, compte **111** inexistant, mail_key suspension/resiliation/retablissement).
- **Détail** : les 12 datent du 16/10, tentatives=1, erreur « dry-run (local, LABUSE_MAIL_REEL absent) — aucun appel Brevo » ; comptes 18 (mdp_oublie ×2), 104 (onboarding1, essai, souscription, resiliation, suspension, retablissement, mdp_modifie), 111 (×3). Les comptes 104 et 111 n'existent plus.
- **Gravité** : GÊNANT (si un worker avec `LABUSE_MAIL_REEL` rejoue la file, il tentera d'envoyer des mails de tests de recette, dont 3 pour un compte supprimé).
- **Correction proposée** : purger les 12 lignes (résidus du test FIX-1 des mails auto résil/susp/rétab du 16/10) ; au rejeu, ignorer les compte_id inexistants.

## A-15 — evenements_compte : 84/89 orphelins compte/utilisateur
- **Table** : `evenements_compte` (496).
- **Requête** : compte_id inexistant → **84** ; utilisateur_id inexistant → **89**.
- **Exemples** : ids 495-499, type mail_en_attente/mail_a_rejouer, compte 111, 2026-10-16.
- **Gravité** : À SURVEILLER (journal : garder la trace d'un compte supprimé peut être voulu, mais 111/104 sont des comptes de recette → même purge que A-14).

## A-16 — parcel_signaux_vie : 185 idu orphelins
- **Table** : `parcel_signaux_vie` (30 896).
- **Requête** : `not exists (parcels.idu)` → **185**.
- **Exemples** : `97415000AB0831`, `97415000CO0138`, `97415000CZ1354`, `97415000CD0122`, `97412000CY1089` — tous signal `assemblage_pm`, updated 2026-08-10.
- **Gravité** : À SURVEILLER (signaux calculés le 10/08 sur des idu disparus depuis ; lignes mortes, pas servies via jointure).
- **Correction proposée** : DELETE des orphelins au prochain recalcul du job assemblage_pm.

## A-17 — pipeline_entries : 38 lignes [GB-TEST] (CONNU)
- **Requête** : `notes like '%[GB-TEST]%'` → **38** / 227 (ids 91→132). Purge SQL déjà fournie, non exécutée. 0 orphelin compte/projet par ailleurs.
- **Gravité** : GÊNANT (CRM pollué) — CONNU.

## A-18 — consultation_log : 617 idu orphelins dont idu forgés
- **Table** : `consultation_log` (9 832).
- **Requête** : idu inexistant → **617**. Top : `97416000QA0001` (×2), `97410000BZ1065` (×2), **`00000000XX0000`** (×2, idu de test forgé), `97416000QA0000`, `97416000QA0002`.
- **Gravité** : COSMÉTIQUE (log d'audience ; les QA* et 0000… viennent des recettes ; les autres = parcelles disparues depuis la consultation).

## A-19 — parcels : 1 593 écarts surface géométrique / contenance fiscale
- **Table** : `parcels` (434 582 ; 1 353 marquées disparues, 1 381 contenance NULL).
- **Requête** : `contenance_m2 > 0 and (surface_m2/contenance_m2 > 2 or < 0.5)` → **1 593**.
- **Exemples** : `97422000BP2028` geom 813 m² vs contenance **8 130 000** (facteur 10⁴ — erreur de saisie source évidente) ; `97421000AO0025` 1 509 303 vs 3 042 500 ; `97419000BH0010` 966 633 vs 9 657 (×100) ; `97415000AO0009` 660 230 vs 4 937 ; `97421000BK0035` 649 403 vs 1 303 200.
- **Gravité** : À SURVEILLER (dépend de quelle surface fait foi dans chaque calcul ; la géométrie est saine — 0 invalide, 0 vide, 0 doublon idu, 0 hors Réunion — c'est la contenance MAJIC qui déraille).
- **Correction proposée** : règle de préférence explicite (geom qui fait foi au-delà d'un ratio 2) + marquage `surface_incertaine` (existe déjà dans `mvt_parcels`).

## A-20 — sitadel_permits : 734 permis sans aucune géométrie
- **Requête** : `geom is null and geom_approx is null` → **734** / 50 809 ; tous ont des `idu_codes` (0 sans geom NI idu).
- **Exemples** : `97441419A0150` Saint-Louis, `9744012520058` Les Avirons, `9744122500193`/`96` Saint-Joseph, `97441616A0763` Saint-Pierre (date_depot NULL en plus).
- **Gravité** : COSMÉTIQUE (rattachables par idu_codes ; absents de la carte seulement).

## A-21 — mairies : Saint-Denis sans email
- **Requête** : `email is null or email=''` → 1 (insee 97411 Saint-Denis, téléphone présent).
- **Gravité** : GÊNANT si le courrier mairie / annuaire s'en sert pour la plus grosse commune ; sinon cosmétique. Correction : compléter depuis l'annuaire service-public.

## A-22 — owner_enrichment : 121 siren sans porteur dans parcelle_personne_morale
- **Requête** : siren valide absent de ppm → **121** / 9 730.
- **Gravité** : COSMÉTIQUE (cache d'enrichissement périmé après rafraîchissement MAJIC ; lignes mortes inoffensives).

## A-23 — parcel_veille_succession : 1 dirigeant de 114 ans
- **Requête** : `dirigeant_age not between 18 and 110` → 1 (max 114).
- **Gravité** : COSMÉTIQUE (date de naissance RNE non mise à jour — personne vraisemblablement décédée ; précisément le signal que la veille cherche, mais l'âge affiché sera douteux).

---

## Observations non-anomalies (notées pour les autres angles)
- `score_labuse` q_v19 introduit une bande **HC** (6 314 lignes, causes `hors_classement:*` : voirie 1 926, DPF 1 336, équipement public 905…) absente de q_v16/q_v18 — nouveau vocabulaire, à vérifier côté UI/documentation bandes (hors mandat angle A).
- `cadastre_historique` : 6 496/6 526 idu absents de `parcels` — **par construction** (parcelles disparues, c'est l'objet de la table).
- `utilisateurs` : 7 `invite` sans hash = normal (invitation non acceptée).
- `parcel_au_statut.classe` mélange ASCII et accentué (`générique` vs `declasse_au_*`) — micro-incohérence de vocabulaire.
- Les écarts de population entre tables parcelles (parcels 434 582 = 433 229 vivantes + 1 353 disparues ; runs q_v18/q_v19 = 433 229 ; q_v16/legacy = 431 663) sont cohérents entre eux.
- Encodage : **0** mojibake « Ã », 0 \n/\r, 0 U+00A0 sur toutes les colonnes texte testées (sirene, ppm, dirigeants, mairies, rnic, dvf_detail, adresses).
- Géométries : 0 invalide/vide sur `parcels` ; 0 geom NULL sur `adresses`, `rnb_batiments`, `mvt_parcels`, `dvf_mutations`.
