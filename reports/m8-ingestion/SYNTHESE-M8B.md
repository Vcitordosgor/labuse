# M8b — Re-run ÎLE COMPLÈTE candidat `q_v6_m8` (prépare la bascule, NON servi)

**Date** : 2026-07-15 · **Branche** : `feat/m8-ingestion` (fix ER = `a14b1cc`) · Modèle P M3.6 GELÉ · Seed 974.
**Servi INCHANGÉ** : cascade `q_v5_m6b`, p_score `m36-l2f-2026-2026-07-14`, `Q_A_RUN_LABEL="q_v5_m6b"`, tuiles/front intacts.
**Candidat** : cascade `dryrun_parcel_evaluations[q_v6_m8]` + p_score `parcel_p_score_v2[q_v6_m8]` — **NON servi**. Aucune bascule, aucun merge.

---

## Lot 0-1 — Cascade île COMPLÈTE (pas un seed)

Seed hybride M8a **supprimé** (cascade + cascade_results + p_score + run metadata). Re-run **des 24 communes** en boucle
`dryrun-evaluate` (parallèle 6, chunk 3000) → cascade neuve `q_v6_m8`. Le fix ER (config `a14b1cc`) s'applique partout.

- **431 663 parcelles, 24/24 communes**, aucune ne reste sur l'étage 0 q_v2. Étage 0 `q_v6_m8` = **353 945** (= q_v5_m6b 353 942 + 3 net St-Louis).
- **St-Louis** : ses 6 ER codés `02` captés (motif « emplacement réservé », rescue).
- **Saint-Benoît corridors (20) + Sainte-Marie PAPA (23 lignes cascade)** : motif honnête (« Corridor écologique protégé… L.151-23 » / « Périmètre d'attente… L.151-41 ») ; **0** ne dit plus « emplacement réservé ».
- ✅ Le re-run complet **reproduit exactement** les tiers du seed M8a (écartée 353 945…) — la confinement à 3 communes est *prouvé*, pas supposé.

## Lot 2 — score-v2 île lisant l'étage 0 candidat
`LABUSE_ETAGE0_RUN=q_v6_m8` (override non destructif, défaut = Q_A_RUN_LABEL). p_score `q_v6_m8` sur 431 663 (136 s) :
`ecartee 353 945 · a_creuser 72 980 · reserve 3 587 · chaude 1 031 · brulante 120` (N_e=2 676, seuil D brûlante=1,544).
**Run servi restauré immédiatement** : `m36-l2f-2026-2026-07-14` redevient le dernier `computed_at` ; candidat inspectable mais **NON servi**.

---

## (4) DELTA ventilé par cause — candidat vs servi (m36-07-14)

Matrice de transition (11 865 changements) entièrement attribuée (C1 ⊂ C3 ; total unique = C2+C3+C4 = 11 865) :

| Cause | n | Transitions | Attribution |
|---|--:|---|---|
| **Atterrissage ANO-1** (q_v6 exclut / q_v2 non) | **11 718** | a_creuser→ec 10 671 · reserve→ec 961 · **chaude→ec 84 · brûlante→ec 2** | 11 715 accumulé datagap+M6 (foncier_public 74, A/N 10, emprise routière… cf. constat) + **3 St-Louis rescue** |
| **Restauration ANO-1** (q_v2 exclut / q_v6 non) | **58** | ec→a_creuser 57 · ec→reserve 1 | ✅ canary `97406000AL0563` : ec→a_creuser |
| **St-Louis rescue net** (⊂ atterrissage) | **3** | reserve→ec 3 | les 3 parcelles où l'ER `02` est la SEULE contrainte (55/58 déjà écartées par d'autres couches) |
| **Corridors 7 + PAPA 9** | **0 changement de tier** | — | restent écartées (étage 0 inchangé q_v2=q_v6) ; **seul le MOTIF change** (honnête, vérifié) |
| **Churn recalibration** | **89** | a_creuser→chaude 80 · a_creuser→brûlante 6 · brûlante→chaude 3 | recalage N_e/brûlante (les slots des 86 fantômes partis) ; étage 0 INCHANGÉ |
| **Total** | **11 865** | | **garde-fou = 13,21 %** (franchi, atterrissage volontaire) |

## (2) Mouvement inexpliqué → **ZÉRO**
Contrôle dur : **0** transition du churn C4 implique « écartée » avec un étage 0 identique entre q_v2 et q_v6 (une telle
transition serait inexplicable). Les 89 sont **tous** des mouvements non-écartée↔non-écartée (recalibration pure).
**11 865 = C2(58) + C3(11 718) + C4(89), aucune parcelle hors des causes.**

