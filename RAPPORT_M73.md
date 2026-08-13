# RAPPORT M73 — Les pièces exportables : cohérence, véracité, direction artistique
## PHASE 0 — DIAGNOSTIC (mesure pure, aucune correction) — **STOP, arbitrage attendu**

Branche `feat/m73-exports`. Les 5 documents ont été **réellement générés** (API `localhost:8000`,
run `q_v8_calibre`) sur **3 parcelles de recette de 3 communes** et leur texte extrait :

| Parcelle | Commune | Tier servi | Particularité |
|---|---|---|---|
| **97410000BV0120** | Saint-Benoît | écartée | la parcelle-problème du mandat (18 354 m², PPR/aléas) |
| **97415000AC0253** | Saint-Paul | chaude | **retenue** (pas seulement écartée), marché dense |
| **97417000AE0003** | Saint-Philippe | à creuser | **sans PLU publié** (RNU) + retenue |

Pièces jointes : `docs/mandats/m73_pieces/` (premium/dossier/banquier PDF + one-pager HTML × 3 parcelles,
+ extractions texte). Les 5 générateurs :

1. **Fiche premium PDF** — `api/pdf_premium.py` (fpdf) — endpoint `/parcels/{idu}/export.pdf`
2. **Dossier parcelle PDF** — `api/dossier.py` + `flash/report.py` + `flash/data.py` + `flash/templates/rapport.html.j2` (weasyprint) — `/dossier/{idu}.pdf`
3. **Dossier banquier PDF** — `api/banquier.py` + `api/briques_pdf.py` (weasyprint) — `/dossier-banquier/{idu}.pdf`
4. **One-pager HTML** — `api/export.py` `fiche_onepager` — `/parcels/{idu}/export?format=onepager`
5. **Fiche écran** — payload `api/app.py` `parcel_fiche` — `/parcels/{idu}`

---

## A — UN POINT DE CALCUL, PAS CINQ (cause racine)

**La fracture n'est pas partout.** Le verdict/tier/rang, le marché commune (DVF condensé) et le ZAN sont
**déjà mono-sourcés** et cohérents : `verdict_servi` + `rang_total` (`verdict_servi.py`), `marche_bloc.bloc_condense`
(`marche_bloc.py`), `commune_conso_enaf`. Là où il y a contradiction, la cause est un **double rail de cascade** :

> **Premium PDF + fiche écran** lisent `_q_v2_fiche` → table **`dryrun_cascade_results`** (run figé).
> **Dossier + banquier + one-pager/md/html** passent par `_build_fiche` / `collect_report_data` → tables
> **`cascade_results` / `spatial_layers`** (recalcul legacy).
>
> Deux chemins parallèles pour les **mêmes** aléas, PPR et zonage, alimentés par le même moteur `phase1.py`
> en amont mais lus à deux stades différents → d'où « eleve » présent d'un côté, absent de l'autre.

### Recalculs locaux à supprimer (priorité)

| Donnée | Recalcul local constaté | Fait foi (proposé) |
|---|---|---|
| **Aléas / PPR / zonage** | double rail `dryrun_cascade_results` (premium+fiche) vs `cascade_results`/`spatial_layers` (dossier+banquier+one-pager) | **une seule cascade servie** pour les 5 |
| **Comparables DVF** | **3 requêtes distinctes** : dossier `dvf_mutations` 500 m/3 ans · banquier `sector_price` rayon adaptatif 1000 m · one-pager `voisinage_proche` <100 m | **1 service comparables** (paramètres uniques) — cf. chevauchement `MANDAT_DVF.md` |
| **Permis voisins (SITADEL)** | **3 requêtes** : `flash/data.py` 500 m/24 mois · `briques_pdf.nearby_permits` · `app._voisinage_proche` <100 m | **1 service permits** |
| **Distances ICPE/ABF** | `ST_Distance` recalculé localement dans `flash/data.py` | service distances partagé |
| **Table sources** | dossier a sa table `_SECTION_SOURCES` en dur ; les autres tirent de `data_sources` | `data_sources` (déclaratif ; cf. réserve M66 : déclaration ≠ mesure) |

### Faux problème / à nommer
- **Total du parc** : **428 239 partout** (premium, dossier, banquier, one-pager, fiche — `rang_total` = parcelles
  scorées). **Le 431 663 du mandat n'est reproduit NULLE PART** dans la sortie actuelle — l'écart historique est
  **résorbé**. Reste que 428 239 (scorées) et 431 663 (parc de référence) sont deux univers légitimes jamais
  **nommés** au lecteur → un banquier ne sait pas sur quoi porte le rang. **À nommer, pas à corriger.**

