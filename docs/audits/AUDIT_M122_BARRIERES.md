# AUDIT M122 — LES BARRIÈRES : QUI RETIRE DES PARCELLES, ET OÙ

**Branche** : `audit/m122-barrieres` — audit pur, aucune correction, jamais mergé.
**Méthode** : 4 sondes de code parallèles (clauses + file:line) + mesures SQL directes sur la
base servie (run `q_v9_m81`, score_v2 `q_v8_calibre`). Chaque barrière porte son `fichier:ligne`
ET son **volume mesuré**.

**La règle de Vic** : il n'y a que deux réductions légitimes — (1) le client filtre, (2) le client
demande à LABUSE d'analyser (et on le lui dit). Toute autre réduction est une barrière cachée.

---

## SYNTHÈSE — CE QU'IL FAUT RETENIR

1. **Le défaut de fond est réel et unique** : `_q_v2_stats` (le COMPTEUR) ne retire PAS l'étage 0 ;
   `_q_v2_list` (la LISTE servie) le retire par défaut (`AND NOT _ETAGE0_SQL`, `app.py:2085`). Quand
   aucun filtre `tiers` n'est passé, **compteur = 431 663, liste = 90 911**. C'est exactement ce qui
   a produit le « 431 663 → 60 » du projet (corrigé en M120-B).

2. **Le front MASQUE ce défaut sur la CARTE** (mais ne le corrige pas) : le panneau Filtre passe
   TOUJOURS un paramètre `tiers` (`tiersParam`, `api.ts:125`). Dès qu'un `tiers` est passé, `_q_v2_list`
   **abandonne** l'exclusion de base (`base = "" if "f_tiers" in xp…`, `app.py:2083`) → compteur ET
   liste comptent alors le même univers. **Sur la carte, compteur et liste sont donc cohérents** ;
   le défaut ne mord QUE là où on appelle `_q_v2_stats` sans `tiers` : le **projet** (corrigé M120-B)
   et le **Copilote/facette** (compte brut, cf. §4).

3. **Trois définitions différentes d'« écartée » coexistent** — c'est la racine de la confusion :
   - **étage 0** (`d.status IN ('exclue','faux_positif_probable')`) = **340 752**
   - **matrice_statut = 'ecartee'** = **412 579**
   - **tier v2 = 'ecartee'** = **354 355**
   Aucun écran ne dit lequel il applique. Le « toute la trame » du front (418 042) et le « sans
   filtre » (431 663) ne comptent pas le même univers : **13 621 parcelles** de différence (tier v2
   'ecartee' mais PAS étage 0), invisibles des deux côtés du front mais comptées par le SQL nu.

4. **Les plafonds sont nombreux (~20), surtout des defaults de pagination** ; un seul est en config
   (`shortlist_max`). Deux plafonds « métier » sont en dur : `chercher-plus` 60 (`projets.py:937`),
   simulateur PLU 400 (`moteurs.py:74`).

5. **Aucune perte silencieuse ACTIVE aujourd'hui** sur le run servi : le run `q_v9_m81` couvre les
   431 663 parcelles, score_v2 aussi → les jointures `INNER`/`run_label` perdent **0** parcelle
   MAINTENANT. Ce sont des barrières **latentes** (elles mordraient si une parcelle manquait au run).

**Correction de deux affirmations des sondes** : (a) « zéro réduction silencieuse » est **faux** — le
projet était muet avant M120-B, et les copropriétés (3 424) + le 3ᵉ écartée (13 621) le sont encore ;
(b) « le compteur carte diverge de sa liste » est **vrai dans le code, faux en pratique** — le front
passe toujours `tiers`, ce qui réaligne les deux sur la carte.

---

## PHASE 3 — LE RECENSEMENT DES NOMBRES SERVIS (l'univers de chacun)

Le **même** cadastre (431 663 parcelles) est compté sous **au moins 9 univers** différents :

