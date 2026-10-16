# VERITE-TERRAIN-3 — Volet B : « Les phrases disent-elles vrai ? »

**Date :** 16 octobre 2026 · **Nature :** LECTURE SEULE. Aucune écriture en base, aucune correction, aucun merge.

## Méthode

- Grep ciblés (fréquences, nombres, couvertures, sources, calculs) sur chaque surface, puis lecture de la phrase ENTIÈRE en contexte.
- Chaque claim confrontée à une **ancre de réalité** : table Postgres (`openclaw@localhost/labuse`), registre des jobs (`src/labuse/jobs.py`, cadence + cron_utc), registre des couches (`src/labuse/api/couches_tuyau.py`), moteur (`solaire.py`, `vefa_neuf.py`, FREEZE du run servi), et `FRAICHEUR.md` (Volet A) pour les fraîcheurs.
- Un claim n'est marqué **LABUSE_FAUX** que s'il est étayé par une preuve concrète (compte en base, cron, ligne moteur). Sinon **NON_VERIFIABLE** avec la raison.

## Comptes de référence utilisés (vérifiés)

| Ancre | Valeur | Preuve |
|---|---|---|
| Sources vitrine | **118** | `SELECT count(*) FROM data_sources WHERE affichage_desactive=false AND retiree_le IS NULL AND alias_de IS NULL` = 118 ; `WHERE_AFFICHEES` (sources_catalog.py) = 118 aussi |
| Sources non retirées / total | 124 / 129 | psql |
| Communes | **24** | `communes_referentiel` = 24 ; `parcel_zone_plu` 24 communes distinctes |
| Parcelles brutes | 434 582 | `parcels` |
| Parcelles **vivantes** (servies par /accueil/chiffres) | **433 229** | `parcels WHERE cadastre_disparue_le IS NULL` ; confirmé par commentaire `api/accueil.py:190` |
| Parcelles du **run scoré servi** (q_v14) | 431 663 | `reports/q-v14/FREEZE-q_v14.json` n_eval=431663 |
| Zonage PLU | 430 320 parcelles / 24 communes | `parcel_zone_plu` (97417 = 9 parcelles seulement) |

## Périmètre couvert

- **app React** (`frontend/src/`) : layers.ts (couvertures/sources/calculs couches), strings.ts (classement/calculs), SourcesPage, Header (mails), ProspectionSolaire, EtudeZone, ProprietaireHistorique, outils (24 communes), VeilleEcrans, dashboard.
- **site Astro** (`/Users/openclaw/labuse.immo/labuse.immo/src/`) : Hero, KeyFigures, Features, Constat, Audience, HowItWorks, Footer, DataLayers, layouts. **Site = one-pager, un seul commit vitrine** ; aucune page mentions/CGU (liens morts `#`).
- **mails** : `emails.py`, `courrier.py` (cadences digest + facturation).
- **copilote** : `ai/prompt.py`, `copilote_v2/*` (prompts système).
- **exports/impression** : cherché `@media print`/export dans fiche ; aucune affirmation factuelle stale trouvée (millésimes servis dynamiques).

## Périmètre NON couvert / limites

- La base locale est un **worktree de dev** : les tables de run scoré (`abuse_scores`, scores servis) sont VIDES ici. Le chiffre « 9,93 % de parcelles à cheval » (layers.ts:82) et le volume exact du run servi ne sont donc pas recalculables localement → NON_VERIFIABLE (et non « faux »).
- Mentions légales / CGU / confidentialité : **inexistantes** (liens `#`). Signalé comme promesse non tenue mais classé NON_VERIFIABLE (libellés de liens, hors « affirmation factuelle » stricte).
- Les littéraux périmés en **commentaires de code** (« 94 sources », « 91 sources vitrine ») ne sont PAS des affirmations visibles par l'utilisateur ; les compteurs réellement affichés sont dynamiques → CONFORME côté client, littéral à rafraîchir hors mandat.

---

## Candidats LABUSE_FAUX (à revérifier à la main par l'orchestrateur)

### 1. `frontend/src/lib/layers.ts:88` (+ strings.ts:287, strings.ts:387) — « 431 663 parcelles » figé