**Synthèse A :** un seul vrai schisme (le double rail de cascade) et deux triplets de requêtes redondantes (DVF, SITADEL) ;
tout le reste est déjà mono-sourcé. Unifier le rail cascade éteint à lui seul les contradictions aléas/PPR/zonage.

---

## B — BON PARCELLE, BONNES DONNÉES + NON-CONTRADICTION

### B1 — Circulation, isolation, contexte : **CONFORME** (aucun défaut)
- **IDU de bout en bout** : chaque document nomme la bonne parcelle/commune/surface sur les 3 cas (18 354 / 1 815 / 1 906 m²).
- **Fuite de session : AUCUNE.** Enchaînements testés au réel (premium AC0253→AE0003, dossier AC0253→AE0003,
  banquier prepare AC0253→AE0003) : le second document ne contient **aucun** résidu du premier. Isolation par IDU vérifiée.
- **Contexte commune correct** : SRU/QPV/ZAN/prix distincts et justes pour Saint-Benoît (34.49% / 2 QPV / 14.3 ha),
  Saint-Paul (18.33% / 11 QPV / 90 ha), Saint-Philippe (9.57% / 0 QPV / 12.3 ha). **Pas de fallback Saint-Paul.**
- **Comparables/permis/distances centrés** sur la parcelle (distances PC croissantes réelles : AC0253 19/47/78 m…).
- **Carte/ortho** : BBOX WMS et liens *remonter le temps* centrés sur les coordonnées exactes de chaque parcelle. **Bonne emprise.**

### B2 — Contradictions confirmées au réel (croisement 5 docs + fiche)

| # | Donnée | Ce qui diverge | Documents |
|---|---|---|---|
| 1 | **Aléa mouvement de terrain** | premium + fiche listent **2 niveaux** (faible/moyen) ; dossier + banquier en listent **3** en ajoutant **« eleve »** (BV0120, AE0003). Sur AC0253 : « faible » vs « faible_a_modere » | tous |
| 2 | **Régime PPR** | couche **GPU** : « Exclue PPR zone rouge » **+** « intersection marginale <10 % sans présomption de contrainte forte » (premium, one-pager, fiche) ; couche **DEAL** : « Interdiction **R1** » **+** « Prescription **B2u** » (dossier, banquier). Deux récits, aucun arbitrage — et « rouge inconstructible » vs « marginal <10 % » se contredit **dans le seul premium** | tous (BV0120) |
| 3 | **Prix médian** | **absent du banquier** (BV0120, AE0003) alors que dossier/premium l'affichent (2 185 / 1 786 €/m²). Sur AC0253 : banquier **3 846 €/m²** (existant, n14) vs dossier/fiche **3 322 €/m²** (appartements, n16) — métriques différentes non réconciliées | dossier/premium vs banquier |
| 4 | **Consommation d'espace (ZAN)** | même donnée, **deux unités** : dossier en **m²/an**, banquier en **ha/période totale** (numériquement concordants après conversion, mais non croisables par un lecteur) | dossier vs banquier (3 parcelles) |
| 5 | **Comptes de ventes marché** | 1 / 14 / 1 selon premium (≤250 m/5 ans) / banquier (1000 m/[2021-25]) / fiche (<100 m) — écart méthodologique **jamais explicité côte à côte** (37/33/0 du mandat = même famille de divergence de fenêtre) | tous |

**Non reproduit / résolu :** le dénominateur **431 663** (partout 428 239) ; pas de contamination de session ; pas de mauvais contexte commune.

**Synthèse B :** l'isolation et le bon-parcelle sont **sains** ; les contradictions réelles sont **4** (aléa, PPR,
prix médian, unité ZAN) + 1 divergence de fenêtre marché — toutes soit issues du double rail (A), soit d'un
**arbitrage manquant** (quelle valeur retenir quand deux couches se recouvrent).

---

## C — FAUX POSITIFS (9/9 confirmés au réel)