## (4) Preuve run servi INTACT (3 fantômes, live API port 8010)
| idu | SERVI `/v2/score` (live) | CANDIDAT `q_v6_m8` |
|---|---|---|
| 97421000AV0615 (Salazie) | **brûlante** (run m36-07-14) | ecartee |
| 97416000CR1039 (St-Pierre) | **chaude** | ecartee |
| 97411000AC0157 (St-Denis) | **chaude** | ecartee |

L'app sert **toujours** brûlante/chaude (servi inchangé) ; le candidat les a en écartées. **Bascule = décision Vic, session séparée.**

---

## (3) Golden — témoins qui changent + cause

**Modernisation** : `qa/golden_check.py` — `RUN_LABEL='q_v3_datagap'` en dur (run mort) → **env `LABUSE_GOLDEN_RUN_LABEL`,
défaut = `Q_A_RUN_LABEL`** (source unique). Committé.

**Au niveau TIER (le champ que M8b modifie) : 29/32 témoins STABLES, 3 changent — TOUS = atterrissage ANO-1, zéro sans cause :**

| Témoin | Commune | ancien → nouveau | Cause (à valider Vic) |
|---|---|---|---|
| 97411000AO0748 | Saint-Denis | a_creuser → ecartee | ANO-1 landing (étage 0 q2=opportunite → q6=exclue) |
| 97413000CD0729 | Saint-Leu | **brûlante** → ecartee | ANO-1 landing (fantôme ; q2=a_creuser → q6=exclue) |
| 97416000CR1351 | Saint-Pierre | reserve_fonciere → ecartee | ANO-1 landing (q2=a_creuser → q6=exclue) |

**⚠️ Golden NON re-basé cette session — volontairement, et voici pourquoi :**
- La **référence `golden-parcelles.json` est de l'ère `q_v3_datagap`** (périmée) : la comparer au candidat surface **toute
  l'évolution cascade q_v3→q_v6** (M6 : emprise_routiere, zonage, +1 ligne cascade…) — **pas ma modif M8b**.
- Le **candidat n'est pas matérialisé** (pas de `matrice-apply`/`build-mvt`, car ils toucheraient les tuiles servies) →
  `matrice_statut`/`q_score`/`a_score` = `None` pour q_v6_m8 → fails structurels non liés au fond.
- Re-baser 3 tiers dans une référence par ailleurs stale la laisserait rouge : **inutile et trompeur**.
- **Recommandation** : régénérer le golden (`--dump`) **au moment de la bascule**, quand le candidat sera servi ET
  matérialisé (matrice + mvt). Les 3 changements ci-dessus sont documentés pour ta validation ; **je ne touche pas le JSON**.

## Cohérence — **3/3 PASS** ✅
`Q_A_RUN_LABEL`, front `SOURCE`, `mvt_meta.run_label` = toujours `q_v5_m6b` (rien touché, pas de `build-mvt` candidat).

## Grep final — `q_v2|q_v3_datagap|q_v4_m6a` hors config/tests
**0 défaut mutant exécutable** (aucun `= "q_v…"` / `Option("q_v…")` / `run_label="q_v…"`). 57 résiduels **sûrs** :
24 noms de fonctions `_q_v2_*` (défauts déjà `Q_A_RUN_LABEL`), 9 label démo `q_v2_demo`/`detect-events`, 3 historique de
lignée, + commentaires (fix M8a/M8b, dont les nouveaux de `golden_check.py`).

---

## 🛑 STOP — état laissé & décisions Vic
- **Servi INTACT** : cascade q_v5_m6b, p_score m36-l2f-07-14 (dernier), Q_A_RUN_LABEL, tuiles, front — inchangés.
- **Candidat q_v6_m8 conservé** (cascade + p_score, 431 663) — reproductible, NON servi.
- **Delta = 11 865, 100 % attribué, 0 inexpliqué.** L'atterrissage (11 718) est volontaire et va tout vers ÉCARTER.
- **À toi** : (1) acter la bascule (session séparée : q_v6_m8 → servi + matrice-apply + build-mvt + Q_A_RUN_LABEL) ;
  (2) régénérer le golden à ce moment ; (3) valider les 3 témoins ci-dessus. **Pas de bascule ni merge ici.**
