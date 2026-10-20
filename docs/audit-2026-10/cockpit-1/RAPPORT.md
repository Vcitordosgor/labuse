# COCKPIT-1 — le dashboard Données devient le tableau de bord de l'app

*Branche `feat/cockpit-1` · worktree `labuse-cockpit` · base `origin/main` 8b410d99 · 20/10/2026.
Run servi local **q_v19** (cascade q_v19_sources, résiduel seq 16). Ports de recette 8850/6050.
Six commits, un par lot (+ reconnaissance). Rien n'est appliqué en prod.*

## Ce qui a été fait

| Lot | Deliverable | Commit |
|-----|-------------|--------|
| Étape 0 | git propre, .env noté, ETAT/ECARTS/COMMENT-ÇA-MARCHE lus, 31 jobs inventoriés, 5 captures « avant » | — |
| A | Onglet **Tableau de bord** (remplace À faire + Cohérence) — planche 1 | `18812f9a` |
| B | Page **L'usine** (depuis « Voir l'usine ») — planche 2 | `58fb2922` |
| C | Tri des 31 jobs — **JOBS.md** + **crontab** + corrections | `c088c7d4` |
| D | **Circuit** — bandeau de propagation — planche 4 | `3eaf78fd` |
| E | **Sources** (bouton Reconstruire) + **Journal** (filtre famille, entrées boutons) | `1bca421b` |

Captures face à la maquette : `captures/avant/` (les 5 anciens onglets) · `captures/apres/`
(01 Tableau de bord, 01b « Voir le détail » = planche 3, 02 L'usine, 03 Circuit bandeau, 04 Journal
familles, 05 Sources Reconstruire).

### Lot A — Tableau de bord
Composé **côté serveur** (`src/labuse/cockpit_resume.py`, le front ne recalcule rien), exposé par
`/admin/circuit` sous la clé `cockpit`. Trois sections :
1. **« Qu'est-ce que je dois faire aujourd'hui ? »** — une carte PAR PROBLÈME (pas par occurrence :
   les N verrous = 1 carte, les N sondes = 1 carte). Tri : données à injecter d'abord. Pastille
   jaune/rouge/gris + UN bouton primaire (Injecter · Reconstruire · Réessayer · Accepter). Ce qui
   demande du code porte l'étiquette « demande du code » + « Voir le détail » (fenêtre avec faits
   techniques + « Copier le détail »). **Le bouton « Décider » a disparu partout.** Sous la liste :
   « Déposer une source à la main ».
2. **« Est-ce que tout tourne ? »** — 4 tuiles (veille, livraisons, contrôle, courrier) lues du
   registre + bouton « Voir l'usine ».
