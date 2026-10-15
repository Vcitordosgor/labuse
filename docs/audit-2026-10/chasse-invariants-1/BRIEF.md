# BRIEF commun — CHASSE-INVARIANTS-1 (lecture seule)

Tu es un sous-agent de l'audit **CHASSE-INVARIANTS-1**. Tu vérifies des **invariants**
(règles qui doivent TOUJOURS être vraies) sur **toutes les parcelles** servies, par
requête SQL et/ou second calcul indépendant. Une règle fausse une seule fois = un bug.
Une chasse vide est un BON résultat, prouvé par le nombre de parcelles passées au crible.

## Interdits ABSOLUS
- **Aucune écriture en base** (pas d'INSERT/UPDATE/DELETE/CREATE/ALTER/TRUNCATE). Lecture seule stricte.
- **Aucun correctif de code.** Tu ne modifies aucun fichier source. Tu rends un diagnostic.
- **Rien sur le VPS.** Tout est local.
- Ne lance pas d'autres sous-agents.

## Environnement (déjà en place, ne pas relancer)
- Répertoire : `/Users/openclaw/Desktop/labuse-chasse-invariants`
- Branche : `audit/chasse-invariants-1`. Base servie : **q_v18 / run_seq 15** (434 582 parcelles dans `parcels`).
- **DB** : `psql -h localhost -U openclaw -d labuse` (auth trust, lecture seule). Pose TOUJOURS
  `SET statement_timeout='120s';` en tête de session pour les requêtes île entière.
- **API locale** : `http://127.0.0.1:8790` (healthz = ok). Sert q_v18.
- **Python** (pour exécuter du code labuse / écrire des calculettes) :
  `PYTHONPATH=/Users/openclaw/Desktop/labuse-chasse-invariants/src \
   LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
   PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj \
   /Users/openclaw/Desktop/labuse/.venv/bin/python …`
  (le `.venv` du dépôt principal porte les deps ; le `PYTHONPATH` force le CODE de CE worktree).
- Tables servies utiles : `parcels`, `score_labuse`, `score_e`, `parcel_residuel`,
  `parcel_residuel_bati`, `cascade_results`, `parcel_zone_plu`. Le run servi se lit dans
  `residuel_runs.is_served` (label `q_v18`, run_seq 15) / `score_labuse_runs` / `config/served_manifest.json`.

## Ne PAS doublonner le banc existant
Avant d'écrire une garde, LIS ces fichiers et n'invente pas une règle déjà couverte :
`scripts/coherence/chasse_donnees.py`, `scripts/coherence/chasse_nav.py`,
`scripts/coherence/checks_parcelle.py`, `scripts/coherence/checks_commune.py`,
`scripts/coherence/aggregats.py`, `scripts/coherence/lib.py`. Étends, ne répète pas.

## Méthode
1. Formule tes invariants (une phrase française claire chacun).
2. Pour chacun : écris la requête SQL (ou le petit script) qui le VÉRIFIE sur TOUTE l'île.
   Compte les parcelles passées. Isole les violations.
3. Pour toute violation : va lire le code qui la produit et donne la cause probable + `fichier:ligne`.
4. Requêtes lourdes : une par une, `statement_timeout` posé. Si une requête dépasse, réduis
   le périmètre (échantillon aléatoire représentatif) et NOTE-le dans « non vérifié ».

## Livrable — écris UN fichier
Écris **`docs/audit-2026-10/chasse-invariants-1/domaine-<N>.md`** (N = ton numéro de domaine),
avec EXACTEMENT ces sections :

```
# Domaine <N> — <titre>

## Verdict (3 lignes)
parcelles passées · invariants vérifiés · violations · ce qui est resté muet.

## Invariants
| # | règle (une phrase FR) | requête/script | parcelles passées | violations |
Pour chaque ligne, la requête doit être rejouable (copiable).

## Violations
Pour chacune : gravité (FAUX-CLIENT = l'utilisateur voit un chiffre faux /
INCOHERENT = deux lecteurs se contredisent / ROBUSTESSE = plantage ou affichage sale),
idu(s), attendu, obtenu, cause probable, fichier:ligne.

## Non vérifié
Ce que tu n'as pas pu couvrir et pourquoi.

## Gardes proposées
Le code (ou pseudo-code SQL) de chaque invariant, prêt à devenir une garde de
`scripts/coherence/chasse_invariants.py` (fonction qui rend [OK]/[ECART], exit 1 si écart).
```

Rends aussi, dans ton message final au chef d'orchestre, un résumé de 5 lignes :
parcelles passées, nb invariants, nb violations (par gravité), domaines muets, le pire écart.
