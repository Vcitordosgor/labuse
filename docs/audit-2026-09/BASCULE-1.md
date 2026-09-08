# BASCULE-1 — un seul chemin de bascule, et qui ne ment pas

**Branche** `feat/paliers-1` (worktree `~/Desktop/labuse-paliers1`), 3 commits à la suite de PALIERS-1.
**Nature** correctif. **Aucune bascule réelle, aucun merge, aucun rescoring.**

## Le problème

`golden promote` annonçait « ✓ Run servi = X » sans rien changer. Depuis CIRCUIT, `runs.current()` lit
`config/served_manifest.json` **en premier** (le point de vérité) ; `golden_ops.promote()` n'écrivait
que `config/served_run.txt`, devenu une **vue dérivée** ignorée tant que le manifeste existe. La commande
était morte et se disait victorieuse — un faux positif sur le geste le plus sensible de l'app.

## Étape 0 — les deux vues redisent la même chose

Le promote raté avait laissé `~/Desktop/labuse/config/served_run.txt` à `q_v14` alors que le manifeste
sert toujours `q_v11_m137`. Remis à `q_v11_m137`. Vérifié en fin de mandat :

```
worktree served_run.txt   -> q_v11_m137
main     served_run.txt   -> q_v11_m137
main     manifest scoring_run -> q_v11_m137
runs.current()            -> q_v11_m137
```

## Lot A — retirer le chemin mort (`3b17a865`)

`bascule_flux.basculer()` est **l'unique geste de bascule** (le même que le bouton admin de la page
Circuit). La commande CLI `golden promote` est **réduite à un alias** qui appelle `basculer()` — elle
n'appelle plus `golden_ops.promote()` directement. `promote()` reste le seul écrivain de la vue dérivée
`served_run.txt`, appelé **par `basculer()`** ; ce n'est plus un point d'entrée de bascule.

**Appelants recensés et traités :**

| Référence | Avant | Après |
|---|---|---|
| `cli.py:4212` `golden_promote_cmd` | appelait `golden_ops.promote(run)` | **appelle `bascule_flux.basculer(s, run, par="cli")`** |
| `bascule_flux.py:217` `basculer()` | `promote(nouveau_run)` (écrit la vue dérivée) | **inchangé** — seul appelant légitime de `promote()` |
| `api/dashboard.py:1666,2407` (bouton admin) | `bascule_flux.basculer(...)` | **inchangé** — déjà le bon chemin |
| `jobs_impl.py:369` (fin d'ingestion) | `golden_ops.rapport_candidat()` (LECTURE) | **inchangé** — ne bascule jamais |
| en-tête `config/served_run.txt` | « POINT DE VÉRITÉ UNIQUE … `golden promote` » | « **VUE DÉRIVÉE** … point de vérité = `served_manifest.json` » |
| docstrings `golden_ops.py`, `docs/EXPLOITATION.md` | présentaient `golden promote` comme le mécanisme | redisent le chemin unique `basculer()` + le manifeste |

Les comptes-rendus d'archive (`docs/CRON-1`, `docs/CRON-2`, `docs/CIRCUIT/*`, rapports d'audit
antérieurs) citent encore `golden promote` : ce sont des **records historiques** de sessions passées,
laissés tels quels ; l'alias `labuse golden promote <run>` reste valide (il route vers `basculer()`).

## Lot B — une commande qui ne peut plus mentir (`9c54c808`)

Sur le chemin conservé (`basculer()`), après l'écrit du manifeste et `runs.invalidate()` :

1. **le manifeste est écrit** (le point de vérité) — déjà le cas, `served_run.txt`/`run_precedent.txt`
   en sont les vues dérivées ;
2. **`runs.current()` est RELU** ; on ne confirme (`ok=True, verifie=True`) **que si** la valeur relue
   est le run demandé. Sinon : `ok=False, verifie=False`, motif explicite, **code de sortie non nul**,
   et le message dit **ce qui a été écrit** (chemin réel du manifeste) et **ce qui fait foi**
   (`runs.current()`) ;
