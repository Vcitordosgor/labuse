# M12 — LOT A : AUDIT (lecture seule)

**Branche** : `audit/m12-a` · **Base** : `main` · **Date** : 2026-07-24
**Règle** : zéro modification de code. Ce document répond, il ne corrige pas.
**Golden** : 116/116 PASS en début de lot (référence `reports/m6-audit/golden/golden-parcelles.json`, API locale bootée sur :8011, run servi `q_v7_defisc`).

> Ce lot bloque B (A1/A3/A5), D, E (A2/A4/A5) et H, et prépare C-bis (A8) et G2 (A7).

---

## A3 — Métrique ×N : suspicion de bug (PRIORITAIRE — trigger d'arrêt dur)

### Verdict : **LE CALCUL N'EST PAS FAUX. Pas d'arrêt dur. La vague continue.**

**Formule (source unique, gelée M3.6).**
`src/labuse/scoring/p_v2/pipeline.py:260` :
```python
"mult_base": np.round(p / taux_base, 2),
```
avec (`pipeline.py:197` et `:216`) :
```python
p = model.predict_proba(df)          # probabilité de mutation, ∈ [0, 1]
taux_base = float(p[hors].mean())    # taux de base = moyenne de p hors copro
```
`mult_v2` servi à l'écran = colonne `parcel_p_score_v2.mult_base` (cf. `api/app.py:1302`, `api/tiles.py:127`). L'affichage `ResultsSection.tsx:104` fait `×${p.mult_v2.toFixed(1)}`.

**Valeurs brutes en base (run servi `q_v7_defisc`) pour les 3 premiers rangs :**

| rang | idu | `p_raw` | `mult_base` | affiché | tier |
|---|---|---|---|---|---|
| 1 | 97423000AB1908 | **1.0** | 63.97 | ×64.0 | brulante |
| 2 | 97408000AP1647 | **1.0** | 63.97 | ×64.0 | chaude |
| 3 | 97408000AP1610 | **1.0** | 63.97 | ×64.0 | chaude |
| 4 | 97423000AB1910 | 1.0 | 63.97 | ×64.0 | brulante |
| 5 | 97408000AP1609 | 1.0 | 63.97 | ×64.0 | chaude |
| 6 | 97423000AB1911 | 0.5409 | 34.6 | ×34.6 | brulante |
| 7 | 97411000KA0296 | 0.34375 | 21.99 | ×22.0 | brulante |

- `taux_base` (moyenne de p hors copro) = **0.015636**. Donc `1.0 / 0.015636 = 63.96…` → arrondi 63.97 → `toFixed(1)` → **×64.0**. Cohérent au centième.
- Distribution `p_raw` hors copro : max=1.0 (partagé par **exactement 5 parcelles**), puis 0.5409 (×1), puis 0.34375 (×15)…

**Explication.** Les 3 (en fait 5) parcelles de tête affichent le même `×64.0` parce que le modèle leur assigne la **même probabilité brute `p_raw = 1.0`** (saturation haute du logistique). `×N = p / taux_base` atteint alors son **plafond mathématique naturel** `1/taux_base ≈ 63.97` : une parcelle « certaine de muter » (p=1) est par construction ~64× plus probable que la moyenne de l'univers. Ce n'est ni un plafond arbitraire codé en dur, ni un arrondi qui fabrique le 64, ni un mauvais affichage : c'est la valeur exacte.

**Ce qui est réel mais N'EST PAS un bug de calcul (et relève du modèle P, gelé — donc hors mandat) :**
- Le `×N` **perd son pouvoir discriminant en tête** : 5 parcelles à égalité parfaite sur P (p=1.0). Leur ordre relatif (rang 1..5) ne vient que du départage seedé 974 + du tier, pas d'un écart de P. Un client qui trie par ×N verra 5 fois « ×64.0 » d'affilée.
- `toFixed(1)` transforme 63.97 en un « ×64.0 » d'apparence ronde/suspecte. **Piste LOT B** (vocabulaire d'affichage), pas une correction de scoring.

