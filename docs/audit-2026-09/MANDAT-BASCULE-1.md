# MANDAT BASCULE-1 — un seul chemin de bascule, et qui ne ment pas

**Nature** : correctif. **Branche** : `feat/paliers-1` (worktree `~/Desktop/labuse-paliers1`), à la suite des commits PALIERS-1.
**Modèle CC** : Fable.
**Pourquoi** : `golden promote` annonce « ✓ Run servi = X » sans rien changer — depuis CIRCUIT, `runs.current()` lit `served_manifest.json` en premier et `promote()` n'écrit que `served_run.txt`, devenu une vue dérivée. La commande est morte et le dit victorieuse. C'est un faux positif sur le geste le plus sensible de l'app.
**Interdits** : aucune bascule réelle, aucun merge, aucun rescoring, aucun élargissement au-delà des trois lots ci-dessous.

## Étape 0
`pwd` = `~/Desktop/labuse-paliers1`, branche = `feat/paliers-1`, arbre propre.
Remettre `~/Desktop/labuse/config/served_run.txt` à `q_v11_m137` (le promote raté l'a laissé à `q_v14` alors que le manifeste sert toujours `q_v11_m137` — les deux vues doivent redire la même chose avant de commencer).

## Décision de Vic (08/09/2026) : UN SEUL chemin de bascule
`bascule_flux.basculer()` est le seul geste de bascule. `golden promote` disparaît en tant que chemin concurrent.

## Lot A — retirer le chemin mort
Supprimer `golden_ops.promote()` comme point d'entrée de bascule et la commande `golden promote` du CLI (`cli.py:4212`), ou la réduire à un alias qui appelle `bascule_flux.basculer()` — au choix de CC, celui qui laisse le moins de code mort. Aucun appelant ne doit subsister ailleurs : les chercher tous (scripts, docs, crons, qa/) et les rediriger. Les docs qui écrivent « bascule via `labuse golden promote <run>` » sont mises à jour, y compris l'en-tête de `served_run.txt`.

## Lot B — une commande qui ne peut plus mentir
Sur le chemin conservé :
1. Écrire le **manifeste** (le point de vérité), pas seulement les vues dérivées.
2. **Relire `runs.current()` après l'écriture** et ne confirmer que si la valeur relue est le run demandé. Sinon : message d'échec explicite, code de sortie non nul, et dire ce qui a été écrit et ce qui fait foi.
3. Afficher **le chemin réel du fichier écrit** et l'arbre concerné, pour que l'écart worktree / install éditable soit visible à l'œil.
4. Un test qui échoue si une bascule annonce un succès alors que `runs.current()` n'a pas changé.

## Lot C — l'écart d'arbre
`labuse` est installé en éditable sur `~/Desktop/labuse` : toute commande lancée depuis un worktree écrit dans le checkout principal. Ne pas réparer la résolution de chemin (risque hors mandat) : **avertir**. Si le répertoire courant est un worktree git différent de celui où le module est installé, la commande affiche un avertissement clair avant d'agir. Le documenter en une ligne dans le README de développement.

## Recette
Rendre compte, dans `docs/audit-2026-09/BASCULE-1.md` : la sortie de la nouvelle commande sur une bascule réussie et sur une bascule impossible, la liste des appelants redirigés, la valeur de `runs.current()` avant et après. Aucune bascule laissée en place : à la fin, le run servi est `q_v11_m137` et le manifeste le dit.
