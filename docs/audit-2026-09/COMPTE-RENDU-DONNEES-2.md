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