**Conclusion pour le mandat.** La condition d'arrêt dur A3 (« le lift est mal calculé ») **n'est pas remplie**. Aucune correction du scoring. Le LOT B ré-habillera l'affichage de `×N` (unité de sens) sans toucher au calcul.

---

## A1 — Tris des résultats

**Verdict : les 4 tris fonctionnent, aucun n'est cassé ni no-op.** Preuve d'exécution : sur le run servi `q_v7_defisc`, `rang` est **unique** (428 239 distincts = 428 239 non-nuls) et `rang IS NULL ⟺ copro` (3 424 des deux côtés) → tri total sans ex-æquo sur la partie classée.

Deux implémentations coexistent :
- **Mode « Toute l'île »** : tri **côté SQL** (`getResults(filters, 500, sort)`, le client ne re-trie pas, `ResultsSection.tsx:283-288`).
- **Mode commune** : tri **côté client** JS (`.sort()`, `ResultsSection.tsx:292-301`).

Boutons définis en `ResultsSection.tsx:220-225` (`rang`/`mult`/`surface`/`commune`).

| Bouton | Ce qu'il trie (backend `_Q_V2_ORDERS_PAGE`, `app.py:1408-1413`) | Frontend | Cohérent |
|---|---|---|---|
| **rang P** | `rang_v2 ASC NULLS LAST, mult_v2 DESC, evenement DESC, (q+a) DESC` (+ chemin index rapide top-N `app.py:1462-1486`). = **rang de scoring P croissant** (rang 1 = meilleur, p=1.0), copros (rang NULL) en queue. | `ra-rb` puis `mult DESC` (Infinity pour NULL) | Oui |
| **×N** | `mult_v2 DESC NULLS LAST, rang_v2 ASC`. = **multiplicateur décroissant** (×63.97 en tête). Quasi-inverse de rang (attendu, pas un no-op). | `b.mult - a.mult` | Oui |
| **surface** | `surface_m2 DESC NULLS LAST, rang ASC`. Grandes parcelles d'abord. | `b.surface - a.surface` | Oui |
| **commune** | `commune ASC, rang ASC`. Alpha. | `localeCompare` (léger écart accents FR, bénin) | Oui |