| # | Constat | Réel | Cause (fichier:ligne) | Correctif |
|---|---|---|---|---|
| 1 | **« usine 0 m » / « temple hindouiste 0 m »** (ABF) | **dossier uniquement** ; premium (« abords ~500 m ») et banquier (« ~500 m ») sont **corrects** | `spatial_layers.kind='abf'` stocke le **tampon 500 m** (polygone), la parcelle est dedans → `ST_Distance`=0 (`flash/data.py:332`, rendu `rapport.html.j2:290`) ; libellé Mérimée brut (`abf_merimee.py:49`) | ne pas afficher une distance à un tampon → « abords ~500 m — covisibilité à instruire » |
| 2 | **`config/plu_<commune>.yaml` « non outillé »** | banquier p.4 | le YAML **existe** (23/24) mais `zones:{}` vide → `resolve_zone` retombe générique `calibree=False` ; message émis sur `if not rules.calibree` sans distinguer « pas de YAML » de « zone non calibrée » (`faisabilite/engine.py:171`) | brancher sur présence réelle du YAML ; dire « zone non calibrée » et **retirer le chemin `config/...`** |
| 3 | **`**SYNTHÈSE EXÉCUTIVE**`** (astérisques markdown) | banquier p.1 | LLM renvoie du markdown ; `_synthese_html` fait `_esc` sans strip (`banquier.py:142`) | strip markdown avant rendu |
| 4 | **Tableau faisabilité vide** (4 en-têtes, 0 ligne) | banquier p.4 | zone A → `steps=[]`, mais `faisabilite()` rend toujours le `<table>` (`briques_pdf.py:474`) | si `not steps` → phrase (« neuf non autorisé en zone A ») |
| 5 | **`(M38)`** | one-pager | chaîne d'honnêteté `site_voisinage.py:79` | retirer `(M38)` |
| 6 | **« Généré via LABUSE pour Pilote LABUSE » ×6** | dossier (pied de chaque page) | `dossier.py:105` imprime `raison_sociale` = défaut « Pilote LABUSE » (`config.py:100`) | masquer « pour … » quand valeur = défaut |
| 7 | **« usage interne »** en en-tête d'un doc client | dossier | `dossier.py:99` `produit_sous_titre="DOSSIER PARCELLE · usage interne"` | sous-titre neutre / retirer |
| 8 | **« LA BUSE »** (2 mots) | one-pager vs « LABUSE » ailleurs | wordmark en dur `export.py:650` | « LABUSE » |
| 9 | **DPE ADEME + INPI RNE en pied** sans aucune donnée DPE/dirigeant | premium, dossier, one-pager | bloc statique `SOURCES_ATTRIBUTION` (`export_commun.py:25`) réutilisé inconditionnellement | conditionner chaque source citée à sa présence effective dans le doc |

---

## D — CLÉS TECHNIQUES & SCORES BRUTS QUI ATTEIGNENT LE PAPIER

| Ce qui fuit | Document(s) | Générateur:ligne | Correctif |
|---|---|---|---|
| `PPR INONDATION_MOUVEMENT_DE_TERRAIN` (MAJ_underscore) | premium, dossier, banquier, one-pager | source cascade `phase1.py` / `flash/data.py:299` | mapper « PPR inondation et mouvement de terrain » |
| `Aléa mouvement terrain — eleve` (**sans accent**) | dossier, banquier | `phase1.py:569` `niveau` brut | dict `faible/moyen/élevé/fort` + accents |
| `mouvement_terrain — niveau faible` (underscore) | premium | `phase1.py:569` `alea_type` brut | « mouvement de terrain » |
| `osm_faux_positif` (clé de couche) | premium | `pdf_premium.py:367` `_LAYER_LABEL` — clé absente | ajouter au dict / masquer couche interne |
| `parcel_residuel` (nom de table) | premium, fiche | `etage0_ext.py:160` détail | réécrire sans nom de table |
| `PM1 (PM1_PPR_i_mvt_SAINT_BENOIT_gen2_ass)` (id SUP) | premium | détail couche `sup` brut | retirer le code d'assiette |
| `**SYNTHÈSE EXÉCUTIVE**` (markdown) | banquier | `banquier.py:142` | strip markdown (cf. C3) |
| `config/plu_<commune>.yaml` (chemin) | banquier | `briques_pdf.py:475` | retirer (cf. C2) |
| `(M38)` (mandat) | one-pager | `site_voisinage.py:79` | retirer (cf. C5) |
| `QUALITÉ 50/100 · ESTIMÉ`, `ACCESSIBILITÉ 50/100` (scores quasi-constants) | premium | `pdf_premium.py:223` | retirer/contextualiser (3 valeurs sur tout le parc, cf. M66) |
| `Confiance … 60/100` (ICD) | premium | `pdf_premium.py:249` | harmoniser les « /100 » nus |
| `N signal(aux)` (dont « Marché 4 signal(aux) » = couches ≠ ventes) | premium | `pdf_premium.py:397` | désambiguïser le libellé Marché |
| `usine`, `temple hindouiste` (Mérimée brut) | dossier, banquier | `flash/data.py` couche abf `name` brut | capitaliser/nettoyer |

