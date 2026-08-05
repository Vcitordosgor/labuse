# M34 — BILAN (dette #14 : le verdict de fiche est une traduction du tier servi)

**Branche `m34-dette14-verdict-fiche`** · base `main` post-M32 · option **(a) dérivation totale**
(arbitrage Vic post-P0). Constat initial : `qa/m34/M34_P0_CONSTAT.md` (STOP Phase 0.4 justifié —
le moteur divergent était le rail cascade legacy, pas `score_e`).

## Ce qui a changé

**Un point de traduction unique : `src/labuse/verdict_servi.py`.** Lit le tier servi
(`parcel_p_score_v2`, `Q_A_RUN_LABEL`), le filtre bâti M28 (badge « bâtie + division possible »,
étage 3 divisible, ratio affiché) et le registre `served_run_exceptions` (motif prioritaire).
Aucun re-calcul. Hors run → « Non évaluée au run servi », jamais un repli legacy muet.
`sql_exists_servable()` = le fragment unique des SÉLECTIONS (« actionnable » = tier actif).

**Surfaces branchées** (aucune ne traduit de son côté) :
`_build_fiche` + `resume.py` (synthèse par tier) · `/parcels/{idu}` sans source · exports
md/html/**one-pager comité** (`export.py`, libellés `TIER_LABELS`, badge division, motif, classes
CSS par tier, rang) · comparateur (`_compare_row` via fiche) · assistant IA (`assistant.py`,
facts + synthèse déterministe) · shortlist (sélection SQL par tier + `verdict_base` par tier —
même hiérarchie 120/50 : brûlante/chaude=120, réserve/à-creuser=50) · Kanban `_entry_dict` ·
`/parcels` liste fallback · `/stats` fallback (opportunité = brûlantes+chaudes, convention front) ·
`voisinage.py` (voisines = tier + rang) · `enrichment.warm_commune`.

**Écarts à la cartographie P0** (découverts en P1 — consommateurs du même rail, AUCUN nouveau
writer, design inchangé) : `/parcels` liste fallback, `/stats` fallback, Kanban, `voisinage`,
`enrichment`. Écarté : `scoreur.py` (verdict de PRIX opportunite/dans_le_marche/cher — autre
concept, inchangé).

Le rail cascade legacy vit toujours (signaux non-francs = VIGILANCES de fiche, scores affichés à
titre informatif) — il ne pilote plus AUCUN verdict.

## Vérifications

- **Re-mesure bout-en-bout (les deux sens)** — `qa/m34/mesure_p2.py`, 1 071 parcelles (brûlantes
  EXHAUSTIVES, strates tous tiers, ancres, échantillon P0, registre) via le vrai `_build_fiche` :
  **0 déclassement silencieux · 0 divergence montante · 0 vocabulaire legacy · 0 incohérence
  verdict≠tier**. CY0197 : Brûlante rang 163 + badge « bâtie + division possible (~29 %) ».
  AT2542/AT2317 : Brûlante, propres.
- **Suite pytest : 1 322 verts.** Verrous de wording mis à jour vers la nouvelle vérité
  (`test_resume`, `test_micro_opportunite`, `test_assistant`, `test_shortlist`, `test_voisinage`,
  `test_api` + nouveau verrou « la fiche traduit le tier ; hors run = non évaluée »). 7 tests
  dédiés `test_verdict_servi.py`. **5 échecs PRÉ-EXISTANTS hors périmètre** (reproduits SANS les
  modifs M34, au stash) : `test_residuel` ×4 (AttributeError) + `test_au_ouverture` ×1 — dérive de
  l'ENV DE TEST, pas du code servi. Réparation d'env faite au passage : les 4 colonnes millésime
  M32 manquaient sur `labuse_test` (ALTER idempotent, même DDL que la prod, cf. commit).
- **Golden : 115/117 — les 2 FAIL ne sont PAS un effet M34** (détail § suivant). Les 115 autres
  PASS, **0 incohérence base↔API**, tous les champs tier/verdict des 117 conformes. Aucun tier n'a
  bougé (aucune écriture sur `q_v8_calibre`, le cache scoring ou `served_run.txt` — vérifiable au
  diff : M34 ne touche que fiche/exports/sélections + tests).
- **Screenshots (7)** : `qa/m34/screens/` — 1 AT2542 (brûlante, ancre golden) · 2 CY0197 (brûlante
  + badge division) · 3 AL1154 (à creuser ex-« Opportunité vérifiée », motif registre piscine
  affiché) · 4 CX0639 (chaude bâtie marginale divisible) · 5 AI1821 (réserve foncière) ·
  6 BW0326 (Déclassée — bâti révélé, verdict de déclassement intact + résiduel « bâtie à 112 % »
  = l'affichage M32) · 7 AP1610 (nue classique, non-régression). Support = one-pager comité (LA
  surface client modifiée).

## ⚠ Les 2 FAIL golden — constat d'environnement, arbitrage Vic requis

`97411000AO0748` et `97423000AB1908` divergent de la référence M32 sur les CHAMPS
`db.residuel.*` UNIQUEMENT (AB1908 : attendu taux 0 %/SDP 122 → obtenu taux 118 %/SDP 0).

Constat tracé : **8 031 lignes du cache fiche `parcel_residuel`** (= exactement le stock bâti
révélé M32) ont été recalculées le 05/08 **23:33–23:37 (+04)** avec le code post-M32
(`emprise = max(BD TOPO, CoSIA)`). Cette fenêtre est **antérieure à tout processus M34
susceptible d'écrire** (uvicorn de vérification démarré 00:49+04, mesure P2 00:38+04 — session
sans commit —, golden 00:52+04 ; les suites pytest tournent sur `labuse_test`). Un agent
persistant externe tourne sur la machine (`hermes … --profile anton`, PID 663, depuis mars) —
attribution exacte à établir par Vic.

Les nouvelles valeurs sont celles que M32 déclare CORRECTES (« ne s'affichent plus terrain nu ») ;
la référence golden M32 avait capturé, pour ces 2 ancres, l'état d'AVANT rafraîchissement du
cache. **Aucun champ tier n'est touché** (cache résiduel isolé du scoring, cf. M32).

Conformément au mandat (« tout écart golden = rapport ») : **rien n'a été rollbacké ni
régénéré.** Options pour Vic : (i) acter le rafraîchissement et régénérer la référence au
prochain geste gardé (`qa/golden_regen.py`) ; (ii) rollback des 2 lignes de cache — déconseillé :
réintroduit le « terrain nu » mensonger sur AB1908, contraire à M32.

## Décisions tracées

- **Option (c) — extinction du rail legacy : REPORTÉE post-Train 8** (décision Vic, ce mandat).
  Dette planifiée : basculer `_build_fiche` et ses payloads sur `_q_v2_fiche`, retirer
  `parcel_evaluations.status` de tout payload.
- **`matrice_statut` (« historique ») — surfaces client où il apparaît encore** (M34 n'y touche
  pas, Vic tranche à la revue) :
  1. Fiche web : chip « Statut matrice (historique) », tiroir Confiance (`Fiche.tsx:1457`),
     tooltip « remplacé par le scoring ». **Reco : sortie** (le tier + ICD suffisent ; garder
     l'info en API le temps de (c)).
  2. `TierBadge` (outils) : mention secondaire « (matrice : X) » avec tooltip de
     désambiguïsation. **Reco : sortie** (même argument ; le badge tier suffit).
  3. **Sélecteur `/communes` : les compteurs « chaudes »/« dossiers » sont calculés sur
     `matrice_statut='chaude'`** (app.py:1023-1026) — des CHIFFRES client sourcés sur le rail
     historique. **Reco : bascule sur les tiers servis (brûlante+chaude) à un prochain geste**
     — c'est la même incohérence que la dette #14, côté compteurs.
  4. Payload fiche v2 `statut` + filtre `statuts` (deprecated) + `/stats?legacy=1` :
     **Reco : maintien** jusqu'à (c), déjà étiquetés deprecated/historique.
  5. `score_v.py:595` (flag v1.3 chaude∧V, interne, plus exposé) : **Reco : maintien** (mort à
     l'affichage, retiré avec (c)).
- **`shortlist` verdict_base** : mapping à deux niveaux conservé (120/50) — aucune hiérarchie
  nouvelle inventée ; recalibrable dans `config/shortlist.yaml`.

## Gardes

Aucune écriture `q_v8_calibre` / cache scoring / `served_run.txt`. Aucun merge. Commits
atomiques `[M34-P0/P1/P2]` pushés sur `m34-dette14-verdict-fiche`.
