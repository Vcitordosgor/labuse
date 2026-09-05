# COMPTE-RENDU CIRCUIT-3 — Le filtre : la qualité à l'intérieur de chaque source

Branche : `feat/circuit-3` (worktree `~/Desktop/labuse-audit`), créée depuis `origin/main`
(`adfd947e Merge CIRCUIT-1 + CIRCUIT-2`) — **CIRCUIT-1 et CIRCUIT-2 sont mergés dans `main`**,
donc départ depuis `main` comme le mandat le prescrit. Rien de ce mandat n'est mergé.

Reprise : « continue CIRCUIT-3 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-3.md ».

## Étape 0 — état de départ

- `pwd` = `~/Desktop/labuse-audit`, arbre **propre**, branche `feat/circuit-3`.
- **Suite de départ : 2407 passed · 1 failed · 49 skipped** (89 s). Le seul rouge est
  `test_front_reliquats.py::test_r5` — le **pré-existant admis depuis CIRCUIT-1** (non lié).
  PIÈGE retenu : les tests exigent `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (WeasyPrint /
  libgobject), et **SIP retire les `DYLD_*` à travers `nohup`** → lancer sans nohup.
- **La base applicative `labuse` est accessible en local** (431 663 parcelles = le chiffre du
  mandat, 78 lignes `data_sources`). Les seuils du lot 2 sont donc **mesurés sur la version
  servie réelle**, pas inventés. Les tests, eux, tournent sur `labuse_test` (base partielle).
- PIÈGE worktree : le paquet `labuse` installé (éditable) pointe sur `~/Desktop/labuse` (le clone
  principal). Toute mesure/CLI du worktree se joue avec `PYTHONPATH=src`. Et **le point d'entrée
  CLI est `app()` (script console `labuse`), PAS `python -m labuse.cli`** — ce dernier heurte une
  garde `if __name__ == "__main__": app()` en MILIEU de `cli.py` (ligne 2263) et ignore toutes les
  commandes tardives (pompe, golden, filtre, agent). Invocation retenue :
  `PYTHONPATH=src python -c "from labuse.cli import app; app()" …`.

---

## Lot 1 — Le cadre — **CLOS**

### Livré

- **1.1 Le module `filtres/`** (`src/labuse/filtres/cadre.py`) : `Controle` (id, nature, sévérité,
  libellé, **seuil écrit avec la mesure qui l'a fixé**, `mesure()`), `Filtre` (source, table, clé,
  colonnes INSEE/géométrie/dates, motif data_sources, portées run/live, contrôles propres),
  `Resultat` (valeur/verdict/détails), l'exécuteur `jouer(db, filtre, version)`. Deux tables
  **`filtre_resultats`** (source, version, controle, nature, severite, valeur, seuil, verdict,
  details_json, joue_le) et **`filtre_versions`** (source, version, verdict, bloquants_ko,
  avertissants_ko, **servir_quand_meme/servi_par/servi_motif** pour le geste de Vic, joue_le).
  Créées au boot (`models._ensure_schema_steps`) et à chaque `jouer` (idempotent).
- **CLI** `labuse filtre jouer <source> [--version V]` (+ `toutes`), `labuse filtre lister`,
  `labuse filtre garde`. Chaque `jouer` écrit les deux tables ET journalise le geste `filtre`
  (`resultat=refuse` si quarantaine, sinon `ok`).
- **1.2 Contrôles universels** hérités sans rien écrire, activés selon la config du filtre :
  `u_communes` (présence des 24 INSEE, référentiel embarqué `REUNION_COMMUNES`),
  `u_non_vide` (**bloquant** : 0 ligne = quarantaine), `u_couloir_lignes` (±30 % autour de la
  version précédente — **la référence est posée au 1er passage, jamais une accusation à vide**),
  `u_doublon_cle`, `u_geom_valide` (ST_IsValid), `u_geom_emprise` (enveloppe Réunion
  55.0..55.95 / -21.45..-20.8), `u_dates_plausibles` (pas < 2000 ni futur), `u_millesime`.
  **Seul `u_non_vide` est bloquant** — application stricte de la règle « aucun seuil bloquant sans
  mesure » : tous les autres universels avertissent.
- **1.3 La vanne enchaîne** : `_lancer_ingestion` (dashboard) lance désormais
  `sh -c "<ingestion> && <filtre jouer même-source --par vanne>"` (détaché, `PYTHONPATH=src` du
  worktree posé pour jouer EXACTEMENT le code servi). Le filtre ne se joue que si l'ingestion
  réussit (`&&`). Geste `filtre` ajouté à `circuit_journal.GESTES`.
- **1.4 Garde de la pompe** : `filtres.garde_pompe(db)` liste les sources à portée `run` dont la
  **version servie est en quarantaine** (bloquant KO, sans « servir quand même »). Branchée en
  **refus** dans `labuse pompe calculer` ET `labuse golden promote` (la bascule) : message nommant
  la source, sa version et les contrôles bloquants KO, refus journalisé (`resultat=refuse`). Vide
  aujourd'hui (aucun filtre `run` n'a encore de bloquant — les portées run se posent au lot 2).
- **1.5 Invariant testé** : `filtres/__init__.py` fusionne un filtre par défaut (universels seuls,
  millésime via le motif) pour **chaque** source de `sources_ingestion.yaml` (33 labels) avec les
  filtres riches du lot 2. Le test `test_toute_source_a_job_a_un_filtre` vire au rouge si une
  source de la vanne n'a pas de filtre.

### Décisions prises en autonomie (lot 1)

1. **Clé de filtre = label de la vanne** (`sources_ingestion.yaml`), pour que l'invariant 1.5 et
   l'enchaînement vanne→filtre partagent la même identité. Les sources du lot 2 SANS vanne
   (cadastre en direct, MAJIC, Filosofi, EDF, LiDAR, FLAIR, GPU/PLU en direct) seront des entrées
   riches supplémentaires du registre (pas exigées par 1.5, mais filtrées quand même).
2. **`u_non_vide` seul bloquant parmi les universels.** Un couloir de lignes, un doublon, une
   géométrie hors emprise : ce sont des avertissements tant qu'aucune mesure ne fonde un blocage.
   0 ligne, en revanche, est un fait non ambigu (rien à servir) → bloquant, comme le mandat le dit.
3. **La version d'une source** = `source_millesime`, sinon `sync <date last_sync_at>`, sinon
   `courante`. C'est la granularité que `data_sources` porte ; le couloir de lignes compare au
   dernier passage d'une AUTRE version enregistrée dans `filtre_resultats`.

### Tests — lot 1

`tests/test_circuit3_lot1.py` **7 verts** : invariant 1.5, filtre par défaut, universels sur table
témoin (3/24 communes → KO, doublon → KO, date 2099 → KO, point Paris hors emprise → KO, aucun
bloquant → « avertissements »), couloir (référence au 1er passage puis quarantaine à 0 ligne),
bloquant → quarantaine + « servir quand même » qui lève le blocage, garde de la pompe (nomme la
source `run` en quarantaine, vide après « servir quand même »), écriture des deux tables.
Régression ciblée circuit + dashboard : **38 verts**. `DYLD_FALLBACK_LIBRARY_PATH` posé.

### Commit

`feat/circuit-3` — un commit lot 1 (après le commit « CIRCUIT-3 — mandat »). Poussé. Rien mergé.

---

## Lots 2 à 6 — à venir

(compte-rendu tenu à jour lot par lot)
