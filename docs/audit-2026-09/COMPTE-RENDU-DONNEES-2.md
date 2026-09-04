# DONNÉES-2 — l'onglet « Mise à jour » reconstruit (branche `fix/donnees-2`)

**Mandat.** Reconstruire l'onglet de mise à jour de la page Données selon
`docs/audit-2026-09/maquette-admin-donnees-v2.html` : **trois étapes verticales**, une action = un
endroit, un chiffre = une liste. Recette dans un vrai navigateur sur la base réelle, bascule vers
q_v12 puis retour arrière, captures avant de committer.

> Le fichier `MANDAT-DONNEES-2.md` n'a jamais été committé (seule la maquette v2 l'a été, `e0d423ca`) ;
> la maquette (sa `note` en tête) a servi de spécification, complétée par les données réelles.

## Ce qui change

Avant, la page Données avait 3 onglets (Catalogue / Circuit / CRON) surmontés d'un **bandeau
« 3 gestes » condensé** ; les vraies commandes (injecter / calculer / basculer) vivaient éparpillées
dans le Circuit. Maintenant :

- **Un 4ᵉ onglet « Mise à jour », premier et par défaut**, qui EST la mise à jour. Le bandeau
  condensé a disparu : ses chiffres vivent dans le **badge de l'onglet** (nombre d'étapes qui
  demandent une action, ✓ sinon) et dans les étapes elles-mêmes.
- **Un en-tête de page** (maquette v2) : « Mes données sont-elles à jour ? » · Run servi · calculé le ·
  garde de cohérence N/N · phrase surfaces — lu de `/admin/flux`.
- **Trois étapes verticales** (rail numéroté + une carte qui porte tout) :
  1. **Injecter** — les sources surveillées avec une version amont plus récente (dot=warn +
     injectable), servi/amont/alimente sur une ligne, bouton « Injecter AAAA-MM → » ; plus une ligne
     discrète « les N autres… » + « Vérifier toutes les sources » (job `sentinelle-sources`, local-safe).
  2. **Calculer** — l'écart run servi ↔ sources, boutons « Lancer un run → » (m36) / « Candidat q_v12 → ».
     Le run qu'on vient de lancer s'affiche « en cours » (barre **indéterminée**, pas de % inventé).
  3. **Basculer** — le run **recommandé** (le plus récent complet non servi) avec écart + note de
     version dépliable + « Basculer vers … → » ; le **retour arrière** (run précédent) ; les runs
     anciens repliés ; la **garde de cohérence** (6 checks) ; l'historique des bascules.
- Les onglets **Catalogue / Circuit / CRON** sont inchangés (composants existants), rappelés comme
  « vues » sans action de mise à jour.

## Aucune mécanique réécrite

Les trois étapes appellent **les mêmes endpoints que le Circuit et le Catalogue** :
`/admin/flux` (+ `/admin/flux/runs` en rendu progressif, RETOURS-9 Q1), `POST /admin/flux/run/lancer`,
`POST /admin/flux/bascule`, `POST /admin/sources/{id}/veille/injecter`, `POST /admin/crons/{nom}/run`
(sentinelle-sources). **Zéro changement backend.**

## Honnêteté — ce que la maquette montre mais que le backend ne fournit pas

La maquette dessine, à l'étape 2, un run « en cours » avec **barre de progression** et bouton
**« Arrêter »**. En vérité :
- un run est lancé en **subprocess détaché** (`start_new_session`, sans PID suivi) ;
- **aucun registre de progression** ni **aucun endpoint d'arrêt** n'existe.

Plutôt que peindre un pourcentage inventé et un bouton « Arrêter » qui ne ferait rien, l'étape 2
affiche le run **qu'on vient de lancer** (session courante), une **barre indéterminée**, et le dit :
« il finit seul (~durée estimée), puis apparaît à l'étape 3 ; il ne peut pas être interrompu depuis
l'écran ». Fidèle à la structure de la maquette, honnête sur la mécanique.

## Recette navigateur — base réelle (Saint-Paul, 431 663 parcelles)

Serveur backend `:8000` (import `labuse` = ce dépôt via `.venv` editable), Vite servi sur `:5174`
(le `:5173` tournait sur un autre worktree). Les données réelles collent à la maquette :

| | valeur réelle observée |
|---|---|
| Run servi | `q_v11_m137` · calculé le 27/08 · garde **6/6 ✓** |
| Étape 1 | SITADEL servi 2026-07 · **amont 2026-08 disponible** · alimente scoring · rattachement · signaux |
| Étape 2 | 1 source plus récente que le run servi |
| Étape 3 recommandé | **q_v12** · 4 688 parcelles changent · Priorité **1 478 → 1 225 (−17,1 %)** + note de version réelle |
| Étape 3 retour arrière | q_v10_m129 · 220 parcelles · +8,7 % |

