# CHASSE-ORFEVRE-1 — Angle B : constats bruts (chaque source de bout en bout)

Exécution de référence : 18/10/2026, script `scripts/angle_b_sources.py` (base + `--en-ligne`).
Base `labuse`, rôle read-only. Producteurs interrogés en GET légers (~1 req/s) :
API Carto IGN, Géorisques v1, ADEME data-fair, BODACC ODS, plateforme BAN, files.data.gouv (geo-DVF).
Les gravités sont PROPOSÉES ; aucune correction appliquée.

## B-01 — dvf_mutations : 1 mutation INVENTÉE toujours en base (vestige du jeu démo)
- **Requête** : `SELECT id, mutation_id, date_mutation, valeur_fonciere, commune, raw FROM dvf_mutations WHERE date_mutation > '2026-01-01'`.
- **Compte** : **1** (id 33217) — `date_mutation = 2026-08-10 03:43:00.150591+04` (un horodatage mur, pas une date de vente ; le flux réel s'arrête au 2025-12-31 et toutes les vraies lignes sont à minuit), `valeur_fonciere = 380 000`, commune Saint-Paul, **mutation_id NULL, raw NULL** (seule ligne de la table dans ce cas).
- **Cause probable** : vestige du jeu de démonstration synthétique `ingestion/demo_saint_paul.py` (INSERT direct dans `dvf_mutations` sans `mutation_id`, commune pilote Saint-Paul) resté dans la base de prod.
- **Déjà connue du code** : `dvf_fenetre.py` la nomme « ligne parasite » et l'exclut par `date_trunc('day', …)` — mais la ligne reste servie à tout lecteur qui ne passe pas par le helper (ex. agrégats ad hoc, exports).
- **Gravité** : GÊNANT (donnée fictive dans une table servie ; contournement actif = dette).
- **Correction proposée (non appliquée)** : `DELETE FROM dvf_mutations WHERE mutation_id IS NULL; -- 1 ligne (id 33217)` puis retirer le contournement de `dvf_fenetre.py`.

## B-02 — sirene_etablissements : 15 009 lignes disparues DANS la journée, sans aucune trace
- **Constat** : l'angle A (script joué le 18/10 au matin) a compté **173 524** lignes ; l'angle B (18/10 après-midi) en compte **158 515** — toutes `actif = true`, tous `ingested_at = 2026-08-29` (aucun rechargement visible).
- **Requêtes** : `SELECT count(*) FROM sirene_etablissements` ; `SELECT coalesce(actif::text,'NULL'), count(*) … GROUP BY 1` → `true | 158515` uniquement ; `SELECT date_trunc('day', ingested_at), count(*) …` → une seule journée 2026-08-29.
- **Journaux muets** : `job_runs` ne contient **qu'UNE ligne** (fiche-commune-cache du 17/10) ; `event_log` : 0 événement le 18/10 ; `ingestion_runs` : rien depuis le 17/10. La purge (vraisemblablement des établissements fermés, `actif=f`) n'est journalisée nulle part.
- **Intégrité préservée** : 0 orphelin dans `etablissement_parcelle` (131 187 sirets tous présents).
- **Gravité** : GÊNANT — pas pour la donnée (purge des fermés plausible et saine) mais pour la TRAÇABILITÉ : une table servie perd 8,6 % de ses lignes sans une ligne de journal ; impossible de dater/attribuer le geste. `job_runs` quasi vide est en soi un signal.
- **Correction proposée** : journaliser toute purge/sync SIRENE (job_runs + compteurs avant/après) ; documenter la politique « actifs seulement ».

## B-03 — BAN : 266 adresses fantômes à Petite-Île (base > producteur), total −849
- **URL producteur** : `https://plateforme.adresse.data.gouv.fr/lookup/{insee}` → `nbNumeros` (18/10/2026).
- **Comptes** : total producteur **340 764** vs base **339 915** (−849, −0,25 %, sync 2026-08-19). Mais le signe varie par commune : **97405 Petite-Île base = 6 700 vs producteur = 6 434** → ~266 adresses en base que la BAN ne publie plus (commune passée en BAL certifiée → renumérotation/nettoyage). À l'inverse 97409 Saint-André producteur +78, 97423 +65, 97424 +26… (retard normal de sync).
- **Gravité** : À SURVEILLER — les 266 fantômes de Petite-Île sont des lignes mortes côté producteur, servies par `adresses`/`adresse_parcelles` ; le reste est un simple retard de deux mois (recroise VERITE-TERRAIN-3 « BAN en retard »).
- **Correction proposée** : re-moissonner la BAN (au moins 97405) et purger les `id_ban` absents du flux.

## B-04 — cadastre : 899 parcelles « vivantes » en base déjà retirées du PCI courant
- **URL producteur** : `https://apicarto.ign.fr/api/cadastre/parcelle?code_insee={insee}&_limit=1` → `totalFeatures` (18/10/2026).
- **Comptes** : producteur **432 330** vs base vivantes (`cadastre_disparue_le IS NULL`) **433 229** — **−899** (−0,21 %), réparti sur TOUTES les communes (de −3 à −149, max Saint-Denis −149, Saint-Paul −136) : édition PCI du producteur plus récente (remembrements/divisions) que le sync du 11/10.
- **Gravité** : À SURVEILLER (dérive d'édition normale ; le prochain sync doit marquer ces parcelles `cadastre_disparue_le`, mécanisme déjà en place — 1 353 disparues gérées). Aucun signe de commune manquante ou de sur-chargement.
- **Correction proposée** : aucune (vérifier au prochain sync que le delta est bien résorbé).

## B-05 — adresses : 2 043 lignes rattachées à une parcelle DISPARUE
- **Requête** : `SELECT count(*) FROM adresses a JOIN parcels p ON p.idu=a.idu WHERE p.cadastre_disparue_le IS NOT NULL` → **2 043**. Idem `dvf_mutations_parcelle` → 116 (légitime : ventes historiques sur parcelles remembrées) ; `dpe_records.parcelle_idu` → 2.
- **Gravité** : À SURVEILLER — le rattachement BAN→parcelle n'est pas rejoué après les disparitions cadastre ; une fiche ouverte par adresse peut pointer une parcelle morte.
- **Correction proposée** : rejouer `rattachement` des adresses dont l'idu est disparu (vers la parcelle remplaçante via `parcel_cadastre_remplacement`/`cadastre_historique`).

## B-06 — Poids mort : 20 colonnes chargées jamais lues, 5 colonnes 100 % NULL
- **Méthode** : `count(col)` par colonne + grep mot entier sur `src/labuse` + `frontend/src` en EXCLUANT les écrivains (`models.py`, `ingestion/`, `connectors/`) ; colonnes ≤ 3 caractères et colonnes de ménage ignorées (prudence : zéro faux « mort » certain, des faux « vivants » possibles).
- **100 % NULL** : `parcels.origine` (434 582 lignes — colonne LUE par `audit.py` avec repli `or "referentiel"`, jamais alimentée : le chemin audit-pull n'a jamais tourné en prod) ; `dvf_mutations_histo.longitude/latitude` (110 477 — archives DGFiP sans géoloc, schéma copié du flux géo) ; `rpls_commune.dpe_classes/pct_passoires` (24 — jamais remplies NI lues).
- **Chargées mais jamais lues hors écrivains** :
  - `arcep_immeubles.technos/debit_descendant_max/debit_montant_max` (330 310 lignes ×3)
  - `ban_plus_liens.type_lien/nb_adr/nb_bat` (738 540 ×3)
  - `bodacc_depots.type_depot/cp_siege/commercant/tribunal` (14 078 ×4)
  - `sirene_etablissements.qp24` (remplie à 18 %), `dpe_records.geocode_score`,
    `piscines.millesime_flair/millesime_cosia`, `batiment_hauteur_lidar.rnb_cause` (remplie à 1,4 %),
    `dfi_filiation.identifiant_dfi`, `dvf_mutations_histo.source_archive`,
    `rpls_commune.surfhab_moy/pct_dpe_renseigne`, `rnic_coproprietes.mandat_en_cours`.
- **Gravité** : COSMÉTIQUE (plusieurs sont de la traçabilité assumée : `source_archive`, `identifiant_dfi`, `rnb_cause`, millésimes piscines). Les vrais candidats à décision : `rpls_commune.dpe_classes/pct_passoires` (ni remplies ni lues → supprimer ou brancher), `arcep` débits/technos (3 colonnes × 330 k jamais servies), `parcels.origine` (lue avec repli mais jamais écrite — mort-vivant).
- **Correction proposée** : trancher colonne par colonne (supprimer du modèle OU brancher un lecteur) ; rien d'urgent.

## B-07 — GASPAR CatNat : Saint-Joseph a 1 arrêté de retard
- **URL** : `https://georisques.gouv.fr/api/v1/gaspar/catnat?code_insee=97412&page=1&page_size=1` → `results: 21` vs base 20. Les 23 autres communes : écart 0 (426 ↔ 427).
- **Gravité** : COSMÉTIQUE (arrêté publié après le sync du 06/09/2026 ; cadence à vérifier).
- **Correction proposée** : resynchroniser GASPAR (le connecteur paginé existe).

## B-08 — SIRENE : 9 dates de création futures + 1 an « 0026 » (recroise A-09)
- Producteur INSEE lui-même en cause (`79821632100025` date `0026-02-02`, 9 dates jusqu'à 2027-08-17). COSMÉTIQUE. Déjà consigné angle A (A-09) — cité ici car revu au passage, rien de neuf.

## B-09 — GPU/PLU : Saint-Philippe quasi à zéro ; 3 communes sans verbatim de règlement (recroise VERITE-TERRAIN-3)
- `parcel_zone_plu` 97417 Saint-Philippe = **9** parcelles zonées sur 4 173 (0 couche `plu_gpu_zone` pour la commune — GPU vide, les 9 viennent de documents voisins débordants) ; `plu_reglement_extrait` = **0** pour 97409 Saint-André, 97413 Saint-Leu, 97417 Saint-Philippe. Conforme aux constats VERITE-TERRAIN-3 (GPU vide / procédure en cours) — pas une anomalie de chargement, cité pour mémoire.

## Observations sans gravité (vérifiées conformes)
- **DVF géo** : fichiers communaux officiels rejoués → 97403/2024 producteur 118 lignes / 70 mutations = base 118/70 ; 97411/2023 producteur 4 858/2 054 = base 4 858/2 054. **Octet pour octet.** `latest` producteur = 2021→2025, exactement la fenêtre en base ; 0 ligne hors fenêtre dans `dvf_mutations_histo` (2014-2020), 0 recouvrement histo/actuel.
- **DPE ADEME** : producteur (`qs=code_insee_ban:974*`) existant 915 / neuf 179 / tertiaire 30 vs base 914/179/30 (1 DPE publié depuis le sync 19/09). Le volume minuscule (1 123) est PAR CONSTRUCTION (seuls les DPE géocodés BAN en 974 sont authentiques — cf. en-tête `connectors/dpe.py`) ; les 5 communes à 0 DPE (Bras-Panon, Entre-Deux, Salazie, Cilaos, Trois-Bassins) sont cohérentes avec ce volume.
- **BODACC** : échantillon 3 sirens (les plus fournis) — producteur 205/34/23 vs base 204/33/23 (annonces publiées après le sync 14/09). Table ciblée par construction (dépôts des comptes des 1 938 sirens d'intérêt), pas un chargement départemental.
- **QPV 2024** : 57 QPV / 13 communes en base = le compte du geojson national ANCT filtré `insee_dep=974` (vérifié au chargement 05/07/2026, consigné dans `connectors/qpv.py`).
- **Comptes auto-déclarés** : Arcep 330 310 = 330 310 ; DFI 409 623 = 409 623 ; RNIC 2 220 = 2 220 (base ↔ `data_sources.source_millesime`).
- **PM DGFiP** : `parcelle_personne_morale` 82 701 toutes millésime 2025 + panel `pm_proprietaires_millesimes` 461 570 (2019→2024) = « Panel 2019→2025 » annoncé. 0 hors fenêtre.
- **Sitadel** : dates 2013→2026-08-31 = millésime déclaré 2026-08 ; 0 permis futur ; 24/24 communes.
- **Fenêtres de dates** : 0 ligne future dans dvf_mutations_parcelle/histo, sitadel, dpe, catnat ; 0 RNB inactif conservé.

## Pièges de méthode
- `~/Desktop/labuse/.venv/bin/python` n'a pas de chaîne de certificats → le script charge `certifi` (sinon repli non vérifié, open data public en lecture).
- geo-DVF : les fichiers communaux sont servis en `.csv` NON gzippé derrière un 302 (`curl -L`) ; l'URL `.csv.gz` répond NoSuchKey.
- `grep` « jamais lue » : exclure `models.py` est indispensable (toute colonne y figure par définition) ; la méthode reste conservatrice (une occurrence texte quelconque suffit à dire « lue »).
- La base est VIVANTE pendant l'audit (cf. B-02) : dater chaque compte.
