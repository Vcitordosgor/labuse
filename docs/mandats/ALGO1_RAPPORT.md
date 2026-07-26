# ALGO-1 — Nettoyage du scoring · Rapport final

**Branche** : `fix/algo-nettoyage` (base main 7976d54, poussée, NON mergée — je ne merge jamais).
1 commit par item. **Référence** : docs/SCORING_SPEC.md §7.
**Interdits respectés et prouvés** : modèle P, tiers, effectifs servis INTOUCHÉS —
`120 / 1 031 / 3 587 / 72 980 / 353 945` au bit près (requête directe + gel golden
`tiers_effectifs` PASS). **Golden 116/116**. Suite 1 141 passed / 1 failed
(`test_auth::test_local_par_defaut_tout_ouvert` = flaky d'ordre PRÉEXISTANT, passe seul,
échoue en suite complète sur main aussi — prouvé au mandat M-RENOUV).

---

## §1 · RR PAR COMMUNE (mesure, priorité) — `reports/algo1-rr-commune.md` (+ CSV)

Protocole GELÉ reproduit : label L2-F fold 2025, scores out-of-sample du walk-forward
(`scores-2025-fold-final.csv`), hors copro, ties seedés 974, harnais `p_model.evaluate`
réutilisé tel quel. **Contrôle : RR@1158 île = 6,73 exactement** (= chiffre gelé) —
la mesure est comparable.

Ce que la moyenne île cachait :

| Lecture | Constat |
|---|---|
| **Tête** | Sainte-Suzanne **19,5** · L'Étang-Salé **17,9** · Le Port **16,1** · Saint-Benoît **14,0** — le classement discrimine TRÈS fort sur ces marchés |
| **Queue (robuste)** | Le Tampon **3,1** · Saint-Denis **3,8** · Saint-Paul **4,6** — les 3 plus gros parcs sont sous la moyenne île |
| **Zéros (fragiles)** | Bras-Panon, Trois-Bassins, Cilaos : RR intra = 0 — aucun positif dans le top-k local, mais < 5 positifs attendus (aucune conclusion ferme) |
| **Médiane** | 6,4 (île 6,73) — la moyenne n'est pas portée par une seule commune |

Lecture honnête : le RR intra-commune élevé des petites communes actives et le RR faible
des gros parcs sont le comportement attendu d'un **rang absolu île** (le top va aux
marchés qui tournent) — pas un bug, mais un fait à connaître pour la prospection
multi-communes. Piste (HORS mandat, non codée) : un affichage « rang dans la commune »
existe déjà (percentile) ; un éventuel rééquilibrage serait une décision produit à passer
par l'arène. **Aucune modification effectuée** (item 1 = mesure).

## §2 · Score V hors affichage produit

- **Retiré** : le bloc fiche « Signaux vendeur » (score 0-100 + barre + bandes v_band +
  liste), `vBandColor`, `SCORE_TIP.v`, la dépendance `v_band` de l'accent Propriétaire.