**Note fiabilité :** une passe **statique** avait conclu « aucune fuite » ; l'**extraction réelle des PDF** la
contredit — ces chaînes naissent en amont (`phase1.py:569`), pas dans le générateur. Les constats ci-dessus
s'appuient sur le texte réellement imprimé (`docs/mandats/m73_pieces/*.txt`).

---

## E — FRAÎCHEUR (date d'ingestion présentée comme millésime)

**Cause unique** : `_sources()` (`flash/data.py:605-635`) — chaîne statique → `source_millesime` (vrai amont) →
**`synchronisé le {last_sync_at}`** → « horizon amont non publié ». Quand `source_millesime` est **NULL** (dette data
sur la plupart des sources) mais `last_sync_at` renseigné, la **date d'ingestion** apparaît dans la colonne
« MILLÉSIME / SYNCHRONISATION ».

| Endroit | Date affichée | Type réel | Correctif |
|---|---|---|---|
| Dossier « 09 Sources » — Sitadel, ITT Cerema, Mérimée, QPV, Géorisques (×3), Cartofriches, BAN | « synchronisé le 2026-07-xx / 08-13 » | **date d'ingestion** (`last_sync_at`, `source_millesime` NULL) | peupler le vrai millésime amont ; sinon afficher « horizon amont non publié », **jamais** `last_sync` sous « MILLÉSIME » |
| Premium — date sous chaque règle (35 signaux) | « 2026-07-29 » (uniforme) | **date de run/pipeline**, pas un millésime par source | remplacer par le millésime amont de la couche ; une date pipeline uniforme n'est pas une « fraîcheur par ligne » |

**Légitime, à conserver** : « généré le 2026-08-13 » (génération du doc, en pied) ; « PLU approuvé le 2020-02-06 »,
« DVF 2025 », « inventaire SRU 01/01/2024 » (vrais millésimes amont) ; « horizon amont non publié » (honnête).

---

## F — CE QUI MANQUE

| Document | Manque | Présent en base ? |
|---|---|---|
| **Premium** | **aucun comparable DVF listé** (1 ligne-signal « médiane terrain 379 €/m², 1 mutation »), pas de prix bâti, pas de dernière mutation | **oui** — `dvf_mutations` 29 566 ; banquier sait produire la table (Q1 3042/méd 3846/Q3 4186, n14) |
| **Premium** | **zéro image** (0 vs 42 pour dossier/banquier) : ni cadastre, ni ortho, ni carte de situation | oui (carte OSM embarquée par les autres) |
| **Premium** | 4 signaux « non imprimés (format 2 pages) » (Marché/Propriétaire tronqués) | oui (portés par la fiche) |
| **Dossier + Banquier** | **réseaux absents** : dossier « 08 Terrain & réseaux » ne cite qu'assainissement/pente/solaire ; le banquier **n'a pas de section réseaux** — aucun AEP/EDF/voirie ni distance de raccordement | partiel — `viabilisation` (score 90) en base, n'irrigue aucune section |
| **Dossier** | comparables sous-échantillonnés (**1 vente / 500 m / 3 ans**) là où le banquier en trouve **14** (1000 m) | oui — paramétrage incohérent entre deux docs de la même parcelle |
| **3 PDF weasyprint** | **scénario réhabilitation (dette M59) jamais rendu ni expliqué** (`mode_b` existe mais gaté ; le PDF ne dit pas pourquoi il est absent) | oui (gate stricte) |
| **Premium + Dossier + Banquier** | **aucun call-to-action / prochaine étape** après la dernière page ; **seul le one-pager** en porte un (« Prochaine action : vérifier PLU/CU… ») | — |

