# M48 — INVESTIGATION du re-score q_v8_calibre du 07/08 00:17 (+04) — lecture seule, STOP

**Mandat** (arbitrage Vic) : établir sur pièces QUI/QUOI a re-scoré le run servi, CE QUE ça a
changé, comparer à l'état attendu, rendre un VERDICT. **Aucune écriture, aucune régén golden,
aucun build-mvt.** Verdict rendu → **STOP, Vic décide** (bénir + rafraîchir, ou rollback).

---

## 1. QUI / QUOI (sur pièces)

**C'est un `labuse score-v2` exécutant la BASCULE M39.** Signature dans `p_score_v2_runs` :

| Champ | q_v8_calibre (courant) | q_v8_calibre_pre_m39 (archive) |
|---|---|---|
| `computed_at` | **2026-08-07 00:17:13 +04** | 2026-08-05 23:20:29 +04 |
| `model_version` | m36-l2f-2026 | m36-l2f-2026 |
| **`model_sha256`** | **00a58008…4959b64** | **00a58008…4959b64** (identique) |
| `params` | seed_ties 974, brulante_seuil_d 1.4369, n_entrée 6389… | **identiques** (seul `prev_run` diffère) |
| `snapshot_label` | m5-2026-08-06 | m5-2026-08-05-2 |
| `duration_s` | 191 | 184 |

→ **Même modèle (SHA identique), mêmes paramètres.** Ce n'est PAS un changement de modèle ni de
calibration : c'est la **re-matérialisation M39** (archive `pre_m39` puis re-score de `q_v8_calibre`).

**Déclencheur — écarté un par un :**
- **Pas moi** : M47 (11:51–12:40 +02) et M48 (13:05+ +02) sont le **lendemain matin** ; le re-score
  est le **soir du 6/08** (00:17 +04 = **22:17 +02**). M47 était en rollback, M48 lecture seule (sauf F1/F4).
- **Pas hermes** (`ai.hermes.gateway-anton`) : ses logs s'arrêtent le **05/08 23:08** — agent inactif le 6–7/08.
- **Pas cron / launchd** : `watch-prod` (600 s) ne fait que des health-checks (aucune écriture DB) ;
  `pull-backups` tire des sauvegardes ; aucun job de scoring planifié.
- **Pas dans `~/.zsh_history`** (mtime 06/08 23:20) : aucune commande `score-v2` — donc lancé via un
  **harnais d'outil** (session agent antérieure) ou dans le **checkout frère** pendant la fenêtre M39.
- **Le golden a été régénéré 7 min APRÈS** (`genere_le` 06/08 22:24:57 +02 = **07/08 00:24:57 +04**) :
  l'opérateur du re-score a **bien régénéré le golden** (il porte les tiers post-M39, cf. §3).

## 2. CE QUE le re-score a changé (diff courant vs `pre_m39`)

| Mesure | Valeur |
|---|---|
| lignes **identiques** | **431 659 / 431 663** |
| **p_raw** modifiés | **0** |
| **rang** modifiés | **0** |
| **tier** modifiés | **4** |

Les 4 : `97415000CX0650`, `97415000BV0606`, `97408000AC2215`, `97401000AR1289` — tous
**vers `a_creuser`** (3 depuis chaude, 1 depuis brûlante), sans `event_date`.

**Agrégat = signature M39 EXACTE** (conforme mémoire `m39-piscine-signal` / M46 « 118/1038/29978 ») :

| tier | pre_m39 | courant | Δ |
|---|---|---|---|
| brûlante | 119 | **118** | −1 |
| chaude | 1041 | **1038** | −3 |
| à creuser | 29 974 | **29 978** | +4 |

## 3. État attendu (référence)

- **`q_v8_calibre_pre_m39`** (archive) = l'AVANT (119/1041).
- **golden 07/08 00:24 +04** = l'APRÈS : sa méta porte déjà `brulante 118, chaude 1038,
  a_creuser 29978` → **le golden reflète la bascule M39**. La base servie == golden sur les tiers.

## 4. VERDICT

**Catégorie (a) — geste LÉGITIME et identifiable : la bascule M39.**
- Modèle + params + SHA **inchangés** ; effet = les 4 déclassements documentés (119→118, 1041→1038),
  `p_raw`/`rang` bit-identiques. **Ni writer inconnu (c), ni corruption de modèle.**
- **Mise à jour d'état** : la mémoire disait « M39 NON basculée (gated) » — **c'est PÉRIMÉ** : M39 a
  été **basculée le 6/08 au soir**. Le gate a été levé et le geste exécuté (par une session antérieure).
- Le golden **a** été régénéré dans la foulée (00:24) → le golden est **à jour** des tiers M39.

**LE DÉFAUT RÉEL = un trou de PROCESS, pas une corruption** :
> La bascule M39 a régénéré le golden **MAIS n'a PAS rejoué `build-mvt`.**
> `mvt_parcels` (bâti **05/08 23:29**) reste **avant** le re-score (**07/08 00:17**) → les **tuiles carte
> sont périmées** des 4 déclassements M39 (+ dérive SDP). **C'est exactement F2/F3**, et exactement la
> doctrine M47 (« toute table run-scopée entre dans le geste ») qui a été enfreinte pour les tuiles.

**Anomalie SÉPARÉE et mineure (à ne pas confondre)** : le golden est à **114/117**, 3 FAIL
`api.fiche.n_lignes_cascade` (`97405000AB0168`, `97421000AC0156`, `97423000AB1341`, ex. 37→36).
La table `dryrun_cascade_results` est **inchangée depuis le 29–30/07** → ce n'est PAS un re-run
cascade : c'est une micro-différence de **dédup des lignes en fiche** postérieure au golden. Petit,
sur 3 parcelles hors témoins ; à regarder, mais sans rapport avec la bascule M39.

---

## RECOMMANDATION (à ton arbitrage — rien n'est fait)

1. **Bénir le re-score** : il est légitime (bascule M39, déjà la vérité servie ; golden déjà aligné).
   **Pas de rollback** — l'état servi 118/1038/29978 est le bon.
2. **Rejeu `build-mvt`** (ton geste) : `labuse build-mvt` — rafraîchit les tuiles → **solde F2/F3**
   (et, doctrine M47, embarque désormais `parcel_flags` + `parcel_renouvellement`).
3. **Poser la garde de péremption des tuiles** (F2/F3, mon geste) : `mvt bâti < dernier
   `p_score_v2`/`parcel_residuel` → alerte bruyante` — pour que « bascule sans build-mvt » **crie**
   la prochaine fois (c'est précisément ce qui a manqué ici).
4. **Regarder** les 3 dérives `n_lignes_cascade` (anomalie séparée) — je peux investiguer sur demande.
5. **F4** reste **staged** (`F4_staged.patch`), à appliquer avec la régén golden **post-décision**.

**STOP.** Tu décides : bénir + rafraîchir (reco), ou rollback à `pre_m39`.
