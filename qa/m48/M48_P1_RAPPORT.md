# M48 — PHASE 1 · RAPPORT d'audit de cohérence (lecture seule) — STOP arbitrage

**Branche** `m48-coherence-globale`, base `origin/main` `e91b46ea`. Run servi `q_v8_calibre`.
Grille outillée sur **26 parcelles × 8 surfaces** (`audit_grid.py`) + vérifications sur pièces.
**Zéro écriture.** Tout ce qui suit est **constaté**, jamais présumé.

---

## Verdict d'ensemble

**Le produit est très majoritairement cohérent** — et surtout, **les prix ne se contredisent
jamais** (la question n°1 de Vic) : CA et charge foncière sont **identiques** entre le module
faisabilité et la fiche (compute_bilan partagé), 20/20 parcelles. Tier / rang / mult / mode B /
vigilances sont cohérents entre fiche V2, fiche legacy, exports et DB (le point de traduction
unique `verdict_servi`/`tier_v2` tient).

**MAIS trois contradictions réelles**, dont **une grave et client-facing** : **l'assistant IA
annonce un classement contraire à la fiche**. Détail ci-dessous. Grille complète :
`grille.csv.gz` · divergences : `divergences.csv.gz` · synthèse : `findings.csv`.

| # | Gravité | Surface fautive | Grandeur | Parcelles | Preuve |
|---|---|---|---|---|---|
| **F1** | **G1** | **Assistant IA** | tier/verdict | jusqu'à **71 115** | `preuves_ia/` |
| **F2** | **G1** | Carte (tuiles) | tier | **4** | grille |
| **F3** | **G1** | Carte (tuiles) | SDP résiduelle | **7 854** | grille |
| F4 | G3 latent | payload fiche V2 + tuiles | `statut` mort | 71 115 | `pieges_latents.csv.gz` |
| P1 | ✅ | — | CA + charge foncière | 20/20 OK | grille |
| P2 | ✅ | — | tier/rang/mult/mode-B/vigilances | 26/26 OK | grille |
| P3 | ✅ cohérent | — | piscine EP0228 | — | qa/m39 |

---

## F1 — GRAVE · L'assistant IA contredit la fiche sur le classement

**Constat empirique (endpoint live `POST /parcels/{idu}/ask`)** :

| Parcelle | Fiche (vérité servie) | Réponse de l'IA |
|---|---|---|
| `97418000AT2542` | **Brûlante**, rang 14, ×22,1 | *« Non, cette parcelle n'est **pas classée prioritaire**… Son statut est **« écartée »**… elle a été exclue »* |
| `97408000AP1610` | **Chaude**, rang 3 | *« n'est **pas classée prioritaire**… statut **« à creuser »** »* |

L'IA dit à un client qu'une parcelle **brûlante** (top ×22) est **écartée, non prioritaire**.
C'est le « LABUSE dit deux choses » exact, dans le pire sens.

**Cause racine (sur pièces)** — `src/labuse/api/fiche_ask.py:130` :
```python
"statut_tier": _F(f.get("statut")),   # f["statut"] = matrice_statut v1, ÉTEINTE M37
```
Le contexte autorisé de l'IA reçoit le champ **mort** `statut` (matrice v1) comme s'il était le
tier — et **le vrai tier (`score_v2.tier`) N'EST PAS dans le contexte du tout**. L'IA n'a donc
qu'une seule notion de « classement » : la fausse. Concerne les **71 115 parcelles** où
`matrice_statut ≠ tier` (16,5 % du parc).

**Point de vérité** : `parcel_p_score_v2.tier` (via `verdict_servi`). **Sens de la correction
proposée (P2, après arbitrage)** : remplacer `f.get("statut")` par le **verdict servi**
(`verdict_servi(db, idu)` → label + tier) dans le catalogue de facts, et retirer le champ mort.
La fiche ne bouge pas — c'est l'IA qu'on raccorde au point de vérité.

## F2 / F3 — Carte : tuiles matérialisées périmées vs tables live

`mvt_parcels` (tuiles carte) est un **instantané matérialisé** bâti **2026-08-05 23:29**
(`mvt_meta.updated_at`). Depuis :
- `parcel_p_score_v2` (q_v8_calibre) **re-scoré 2026-08-07 00:17** → **4 parcelles** ont un
  **tier de tuile ≠ tier servi** (ex. `97415000CX0650` : tuile **chaude**, fiche+DB **à creuser**,
  même rang 688). Les 4 concernent des **tiers servables** (client-visible).
- `parcel_residuel` **recalculé 2026-08-05 23:34** (5 min après le build tuile) → **7 854
  parcelles** ont une **SDP de tuile ≠ SDP live** (ex. `97416000EY1406` : tuile 111 m², fiche+DB 0).

**Cause racine** : aucune **garde de péremption** sur `mvt_parcels`, et `build-mvt` non rejoué
après le re-score. **C'est la classe de risque M47** appliquée à la table des tuiles.
**Sens de la correction (P2)** : rejouer `build-mvt` (raccorde la carte au run servi) **+** une
garde « mvt bâti < dernier calcul p_score_v2/parcel_residuel → alerte » (comme la garde M47).

## F4 — Piège latent : le champ mort `statut`/`status` encore exposé

