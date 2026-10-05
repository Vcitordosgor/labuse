# DASHBOARD-FIX-1 — corriger DASHBOARD-AUDIT-1

**Branche `fix/dashboard-1` · base `b44e10dd` (DASHBOARD-AUDIT-1 mergé) · ports 8775/5975 · PAS de merge.**

L'audit disait : le dashboard **ne fabrique aucun chiffre faux**, mais **ment par PÉRIMÉ** et reflète
une automatisation à l'arrêt. Les six corrections ci-dessous ferment ces écarts. Chaque point est
prouvé par un test rejouable ; aucune requête lourde (garde CHASSE-2 tenue : `pg_stat_activity` avant
chaque accès base, aucune requête sur l'île 431k).

Env : interpréteur `~/Desktop/labuse/.venv/bin/python` + `PYTHONPATH=src` (conda `labusedb` cassé).

---

## 1. Horloges — le crontab de deploy.sh couvre les 25 jobs ✅

**Constat.** Rien ne prouvait que la crontab posée sur le VPS couvrait toutes les horloges (l'audit
n'en listait que 11, celles vues « gelées » localement).

**Vérité du code.** `deploy.sh` (ligne 62) pose `/etc/cron.d/labuse` en lançant **exactement**
`labuse jobs crontab --tz <tz>` = `cli._crontab_du_registre(tz)`, qui **itère tout le registre**
`labuse.jobs.JOBS` (une ligne `labuse jobs run <nom>` par job). Mesure : **25 jobs au registre, 25
dans le crontab, 0 manquant, 0 en trop** (utc ET reunion). Aucun job « absent justifié » : le registre
EST la vérité, et `deploy.sh --verifier` refuse tout écart.

**Livrables.**
- `docs/audit-2026-10/DASHBOARD-FIX-1/HORLOGES.csv` — liste finale : job · cadence · heure Réunion ·
  touche · **posé par** (deploy.sh → /etc/cron.d/labuse) · **commande** (`labuse jobs run <nom>`).
- **Test** `tests/test_dashboardfix1_horloges.py` : le crontab généré par la commande de deploy.sh
  contient chaque job du registre (utc + reunion), et HORLOGES.csv reflète exactement le registre.

> Le gel 24/09 local est normal : **aucun lanceur n'est installé sur le Mac** (par conception — les
> horloges tournent sur le VPS). DASHBOARD-FIX-1 prouve la **couverture** ; l'exploitation démarre au
> premier `deploy.sh` sur le serveur.

## 2. Backup — « local : voir ~/labuse-backups » sur le Mac ✅

**Constat.** La tuile lisait `os.getmtime(/var/backups/labuse)` (chemin VPS) → « non configuré » à
tort sur le poste de Vic, alors que `pull_backups.sh` rapatrie les dumps dans `~/labuse-backups`.

**Côté VPS (vérifié dans `deploy/`).** `/var/backups/labuse` est **créé** par `vps_setup.sh:30`
(`mkdir -p` + chown labuse) et par le job/script (mkdir idempotent). Il est **alimenté** par deux
voies à l'horaire exact du legacy : le cron `backup-postgres` (**quotidien 13:30**, `jobs_impl` →
`.sql.gz`, rotation **7**) et `deploy/scripts/backup_postgres.sh` (`pg_dump -Fc` → `.dump`, KEEP **7**
+ hebdo retenu **4 semaines**, dump vide/illisible rejeté bruyamment). `restore-test` (mensuel) vérifie
la restaurabilité.