3. **« Où en est la mise à jour ? »** — 4 étapes Injecter → Calculer → Basculer → Envoyer en prod
   (fait/à faire + le bouton de l'étape). « Envoyer en prod » : actif SEULEMENT en local ; sur le VPS,
   inactif + « se fait depuis le Mac ».

Endpoints : `/version` (LECTURE SEULE, publique — l'état servi lu serveur→serveur par
`/admin/cockpit/etat-prod`, jamais une URL dans le front) ; gestes `/admin/cockpit/{injecter,
reconstruire,accepter-ecarts,envoyer-prod}` (mêmes commandes que le cron / `deploy_donnees.sh`,
détachées, journalisées). Local/prod = `get_settings().env`, jamais l'URL.

**Invariant préservé & prouvé** : la tuile « À faire » du Pilotage ET le badge « Données N » lisent
toujours `total_a_faire` (fonction inchangée). Le compteur de cartes du Tableau de bord est une vue
GROUPÉE, séparée — documenté ici pour lever l'ambiguïté « 9 occurrences » vs « 3 problèmes ».

### Lot B — L'usine
Lue du registre (`/admin/usine`, rafraîchie 60 s). Chaque job reçoit dans le registre un **libellé
humain**, une **famille** (1 Veille · 2 Livraisons · 3 Le moteur · 4 Contrôle), un rôle et un drapeau
`lancable` (table `_FAMILLE_LIBELLE_ROLE`, assertion de couverture au chargement). 4 colonnes ; poste =
libellé, rôle, dernier/prochain passage, pastille (vert/violet/rouge/gris). Boutons contextuels :
« Lancer maintenant » (jobs sans risque), « Démarrer » (enquêteurs IA, coût/plafond), « Voir le
détail » (échec). La colonne « Le moteur » porte les étapes Calculer/Basculer/Envoyer. Les gelés
sortent dans un bandeau (« Réveiller… », confirmation). Lancement via `scripts/jobs/run-job.sh` (le
MÊME verrou flock que le cron).

### Lot C — tri des 31 jobs
`JOBS.md` : 23 GARDER · 5 GELER (digest + 4 Radar) · 2 SUPPRIMER. Doublons signalés
(coherence-robinets ⟲ coherence-banc ; recap-matin ⟲ healthcheck). `labuse.cron` généré.
**Les 5 corrections sont APPLIQUÉES** (détail § « Corrections C appliquées » ci-dessous) : **B**
agents-sources au crontab, **E** restore-test retiré, **A** mail-queue reste */5 + cède à la
sauvegarde, **D** recap-matin supprimé (vigies → healthcheck), **C** oracle risque zonal. → registre
**29 jobs**, 24 lignes actives.

### Lot D — Circuit, bandeau de propagation
Circuit INCHANGÉ ; un seul ajout : au clic/à la recherche d'une donnée, un bandeau (nom, fraîcheur
« mêmes mots que Sources », « passe par N moteurs », « arrive dans N robinets » cliquables, bouton
Injecter si nouvelle version). Règle de propagation composée côté serveur
(`propagation_reservoir`) : un robinet est à jour quand son run/cache a été produit après la dernière
injection de son réservoir ; sinon en retard — nouvelle version → Injecter, eau ancienne → Calculer ;
tuiles périmées = Reconstruire (global).