- **Conservé** (et pourquoi) : le CALCUL (`parcel_v_score`, backtest — exigence du mandat) ;
  le payload API `score_v` (audit + golden qui le gèle — l'API n'est pas un affichage) ;
  les **signaux propriétaires factuels** (BODACC, DPE…) qui ne sont PAS le score : tiroir
  Propriétaire (lines cascade), chips verdict, filtre « signaux propriétaire » du Header,
  badge veille_succession (tous pilotés par les événements, pas par l'agrégat 0-100).
- Vérifié : plus AUCUNE conso front de v_score/v_band (grep), tsc 0, build OK. Les PDF
  n'affichaient déjà pas le Score V (vérifié).

## §3 · Vue legacy `v_parcelles_brulantes` supprimée

`ensure_score_v_view` (schema-heal, 2 points d'appel) devient un **DROP VIEW IF EXISTS**
idempotent : la vue disparaît partout où le heal tourne — y compris **en prod au prochain
déploiement**, sans geste manuel. Droppée en base locale (vérifié `to_regclass` = NULL).
Il ne reste qu'UNE définition de « brûlante » : le tier de `parcel_p_score_v2`.
Rollback : `git revert` (la définition complète est dans l'historique du commit).

## §4 · Radar Mutation V1 — avis : CONSERVER-DOCUMENTER (exécuté)

Pourquoi pas supprimer : moteur pur en lecture seule, testé (test_mutation*,
57 tests ciblés verts), **zéro UI** (vérifié : aucune référence frontend) — la
suppression casserait des tests et effacerait un travail réutilisable sans réduire
aucun risque produit réel. Le risque réel était l'AMBIGUÏTÉ : réglée par un bandeau
en tête de `mutation.py` (pas le modèle P · hors tiers · poids placeholder · toute
exposition = calage terrain + dossier de revue préalables) et le marquage
`[NON SERVI — ALGO-1 §7-G]` des 3 endpoints d'exploration (`/mutation/{idu}`,
`/mutation`, `/map/mutation.geojson`).

## §5 · Les 2 docs corrigées (bandeaux, journaux non réécrits)

- `docs/BAREME_VERDICT_MUTABILITE.md` : bandeau « DOCUMENT HISTORIQUE — pas le système
  servi » + ce qui reste vrai (la cascade = étage 0 ; la règle bâti) + renvoi
  SCORING_SPEC (tiers dynamiques n_entree/hystérésis/garde-fou).
- `NOTES_SCORING_DRYRUN.md` : bandeau « JOURNAL HISTORIQUE » — la spec promise
  (`SCHEMA_SCORING_LABUSE.md`) n'a jamais existé, celle qui fait foi est SCORING_SPEC ;
  baselines chiffrées = instantanés d'époque à ne plus citer.
  (Note : le grief « run_label='q_v2' en source de vérité » rapporté par l'agent de
  cross-check DOC-P était une sur-paraphrase — absent du fichier ; corrigé pour ce qui
  y est réellement.)

## §6 · Lecture du run UNIFIÉE — épinglage partout

| Surface | Avant | Après |
|---|---|---|
| Fiche (`app._score_v2_run_id`) | épinglé `Q_A_RUN_LABEL` | inchangé (référence) |
| Scoreur d'adresse | épinglé | inchangé |
| **`/v2/*` (score_v2.py)** | **dernier `computed_at`** | **épinglé `Q_A_RUN_LABEL`, 503 explicite si absent** |
| Harnais golden (`served_v2_run`) | dernier `computed_at` | épinglé (« même règle que l'API », enfin vraie) |
| Arène (outil d'analyse) | dernier computed_at (champion par défaut, overridable) | inchangé VOLONTAIREMENT — outil d'évaluation, pas une surface produit ; le champion se passe en argument |

Conséquence concrète : scorer un run CANDIDAT après le servi ne fait plus fuir le
candidat dans `/v2` ni dans le golden. `_latest_run` reste en alias (rétro-compat
imports), même épinglage. `tests/test_p_v2_api.py` seed désormais le label servi
(pattern déjà utilisé par `test_verdict_effectif`).

---

## Preuves globales

- Tiers servis : requête directe **120/1031/3587/72980/353945** + golden
  `PASS tiers_effectifs` (gel strict M-RENOUV C, mergé dans main entre-temps).
- Golden : **116/116 PASS** contre une instance bootée sur le code de la branche
  (port 8032, LABUSE_DEV_MODE=1) ; `/v2/modele` sert bien `q_v7_defisc`.
- Tests : ciblés 57/57 ; suite 1 141/1 (flaky préexistant documenté) ; tsc 0 ; build OK.
- Aucun fichier du modèle P (`p_model/`, `p_v2/pipeline.py`, `statuts.py`, artifacts)
  touché — `git diff --stat main` en foi.

## Hors périmètre, consigné pour la suite

- L'hétérogénéité communale (§1) est une CONNAISSANCE nouvelle : tout rééquilibrage
  (quota communal, rang local) = décision produit + arène, jamais un patch discret.
- `V_BAND_META`/types front conservés (payload typé) ; s'ils gênent, un mandat front
  de dégraissage des types morts peut suivre.
- La ligne « matrice_legacy … DEPRECATED » de `/v2/modele` reste vraie et utile.
