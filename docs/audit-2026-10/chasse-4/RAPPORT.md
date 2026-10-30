# CHASSE-4 — Audit en lecture seule des features mergées du 28 au 30 octobre

**Branche** `audit/chasse-4` · worktree `~/Desktop/labuse-chasse4` · API `127.0.0.1:8990` + front `127.0.0.1:6190` (base du Mac `postgresql:///labuse`, run servi **q_v20**).
**Opus, lecture seule.** Aucun correctif, aucun merge, aucune écriture base, aucun accès prod. `.env` copié depuis `labuse-main`.
**Méthode** : vrai navigateur (Playwright) + API en direct. Un bug n'est retenu que s'il est **reproduit à l'écran ou dans une réponse d'API**, jamais déduit du code seul ; `fichier:ligne` n'est donné que comme cause probable après reproduction.
**Périmètre strict** : ANNONCE-1→5 (outil, Docs, PDF), RADAR-FIX-3, RADAR-SOURCES-2 (Bien'ici), CORRECTIFS-2, REMISE-1. Rien d'autre.

> La suite sera **CHASSE-4-FIX**, rédigée par Vic sur ce registre. Aucune correction ici.

---

## Les cinq chiffres

| Parcours joués | Bugs | Bloquants | Majeurs | Mineurs |
|---:|---:|---:|---:|---:|
| **17** | **5** | **0** | **2** | **3** |

(Les parcours principaux — entrée adresse BZ1065 et entrée lien Leboncoin — ont été joués deux fois : à froid au démarrage, puis à chaud ; résultats **identiques** à chaque fois, logique déterministe.)

---

## Ce qui a été vérifié SAIN (pas de bug)

- **PDF outil == PDF Docs** : les deux passent par **la même route** `/analyse-annonce/{idu}.pdf` (et `/analyse-annonce.pdf?url=`). L'export de l'outil (`AnalyserAnnonce.tsx:40` → `ouvrir(url,'analyse-annonce')`) et Docs (`DocumentsView.tsx:315` → `docAnalyseAnnonceUrl`) appellent la même URL ; un test unitaire fige l'égalité (`AnalyseAnnonceDoc.test.tsx:18`). Identiques par construction.
- **Qualité PDF** (BZ1065, CX0800, lien LBC) : parcelle **entière** sur les 2 cartes (ortho + cadastre/zonage/aléas), aucun champ vide, aucun texte coupé, pagination `1/2`–`2/2`, formats FR (`3 235 €/m²`, `10,3 m`), **aucun code brut** (grep `None/null/dict/NaN/{}` → 0).
- **Entrée lien — cas d'erreur** : tous gérés, HTTP 200, message clair. LBC absente → « Cette annonce n'a pas encore été relevée par LABUSE et Leboncoin bloque sa lecture automatique. Entrez l'adresse… ». Bien'ici / SeLoger / URL invalide → « Collez un lien d'annonce Leboncoin… ». Le bandeau outil « SeLoger et Bien'ici à venir » est **exact** (l'entrée lien est Leboncoin-seule par conception — ce n'est pas un bug).
- **Règles transversales de l'outil** : « Changer de parcelle » revient à l'écran d'entrée ; « Retour » est unique et ramène d'un cran ; **changer d'outil vide tout** (réouverture de l'outil → champ lien vide, bouton désactivé).
- **CORRECTIFS-2 — `etat_bien`** : servi sur la fiche (BZ1065 `bati_encore`, CX0800 `nu`, AR0420 `bati_encore`) et **cohérent sur les 4 écrans** : fiche et liste utilisent la même constante `_ETAT_BIEN_SQL` (`app.py:3861`), la carte utilise un CASE inline **logiquement identique** (`app.py:3723-3726`, vérifié live : `/map/parcels.geojson` BZ1065 = `bati_encore`), les projets lisent la valeur de fiche.
- **RADAR-FIX-3** : colonne `pige_passes.n_non_verifiees` présente et servie ; `/admin/radar/etat` répond 200 (dernière capture + actives). Passes de confirmation historiques présentes (`n_supprimees` jusqu'à 134, `n_non_verifiees` 0).
- **RADAR / Leboncoin (UI)** : liste des biens en vente rendue intégralement — type · commune · quartier, prix (format FR), pièces/surface/terrain/€/m², lien « Voir l'annonce ↗ » vers `leboncoin.fr/ad/…`, type de vendeur + ancienneté, badge « En vente depuis N j ».
- **Console navigateur** : **0 erreur, 0 avertissement** sur tout le parcours. **API** : aucun 5xx hormis le C4-004 déclenché exprès (voir plus bas).

### Limites de reproduction (base Mac, lecture seule)

Ces points du mandat **n'ont pas pu être reproduits** et ne sont donc **pas** comptés comme bugs :

- **Bien'ici dans le Radar (portail, lien, commune, prix, dédoublonnage)** : la base Mac ne contient **que du Leboncoin** (`pige_annonces` : 428 lignes leboncoin, 0 Bien'ici ; `pige_biens` : 416, tous leboncoin). Les 95 annonces Bien'ici conservées au DEPLOY-1029b sont **en prod**, pas sur ce poste. Impossible à vérifier sans écrire dans la base (interdit : lecture seule). **À rejouer en recette prod.**
- **Clic carte → adresse dans la barre** : non reproduit en navigateur headless (sélection d'une parcelle au pixel sur la carte vectorielle). Le câblage existe dans l'entrée (« ou cliquez une parcelle sur la carte »).
- **Parcelle bâtie « sans emprise mesurée »** : aucune parcelle **non disparue** `taux_emprise_pct ≥ 5 %` sans `p_model_bati.emprise_bati_m2` sur la base (requête = 0 ligne). Le cas ne se présente pas pour une parcelle vivante.

---

## Registre des bugs

### C4-001 — MAJEUR — L'outil affiche « Fiabilité Moyenne » quand le modèle dit « Limitée » (sur-vente + contradiction avec le PDF)

**Écran (entrée adresse)** : pour BZ1065 le bloc « Estimation du prix » affiche **Fiabilité : Moyenne**, « 42 ventes comparables · rayon 500 m · 2021–2025 », « Précision mesurée sur les ventes 2025 : ±32 % ».

**API** `/radar/annonce/estimation/97411000BZ1065` :
```json
{ "fiabilite": "limitee", "precision_pct": 32, "n": 42, "commune_fallback": false, ... }
```
Le modèle classe la fiabilité **« limitee »** (écart médian ≥ 25 % → `_fiabilite_segment`, `pige/api.py:1513`), mais l'écran montre **« Moyenne »**.

**PDF (même parcelle, `/analyse-annonce/97411000BZ1065.pdf`)** : affiche correctement **« Fiabilité Limitée »**. → **l'écran et le PDF de la même parcelle se contredisent.** (Capture `captures/c4_bz1065_pg-1.png` : tuile « Fiabilité Limitée » ; capture écran `captures/C4-001_bz1065_ecran_moyenne.png` : « Moyenne ».)

**Reproduit sur** : BZ1065 (maison, ±32 % → limitee) **et** AR0420 (copro, ±32 % → limitee) — l'écran dit « Moyenne » dans les deux cas. À froid et à chaud : identique.

**Cause probable** — `frontend/src/components/outils/AnalyserAnnonce.tsx:59-61` :
```ts
if (communeFallback) return { mot: 'Limitée', ton: 'ambre' }
if (f === 'fiable')   return { mot: 'Élevée',  ton: 'vert'  }
return { mot: 'Moyenne', ton: 'ambre' }   // ← attrape 'moyen' ET 'limitee'
```
La fonction ne connaît que `'fiable'` et le repli commune ; la valeur backend **`'limitee'`** (hors repli) tombe dans le défaut « Moyenne ». Le PDF, lui, mappe correctement (`exports/blocs/annonce.py:66-67` : `if fiabilite == "limitee": return ("Limitée", …)`). Une branche `f === 'limitee'` manque côté front.

**Pourquoi c'est majeur** : la fiabilité est **remontée d'un cran** à l'écran principal de l'outil, exactement là où le produit ne doit pas sur-vendre la précision (cf. banc ESTIMATION-BANC-1). L'écran est aussi le premier vu par le client.

---

### C4-002 — MAJEUR — Le nombre d'aléas diffère entre l'écran et le PDF (même parcelle)

**Écran (entrée adresse), tuile « Risques »** :
- BZ1065 → **« 1 aléa »**
- CX0800 → **« 4 aléas »**

**PDF des mêmes parcelles, tuile « RISQUES »** :
- BZ1065 → **« 2 aléas »** (`captures/c4_bz1065_pg-1.png`)
- CX0800 → **« 2 aléas »**

→ Contradiction dans **les deux sens** (PDF > écran pour BZ1065 ; PDF < écran pour CX0800).

**API** `/parcels/{idu}` :
- BZ1065 `aleas.n = 1` (une entrée « PPR — zone bleue » couvrant inondation + mouvement de terrain) ; le PDF éclate le PPR en **2 lignes de risque** (Inondation, Mouvement de terrain) et compte 2.
- CX0800 `aleas.n = 4` (natures : `Aléa inondation`, `Aléa mouvement_terrain`, `PPR — zone rouge`, `PPR — zone bleue`) ; le PDF déduplique à **2 aléas** (une ligne par aléa, « sans doublon DEAL/PPR »).

**Cause probable** — deux sources différentes pour le **même compteur affiché identiquement « N aléa(s) »** :
- Écran : `frontend/src/components/outils/AnalyserAnnonce.tsx:116` → `const nAleas = f.aleas?.n ?? 0` (longueur brute de `aleas.liste` de `/parcels`).
- PDF : `src/labuse/exports/blocs/annonce.py:147,154` → `n_al = len(risq)` où `risq` est la liste **dédupliquée** `risques` du rapport (`_risques`, `annonce.py:311-312`).

**Pourquoi c'est majeur** : un chiffre d'en-tête, décisionnel en immobilier (nombre de risques), qui **se contredit** entre l'outil et son propre export PDF — le mandat vérifie explicitement « chaque chiffre du PDF existe à l'écran, et inversement ».

---

### C4-003 — MINEUR — Une copropriété est analysée comme une « Maison » individuelle, sans aucune mention « copropriété »

**Écran (entrée adresse)** — AR0420 (`p_model_ext_copro` + `copro_v2=true` côté carte) :
- en-tête « AR 0420 », note **« Maison — comparée aux ventes de maisons autour de la parcelle »** ;
- « Ordre de grandeur du bien : D'après l'emprise au sol BD TOPO (311 m²) × 1 971 €/m² = **613 000 €** », fourchette 417 000 – 809 000 € ;
- **aucune indication que la parcelle est une copropriété.** (Capture `captures/C4_ar0420_copro.png`.)

**API** `/radar/annonce/estimation/97420000AR0420` : `nature=batie`, `type_bien=maison`, `emprise_bati_m2=311`.

**Problème** : pour une copropriété (un bâtiment, plusieurs lots/propriétaires), présenter **l'emprise totale du bâti (311 m²) × €/m² maison** comme « l'ordre de grandeur du bien » est trompeur, et le label « Maison » est inadéquat. L'outil ne détecte pas la copro (`copro_v2` existe pourtant côté carte). Les garde-fous de l'estimation (« ordre de grandeur, pas un calcul exact », « surface habitable réelle non connue ») atténuent, mais ne disent jamais « copropriété ».

**Cause probable** : l'estimation (`pige/api.py`, chemin `estimation_annonce`) choisit le comparateur sur la nature bâti/nu sans lire l'indicateur de copropriété ; le front n'affiche pas `copro_v2`.

---

### C4-004 — MINEUR (environnemental) — 500 sur l'estimation d'une parcelle disparue du cadastre

**API** `/radar/annonce/estimation/97418000AP0782` → **HTTP 500 Internal Server Error** (reproduit 2×).

**Traceback (journal API)** :
```
psycopg.errors.UndefinedTable: relation "parcel_cadastre_remplacement" does not exist
[SQL: ... FROM parcel_cadastre_remplacement r JOIN parcels p ... WHERE r.ancienne_idu = %(i)s ...]
```

**Analyse** : AP0782 est une **parcelle disparue** (`parcels.cadastre_disparue_le` renseigné). La garde « parcelle disparue » (`cadastre_disparue.py:47-51`, CHASSE-DONNEES-FIX-1 — **hors périmètre chasse-4**) interroge `parcel_cadastre_remplacement`, **table absente de la base Mac** (`to_regclass` = NULL). Les parcelles **vivantes** (BZ1065, CX0800…) ne déclenchent pas cette garde et répondent 200.

**Portée réelle** : **environnemental**. La table existe en prod → le 500 ne se reproduirait **pas** en prod (la garde y rendrait vraisemblablement le message de courtoisie « parcelle disparue »). Le comportement de l'outil « Analyser une annonce » face à une parcelle disparue **en prod** n'a pas pu être testé (pas d'accès prod). À noter tout de même : le **nouvel** endpoint d'estimation (chasse-4) n'est pas résilient à l'absence de cette table. Non reproductible via le parcours UI normal (une parcelle disparue n'est ni cherchable ni cliquable).

---

### C4-005 — MINEUR — Terrain nu : deux comptes de ventes différents sur le même écran (78 vs 118)

**Écran (entrée adresse, parcelle nue)** — CX0800 :
- ligne d'estimation : « 495 €/m² · Fiabilité Moyenne · **78 ventes de terrain** · secteur cadastral · 2021–2025 » ;
- accordéon juste en dessous : « **Les ventes de terrain nu (118)** » (8 affichées + « 110 autres ventes de terrain nu à proximité »).

**API** `/radar/annonce/estimation/97413000CX0800` : `n = 78` (repère €/m² calculé sur le secteur cadastral) ; `n_total = 118` (liste illustrative « à proximité »).

**Problème** : deux nombres de « ventes de terrain nu » coexistent sur le même panneau, avec des périmètres différents (**secteur cadastral** = 78, **à proximité** = 118) mais sans que leur différence soit explicitée — un client peut y voir une incohérence. Le cas « bâti » ne se présente pas : pour BZ1065 `n == n_total == 42` (même population). Spécifique au comparateur terrain nu.

**Cause probable** : le repère €/m² terrain est calculé sur un périmètre « secteur » (`repere_terrain_nu.n`), tandis que l'accordéon liste `n_total` (comparables « à proximité »). Deux champs distincts du même payload, affichés avec le même vocabulaire « ventes de terrain nu ».

---

## Observations (hors registre — ni bug reproduit, ni dans le périmètre strict)

- **PDF plus riche que l'écran (par conception)** : la page 2 du PDF parcelle ajoute un tableau de règles « Le foncier », un tableau « Risques et contraintes », une section « Le marché · commune » (ex. BZ1065 : 289 ventes, médiane maison 3 235 €/m², appartement 2 600 €/m², terrain nu 459 €/m², −3,3 %) et « Ce qu'il reste à vérifier » — absentes de l'écran outil. Ces chiffres sont **additifs** (sourcés, étiquetés par périmètre), pas contradictoires. Conforme au design ANNONCE (document 2 pages vs panneau résumé). Signalé pour mémoire au regard de la règle « chaque chiffre du PDF existe à l'écran ».
- **Accueil Radar** : le libellé « Les biens en vente sur **Leboncoin** » (et la section « Radar ») ne mentionne pas Bien'ici alors que la prod en contient désormais. Copie potentiellement à rafraîchir — non confirmable ici (aucune donnée Bien'ici sur la base Mac).
- **Panneau marché du Radar** (hors périmètre chasse-4, pré-existant) : typographie FR non uniforme — « 3 038€/m² » (sans espace avant €) et « +29.6 % » (point décimal) au lieu de « 3 038 €/m² » / « +29,6 % ». Mentionné car visible à l'écran, mais hors des features mergées 28–30/10.

---

## Annexes — reproduction

- **Lancement** : API `PYTHONPATH=…/labuse-chasse4/src labuse-main/.venv/bin/python -m uvicorn labuse.api.app:app --port 8990` (venv main = weasyprint OK pour les PDF) ; front `LABUSE_API_DEV=http://127.0.0.1:8990 npm run dev -- --port 6190 --strictPort` (servi sous `/socle/`).
- **Parcelles de test** : BZ1065 `97411000BZ1065` (bâtie, maison) ; CX0800 `97413000CX0800` (nue, Saint-Leu) ; AR0420 `97420000AR0420` (copropriété, Sainte-Suzanne) ; AK0182 `97411000AK0182` (nature inconnue / non mesurée) ; AP0782 `97418000AP0782` (disparue, pour C4-004).
- **Lien de test** : `https://www.leboncoin.fr/ad/ventes_immobilieres/3226754959` (maison Saint-Leu, relevée Radar le 27/10/2026).
- **Captures** : `captures/` — `C4-001_bz1065_ecran_moyenne.png` (écran « Moyenne »), `c4_bz1065_pg-1.png` / `c4_bz1065_pg-2.png` (PDF, « Limitée » + « 2 aléas »), `C4_ar0420_copro.png`, `C4_lien_lbc.png`, + PDF `c4_bz1065.pdf`, `C4_cx0800.pdf`, `c4_lien_lbc.pdf`.