3. le geste retourne **le chemin réel écrit** (`manifeste_path`) et **l'arbre concerné** (`arbre`) —
   l'alias CLI les affiche, pour que l'écart worktree / install éditable soit visible à l'œil ;
4. `tests/test_bascule1.py` **échoue si une bascule s'annonce réussie alors que `runs.current()` n'a pas
   changé** (le bug d'origine, reproduit par neutralisation de l'écrit du manifeste).

## Lot C — l'écart d'arbre (`19672a43`)

`labuse` est installé en éditable sur un checkout : une commande lancée depuis un **autre worktree git**
écrit le manifeste dans le checkout d'installation, **pas** dans le cwd. On **ne répare pas** la
résolution de chemin (hors mandat) — on **avertit**. `bascule_flux.avertissement_arbre()` compare
l'arbre où vit le module au cwd et, s'ils diffèrent, la commande affiche un `⚠ ARBRE …` **avant d'agir**.
Documenté en une ligne dans `README.md` (bloc « Worktree & install éditable »).

## Recette — sorties de la commande

### Bascule réussie (bac à sable — pointeurs `tmp`, écritures DB neutralisées ; forme identique au réel)

`PYTHONPATH=src python scripts/recette_bascule1.py`

```
runs.current() AVANT : q_old
✓ Run servi = q_new (ancien : q_old, sens : avant).
  manifeste (fait foi) : /…/tmp…/served_manifest.json
  arbre servi          : /…/tmp…
  runs.current() relu  : q_new
  exit = 0
runs.current() APRÈS : q_new
```

### Bascule impossible (RÉEL, sans effet de bord — run inconnu)

`PYTHONPATH=src labuse golden promote __run_inexistant__`

```
✗ Bascule refusée : run « __run_inexistant__ » absent de p_score_v2_runs (non scoré) — bascule refusée.
exit=1
```
`runs.current()` **inchangé** (`q_v11_m137`) après ce refus.

### Bascule qui aurait menti → REFUSÉE (le cœur BASCULE-1, bac à sable)

Quand l'écrit ne prend pas effet (manifeste neutralisé — simule une vue dérivée écrite dans le mauvais
arbre / un manifeste ignoré), la commande **refuse de confirmer** :

```
runs.current() AVANT : q_old
✗ Bascule NON confirmée : le manifeste demande « q_new » mais runs.current() relit « q_old ».
  Écrit : /…/served_manifest.json — c'est CE fichier (arbre /…) qui fait foi. Rien n'a basculé pour les clients.
  exit = 1
runs.current() APRÈS : q_old  (inchangé — aucun mensonge)
```

## `runs.current()` avant / après

| Moment | Valeur |
|---|---|
| Avant le mandat (manifeste) | `q_v11_m137` |
| Après Étape 0 (les deux vues alignées) | `q_v11_m137` |
| Après bascule **impossible** (réel) | `q_v11_m137` (refus, aucun changement) |
| **Fin de mandat** | `q_v11_m137` — et le manifeste le dit |

**Aucune bascule laissée en place.** Le run servi est `q_v11_m137`, `served_manifest.json` le dit, et
`served_run.txt` (vue dérivée) concorde. Vic bascule lui-même quand il le décide, par le chemin unique.

## Vérifications

- `tests/test_bascule1.py` : 3 verts (succès confirmé · refus de mentir · avertissement d'arbre).
- Suite backend complète (`--ignore=tests/test_non_contradiction.py`) : **2860 passed / 12 failed /
  43 skipped** en 101 s. Les 12 échecs sont le **baseline PALIERS-1 identique** (weasyprint/libgobject
  PDF, base-réelle `test_lot1_tables`, stripe/courrier DB, `test_ia_log` FK 4242, cerfa, `test_r5_etudier`)
  — aucun ne touche bascule/golden/circuit/flux. `2860 = 2857 (baseline) + 3 (BASCULE-1)` → **0 régression**.
- Frontend : **aucun fichier front touché** (backend + docs uniquement) → tsc/vitest inchangés vs PALIERS-1.
