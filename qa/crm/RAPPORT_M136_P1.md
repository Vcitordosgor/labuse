# M136 Partie 1 — Retrait des infos de coin de cellule CRM (`fix/crm-cellules`)

Branche `fix/crm-cellules` @ `f3af830a` (origin/main avancé `4967c736 → f3af830a` =
merge M135, hors périmètre CRM — branché sur le HEAD courant, signalé). **Affichage
seul : aucune logique, aucun endpoint, aucune donnée modifiés.**

## 1. Composant localisé

Cellule = composant `Card` dans **`frontend/src/components/crm/Kanban.tsx:21`**
(la page = `Kanban()`, l.157). Les deux infos de coin étaient dans la **rangée du
bas** de la carte (`<div className="mt-2 flex flex-wrap …">`, ex-lignes 92-107).

## 2. Ce qui est retiré (les deux coins)

| Coin | Rendu | Ce que c'était |
|---|---|---|
| **bas-gauche** — « À suivre #234 » | `meta.label` (verdict coloré) + `#{rang_v2}` | tier verdict (`verdictMeta`) **+ le RANG P v2** |
| **bas-droite** — « moyenne » | `e.priority` (`ml-auto`) | priorité CRM saisie par l'utilisateur |

Retiré : la rangée du bas entière + les variables d'affichage devenues inutiles
(`const prem`, `const meta`) + les imports `verdictMeta`, `SCORE_TIP` (plus utilisés).
`Tip` reste (badge cloche « nouveau »). **`tsc --noEmit` passe sans erreur.**

## 3. Layout avant / après (structure DOM — pas de trou, pas de décalage)

La rangée du bas était le **DERNIER enfant** de la carte (`<div … p-3>`). L'enlever
raccourcit la carte ; le padding `p-3` fournit l'espace bas — **aucun trou, aucun
décalage** des autres éléments.

```
AVANT (enfants de la carte)          APRÈS
─────────────────────────────        ─────────────────────────────
· IDU · badge « nouveau » · ✕        · IDU · badge « nouveau » · ✕
· surface · commune                  · surface · commune
· ▸ projet (si piste projet)         · ▸ projet (si piste projet)
· propriétaire (public/particulier)  · propriétaire (public/particulier)
· [meta.label] [#rang] … [priorité]  (retiré)
```

*(Capture pixel non produite : le front n'est pas servi dans cet environnement ;
la preuve est structurelle — dernier enfant retiré, `tsc` vert.)*

## 4. Constat à remonter (NON appliqué — décision de Vic)

**Ce que sont exactement les deux champs, et d'où ils viennent** (`app.py:_entry_dict`
l.4475, `/pipeline`) :
- **coin bas-gauche** = `premium.rang_v2` + `premium.tier_v2/statut` → `_premium_head`
  (`app.py:4529`) qui lit `parcel_p_score_v2.rang` (le **RANG P v2**) et
  `dryrun_parcel_evaluations`. Le `#234` est donc le **rang de scoring**, servi tel
  quel. Le verdict `meta.label` vient de `verdictMeta(statut, tier_v2, etage0)`.
- **coin bas-droite** = `e.priority` (`app.py:4486`), colonne `pipeline_entries.priority`
  — un champ **CRM saisi/par défaut** (config `_pipeline_cfg`), pas un score.

**Restent-ils au payload alors que plus rien ne les rend ?** OUI. `_entry_dict`
(`app.py:4482-4506`) renvoie toujours `premium` (dont **`rang_v2`**, `tier_v2`,
`statut`, `completeness_score`, `etage0`), `verdict` (dont **`rang`**) et `priority`.
**Le rang (`rang_v2`, `verdict.rang`) transite donc dans le JSON `/pipeline` sans être
rendu — la fuite du précédent M133 B.6.** La **purge du payload est une décision de
Vic**, pas un geste de cette branche (elle sera pesée dans l'audit Partie 2 §D.1).

**Le `#234` est-il une ancre technique (clé drag-drop, lien) ?** NON. Le drag-drop
utilise **`e.id`** (`setDragId(e.id)` l.~377, `move.mutate({ id: dragId … })`) et la
clé React est `e.id`. `rang_v2` était **purement décoratif** — le retirer de l'écran
**ne casse aucune mécanique** (drag-drop, ouverture fiche, suppression : tous sur
`e.id`/`e.idu`, intacts).