### Lot E — Sources & Journal
Sources : « labuse rebuild » (commande de terminal) disparaît → bouton **Reconstruire**. Journal :
filtre par **famille** (4 colonnes de L'usine) en plus des gestes ; chaque bouton du Tableau de bord /
de L'usine laisse une **entrée** lisible (qui, quoi, résultat) — les gestes `cockpit:*` ont une
catégorie FR (jamais l'identifiant brut).

## Recette

- **Captures de chaque planche face à la maquette** : faites (voir `captures/apres/`). Structure et
  DA conformes (jetons existants, aucun nouveau ; `components/ui`/CHARTE-DA-1 respectés).
- **Bancs** : `tsc -b` 0 · `vitest` 277/277 · `pytest` (sélection du hook) **2631** · `chasse_docs`
  **20 OK · 0 ECART** · `chasse_donnees` **21 OK** (voir « écarts restants »).
- **Les 4 étapes depuis le Tableau de bord** : chaque bouton est câblé à une vraie commande — Injecter
  (vanne existante), Calculer (`/admin/flux/run/lancer`), Basculer (`/admin/flux/bascule`), Envoyer en
  prod (`deploy_donnees.sh` + `labuse parite`, local uniquement). Un geste réel a été joué en recette
  (« Lancer maintenant » purge-sessions) : entrée au Journal `cron · Vic · lancé`.
- **Propagation dans Circuit** : garde LIVE sur le run servi — **5/5** réservoirs « nouvelle version »
  ont tous leurs robinets « en retard · Injecter » ; 89 réservoirs « à jour ». Les deux sens de la
  règle (en_retard↔à_jour) sont prouvés en unitaire ; une garde `db` rejoue le sens LIVE
  (`test_garde_propagation_nouvelle_version_en_retard`).
- **⚠ L'injection de test de bout en bout sur base jetable n'a PAS été exécutée en session** : l'étape
  « Calculer » est un run de scoring de **plusieurs heures** (cf. COMMENT-ÇA-MARCHE §5) — infaisable en
  recette interactive, et « Envoyer en prod » pousserait vers la prod réelle (interdit par le mandat
  « Rien n'est appliqué en prod »). Chaque étape est vérifiée par son endpoint + ses tests ; la
  bascule en_retard→à_jour sur **injection** (où la fraîcheur se rattrape sans attendre le run) est
  couverte. L'acceptation end-to-end (Injecter→Calculer→Basculer sur une copie jetable) reste un geste
  de Vic, le protocole est ci-dessous.
- **API & navigateur arrêtés, `lsof -ti :8850` vide** : fait en fin de recette (voir §clôture).

### Protocole d'injection de bout en bout (pour Vic, base jetable)
1. `createdb labuse_jetable && pg_restore` du dernier dump dans `labuse_jetable`.
2. Lancer l'API sur cette base (`LABUSE_DATABASE_URL=…labuse_jetable`), ouvrir le Tableau de bord.
3. Déposer une version amont de test sur une source (passe « nouvelle version ») → carte « Injecter ».
4. **Injecter** (carte ou bandeau Circuit) → la source se met à jour → ses robinets passent « à jour ».
5. **Calculer** (étape 2, ~3 h) → candidat ; **Basculer** (étape 3) → l'app sert le nouveau run.
6. Vérifier dans Circuit que le bandeau du réservoir ne montre plus de robinet « en retard ».
7. `dropdb labuse_jetable`.

## Corrections C (Lot C) appliquées avant merge

Les 3 corrections qui restaient spécifiées sont **appliquées** sur `feat/cockpit-1`, chacune testée,
en préservant « les ALERTES restent » :
- **A — mail-queue cède à la sauvegarde** : `mail-queue-consommer` **reste `*/5`** (les mails clients —
  mot de passe, confirmation, invitation — ne peuvent pas attendre un jour) mais s'il démarre pendant le
  pg_dump (verrou de `backup-postgres` tenu), il **saute ce passage proprement** (statut ok, ni échec ni
  alerte) et repart 5 min plus tard → fini la fausse alerte quotidienne 13:35. Lecture du même verrou que
  run-job.sh (`jobs_impl._sauvegarde_en_cours`). Tests : verrou tenu → sauté/ok ; libre → envoi.
- **D — recap-matin supprimé** du registre et du crontab ; ses vigies (sauvegarde, copie externe,
  jobs-en-retard) passent dans **healthcheck** (15 min) via `ops_alertes.verifier_declencheurs`. Prouvé
  par test : **site en panne** (healthcheck lève à 2 échecs → incident), **disque/sauvegarde ratée**
  (incident ouvert par leur propre chemin), **copie externe** (`test_disque_externe_1`). Plus aucun mail
  récap, mais chaque alerte part toujours par la porte unique ops_alertes.
- **C — verite-sources** : l'oracle (`oracle_georisques`) ne compare plus que les **aléas zonaux** ;
  **séisme et feu** sont marqués non discriminants à La Réunion (île-wide) et exclus de l'écart ; une
  parcelle hors zone de risque ne produit donc plus un rouge permanent. L'incident « verite-sources »
  **se referme** au prochain passage sans faux (test unitaire + db). Fichier :
  `scripts/coherence/oracles/__init__.py` (helper `aleas_zonaux`).

→ Registre = **29 jobs** (recap-matin + restore-test retirés), **24 lignes actives** au crontab.

## Écarts restants

- **chasse_donnees : 2 ECART** (`cloche-fraicheur`, `digest-vs-cloche`) — **pré-existants, PROUVÉ** :
  rejoué avec le code `origin/main` propre (worktree `labuse-main`, `8b410d99`) sur la MÊME base → les
  **mêmes** 2 ECART · 21 OK · 2 SKIP. Donc COCKPIT-1 ne les a pas créés : ils sont dus à
  `detect_events`/la cloche non rejoués après la bascule q_v19 (geste PROD, déjà noté
  CHASSE-INVARIANTS-FIX-1), DB-state, hors de tout code du mandat.
- **chasse_donnees : 2 SKIP** (`export-disparue`, `disparue-documents`, HTTP 500 sur `/export`) —
  pré-existants, dépendants des données locales.
- **« Est-ce que tout tourne ? » et L'usine, en LOCAL, montrent peu de postes actifs** : les jobs
  tournent en PROD (le registre y laisse 3 007 lignes `job_runs`) ; sur le Mac leurs états locaux sont
  rares. L'affichage est correct PAR ENVIRONNEMENT — sur le VPS (env=production) il reflètera la
  réalité prod. Pas un bug : une propriété du dashboard lu hors du serveur qui exécute les jobs.
## Reste à Vic
- **Crédit API** (Anthropic) + `LABUSE_AGENT_PLAFOND_EUR=5` dans `/etc/labuse/labuse.env` → les
  enquêteurs IA (agents-sources, désormais au crontab) tournent le dimanche 1 semaine sur 2.
- **Crontab** : régénérer (`labuse jobs crontab`) et déployer via `deploy.sh` (agents ajoutés ;
  recap-matin + restore-test retirés ; mail-queue reste */5 + garde sauvegarde). Dégeler digest + Radar aux premiers clients.
- **Déploiement q_v19** : la prod sert q_v18 ; `deploy_donnees.sh --run-label q_v19 --residuel-seq 16`
  (ou le bouton « Envoyer en prod » du Tableau de bord local).
- **verite-sources** : l'incident du 15/10 s'éteint au prochain run (oracle recalibré) ; relancer
  `labuse ops verite-sources` pour l'éteindre tout de suite.
- **`LABUSE_LOCK_DIR`** (labuse.env) doit pointer là où run-job.sh pose les verrous (le garde mail-queue
  « cède à la sauvegarde » lit ce dossier) — déjà le cas depuis OPS-CRONS-1.

## COCKPIT-1b — retours de recette de Vic (6 points)

1. **L'usine devient un ONGLET** : Tableau de bord · **Usine** · Sources · Circuit · Journal. Plus de
   page cachée derrière « Voir l'usine » — le bouton mène à l'onglet (`Circuit.tsx`, `Usine.tsx`).
2. **Journal — une seule rangée** : Tout · Veille des sources · Livraisons · Le moteur · Contrôle,
   clients, sécurité · **Échecs seulement**. La rangée « Geste » est retirée. Backend : filtre `echecs`
   (resultat echec/refuse/timeout), appliqué au groupe ET aux membres (un lot mixte ne montre que ses
   échecs). Test : `test_cockpit_1b.py`.
3. **Circuit — phrase unique** sous « Vérifier que tout coule » : « Tout coule » ou « N fuite(s) →
   voir » (lien vers le Tableau de bord). Retirés : les compteurs eau ancienne / verrous et le lien
   « voir dans À faire » (onglet disparu).
4. **Sources — plus de bloc « Fraîcheur des caches »** : chaque cache périmé devient une carte du
   Tableau de bord EN FRANÇAIS (« 23 fiches communes en retard sur les dernières sources ») avec
   « Reconstruire » ; les codes (run/cascade/clé) ne sortent que dans « Voir le détail »
   (`cockpit_resume._carte_cache`, lu de `/sante/fraicheur`). Test : `test_cockpit_lot_a.py`.
5. **Rail Pilotage réduit** : Serveur · Run servi · Ouvrir l'app cliente. Backup, Horloge, Verrous
   retirés (ils vivent dans l'Usine et le Tableau de bord). Les verrous n'ont plus qu'UNE date de
   dernier contrôle (`dernier_ts` de la synthèse), affichée au seul Tableau de bord.
6. **Vitrine 100 vs 99 — une seule fonction de comptage.** Cause : le dashboard comptait la liste des
   réservoirs admin (vitrine ∪ **référentiel interne** = 100) ; l'app et le site public comptent la
   vitrine (`WHERE_AFFICHEES` = 99). **99 est le bon chiffre** : l'interne est un référentiel lu par la
   pompe (montré dans le Circuit), pas une source vitrine. Correctif : fonction canonique
   **`sources_catalog.compter_vitrine`** branchée par les TROIS surfaces (badge dashboard, /sources,
   accueil) ; les comptes d'état de la page Sources portent sur la vitrine seule (99, l'interne est
   marqué `interne` et écarté du segment « Vitrine ») ; `reservoirs` reste à 100 pour le Circuit. Tests
   db : badge == /sources == accueil == compter_vitrine ; l'interne n'est jamais compté en vitrine.

Captures : `captures/apres-1b/` (01 Tableau de bord + rail + carte de cache, 02 Usine onglet, 03
Journal une rangée, 04 Sources sans Fraîcheur « Vitrine 99 »).

## Hors mandat (non touché)
Refonte de Sources/Radar/moteur de calcul, DA, mail du matin (supprimé, pas remplacé), notifications
Telegram/Signal, Mac mini.