**Bascule → q_v12 (effective en direct)** : `served_run.txt` = q_v12, l'API sert q_v12, l'en-tête
passe à « Run servi q_v12 · calculé le 03/09 », confirmation « Bascule q_v11_m137 → q_v12 · 8 caches
purgés · garde relancée ». La **garde tombe honnêtement à 5/6** : le check « Aucune lecture de table
obsolète » signale `parcel_renouvellement, score_e, parcel_flags` périmées pour q_v12 (donnée réelle,
pas un défaut de l'UI).

**Retour arrière → q_v11_m137** : via « Basculer vers q_v11_m137 → » (le recommandé après bascule).
`served_run.txt` re-devient q_v11_m137, garde **6/6 ✓**. Les deux fichiers pointeurs ont ensuite été
**remis à l'identique** (`served_run.txt` = q_v11_m137, `run_precedent.txt` = q_v10_m129) — `git status`
sur `config/` est propre.

Captures : `docs/audit-2026-09/captures-donnees-2/` (01 avant · 02 étape 3 · 03/04 après bascule ·
05 restauré · 06 note de version dépliée).

## Observation (hors périmètre, pour Vic)

Dans la charge `/admin/flux`, `run.precedent` provient d'une **constante de module**
(`scoring.score_v_constants.RUN_PRECEDENT` = `q_v10_m129`), pas du pointeur vivant
`config/run_precedent.txt`. Juste après une bascule, l'étiquette « ancien run servi » peut donc
désigner l'avant-dernier run plutôt que le tout dernier. Sans effet fonctionnel (le run « recommandé »
proposé est exactement la bonne cible de retour arrière), mais à savoir si un jour on veut que
l'étiquette suive le pointeur vivant.

## Vérifs

- Front `tsc --noEmit` : **0 erreur** · `npm run build` : OK.
- Tests : `MiseAJour.test.tsx` (5, réponse réelle capturée) + `Flux.circuit.test.tsx` (3) verts ;
  dossier admin **18/18**.
- ⚠ Redémarrage serveur non nécessaire (aucun changement backend) ; branche `fix/donnees-2`, non mergée.

---

# DONNÉES-2 · Partie B (backend étape 2 + statuts + garde q_v12 + précédent vivant)

Quatre chantiers, dans l'ordre du mandat. Aucune mécanique de scoring réécrite ; on RÉUTILISE le
geste unique `rebuild_mvt_servies` (M48) et le pipeline existant.

## B1 — la garde 5/6 sur q_v12 : cause & correction (bloquant pour la bascule)

**Cause.** Trois tables SERVIES run-scopées — `parcel_flags`, `score_e`, `parcel_renouvellement` —
ne portaient QUE `q_v11_m137`, pas `q_v12`. Le run q_v12 a été calculé par `flux-run` (cascade +
score-v2), qui ne construit PAS ces tables : elles se montent par `build-mvt` (geste `rebuild_mvt_servies`,
« un geste = tout ou rien »), jamais rejoué pour q_v12. Elles sont **mono-run** (DROP + rebuild) : on
ne PEUT pas les pré-remplir pour q_v12 sans écraser celles du run servi (q_v11) → la garde du servi
tomberait à son tour. Le seul moment correct de les bâtir pour q_v12, c'est **au moment où il devient
servi** — ce que le commentaire de la garde appelait déjà « montent DANS le geste », jamais câblé.