**Divergence bénigne** : le backend ajoute des tiebreakers (`evenement_rouge`, `q+a`) absents du front, invisibles en pratique (clé rang déjà unique ; le front ne re-trie qu'en mode commune, petits volumes). **Aucune correction B3 nécessaire côté logique de tri** — B3 se limitera aux libellés + marges.

## A2 — Plafond 500 résultats

**Cinq caps empilés :**

| # | Cap | Emplacement |
|---|---|---|
| 1 | slice client **200** (`CAP`) | `ResultsSection.tsx:217`, appliqué `:303` |
| 2 | réseau **500** (`getResults(...,500,...)`) | `ResultsSection.tsx:247` → `api.ts:104` |
| 3 | borne serveur `/parcels` défaut 100, **le=1000** | `app.py:828` |
| 4 | borne CSV défaut 1000, **le=5000** | `app.py:896` |
| 5 | demande CSV = **5000** | `api.ts:108` |

- Les deux libellés du mandat viennent tous deux de `ResultsSection.tsx:426-430` : **« 200 visibles ici / 500 »** = slice 200 / 500 renvoyés ; **« 500 premiers (île) »** = cap #2 atteint.
- Le bouton **« Tout voir »** (`:437-441`) ne déplafonne QUE le slice 200→500 (`showAll`). **Il ne va PAS chercher au-delà des 500.** En mode île, impossible de voir plus de 500 parcelles.
- **Aucune pagination ni infinite scroll** câblés côté front pour cette liste.
- **CSV** : échappe au cap 500 → monte à **5000** (mêmes filtres, même tri, `app.py:909-914`), mais **pas exhaustif** (77 718 en « Tout »). → E4 dit « CSV inchangé » : on n'y touche pas.
- **Mécanique** : LIMIT/OFFSET **en SQL** (top-N sur index `ix_p_v2_run_rang`, ~2 ms sur le tri `rang`), PAS de fetch-all-then-slice. Le seul « slice » est le 200 client sur les 500 SQL.
- **Coût pagination (pour E3)** : le paramètre `offset` **existe déjà** jusqu'au `LIMIT :lim OFFSET :off` (`app.py:828`, `:1485/:1501`) — seul le câblage front manque. Tri `rang` = keyset quasi-gratuit (index top-N). Tris `mult/surface/commune` = chemin historique avec JOIN complet → OFFSET profond coûteux (VPS CPU-bound). **Reco E3 : pagination par offset (bon marché sur premières pages, dégrade en profondeur pour 3 tris) ou keyset sur le tri `rang` par défaut.**

## A4 — Cohérence des compteurs
_(à compléter)_

## A4 — Cohérence des compteurs → **cohérent, deux définitions distinctes voulues**

- **« opportunités détectées »** = `_q_v2_stats()` `app.py:1608` : `opportunites = t_brulante + t_chaude`. Tooltip `ResultsSection.tsx:170` : « brûlantes v2 + chaudes v2, hors étage 0 ».
- **120 / 1 031 / 3 587** = découpage par tier effectif (étage 0 prime, `app.py:1571`), montré dans l'entonnoir « pourquoi ? ».

**Vérifié en base (run `q_v7_defisc`, tier effectif) :** brûlante **120** + chaude **1 031** = **1 151** ✓ (= bandeau exact). réserve **3 587**, à creuser 72 980, écartée 353 945, total 431 663.

**Verdict : pas d'incohérence.** « Opportunité » = **brûlante + chaude uniquement** (shortlist de prospection). La réserve foncière (3 587) et à creuser sont **volontairement exclues** du compteur. Le « 4 738 » du mandat additionne un sous-ensemble (les 2 tiers chauds) avec un tier non-opportunité — quantité que l'app ne calcule jamais. → **E2 : garder les chiffres 120/1031/3587 en info non cliquable, ils sont cohérents.**

## A5 — Audit de couverture des filtres (run servi `q_v7_defisc`, chaque filtre seul)

| Filtre (UI) | param | prédicat (court) | source | count | verdict |
|---|---|---|---|---|---|
| Avec événement (BODACC) | `ev` | EXISTS dryrun_cascade_results evenement='rouge' | dryrun_cascade_results | **40** | **marginal** |
| Veille succession | `vs2` | EXISTS parcel_veille_succession | parcel_veille_succession | **7 092** | utile |
| Masquer les copropriétés | `hc` | `NOT copro` | parcel_p_score_v2.copro | masque **3 424** | utile |
| Pollution | `fl=sol_pollue` | cascade layer_name='sol_pollue' SOFT_FLAG | dryrun_cascade_results | **10 333** | utile |
| ABF | `fl=abf` | layer='abf' SOFT_FLAG/UNKNOWN | dryrun_cascade_results | **60 618** | utile |
| ICPE | `fl=icpe` | layer='icpe' | dryrun_cascade_results | **66 820** | utile |
| Risques (PPR/aléa) | `fl=risques` | layer='risques' | dryrun_cascade_results | **403 865** | utile mais **quasi-universel 93,6 % → discriminant faible** |
| Prescription PLU | `fl=prescription_plu` | layer='prescription_plu' | dryrun_cascade_results | **127 513** | utile |
| Procédure collective | `vs=pcl` | signal code IN (BODACC_LJ, LJ_CLOT, RJ, SAUVEGARDE, RADIATION) | parcel_v_score.signals | **314** | utile |
| Friche | `vs=friche` | code='FRICHE' | parcel_v_score.signals | **1 526** | utile |
| Propriétaire hors île | `vs=hors_ile` | code='GEO_HORS_ILE' | parcel_v_score.signals | **944** | utile |
| DPE F-G | `vs=dpe_fg` | code IN (DPE_G_MULTI, DPE_G, DPE_F) | parcel_v_score.signals | **27** | **marginal** (data mince) |
| Détention longue | `vs=tenure` | code='DVF_TENURE_OBS5' | parcel_v_score.signals | **10 814** | utile |
| **Dirigeant 65+** | `vs=dirigeant` | code IN (RNE_DIRIGEANT_75/70/65) | parcel_v_score.signals | **0** | **CASSÉ / MORT** |

**« Dirigeant 65+ » est MORT** : les 3 codes `RNE_DIRIGEANT_75/70/65` sont **totalement absents** de `parcel_v_score.signals` (le prédicat est valide, mais ne matche jamais). Codes réellement présents : `DVF_TENURE_OBS5`(10814), `GEO_AUTRE_COMMUNE`(8912), `BODACC_CESSION_FONDS`(2021), `FRICHE`(1526), `RNE_CESSATION`(1123), `GEO_HORS_ILE`(944), `NU_PM_HORS_IMMO`(861), `BODACC_RADIATION`(92), `BODACC_LJ`(91), `BODACC_LJ_CLOT`(76), `BODACC_RJ`(52), `DPE_G`(13), `DPE_F`(13), `BODACC_SAUVEGARDE`(3), `DPE_G_MULTI`(1). → **E1 : masquer « Dirigeant 65+ » (jamais supprimer le code — R1) ; il ne renverra 0 que tant que le signal n'est pas backfillé.**

**`Score Q ≥`** (`q` → `d.q_score`) : **axe Q de la matrice v2** (potentiel/qualité constructible, distinct de l'axe A). Range **1–100** entier, non-null partout, moy ≈ 48.
**`SDP ≥ m²`** (`sdp` → EXISTS `parcel_residuel.sdp_residuelle_m2`) : **surface de plancher résiduelle** (m² constructibles restants). Range 0–436 668. **Attention : seules 263 169 / 431 663 (61 %) ont une valeur** — l'`EXISTS` **exclut silencieusement les 39 % sans ligne `parcel_residuel`**. → E1 : renommer/expliciter, signaler l'exclusion silencieuse.

**Pour E1** : garder (utiles) — Veille succession, Masquer copro, Pollution, ABF, ICPE, Prescription PLU, Procédure collective, Friche, Propriétaire hors île, Détention longue, Score Q, SDP. Marginaux (data mince, garder mais reléguer) — Avec événement, DPE F-G. Faible discriminant (garder, prévenir) — Risques. **Masquer — Dirigeant 65+ (mort).**

## A6 — Contenu réel du panneau Notifications

Composant : `NotifBell` dans `frontend/src/components/header/Header.tsx:281-356`. Backend : `src/labuse/api/events.py`.

**Événements qui déclenchent une notif (exhaustif — table `event_log`, peuplée par `detect_events()` `events.py:61-136`)** — 4 `kind` :
1. **`bascule`** (`events.py:66-83`) — `matrice_statut` d'une parcelle change entre deux runs.
2. **`bodacc`** (`events.py:86-101`) — nouvel événement BODACC « rouge ».
3. **`veille`** (`events.py:150-192`) — bascule montante `▲` qui matche le hash d'une recherche sauvegardée, scopée au `compte_id` propriétaire.
4. **`permis`** (`events.py:111-134`) — permis Sitadel < 300 m d'une parcelle suivie, daté < 12 mois.
`detect_events` **diffe deux runs** → avec un seul run réel servi, la liste ne se peuple **que via le seeder démo**.
Moteur d'alertes parallèle `src/labuse/alertes.py` = **mort** vis-à-vis de cette cloche (elle lit `/events`, pas `/alertes`).

**Badge `DÉMO` + « 0 NON LUE » liste pleine → données de démonstration, pas de dur codé en front.** Origine : `seed_demo()` (`events.py:195-229`) fabrique un faux run `q_v2_demo` sur 8 parcelles, insère avec `demo=true`. Badge rendu `Header.tsx:325`. Déclenché à la demande via `POST /events/demo`. **« 0 non lue + liste pleine »** = comportement normal : `unread = count(*) WHERE NOT lu` (`events.py:247-248`), la liste montre les 100 dernières lignes quel que soit l'état lu (lignes lues à `opacity-55`). Compteur **réellement calculé**, pas figé à 0.

**Veilles (recherches sauvegardées)** : table Postgres réelle `saved_searches` (`events.py:45-48`) `id, nom, hash, created_at, compte_id` — **pas localStorage**. Stocke un **nom + hash de filtres** (`filtersToHash`, `Header.tsx:291`). API `GET/POST /events/searches`, `DELETE …/{sid}`, scopée compte. Reliée aux notifs via `_veilles_match()` : à chaque run, re-parse le hash, produit un `kind='veille'` pour chaque bascule montante matchante.

**E-mail : AUCUN envoi.** SMTP présent seulement en **config** (`config.py:127-136`), jamais importé/utilisé. Digest = **génération HTML seule** (`events.py:373-400`, « L'envoi SMTP = config à brancher »). Resend **retiré** le 2026-07-22 (`config.py:145-152`). `courrier.py` = courrier **postal**, distinct. Notifs = pull-only (poll `/events` toutes les 60 s).

**Saisie langage naturel pour créer une veille : NON.** Seule voie = « nommer les filtres courants » (`Header.tsx:344-348`). `nl_semantics.py` traduit le NL en recherche, mais **aucun chemin NL→veille**. → À noter pour B/E : le NL existe pour la recherche, réutilisable pour créer une veille (piste, hors mandat strict).

## A7 — Bouton carré inopérant → **décision G2 : GARDER (le doute ne supprime pas)**

**Ce n'est PAS un bouton cassé.** C'est le **4e outil « Zone »** du `MapToolbar` (icône cadre pointillé + point central), `MapToolbar.tsx:28-36`. Fonction prévue : dessiner un polygone qui filtre les résultats à la zone — **entièrement implémentée** (`MapView.tsx:785-787` : `setZone(pts)` au double-clic ≥3 points, polygone persistant `MapView.tsx:374-377`, chip « Zone active × »).

**Pourquoi rien ne se passe** : il est **volontairement désactivé quand aucune commune n'est choisie** (`off = t.key === 'zone' && ile`, `MapToolbar.tsx:114`), et « Toute l'île » est **l'état par défaut au chargement** (`useApp.ts:172 commune:null`). Au clic en mode île → seulement `setZoneHint(true)` (tooltip « Par commune — choisissez une commune » 2,5 s). **Dès qu'une commune est choisie, le bouton fonctionne normalement.** C'est une **désactivation par design**, pas un handler stubé.

**Doublon** : non dans l'UI (les 3 autres outils sont des mesures Distance/Surface/Altitude). Chevauchement conceptuel avec `watch_zones` (`alertes.py`, non câblé UI).

**Coût réparer vs supprimer** : supprimer = trivial mais **perd une vraie fonction qui marche**. Réparer « toujours utilisable île entière » = lourd (filtre spatial sur tuiles MVT au lieu du GeoJSON commune — raison même du gating). **Amélioration bon marché retenue en G2** : clarifier l'état désactivé (l'`aria-label` et le tooltip existent déjà) — p.ex. au clic en mode île, guider vers le sélecteur de commune, **sans retirer ni le bouton ni sa fonction**. → Défaut réversible R1/R2 respecté.

## A8 — Périmètre exact de la section « Vues » (préparatoire C-bis)

**Résumé** : Vues = moteur de ciblage commercial (presets métiers + query builder + NL) sur les données du socle. **Le `Builder` et la `BarreNL` de Vues sont EXCLUSIFS à Vues** ; mais une **brique NL jumelle et partagée existe déjà** dans l'app (le Copilote) et reste.

**Composition Vues (PART au spin-off) :**
- Front : `frontend/src/components/segments/SegmentsPage.tsx` (page + `Builder` `:193` + `BarreNL` `:578`) ; entrée rail `Rail.tsx:46,61` ; routage `App.tsx:13,256-259,268,291` (`view==='segments'`, alias `#pg=vues`) ; client `api.ts:372-459`.
- Back : router `src/labuse/api/segments.py` (`/segments`) ; `src/labuse/api/ortho.py` **routes `/validation` seulement** ; endpoint `/ia/segments-search` (`ia.py:417`) + `src/labuse/ai/nl_segments.py` ; package `src/labuse/segments/*`.
- Tables **exclusives** : `segment_presets`, `segment_preset_counts`. Config : `config/segment_presets.yaml`.

**Builder « composez sur N critères » + NL — deux surfaces distinctes :**
| Surface | Composant | Endpoint | Statut |
|---|---|---|---|
| **NL de Vues** | `Builder`/`BarreNL` (SegmentsPage) | `/ia/segments-search` | **EXCLUSIF Vues → part** |
| **NL Copilote (app)** | `IAStub` + `useApplySearch` | `/ia/search` (`nl_semantics.py`, `nl_aggregate.py`) | **PARTAGÉ → reste** |

→ Pour un **réemploi dans le panneau Filtres (piste E1)**, la cible est `useApplySearch` + `/ia/search` (déjà partagé), **PAS** le `Builder`/`nlSegmentsSearch` de Vues.

**Modèles Pergolas & terrasses / Paysagistes / Piscinistes** : définis dans `config/segment_presets.yaml` (catégorie `exterieur`). Dépendances = tables **socle partagées** (`dvf_mutations`, `parcel_terrain`, `parcel_equipements`) via `segments/registry.py`. Les presets partent (config Vues), les tables restent.

**Détection piscines (FLAIR + probe, ~8299)** : utilisée **hors Vues** :
- `parcel_equipements` (table matérialisée) → lue par la **FICHE PARCELLE** (`/ortho/equipements/{idu}` → `Fiche.tsx:590`). **PARTAGÉ — reste.**
- `ortho_detections` (validation brute) → lue par Vues ET par `scoring/p_model` (**expérimental, pas le run servi** ; le score servi `score_v_constants.py` n'a **aucun** flag piscine). → **La détection piscine ne change pas le score en ligne.** `ortho_detections` peut partir sans impact fiche/score, à trancher selon l'avenir de `p_model`.

**Signal ANC** : utilisé **hors Vues** — `ingestion/anc.py` écrit `parcel_anc` / `parcel_signals` / `spatial_layers`, lues par **FLASH** (`flash/data.py:80,364`, produit vendu). → **PARTAGÉ — reste. Décision B7 (QA-36) : GARDER l'ANC dans le bloc Précision** (preuve formelle qu'il existe hors Vues).

**Piège** : `moteurs.py` / `M22Programme.tsx` / `moteurs.tsx` **NE font PAS partie de Vues** (montés par `ModulePanel` de la fiche, `App.tsx:284`) — le mot « moteur » est du wording, pas un import. **Partagés — restent.**

**Colonne « DOIT RESTER »** : `IAStub`, `useApplySearch`, `/ia/search`, `nl_semantics.py`, `nl_aggregate.py`, `/ortho/equipements/{idu}`, `moteurs.py`/`rarete.py`, tables socle (`parcel_equipements`, `parcel_terrain`, `parcel_anc`, `parcel_signals`, `spatial_layers`, `dvf_mutations`, `parcel_p_score_v2`), `config/detection_ortho.yaml`.

---

## Synthèse LOT A — entrées pour les lots suivants

- **A3 → pas d'arrêt dur.** Lift correct (`p/taux_base`, plafond naturel ×63.97 à p=1). B ré-habille l'affichage, ne touche pas au calcul.
- **A1 → B3** : les 4 tris marchent ; B3 = libellés + marges seulement.
- **A2 → E3** : cap dur 500 (mode île), `offset` déjà supporté en SQL, front à câbler ; pagination sur tri `rang` bon marché. CSV = 5000, **E4 : inchangé**.
- **A4 → E2** : compteurs cohérents, garder 120/1031/3587 en info.
- **A5 → E1** : masquer « Dirigeant 65+ » (mort, R1 = masquer pas supprimer) ; reléguer marginaux (Avec événement 40, DPE F-G 27) ; prévenir sur Risques (93,6 %) et SDP (exclut 39 %). Renommer Score Q / SDP.
- **A6** : notifs = démo (`event_log`, `seed_demo`), aucun e-mail, veilles = `saved_searches` réel, NL→veille absent.
- **A7 → G2** : bouton « Zone » = **garder** (marche en mode commune), clarifier l'état désactivé île.
- **A8 → C-bis** : périmètre net ; NL builder Vues exclusif, brique NL app partagée reste ; ANC + piscines (via `parcel_equipements`) restent.
