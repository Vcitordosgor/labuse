# VERITE-TERRAIN-3 — ECARTS (faux confirmés + correction proposée)

**Date :** 16 octobre 2026 · **Nature :** LECTURE SEULE — chaque écart ci‑dessous a été **revérifié à la main par l'orchestrateur** (code + base + preuve amont en cache). **Aucune correction appliquée.** Ne pas merger.

Deux familles :
- **B — Phrases fausses** (Volet B, verdict `LABUSE_FAUX`) : une affirmation visible par l'utilisateur ne dit pas vrai.
- **A — Données en retard** (Volet A, verdict `EN RETARD` confirmé) : la version servie n'est plus la dernière publiée.

Un troisième bloc isole un **écart interne** (commentaire de code faux, non visible utilisateur).

---

## B — Phrases fausses confirmées (4 défauts, 9 occurrences)

### B1 — « 431 663 parcelles » : nombre figé, périmé (3 occurrences)
- **Où :** `frontend/src/lib/layers.ts:88` · `frontend/src/lib/strings.ts:287` · `frontend/src/lib/strings.ts:387` (+ commentaire interne `strings.ts:195`).
- **Texte servi :** « Les **431 663** parcelles cadastrales de l'île (source DGFiP)… » / « Échantillon : les **431 663** parcelles » / « **431 663** parcelles pour dire lesquelles regarder en premier ».
- **Réalité (vérifiée en base, 16/10/2026) :** le parc cadastral de l'île servi vivant = **433 229** (`parcels WHERE cadastre_disparue_le IS NULL`), brut = **434 582** (`parcels`). Le nombre **431 663** est le `n_eval` du **run scoré q_v14** gelé (`reports/q-v14/FREEZE-q_v14.json`, contient bien `431663`), pas « les parcelles de l'île ». Présenté comme l'effectif cadastral, il est **faux** et **dérivera encore** à chaque nouveau run scoré.
- **Preuve que l'équipe le sait déjà :** `frontend/src/components/panel/FiltreLabuse.tsx:629` — commentaire : *« …le total de repli n'est plus un littéral figé (périmé à chaque bascule de run) : on lit la notion servie `n_parcelles_ile` (/accueil/chiffres) »*. Ces 3 occurrences ont été oubliées lors de ce dé‑codage‑en‑dur.
- **Correction proposée (NON appliquée) :** remplacer le littéral par la notion servie `n_parcelles_ile` (déjà disponible via `/accueil/chiffres`, cf. FiltreLabuse), ou par une tournure non chiffrée (« toutes les parcelles cadastrales de l'île »). Ne pas ré‑écrire un autre littéral.

### B2 — Fenêtre d'apprentissage du classement : décrite à tort (2 occurrences)
- **Où :** `frontend/src/lib/strings.ts:210` (`rangTip`) · `frontend/src/lib/strings.ts:371` (bloc « Comment »).
- **Texte servi :** rangTip — « …la probabilité de vente sous 1 an, **apprise sur les ventes réelles 2017‑2024 (calibrée sur 2025)**… » ; corps — « le modèle a appris … **les mutations 2017‑2024**, calibré sur les millésimes les plus récents ».
- **Réalité (FREEZE du run servi q_v14) :** entraînement **jusqu'en 2023**, **calibration isotonique par segment sur 2024**, **2025 = année de TEST tenue hors apprentissage** (banc K0, `test_fuite.annee_testee = 2025`, vérifié). Le texte affiché inverse les rôles : il annonce 2025 comme année de **calibration** alors que c'est l'année de **contrôle**, et étend l'entraînement à 2024 qui est l'année de calibration.
- **Preuve interne contradictoire :** le **commentaire du même fichier** `strings.ts:350‑354` énonce les faits corrects du FREEZE (« entraînement : mutations JUSQU'EN 2023 ; calibration sur 2024 ; vérifié sur l'année 2025 tenue à l'écart »). Le texte affiché contredit son propre commentaire d'en‑tête.
- **Correction proposée (NON appliquée) :** aligner sur le FREEZE — « apprise sur les mutations jusqu'en 2023, calibrée sur 2024, vérifiée sur 2025 (année tenue à l'écart) », ou la tournure vague « calibrée sur les millésimes les plus récents » **sans** citer « (calibrée sur 2025) ».

### B3 — Site public : « 3 000+ parcelles analysées » (2 occurrences)
- **Où :** `~/labuse.immo/labuse.immo/src/components/KeyFigures.astro:5` · `~/labuse.immo/labuse.immo/src/components/Hero.astro:61`.
- **Texte servi :** tuile « **3 000+** » / label « parcelles analysées ».
- **Réalité :** l'app analyse **431 663** parcelles (run servi, 24 communes) / **433 229** vivantes — « 3 000+ » **sous‑estime d'un facteur ≈ 140**. Vestige de la photo « pilote Saint‑Paul » du site (one‑pager, jamais remis à jour).
- **Preuve :** `parcels` vivants = 433 229 ; FREEZE contient `431663`, 24 communes (`communes_referentiel` = 24).
- **Correction proposée (NON appliquée) :** « **430 000+** parcelles analysées » (ou le chiffre servi dynamique si le site peut lire `/accueil/chiffres`).

### B4 — Site public : « Saint‑Paul, commune pilote » (2 occurrences)
- **Où :** `~/labuse.immo/labuse.immo/src/components/Hero.astro:85‑86` (« Saint‑Paul » / « en pilote ») · `~/labuse.immo/labuse.immo/src/components/KeyFigures.astro:8` (« Saint‑Paul » / « commune pilote »).
- **Texte servi :** présente **Saint‑Paul** comme « la commune pilote ».
- **Réalité :** LABUSE sert **les 24 communes** (`parcel_zone_plu` = 24 communes, scoring 24 communes, FRAICHEUR Tableau 1 = 21 PLU calibrés + zonage partout). L'état « pilote Saint‑Paul » est périmé.
- **Incohérence interne :** le **même** `KeyFigures.astro:6` affiche « **24** · communes visées » juste au‑dessus de « Saint‑Paul · commune pilote ».
- **Correction proposée (NON appliquée) :** remplacer la tuile « Saint‑Paul / commune pilote » par « **24 / communes couvertes** » (cohérent avec la tuile voisine), ou retirer la tuile pilote.

> Note sur le site public : il n'a **aucune page mentions légales / CGU / confidentialité** — les liens de pied de page pointent sur `#` (promesse de page non tenue). Classé `NON_VERIFIABLE` côté affirmation factuelle, mais à signaler (obligation légale).

---

## A — Données en retard confirmées (Volet A)

Preuve amont datée, en cache (`cache/`). Ce sont des **mises à jour de données**, indépendantes du run de scoring de ce soir. Détail et correction dans `FRAICHEUR.md § Candidats écarts`.

| # | Source | Servi | Dernière version amont | Écart | Correction proposée (NON appliquée) | Gravité |
|---|---|---|---|---|---|---|
| A1 | **GéoLittoral — érosion côtière** | millésime **2018** | nouvel INEC Cerema présenté 26/08/2026 | ~8 ans / 1 version majeure | Ré‑ingérer l'INEC 2026 en remplacement du trait de côte 062018 | moyenne |
| A2 | **Classement sonore ITT (Cerema)** | arrêtés **déc. 2023** | arrêtés préfectoraux 974 du **26/12/2024** | ~12 mois | Resync la couche V2 sur les arrêtés 26/12/2024 (preuve : web, dataset data.gouv dédié) | moyenne |
| A3 | **ZNIEFF (INPN)** | màj **29/08/2025** | resource rafraîchie **08/10/2026** (cycle 2×/an) | ≥1 cycle | Resync INPN ZNIEFF | faible |
| A4 | **DPE ADEME existant** | sync **19/09/2026** | `dataUpdatedAt` **14/10/2026** (flux hebdo) | ~4 sem. | Relancer la sync hebdo (cadence normale) | mineure |
| A5 | **Base Adresse Nationale** | sync **19/08/2026** | republiée en continu | ~2 mois | Relancer la sync mensuelle | mineure |

**Contrôle fait → CONFORME (16/10/2026, lecture seule) :**
- **PPR Saint‑André (97409)** — **À JOUR, confirmé.** La couche servie `kind='ppr'` (zonage réglementaire, source WFS DEAL `01risque/PPR_APPROUVE`, ingérée 2026‑07‑01) porte `approbation = 2026‑04‑16` / `document = PPR` : c'est bien le PPRN inondations+mouvements de terrain approuvé par l'**AP n°477 du 16/04/2026**. Comparaison à la source officielle vivante (fetch direct 16/10, cache `deal_ppr_approuve_97409.json`) : composition identique (2 INTERDICTION + 3 PRESCRIPTION) et **emprise identique au m² près** (INTERDICTION 13 886 488 m² = 13 886 488 m² ; PRESCRIPTION 26 802 341 ≈ 26 802 342 m²). Le PPRL littoral (`approbation 2024‑07‑17`) est servi séparément (correct). Aléas `georisque_alea` ingérés 2026‑09‑14 (postérieurs à l'approbation). **Rien à ingérer.**
- **Contours IRIS (64)** / **Filosofi 200 m (52)** : millésime d'édition non exposé / slug de veille incohérent → voir `FRAICHEUR.md` (NON VÉRIFIABLE, à fiabiliser hors run).

---

## Écart interne (non visible utilisateur)

- **`src/labuse/sentinelle.py` lignes 214, 587, 604** : le code sonde `codeInsee=97410` en le nommant « **Saint‑Pierre** » (second chef‑lieu témoin). Or **97410 = Saint‑Benoît** ; **Saint‑Pierre = 97416** (`communes_referentiel`, vérifié). Les témoins GASPAR/cavités/mvt/ssp/catnat échantillonnent donc **Saint‑Benoît**, pas Saint‑Pierre.
- **Effet :** nul sur la donnée servie (le témoin détecte bien un changement amont, peu importe la commune). C'est une **erreur de libellé** dans les commentaires.
- **Correction proposée (NON appliquée) :** soit corriger le libellé en « Saint‑Benoît (97410) », soit, si l'intention était bien Saint‑Pierre, passer les `url2`/`code_insee` témoins à **97416**. Hors périmètre de ce mandat.
