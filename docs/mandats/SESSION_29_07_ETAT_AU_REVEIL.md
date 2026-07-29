# ÉTAT AU RÉVEIL — session du 29/07/2026 (à lire en premier)

> Résumé pour la session neuve : ce qui SERT, ce qui est ACQUIS, ce qui RESTE. Écrit à la clôture,
> après rollback complet et golden repassé.

## Le produit sert normalement — `q_v7_defisc`, intact
Le run servi est **`q_v7_defisc`**, jamais touché de toute la session. Tiers au bit près :
**120 / 1031 / 3587 / 72980 / 353945**. L'API sert q_v7 (aucune bascule d'env). `parcel_residuel`
restauré à l'original (263 169, dates pré-15/07). Golden **116/116** (face DB) contre q_v7. **Base
saine, rien en suspens côté production.**

## ACQUIS (mergé / actif)
- **Correctif « tête de liste non constructible » — CÂBLÉ et ACTIF EN FICHE.** Le moteur pose une
  cause structurée (`Faisabilite.cause`) ; `parcel_constructibilite` classe A (zone fermée) / B
  (parcelle inconstructible) / C (non vérifiable) ; la fiche affiche les 3 motifs **dès maintenant**,
  indépendamment du tier servi → le pire du défaut (foncier inconstructible présenté sans le dire)
  est déjà levé. Le déclassement des TIERS, lui, n'agira qu'au prochain run servi (post-bascule).
  Garde-fou anti-21 077 (détection par verdict moteur, jamais `constructible_neuf(name)`) testé.
- **Arène du re-run — PASSÉE.** Même champion (`sha 00a58008…`), 2 états de features, RR@1158
  hors copro, 5 folds : **0 dégradation significative** (IC95 ∋ 0 partout). Le modèle n'exploitait
  pas le biais du repli. Pas d'obstacle arène à la bascule.
- **Tiers cibles du run calibré CONNUS** (mesurés sur run jetable) : brûlante 120 · chaude 1043 ·
  réserve 3208 · à-creuser 63948 · **déclassée A 3221** · **déclassée B 6178** · écartée 353945.
- **Barème `residuel_socle`** : re-dérivation RETIRÉE des préalables (bornes physiques, pas
  statistiques). **Canal cascade** : mesuré, sens correct. Les deux préalables sont clos.
- Séquence de mesures rendues (tous les rapports `*_MESURE.md` sur la branche).

## RESTE (session neuve, à froid)
- **Réécrire le script de bascule** `bascule_v8_calibre.py` — le précédent produisait un run
  INCOMPLET (scores P sans cascade `dryrun_*`) et se déclarait terminé. Le refondu doit :
  1. migrer `parcel_residuel` ← `parcel_residuel_rerun` ;
  2. **RE-PASSER la cascade île entière** (`evaluate_parcels` + `compute_matrice`) — PAS une copie
     (prémisse « cascade subsumée » prouvée FAUSSE : 50/50 parcelles divergent — cf. 6e principe) ;
  3. re-scorer le champion (sha gelé) ;
  4. **auto-vérifier la complétude** avant de rendre la main (chaque table comptée vs attendu :
     parcel_p_score_v2 431 663 ∧ dryrun_parcel_evaluations 431 663 ∧ dryrun_cascade_results > 0 ∧
     snapshot 431 663) — sinon échec BRUYANT (7e principe) ;
  5. **puis seulement** réaligner le golden sur le VRAI q_v8 (cascade ET tier), jamais en avance.
  Tester de bout en bout sur un run jetable avant de le proposer (5e principe).
- Après bascule réussie : contrôles post (golden 116/116 vs q_v8, 35 candidats O12 avant/après,
  invariant des tiers gravé partout avec date+motif, matrice finale intrinsèque/relationnel),
  puis `build-score-e` (SUITE, 31 129/77 718 lignes périmées), puis reprise du repli non optimiste
  (population cause A portée par ce correctif).

## Les 3 arrêts de la soirée (chacun aurait coûté cher plus tard)
1. **KeyError 'label'** — collision de nom au merge du déclassement (le dataset porte déjà `label`,
   le y d'entraînement). Alias `declasse_label`. Test de régression ajouté.
2. **Débordement varchar(24)** — `declasse_non_constructible` (26 car.) > colonne `tier`/`statut`.
   Élargi à 32. Attrapé par le test sur run jetable (5e principe).
3. **Prémisse « cascade subsumée » FAUSSE** — vraie pour l'effet tier, fausse pour les tables
   (6e principe : équivalence d'effet ≠ équivalence d'état). Établie par vérification empirique sur
   50 parcelles, pas par raisonnement — a évité une copie de 14,6 M lignes sur une base fausse.

## Pièges consignés
- **Golden rate-limit** (`docs/TESTS.md`) : 232 requêtes vs quota 60/min → FAIL `<absent>` non
  déterministes, PAS une régression. Se fier à la face DB. Contre-mesure : `LABUSE_DEV_MODE=1`.

*Branche : `mesure/repli-non-optimiste-phaseA` (tout poussé). Principes 1-7 en mémoire permanente.*