| Nombre | Univers exact | Où c'est servi | Clause |
|---:|---|---|---|
| **431 663** | tout le cadastre / toutes les lignes du run | `total` de `_q_v2_stats` sans `tiers` ; Copilote « combien de parcelles à X » | `app.py:2244` (pas d'exclusion) |
| **418 042** | trame front « analyse coupée » (11 tiers énumérés) | compteur carte, interrupteur OFF | `api.ts:125` `tiersParam` |
| **90 911** | **figeable** = hors étage 0 | LISTE par défaut ; **vivier** projet ; `/projets/compteur` | `app.py:2085` `AND NOT _ETAGE0_SQL` |
| **77 290** | retenu par l'analyse (hors 'ecartee') | compteur carte, interrupteur ON | `api.ts:120` `TIERS_ANALYSE` |
| **51 129** | Saint-Paul, tout le cadastre | Copilote/facette « combien à Saint-Paul » | count brut, `demo.py:18` |
| **15 327** | Saint-Paul figeable | (jamais servi tel quel) | mesuré |
| **340 752** | étage 0 (exclue+faux_positif) | tier « écartée » de la carte | `app.py:725` |
| **34 098** | servables v2 (brûlante+chaude+réserve+à creuser) | « opportunités » (reperes, communes) | `verdict_servi.TIERS_SERVABLES` |
| **19 084** | matrice non-écartée (chaude+a_surveiller+a_creuser) | ancien compteur `/apercu` (avant M120) | `projets.py` (retiré) |

**Décomposition de l'étage 0 (340 752)** — mesuré M122-précédent :
faux_positif_probable = **262 531** (77 %, dominé par *déjà bâti* 181 484) · exclue = **78 221** (23 %,
dominé par risque PPR 44 764 / zonage N-A 39 885 / foncier public 36 379).

### Les endroits où DEUX nombres du même écran comptent des univers différents

1. **Projet — cadrage → shortlist** : compteur `431 663` (avant M120-B) vs shortlist `60`. **CORRIGÉ
   M120-B** : `/projets/compteur` sert désormais le vivier (90 911) et la shortlist se dit « top 200
   sur N ». *Le défaut type de tout l'audit.*
2. **Carte — « toute la trame »** : `418 042` (11 tiers) vs `431 663` (SQL nu) = **13 621** de
   différence, muette. Deux façons de dire « tout » qui ne s'accordent pas.
3. **Copilote — « 51 129 à Saint-Paul »** : compte factuel brut (tout le cadastre). Il ne sert pas de
   liste → pas de divergence à l'écran, mais **seules 15 327 sont figeables** ; le 51 129 ne dit pas
   qu'il compte 79 % de non-figeable (cf. §4, verdict).

---

## PHASE 1 — INVENTAIRE DES RÉDUCTIONS PAR SURFACE

Univers COMPTÉ (le nombre annoncé) × SERVI (ce qu'on peut parcourir) × clause × dit au client.

| Surface | Compté | Servi | Clause réductrice (fichier:ligne) | Dit ? |
|---|---|---|---|---|
| **Carte — compteur** | trame selon interrupteur (418 042 / 77 290) | idem (front passe `tiers`) | `_q_v2_stats` `app.py:2217` + `tiersParam` `api.ts:125` | **Oui** (interrupteur Analyse + ventilation tiers) |
| **Carte — liste/palette** | = compteur (avec `tiers`) | figeable ou trame ; palette IDU **coupée à 20 000** | `_q_v2_list` `app.py:2067` ; `_FILTRE_IDUS_CAP=20000` `app.py:1677` | **Oui** (toast `idus_tronque`, `MapView.tsx:475`) |
| **Carte — tri rang (défaut)** | (compteur inclut copro) | **hors 3 424 copropriétés** (rang NULL) | fast-path `AND s2.rang IS NOT NULL` `app.py:2136` | **Non** (muet sur la carte) |
| **Filtre `/filtre`** | `total` (incl. étage 0 si pas de `tiers`) | `page` hors étage 0 (si pas de `tiers`) | `app.py:1742` (compte) vs `app.py:2085` (liste) | **Partiel** (cohérent seulement avec `tiers`) |
| **Projet — cadrage** | **vivier 90 911** (hors étage 0) | shortlist top-cap | `/projets/compteur` `projets.py:379` ; `_vivier_figeable` `projets.py:260` | **Oui** (M120-B : glose + « top N sur M ») |
| **Projet — shortlist figée** | vivier | top **cap=200** (config) best-first | `_figer_shortlist` `projets.py:524` ; `shortlist_max` `config/projets.yaml` | **Oui** (« les 200 meilleures sur N ») |
| **Projet — /parcelles (kanban)** | la shortlist figée | idem (statuts) | sert `projet_parcelles` (rien de neuf) | **Oui** (statut par carte) |
| **Projet — chercher-plus** | vivier élargi | **≤ 60** ajoutés/appel | `lim = min(body.limit, 60)` `projets.py:937` (en dur) | **Partiel** (`n_search` rendu, cap tu) |
| **Copilote mission 1 (facette)** | `total` brut (incl. étage 0 comme 'ecartee') | — (compte pur, pas de liste) | `compter_parcelles` → `filtre()` → `_q_v2_stats` `outils.py`/`app.py:2217` | **Partiel** (source+millésime dits ; « figeable » non) |
| **Fiche — voisinage 100 m** | ventes/permis 36 mois, rayon 100 m | idem | `site_voisinage.py:66-75` (fenêtre+rayon, pas d'étage 0) | **Oui** (contexte) |
| **Fiche — comparables DVF** | ventes rayon 500 m / 3 ans, bâti ≥20 | **top 12** | `LIMIT 12` `marche_service.py:161` | **Oui** (n comparables) |
| **Fiche — assemblage** | contiguës SDP ≥1000 | **top 5** | `LIMIT 5` `assemblage.py:62` | **Oui** |
| **Export CSV** | run servi hors étage 0 (sauf `tiers`) | **≤ limit (1000, max 5000)** | `_q_v2_list` `app.py:1290` ; `Query(1000,le=5000)` | **Oui** (col « statut » = écartée visible) |
| **PDF premium/projet** | 1 parcelle / top d'aperçu | idem | pas de LIMIT parcellaire ; étage 0 prime au verdict | **Oui** (verdict d'en-tête) |
| **Outils — simulateur PLU** | zone AU, ≥300 m² | **top 400** | `LIMIT 400` `moteurs.py:74` (en dur) | **Oui** (N parcelles) |
| **Outils — assemblage multi** | IDU fournis | **max 30** | `body.idus[:30]` `moteurs.py:107` | **Oui** |
| **Outils — ZAN / division-or** | communes / candidats stockés | idem | agrégats, pas de LIMIT parcellaire | **Oui** |
| **Communes — totaux** | `parcelles`=brut, `evaluees`=classées v2 | idem | `_communes_data` `app.py:1355` (LEFT JOIN, pas de LIMIT) | **Oui** (page /communes) |
| **Surveillance / veille** | faits DVF/permis/BODACC > `zone.created_at` | idem | `alertes.py:137-250` (fenêtre depuis création) | **Oui** (n_alertes) |
| **Copilote — récap** | communes actives | **top 3 + île** | `LIMIT 3` `recap.py:19` | **Oui** |

---

## PHASE 2 — LES TROIS FAMILLES

### Famille 1 — les exclusions de STATUT

| Barrière | Fichier:ligne | Volume | Où s'applique / où PAS |
|---|---|---:|---|
| **étage 0** (`status IN exclue,faux_positif`) | déf. `app.py:725` ; retiré de la liste `app.py:2085` ; **PAS** du compte `app.py:2244` | **340 752** | Retiré de : liste par défaut, vivier projet, figeable. PAS retiré de : `_q_v2_stats.total`, Copilote facette (compté « écartée »). |
| **3ᵉ écartée** (tier v2 'ecartee' mais NON étage 0) | interaction `_q_v2_where` tiers `app.py:899/902` × énumération front `api.ts:120` | **13 621** | Invisible dès qu'un filtre `tiers` est passé (carte, analyse) ; compté seulement par le SQL nu (431 663). |
| **copropriétés** (rang NULL, hors classement M89) | fast-path `AND s2.rang IS NOT NULL` `app.py:2136` | **3 424** | Exclues du tri **rang** (vue carte par défaut). Réapparaissent au tri surface/commune (legacy path, LEFT JOIN). |
| **matrice vs tier v2 vs étage 0** | 3 définitions parallèles | 412 579 / 354 355 / 340 752 | Aucun écran ne nomme laquelle. |

### Famille 2 — les PLAFONDS

**En config (1)** : `shortlist_max: 200` (`config/projets.yaml`, lu `projets.py:255`, défaut nommé
`_SHORTLIST_MAX_DEFAUT` `projets.py:249`).

**En dur, « métier » (2)** :
- `chercher-plus` **60** — `projets.py:937` `min(body.limit, 60)`.
- simulateur PLU **400** — `moteurs.py:74` `LIMIT 400`.

**En dur, pagination/perf (les autres, ~15)** — defaults raisonnables, opt-in via `?limit=` :
`/filtre` 20 (max 200) `app.py:1710` · `/parcels` 100/1000 · export CSV 1000/5000 `app.py:1292` ·
geojson 60000/200000 `app.py:1772` · spatial 6000/20000 · assemblages 100/500 · score_v2 100/200
`score_v2.py:114,149` · modules permis/promesses 2000, fantôme 600 `modules.py:252,393,543` ·
comparables 12 · assemblage 5 · voisinage nearby 6/12 · récap 3 · demo 20.

**Caps « structurels »** :
- `_FILTRE_IDUS_CAP = 20 000` — `app.py:1677`. La palette exacte de la carte est **coupée** au-delà
  (idus=null). Déclenché par la vue par défaut (**90 911 > 20 000** ⇒ palette tronquée). **Dit** (toast
  `MapView.tsx:475`).
- `MIN_DISPLAY_SURFACE_M2 = 2.0` — `app.py:61`, `app.py:2090`. **850** parcelles < 2 m² retirées de la
  liste, gardées au compteur — MAIS **0 figeable** parmi elles → impact servable net **≈ 0**.
- `copilote_max_candidats: 5000` — `config.py:177` (borne l'ancien moteur RECHERCHE, retiré du chat en
  M118).

### Famille 3 — les PERTES SILENCIEUSES (jointures / filtres implicites)

| Mécanisme | Fichier:ligne | Volume ACTUEL | Nature |
|---|---|---:|---|
| **run_label INNER JOIN** (parcelle absente du run = invisible) | `app.py:2125,2152` ; `modules.py:419` ; `score_v.py:618` | **0** (run couvre 431 663/431 663) | **Latente** — mordrait à couverture partielle |
| **score_v2 INNER (fast-path)** | `app.py:2123` ; `copilote/moteurs.py:135` | **0** (score_v2 couvre 431 663) | Latente. NB : runs différents (dryrun `q_v9_m81` ≠ score_v2 `q_v8_calibre`), mais **même couverture** aujourd'hui. |
| **`s2.rang IS NOT NULL` (fast-path)** | `app.py:2136` | **3 424** (copro) | **Active** — cf. Famille 1 |
| **`surface_m2 >= 2.0`** | `app.py:2090` | 850 (0 figeable) | Active, impact net ≈ 0 |
| **`geom_2975 IS NOT NULL`** (spatial, voisinage) | `app.py:2598` ; `site_voisinage.py:74` | ~0 (géométrie quasi universelle) | Latente |
| **`pm.groupe NOT IN (1,2,3,4,9)`** (outil fantôme/nu_pm) | `modules.py:556` | tool-spécifique | Active, périmètre outil (dit) |

---

## PHASE 4 — LE VERDICT (trié par volume de parcelles concernées)

### 🟥 ILLÉGITIME — aucune trouvée
Aucune barrière ne réduit l'univers **sans raison** ou **en contredisant** la règle de Vic. Toutes ont
une justification (exclusion dure, pagination, classement). Le grief n'est jamais « pourquoi retirer »
mais « pourquoi ne pas le dire / pourquoi deux nombres divergent ».

### 🟧 LÉGITIME MAIS MUETTE (le client ne sait pas) — à dire

| # | Barrière | Volume | Où | Preuve |
|---|---|---:|---|---|
| 1 | **étage 0 compté mais non servi** (compteur ≠ liste sans `tiers`) | **340 752** | Copilote facette (compte brut) ; tout appel `_q_v2_stats` sans `tiers` | `app.py:2244` vs `2085` — **corrigé pour le projet en M120-B**, reste pour le Copilote/facette |
| 2 | **3ᵉ écartée** (tier v2 'ecartee' ≠ étage 0), le « tout » du front n'est pas tout | **13 621** | Carte (418 042 vs 431 663) | `api.ts:120` × `app.py:899/902` |
| 3 | **Copropriétés hors tri rang** (vue carte par défaut) | **3 424** | Carte, tri rang | `app.py:2136` (M89 : exclusion *délibérée*, mais non dite sur la carte) |
| 4 | **`chercher-plus` cap 60 en dur**, non annoncé | 60/appel | Projet | `projets.py:937` |

### 🟨 LÉGITIME ET DITE (le client sait) — rien à faire
- **Projet — vivier / shortlist « top 200 sur N »** (`projets.py:379`, M120-B) — le modèle du « bien
  dit ».
- **Palette carte coupée à 20 000** — toast `idus_tronque` (`MapView.tsx:475`).
- **Comparables 12 / assemblage 5 / simulateur PLU 400 / récap 3** — top-N annoncés (« N comparables »,
  « N parcelles »).
- **Export CSV** — colonne statut = « écartée » visible.
- **Interrupteur Analyse LABUSE** — la bascule 418 042 ↔ 77 290 EST le geste « demander à LABUSE » de
  la règle de Vic, avec la ventilation par tier.

### 🟦 SUSPECTE (effet non mesuré / latent) — à surveiller

| # | Barrière | Volume actuel | Risque |
|---|---|---:|---|
| 1 | **run_label / score_v2 INNER JOIN** | 0 | Une parcelle absente d'un futur run devient invisible **partout**, sans message. Les DEUX runs (`q_v9_m81`, `q_v8_calibre`) doivent rester à couverture 100 %. |
| 2 | **`< 2 m²`** | 850 (0 figeable) | Impact net nul aujourd'hui ; à re-mesurer si le seuil ou l'ingestion bouge. |
| 3 | **Copilote facette « combien à Saint-Paul » = 51 129** | 51 129 vs 15 327 figeable | Compte factuel légitime (« combien de parcelles »), mais si un jour il sert de base à une action, l'écart avec le figeable (79 %) devra être dit — comme le projet l'a fait. |
| 4 | **Trois définitions d'« écartée »** (340 752 / 354 355 / 412 579) | — | Pas une barrière en soi, mais la SOURCE de confusion : nommer l'univers partout lèverait l'ambiguïté. |

---

## LA HIÉRARCHIE (par volume)

```
340 752  étage 0 — compté partout, servi nulle part (muet hors projet corrigé M120-B)   🟧
 13 621  3ᵉ écartée (tier v2 'ecartee' ≠ étage 0) — le « tout » du front ampute            🟧
  3 424  copropriétés — hors tri rang par défaut (M89 délibéré, non dit sur la carte)      🟧
    850  < 2 m² — hors liste, 0 figeable (impact net nul)                                  🟦
      0  jointures run/score INNER — 0 perte aujourd'hui, latentes                         🟦
```

---

## CE QUI N'A PAS ÉTÉ TOUCHÉ

Audit strictement en lecture. Aucune correction, aucun renommage, aucun changement de code, de
schéma ou de test. Toutes les surfaces de la Phase 1 sont couvertes. Branche `audit/m122-barrieres`
non mergée.