**Constats du mandat infirmés au réel** : le **banquier a bien** une charge foncière (319 k€ sur AC0253), un prix
médian et une table de comparables ; le **premium affiche bien** le ratio ×N (×5.0). Le « Terrain & réseaux sans
réseau » avéré est **côté dossier** (le banquier n'a pas du tout cette section).

**Retenue (chaude) vs écartée** : même squelette, mais contenu réellement plus riche pour la retenue (charge foncière,
14 comparables, 10 permis, bilan CA 3.7 M€) — l'adaptation est réelle. Les trous (pas de comparables au premium,
pas de réseaux, pas de CTA) sont **structurels**, pas un défaut d'adaptation.

---

## ARBITRAGES DEMANDÉS (avant toute correction Phase 1)

**Cause racine & source unique**
1. **Double rail de cascade** — unifier les 5 documents sur **une seule cascade servie**. Quel rail fait foi :
   le **dryrun figé** (`dryrun_cascade_results`, ce que voit la fiche écran + premium) ou le **legacy recalculé**
   (`cascade_results`) ? Recommandation CC : **le dryrun servi** (cohérent avec la fiche, source de vérité du Socle),
   dossier/banquier/one-pager s'y branchent. C'est le chantier lourd du mandat.
2. **DVF/comparables** — un seul service comparables pour les 5 docs, **mais** le fond du calcul (le 379 €/m² faux,
   rayon, seuil de ventes) relève de **`MANDAT_DVF.md`** déjà écrit en M70. **Question : traite-t-on l'unification
   du point d'appel dans M73 et on laisse le calcul à MANDAT_DVF, ou on fusionne les deux ?** Recommandation :
   M73 unifie l'**appel**, MANDAT_DVF corrige le **calcul** — les deux se rejoignent sur le même service.

**Arbitrages de valeur (règle « la plus contraignante, nommée, jamais côte à côte »)**
3. **Aléa mouvement de terrain** — retenir le niveau **le plus contraignant** (« élevé »), le nommer, ne jamais
   lister les niveaux ensemble. Confirmer la règle.
4. **Régime PPR** — GPU (rouge/marginal <10 %) vs DEAL (R1/B2u) : **quelle couche fait foi** ? Recommandation :
   la **DEAL réglementaire** (R1/B2u) prime sur l'intersection GPU géométrique ; on retient le régime le plus
   contraignant et on supprime le « marginal <10 % » quand une prescription/interdiction s'applique.
5. **Consommation d'espace** — **une seule unité** partout. Recommandation : **ha par période** (langage banquier),
   + un pas annuel dérivé si utile, mais pas deux unités concurrentes.
6. **Prix médian** — l'**ajouter au banquier** ; réconcilier 3 846 (existant) vs 3 322 (appartements) en **nommant
   le segment** de chaque médiane plutôt qu'en les opposant.
7. **Dénominateur du parc** — **nommer** « rang sur N parcelles scorées » (428 239) partout ; confirmer qu'on ne
   réintroduit pas 431 663.

**Faux positifs & fuites (C + D + E)** — lot de corrections mécaniques, peu d'arbitrage :
8. GO sur les 9 faux positifs (C1-C9) et les fuites D — **sauf** décision sur les **scores nus 50/100 & 60/100**
   du premium (retirer entièrement, ou conserver l'ICD /100 seul ?).
9. **Fraîcheur (E)** — GO sur le correctif structurel `_sources()` (ne jamais afficher `last_sync_at` sous
   « millésime ») ? Le vrai millésime amont est parfois à peupler (dette data séparée).

**Manques (F)** — ce sont des **ajouts** (arbitrage de périmètre) :
10. Premium : **ajouter comparables DVF + un plan/ortho** (aujourd'hui 0 image) ? — plus gros poste.
11. **Réseaux** dans dossier/banquier (brancher `viabilisation`) ?
12. **Réhabilitation M59** dans les 3 PDF, ou au moins **expliquer** son absence ?
13. **Call-to-action / « Ce que ce document ne peut pas dire »** (point 5 du mandat) en fin de **chaque** document ?

**Direction artistique (point 4)** — recopier les classes des maquettes `DA-BANQUIER-v1.html`, `DA-DOSSIER-v1.html`,
`DA-PDF-v2.html`, comparaison côte à côte avant commit. **Chantier visuel confirmé pour la Phase 1 ?**

---

### Garde-fous Phase 0
Aucune écriture de code (mesure pure). API servie, 5 documents × 3 parcelles générés en HTTP 200. Pièces jointes
dans `docs/mandats/m73_pieces/`. **NE PAS MERGER — STOP arbitrage.**
