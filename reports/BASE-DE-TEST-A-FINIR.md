# Base de test `labuse_test` — pollution : à finir

> État laissé par OUTIL-PERMIS-FIX-11 (branche `fix/outil-permis-1`, **non poussée**). Le diagnostic, la
> reproduction du risque et le nettoyage ponctuel sont faits. Le **correctif de fond n'est pas terminé** :
> la fixture de nettoyage automatique a été **retirée** parce qu'elle est dangereuse en concurrence (voir
> § Risque). Ce document dit la cause, ce qui reste, et la solution envisagée.

## Cause

Des tests **committent** dans des tables d'**accumulation** de `labuse_test` via une session committante
(`session_scope`, l'app sous `TestClient`, …) et **ne nettoient pas derrière eux**. D'un run à l'autre, la
base enfle. Compté avant nettoyage (25/11/2026) :

| Table | Lignes | Depuis |
|---|--:|---|
| `comptes` (parent, `ON DELETE CASCADE` vers ~25 filles) | 43 511 | 06/09/2026 (+~89/jour) |
| `event_log` | 658 (dont **≥ 50 `systeme`/jour**) | 06/09/2026 |
| `ops_incidents` | 115 (93 ouverts) | 14/10/2026 |
| `watch_zones` / `watched_parcels` / `veilles` / `saved_searches` / `notif_prefs` | 93 / 88 / 419 / 383 / 1 542 | 28/09/2026 |

**Le plafond de 50 alertes/jour.** `labuse.api.events.creer_notification` refuse d'insérer le N‑ᵉ event
`(kind, compte, jour)` au‑delà de `NOTIF_CAP_JOUR = 50` : il agrège en « +N autres ». Comme les runs
répétés avaient committé **51 lignes `kind='systeme'` (compte NULL)** le même jour, tout nouveau `systeme`
était agrégé au lieu d'être créé → `test_silence_1`, `test_cockpit_corrections_c`, `test_notifications_m85`
(qui créent **et relisent** un `systeme`) tombaient **dans la suite complète** (verts seuls).
Producteurs `systeme` : `ops_alertes.signaler`, `sentinelle`, `mail`. Comptes : tout test en créant un
(p. ex. `test_brand_colors`, `test_recette_generale1_mails_circuit`).

## Ce qui a été nettoyé (fait)

Script `scripts/outil_permis_fix8/fix11_nettoyer_labuse_test.py` (garde‑fou dur :
`current_database() == 'labuse_test'`, jamais `labuse`). Exécuté une fois sur la base PARTAGÉE
`labuse_test` (sortie : `docs/audit-2026-11/outil-permis-fix-1/fix10/fix11-cleanup.txt`) :

```
comptes        43 511 → 0   (+ filles ON DELETE CASCADE)
event_log         658 → 0   (dont 296 à compte NULL — systeme/zone)
ops_incidents     115 → 0
watch_zones/watched_parcels/veilles/saved_searches/notif_prefs → 0
```

Ce nettoyage est **ponctuel** : il ne protège pas des runs futurs (l'accumulation reprend).

## Risque de concurrence (reproduit) — pourquoi la fixture auto a été retirée

La correction tentée était une fixture de **session** qui photographiait `max(id)` au début et supprimait
`id > photo` à la fin. Elle est **dangereuse quand deux suites tournent en même temps sur la même base** :
la fin de session d'une suite efface les lignes qu'une autre suite vient de créer (`id` partagés, séquence
commune). **Reproduit** (sortie `docs/audit-2026-11/outil-permis-fix-1/fix10/fix11-repro-concurrence.txt`) :

```
suite A : max(id) au départ = 0 ; suite B : max(id) au départ = 0
A insère compte id 62518 ; B insère compte id 62519 (B tourne encore)
A termine → DELETE comptes WHERE id > 0  →  compte de B (62519) présent ? False  ← EFFACÉ par A
```

Sur cette machine, **plusieurs worktrees** (`labuse-permis-fix`, `labuse-plu-fix`,
`labuse-assemblage-fix`, …) lancent la suite **en parallèle** sur la MÊME `labuse_test` — le risque est donc
réel, pas théorique. La fixture a donc été **retirée du commit** (elle reste consultable dans l'historique
de `2346ee8a0` si besoin).

## Solution envisagée — une base de test PAR DOSSIER DE TRAVAIL (worktree)

La plus simple qui **tient unilatéralement** (sans coordination entre worktrees, contrairement à un verrou
consultatif qu'il faudrait que TOUS les worktrees prennent) : chaque worktree utilise **sa propre** base de
test, dérivée du dossier (`labuse-permis-fix` → `labuse_test__labuse_permis_fix`). Le nettoyage de fin de
session d'une suite ne porte alors JAMAIS que sur **sa** base privée — jamais sur celle d'un autre worktree.
La fixture de nettoyage `id > photo` redevient sûre dans ce cadre (aucune concurrence sur une base donnée).

Esquisse (conftest, non committée, à reprendre) :
```python
def _nom_base_test() -> str:
    import re, os
    racine = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return "labuse_test__" + re.sub(r"[^a-z0-9]+", "_", racine.lower()).strip("_")
_TEST_URL = os.environ.get("LABUSE_TEST_DATABASE_URL") or (_APP_URL.rsplit("/",1)[0] + "/" + _nom_base_test())
```

## Ce qui reste à résoudre pour terminer

1. **Bootstrap de la base par worktree.** Une base fraîche par worktree doit être **créée ET son schéma
   healé** AVANT les tests non‑db qui écrivent via `session_scope` (sinon « database does not exist »). La
   fixture `engine` (session) le fait déjà (create DB + `models.create_all` + séquence de heal
   `api/app.py::_lifespan`), mais elle n'est appelée que par les tests qui la demandent (db) et fait
   `pytest.skip` si pas de base. Il faut un **bootstrap de session tolérant** (create+heal, **no‑op** si
   pas de PostgreSQL — jamais un skip global, sinon le hook `-m "not db"` sans base skippe tout) partagé
   par `engine` et par le nettoyage.
2. **Réintroduire la fixture de nettoyage** `id > photo` (retirée ici) UNE FOIS la base par worktree en
   place — elle est alors sûre. Garder : `comptes` d'abord (CASCADE), puis les lignes à compte NULL
   (`event_log` systeme/zone, `ops_incidents`). Portée session, nettoyage POST‑session (aucune assertion
   touchée).
3. **Preuve** : suite non‑db complète lancée **2×**, zéro rouge les deux fois, et empreinte de la base de
   test **identique avant/après** chaque run.
4. **Migration éventuelle** si l'on veut une base par worktree aussi en CI / pour les autres dossiers (le
   nom de base devient dérivé du dossier pour tout le monde après fusion).

## Note test_r2 (réglée, pas un sujet de ce document)

`test_etude_fiable_1::test_r2` échouait sous charge — **pas** à cause de la pollution, mais du garde‑fou
TEMPS de la grille + d'un appel réseau IGN. C'est **déjà réparé dans `main` par `49ad672ad`** (les deux
neutralisés DANS le test). La branche contient ce commit (merge `origin/main`). Ne pas ré‑ajouter un second
correctif qui le contredirait.