**Correction.** La bascule LANCE, **détachée**, `build-mvt --label <nouveau run>` (même geste que
`labuse build-mvt`). En ligne c'est impossible : un `DROP TABLE` prend un verrou EXCLUSIF qui
**DEADLOCK** avec les lectures de la garde (l'admin sonde `/admin/flux` en boucle) — constaté en base
réelle. On borne donc l'attente de verrou (`SET lock_timeout='30s'`) et on **réessaie le geste entier**
(transaction annulée → rien de partiel) : le rebuild finit par gagner. Pendant qu'il tourne, la garde
reste honnêtement à 5/6 (tables encore sur l'ancien run) ; elle repasse **6/6** à la fin. L'UI l'annonce
(« reconstruction des tables servies en cours… ») et poll jusqu'au vert.

> Bug latent trouvé & corrigé au passage : `build-mvt` faisait `from .api.tiles import RUN` — `RUN`
> n'existe pas dans `tiles` → la commande levait `ImportError` à chaque appel. Remplacé par
> `runs.current()` (le run servi, lu vivant).

**Recette réelle.** Bascule q_v11_m137 → **q_v12** : la garde passe 5/6 (périmées : les 3 tables)
puis, le `build-mvt` détaché terminé (146 s, une tentative rejouée après un deadlock), **6/6 ✓** —
`Run servi q_v12 · garde 6/6`. Retour arrière q_v12 → q_v11_m137 : idem, tables reconstruites,
**6/6 ✓**. Pointeurs `config/` remis à l'identique (served=q_v11_m137, precedent=q_v10_m129).

## B2 / D3 — le statut de chaque run

Chaque run porte désormais un **statut** dérivé (dans `bascule_flux.runs_termines`) :
`servi` (pointeur servi) · `retour_arriere` (= `config/run_precedent.txt`) · `termine` (complet, plus
récent que le servi = candidat en avant, le recommandé) · `ancien` (complet mais plus vieux que le
servi) · `en_cours` / `abandonne` (runs lancés, lus de l'état de progression). Les runs LANCÉS mais
jamais terminés — **absents de `p_score_v2_runs`** — sont ajoutés à la liste. À l'étape 3, `termine`
= recommandé, `retour_arriere` = « ancien run servi », le reste (`ancien` + `abandonne`) est masqué
derrière « ▸ N runs anciens ou abandonnés ». **Un run « en cours » dont le processus a disparu passe
« abandonné » au chargement** (`run_progress.reconcile`) ; les 3 runs tués du 03/09 (logs `/tmp`
orphelins) sont récupérés « abandonné » — vérifié à l'écran.

## B3 — backend de l'étape 2 : progression, arrêt, refus

Nouveau module `run_progress.py` : un état JSON par run (`/tmp/labuse-run-<label>.json`), écrit par le
process du run, lu par l'API.
- **Le run écrit sa progression** : `flux-run` publie phase (cascade/scoring), **commune en cours**,
  done/total et **%** — barre RÉELLE à l'étape 2 (plus de faux pourcentage).
- **Arrêt propre** : `POST /admin/flux/run/arreter` envoie un `SIGTERM` au **groupe de process** (le run
  est `start_new_session`) puis marque « abandonné ». Bouton « Arrêter » à l'étape 2.
- **Refus** : `POST /admin/flux/run/lancer` réconcilie puis **refuse (409)** si un run tourne déjà
  (« un seul run à la fois ») ; les boutons « Lancer » sont désactivés pendant.
- `GET /admin/flux/run/etat` : poll léger (3 s) pour la barre.

**Recette réelle.** « Candidat q_v12 → » lancé : l'étape 2 montre « En cours · cascade · Les Avirons »,
barre réelle, `0/25 étapes`, « Arrêter » ; les boutons Lancer désactivés. Clic « Arrêter » → le run
s'interrompt et repasse « abandonné » (disparaît de l'en-cours, réapparaît masqué à l'étape 3).

## B4 — `run.precedent` lu vivant

`run.precedent` de `/admin/flux` provenait d'une **constante de module**
(`scoring.score_v_constants.RUN_PRECEDENT`, figée à l'import) → après une bascule elle désignait le
mauvais « ancien run servi ». Nouveau `runs.precedent()` (lit `config/run_precedent.txt`, cache court,
override `LABUSE_RUN_PRECEDENT`, invalidé à la bascule), et `RUN_PRECEDENT` rendu **dynamique** via
`__getattr__` (comme `Q_A_RUN_LABEL`). `flux.py` et `accueil.py` (imports figés au module) convertis.
La bascule lit le précédent AVANT de réécrire le pointeur (calcul du sens avant/arrière correct).

## Vérifs

- Backend : `test_run_progress.py` (8), `test_donnees2_precedent.py` (4), `test_flux`/`test_bascule_gardes`
  verts ; sweep large **140 passed / 1 skipped** (QA distante).
- Front : `tsc` 0 · `build` OK · `MiseAJour.test.tsx` (6, statut + en-cours + Arrêter) + admin **19/19**.
- Captures Partie B : `captures-donnees-2/07`→`12` (statuts · abandonnés masqués · étape 2 en cours +
  Arrêter · reconstruction après bascule · q_v12 6/6 · retour arrière q_v11 6/6).
- ⚠ Piège branche (récurrent, cf. [[retours-7]]) : une session RETOURS-11 a `git checkout`é le dépôt
  partagé sur `fix/retours-11bcd` en cours de Partie B et **stashé** mon travail ; récupéré (`git stash
  apply`) sur `fix/donnees-2`, DB réparée (`build-mvt q_v11_m137`), recette rejouée. Branche
  `fix/donnees-2`, non mergée.