- **Texte :** « Les 431 663 parcelles cadastrales de l'île (source DGFiP)… présente sur les 24 communes. » (idem strings.ts:287 « Échantillon : les 431 663 parcelles » ; strings.ts:387 « 431 663 parcelles pour dire lesquelles regarder en premier »).
- **Réalité :** 431 663 = total du RUN scoré servi q_v14 (FREEZE). Le parc réellement servi à l'utilisateur via `/accueil/chiffres` est le parc VIVANT = **433 229** ; la table brute = 434 582. L'équipe a elle-même dé-codé-en-dur ce nombre ailleurs (`FiltreLabuse.tsx:628` : « le total de repli n'est plus un littéral figé (431 663, **périmé à chaque bascule de run**) : on lit la notion servie `n_parcelles_ile` »). Ces trois occurrences sont restées figées.
- **Preuve :** psql `parcels` vivants = 433 229 ; `reports/q-v14/FREEZE-q_v14.json` n_eval=431663 ; `api/accueil.py:190` ; `FiltreLabuse.tsx:628`.
- **Correction suggérée (NON appliquée) :** remplacer le littéral « 431 663 » par la notion servie (`n_parcelles_ile` / « plus de 430 000 ») comme déjà fait dans FiltreLabuse, ou par une tournure non chiffrée (« toutes les parcelles cadastrales de l'île »).

### 2. `frontend/src/lib/strings.ts:210` (+ strings.ts:371) — fenêtre d'apprentissage du classement

- **Texte (rangTip) :** « Le classement LABUSE — la probabilité de vente sous 1 an, **apprise sur les ventes réelles 2017-2024 (calibrée sur 2025)** … » ; corps:371 « les mutations **2017-2024**, calibré sur les millésimes les plus récents ».
- **Réalité :** le run servi q_v14 est **entraîné jusqu'en 2023**, **calibré (isotonique par segment) sur 2024**, et **2025 est l'année de TEST** tenue hors apprentissage (banc K0). Le texte client (a) étend l'entraînement à 2024 (qui est en réalité l'année de calibration) et (b) présente 2025 comme l'année de calibration alors que c'est l'année de test. Le propre commentaire du fichier (strings.ts:352) dit l'inverse du texte affiché.
- **Preuve :** `reports/q-v14/FREEZE-q_v14.json` (`test_fuite.annee_testee=2025`, `metriques_k0_2025`, variante `metriques_24m_test2024`) ; commentaire strings.ts:352 « entraînement : mutations JUSQU'EN 2023 ; calibration sur 2024 ; vérifié sur l'année 2025 tenue à l'écart de l'apprentissage ».
- **Correction suggérée (NON appliquée) :** aligner le texte sur le FREEZE : « apprise sur les mutations jusqu'en 2023, calibrée sur 2024, vérifiée sur 2025 (année tenue à l'écart) » — ou tournure vague « calibrée sur les millésimes les plus récents » SANS citer 2017-2024/2025 à tort.

### 3. `/Users/openclaw/labuse.immo/labuse.immo/src/components/KeyFigures.astro:6` (+ Hero.astro:61) — « 3 000+ parcelles analysées »

- **Texte :** stat « 3 000+ » / label « parcelles analysées ».
- **Réalité :** l'app analyse **431 663** parcelles (run servi q_v14, 24 communes) / **433 229** vivantes. « 3 000+ » sous-estime la réalité servie d'un facteur ≈ 140. Vestige de la photo « pilote Saint-Paul » du site (one-pager, un seul commit, jamais mis à jour).
- **Preuve :** psql parcels vivants=433229 ; FREEZE n_eval=431663, n_communes=24.
- **Correction suggérée (NON appliquée) :** « 430 000+ parcelles analysées » (ou le chiffre servi dynamique si le site peut le lire).

### 4. `/Users/openclaw/labuse.immo/labuse.immo/src/components/Hero.astro:85` (+ KeyFigures.astro:8) — « Saint-Paul commune pilote » / « Saint-Paul en pilote »

- **Texte :** stat « Saint-Paul » / label « en pilote » (Hero) ; « Saint-Paul » / « commune pilote » (KeyFigures).
- **Réalité :** LABUSE sert désormais **les 24 communes** (parcel_zone_plu 24 communes, scoring n_communes=24, FRAICHEUR Tableau 1 : 21 règlements PLU calibrés + zonage partout). Présenter Saint-Paul comme « la commune pilote » décrit un état antérieur. Incohérence interne : le MÊME fichier KeyFigures affiche aussi « 24 communes visées ».
- **Preuve :** psql communes_referentiel=24, parcel_zone_plu 24 communes ; FREEZE n_communes=24 ; KeyFigures.astro:8 « 24 communes visées ».
- **Correction suggérée (NON appliquée) :** remplacer « Saint-Paul / commune pilote » par « 24 / communes couvertes » (cohérent avec le reste), ou retirer la tuile pilote.

---

## Candidats CONFORME remarquables (vérifiés en base/jobs — pièges évités)

- **layers.ts:97 « Aléa mvt — 23 communes, Saint-Denis non couverte »** : VRAI. La couche servie est `georisque_alea/mouvement_terrain` (couches_tuyau.py:64), pas le kind `mvt` brut (source 36, lui 24 communes). Le kind servi = 23 communes, 0 feature Saint-Denis. **Piège évité** (le kind `mvt` aurait donné un faux positif).
- **layers.ts:120 « neuf VEFA — 60 mois / 8 ventes »** : VRAI pour la COUCHE carte (`vefa_neuf.py:36` 60 mois, seuil 8). À NE PAS confondre avec la notion fiche `prix_neuf_vefa_acte` = 36 mois / ≥10 ventes (`regles/prix_neuf_observe_eur_m2.py`), qui est une autre donnée.
- **NPNRU 8/6 communes, QPV 57/13 communes** : exacts au feature et à la commune près (psql).
- **SourcesPage « vérifiées chaque jour »** : job `sonde-sources` quotidien (cron `0 3 * * *`). Formulation « la plupart » honnête (l'IA `agents-sources` pour les sources illisibles est `planifie=False`).
- **ProspectionSolaire « carré 400 m »** : `config/solaire.yaml:11 grid_step_m: 400`.
- **SIRENE mensuel, digest 7h, DGFiP 2019→2025** : tous alignés sur jobs.py / FRAICHEUR.