Le champ `statut` (matrice v1, éteinte M37) est **exposé au top-level de la fiche V2** et **baké
dans `mvt_parcels.status`** ; il **diffère du tier effectif pour 71 115 parcelles**. Le **front
est protégé** (`verdictMeta` préfère `tier_v2`), donc **pas de contradiction à l'écran web
aujourd'hui** — mais c'est la munition qui a explosé en F1 (l'IA le lit). **Sens (P2)** : retirer
`statut` du payload fiche V2 et de `mvt_parcels`, ou le renommer explicitement
`matrice_statut_MORTE` pour qu'aucun consommateur ne le prenne pour le tier.

## P1 / P2 — Ce qui est SAIN (constaté, à ne pas casser)

- **Prix jamais contradictoires** : `bilan.ca.central` et `bilan.charge_fonciere.central`
  **identiques** module faisabilité == fiche legacy sur 20/20 parcelles (ex. AL1154 : CA 3,4 M€,
  charge 100 k€ des deux côtés ; one-pager idem). `compute_bilan` est bien le point unique.
- **Verdict unifié** : tier/rang/mult identiques fiche V2 / fiche legacy / DB — `verdict_servi`
  (M34, dette #14) traduit le **même** `parcel_p_score_v2.tier` partout. La crainte d'un « verdict
  split V2 vs legacy » (hypothèse de cadrage) est **infirmée sur pièces**.
- **Vigilances cohérentes** : la cascade complète (`fiche.lines`) == `mvt_parcels.flags` ==
  `parcel_flags` == cascade live (ex. AT2542 : `bruit_route, declassement, ocs_ge, residuel_socle,
  risques` des trois côtés). *(Note méthodo : comparer le champ partiel `fiche.flags` produirait
  16 faux G3 — évité.)*
- **mode B** : disponibilité identique fiche V2 / legacy / endpoint.

## P1.2 — Le cas EP0228 (dossier M40) — tranché

`97411000EP0228` : piscine détectée sur ortho (probe 0,940 ; en bande **[15;60]** ; géométrie
**CONTENUE** ; centrale), **elle QUALIFIERAIT** la règle M39. **Pas de vigilance** parce que la
règle M39 [15;60] **n'est pas basculée** : **aucune couche/table piscine n'est servie** (0 dans
`dryrun_cascade_results`, tables `parcel_piscine`/`piscine_signaux` absentes). Donc **ni hors
bande, ni contenance échouée, ni trou FLAIR** : le signal existe mais est **délibérément gated
off**. **Verdict cohérence : NON-issue** — aucune surface ne prétend le contraire, rien ne se
contredit. À garder tel quel tant que M39 n'est pas basculé (servir un demi-signal serait pire).

## P1.3 — Le libellé « 0 retenue » du segment Renouvellement — mention proposée

Le filtre Renouvellement affiche (constaté M47) « **0** retenues par l'analyse · **67 258** avant
analyse » — exact mais déroutant (le segment EST des écartées/occupées, 0 passe l'analyse).
**Mention proposée** (à poser en P2 si arbitrée), sous le compteur du tiroir « Ça va muter ? » :

> *« Segment consultable via la voie manuelle — coupez l'Analyse LABUSE pour l'explorer (ces
> parcelles occupées sont écartées du classement principal par conception). »*

Texte seul, aucun calcul touché.

## P1.4 — Backlog vs réel (affirmations factuelles encore FAUSSES — ne pas corriger ici)

Vérifié sur DB. **Encore faux dans `docs/BACKLOG.md`** (lignes à re-confirmer au fix) :

| Ligne | Affirmation | Réel |
|---|---|---|
| ~L100 | `score_e` « défaut `run='q_v7_defisc'` en dur, bâtit sur l'ancien run » | **FAUX** — corrigé M44 (`run=Q_A_RUN_LABEL`) |
| ~L100 | `pc_caducs` « bâtit le signal sur l'ancien run q_v7 » | **FAUX** — pc_caducs ne dépend d'aucun run (M44) |
| ~L81/L126 | `parcel_renouvellement` « morte q_v7 depuis bascule v8 » | **STALE** — rebâtie q_v8 (M47), 67 258 |
| ~L126 | Renouvellement « **68 445** parcelles » | **FAUX** — 67 258 |
| ~L126 | `entonnoir_motifs` « mort depuis q_v2/q_v6 » | **STALE** — 317 lignes sur q_v8 |

*(Tout le reste de checkable dans le backlog vérifie VRAI : 118/1038/29978/2964, 431 663,
33 958 = 29 907+4 051, served_run = q_v8_calibre, etc.)*

---

## PROPOSITION DE CORRECTIONS (P2 — j'attends ton arbitrage, une par une)

Chaque correction **raccorde la surface fautive au point de calcul unique** (jamais l'inverse) :

1. **F1 (IA)** — `fiche_ask.py` : `statut_tier` = **verdict servi** (`verdict_servi`), pas le
   champ mort. **La plus urgente** (client-facing, avant toute démo). Golden inchangé (l'IA n'a
   pas d'ancre golden). *Recommandé en premier.*
2. **F4 (champ mort)** — retirer `statut` du payload fiche V2 + `mvt_parcels.status` (ou renommer
   `matrice_statut_MORTE`). Ferme la munition de F1 durablement.
3. **F2/F3 (tuiles)** — rejouer `build-mvt` **+** garde de péremption `mvt_parcels`. (Geste servi
   → à faire quand tu veux, c'est ta main.)
4. **Backlog** — corriger les 5 affirmations fausses (P1.4).
5. **Renouvellement** — poser la mention P1.3 (si arbitrée).

**STOP.** Tu arbitres : quelles divergences corriger, dans quel sens, lesquelles sont des faux
positifs. Rien n'est appliqué avant. Pas de merge.

## Annexes (.csv.gz — la grille est un actif, elle resservira à chaque release)
- `echantillon.csv[.gz]` · `grille.csv.gz` · `divergences.csv.gz` · `pieges_latents.csv.gz`
- `findings.csv` (synthèse) · `preuves_ia/ia_*.json` (réponses IA contradictoires)
- Scripts : `select_sample.py` · `audit_grid.py` (rejouables : `LABUSE_DEV_MODE=1 labuse api` puis le script)