**Correctif (`dashboard._age_backup`).** Si le répertoire de prod n'existe pas (hors VPS), la tuile
pointe le **miroir local** `~/labuse-backups` → état `local`, « **local : voir ~/labuse-backups** »
(LED neutre, **jamais** la tâche rouge « Sauvegarder la base »). Prod inchangée ; « non configuré » ne
reste que si ni prod ni miroir local n'existent. Vérifié live : `{'etat':'local','portee':'local',
'chemin':'~/labuse-backups','fichier':'labuse-c6-…-2026-08-26.dump'}`.

Front : `AdminView.tsx` (LED + libellé + exclusion de l'alerte), type `backup.etat` + `portee`.

## 3. Bascule / Revenir — commitent leurs 3 pointeurs ; rattrapage du 05/10 ✅

**Constat.** `basculer()` écrivait `config/served_run.txt` + `run_precedent.txt` +
`served_manifest.json` (suivis git) **sans jamais commiter** → arbre sale (le « précédent q_v16 »
commité à la main). Et la bascule q_v16 du 05/10, posée **hors** `basculer()`, n'avait pas écrit
`run_bascule_journal` → « dernière bascule » périmée au 05/09.

**Correctif.**
- `bascule_flux._commit_pointeurs(arbre, run)` commite **exactement** les 3 fichiers config/*
  (`git add -- <les 3>`, jamais `git add -A`), message **« bascule: <run> »**, idempotent (rien
  d'indexé → pas de commit vide). `basculer()` l'appelle après la bascule confirmée (Bascule ET
  Revenir passent par là) et renvoie `commit` dans sa réponse.
- Git indisponible/échec → `commit.ok = False` → **bandeau rouge « 3 fichiers à commiter »** avec les
  gestes à la main (front `Detail.tsx`).
- **Rattrapage** (`scripts/dashboard-fix/rattrapage_bascule.py`, idempotent) : une ligne au
  `run_bascule_journal`, datée du vrai `promoted_at` du manifeste (2026-10-05T11:35 UTC), `par =
  « rattrapage »`, motif « rattrapage » (jsonb). Exécuté : `derniere_bascule` rend désormais
  **q_v11_m137 → q_v16 du 05/10**.

**Test** `tests/test_dashboardfix1_bascule.py` : commit des 3 pointeurs (et d'eux seuls), idempotence,
git absent → bandeau.

## 4. Verrous — date du dernier passage + « à rejouer » ✅

**Constat.** La LED « Verrous » montrait « 21/24 » **sans date**, depuis un contrôle pré-correctif, et
la bascule ne rejoue pas les verrous.

**Correctif (`dashboard._verrous`).** La LED porte désormais `dernier_ts` (date du dernier passage
journalisé, via `synthese_pour_page`) ET `a_rejouer` : vrai quand une **bascule est postérieure** au
dernier passage des verrous (`_apres(derniere_bascule.ts, dernier_ts)`) — l'état affiché précède alors
le run servi. Front `AdminView.tsx` : « 23 / 24 · <date> », ou « … · à rejouer » en ambre. Vérifié
live : `{'ok':23,'sur':24,'dernier_ts':'2026-10-05T17:43…','a_rejouer':False}` (les verrous ont été
rejoués à 17:43, après la bascule de 11:35 → pas « à rejouer », et c'est juste).

**Test** `tests/test_dashboardfix1_etat.py::test_apres_compare_les_timestamps`.

## 5. « Tâches à effectuer » — un seul compteur ✅

**Constat.** Tuile Pilotage + rail lisaient `resume.total` (= **5**, le Résumé groupé), l'onglet « À
faire » lisait `a_faire.total` (= **9**, les gestes concrets). Deux nombres pour une promesse d'égalité.

**Correctif.** Les **trois** lisent désormais `a_faire.total` (`AdminView.tsx` tuile + rail) — la même
valeur de la même réponse `/admin/circuit`, égalité **par construction**. Côté serveur, l'invariant est
réparé : `circuit_resume.total_a_faire` compte **aussi** la ligne bloquante « Reconstruire les tuiles »
(paramètre `tuiles`), et `circuit_taches_a_effectuer` (champ Pilotage) lui passe désormais tuiles +
calculer → il égale `len(composer_a_faire.lignes)`. Vérifié live : `taches_a_effectuer = 7`, sans crash.

**Test** `tests/test_circuit_p7_lot4.py::test_tuiles_perimees_comptent_dans_invariant` (+ l'invariant
strict existant reste vert).

## 6. « Jamais vérifiées » — un seul moteur d'état ✅

**Constat.** Deux moteurs, deux définitions : le circuit (`circuit_etats`) comptait **11**
(toute source sans passage, y compris **non surveillées**), `/admin/sources` (`etats_sources`)
comptait **4** (seules les **surveillées** jamais passées). « Attendent les agents » sur-promettait.

**Correctif.** Un **prédicat unique** `etats_sources.est_surveillee(methode, actif)` (vraie sonde
amont api/page/entete/temoin, active), **partagé** par les deux moteurs. `circuit_etats.etat_reservoir`
ne classe « jamais vérifiée » que pour une source **surveillée** jamais passée (statut vide) ; une
source non surveillée devient « à jour par construction » (comme les sources sans millésime) — elle
n'attend aucun agent. Le compteur `jamais_verifies` de `/admin/circuit` lit le libellé déjà posé (plus
un 3ᵉ prédicat `not veille`). Vérifié live : **circuit 4 = /admin/sources 4** (était 11 vs 4).

**Test** `tests/test_dashboardfix1_etat.py` (prédicat unique + même verdict des deux moteurs) +
`tests/test_circuit_p4_etats.py` mis à jour (non surveillée → à jour).

---

## Tests

- **Backend** (venv + `PYTHONPATH=src`) : 5 fichiers neufs/MAJ verts +
  `test_dashboard.py` (57) + suites circuit/etats_sources/cron **vertes**.
- **Front** : `tsc --noEmit` **0 erreur** · `vitest` **234 passés / 1 échec PRÉ-EXISTANT**
  (`layersCoquilles.test.ts`, compteur BPE 35 546 figé en infobulle — hors périmètre, non touché par
  ce mandat) · `npm run build` **OK**.
- **Live** (requêtes légères, sources seulement) : backup `local`, verrous datés, jamais 4=4, bascule
  q_v16 au journal, `taches_a_effectuer` sans crash.

## Cosmétique — HORS PÉRIMÈTRE (listé, non corrigé)

Repris de l'audit (§7-10) + observés :
1. **Snapshot ≠ live** : `dernier_controle` (instantané d'un contrôle) peut différer des compteurs
   live (ex. 1 fuite soldée vs 0) — lisible comme une incohérence, ce n'en est pas une.
2. **Onglet Cohérence vide** : `coherence_runs = 0` tant que le banc nocturne V6b n'a pas tourné (il
   démarre avec les horloges, point 1). `fichier_ecarts` = chemin Mac en dur (faux/vide sur VPS).
3. **Docstrings périmés** « verrous /16 » « /22 » (l'écran montre /24) ; le repli front `?? 22`/`?? 30`
   vit dans `Resume.tsx`, **composant non monté** → jamais atteint. Sans impact écran.
4. **Crédit Anthropic « — »** en dur (l'API fournisseur ne l'expose pas) — honnête, noté tel quel.
5. **Marqueur de déploiement** = baseline placeholder du 21/09 → « N commits d'avance » surestime tant
   qu'aucun `deploy.sh` ne le réécrit (il s'auto-corrige au premier déploiement, cf. deploy.sh §marqueur).

## Fichiers touchés

`src/labuse/{bascule_flux,circuit_etats,circuit_resume,etats_sources}.py`,
`src/labuse/api/dashboard.py`, `frontend/src/components/admin/{AdminView.tsx,circuit/Detail.tsx}`,
`frontend/src/lib/api.ts`, `scripts/dashboard-fix/rattrapage_bascule.py`,
`tests/test_dashboardfix1_*.py` + `tests/test_circuit_p{4_etats,7_lot4}.py`,
`docs/audit-2026-10/DASHBOARD-FIX-1{.md,/HORLOGES.csv}`.
