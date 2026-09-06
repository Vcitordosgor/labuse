# COMPTE-RENDU — CIRCUIT-P (la page Circuit en trois onglets)

Branche : `feat/circuit-page` · worktree `~/Desktop/labuse-audit` · créée depuis `main`
(`feat/circuit-3` y est mergée : `git merge-base --is-ancestor feat/circuit-3 main` = vrai,
main = `dc966d5`). Rien n'est mergé. Référence visuelle : `docs/CIRCUIT/maquette-circuit-v8.html`
(validée par Vic le 06/09/2026). Référence des données : le registre + le manifeste + la sonde +
les filtres + le journal de CIRCUIT-1 à 3.

Reprise : « continue CIRCUIT-P depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-P.md ».

## État au départ (étape 0)

- pwd propre, `feat/circuit-3` clos (`COMPTE-RENDU-CIRCUIT-3.md` présent, DoD atteinte).
- Suite backend circuit de départ : verte (`test_circuit1_lot5/lot8`, `circuit2_lot5`,
  `circuit3_lot5` = 19 passed). Vitest de départ : **164 passed / 36 fichiers**.
- L'ancien `Circuit.tsx` (CIRCUIT-1 lot 5, étendu 2/3) : bandeau à pastilles + trois colonnes +
  tiroir du bas + tuyaux SVG. Tout ce qu'il sait afficher est repris, réorganisé (lots 2→6).

## Divergences maquette ↔ données (tranchées, écrites)

- **10 familles d'affichage, pas 9.** Le mandat dit « neuf blocs » ; la maquette validée en montre
  **dix** (+ « LABUSE interne »). La `category` de `data_sources` est fine (28 valeurs) ; on la
  range en familles lisibles par `FAMILLE_DE_CATEGORIE` (option la plus sûre : suivre la maquette
  validée). Les blocs famille sont rendus **dynamiquement** depuis le backend, jamais codés en dur.
- **États sans donnée live.** La maquette a des états qu'aucune donnée ne porte encore :
  `écart à la règle` / `choix LABUSE` (CIRCUIT-4, chiffres × règles), `horloge qui ment`
  (détecteur de cron menteur), `agent en route` (transitoire). La **grammaire** (couleur + libellé)
  et la **mécanique** du résumé sont posées et **testées** (fixtures synthétiques) ; en live ces
  lignes sortent à **0** — aucun faux positif. Accroches pour CIRCUIT-4 : `circuit_resume.composer`
  accepte `regles_ecart`, `regles_choix`, `horloges` ; `circuit_etats.etat_robinet` lit
  `ecart_regle_robinets` / `choix_robinets` dans son `ctx`.
- **`à vérifier (cadence dépassée)`** : le vrai drapeau `a_verifier` n'existe pas dans la maquette.
  Ajouté en **ambre** (« à regarder »), dans la même grammaire, + une ligne de résumé « réservoirs
  à revérifier » (verbe « Vérifier »).
- **« hors moteur »** : la maquette parle de `sql_propre`/`front` ; les vrais préfixes de `calcul`
  sont `moteur` / `passe_plat` / `constante`. « Hors moteur » = `passe_plat` (un chemin unique, pas
  de moteur nommé). `constante` est délibéré, jamais compté.
- **Identifiants d'URL** : un réservoir = `id` **numérique** (`data_sources.id`), un robinet = son
  slug de registre (chaîne), la pompe = sans id. Les deep-links (lot 4) : `#reservoir/42`,
  `#robinet/fiche_parcelle`, `#pompe` (la maquette illustrait avec un slug de réservoir ; le réel
  est numérique).
- **Pont nom → slug de réservoir** : `data_sources` n'a pas le slug du registre. On le retrouve par
  le nom via `NOM_VERS_SLUG` (généré depuis `reservoirs.csv`, l'inventaire validé). Un réservoir
  absent du pont « s'allume seul » (comportement d'avant, sans erreur).

## Lot 1 — Les données de la page ✅ (commit `CIRCUIT-P lot 1`)

**Fait, testé, poussé.**

- **1.4 — la fonction d'état UNIQUE** : `src/labuse/circuit_etats.py`. `etat_reservoir(r)` et
  `etat_robinet(rob, ctx)` rendent `(couleur, libellé court)` — transposition fidèle de
  `tankEtat` / `tapEtat` de la v8. Cinq couleurs, une par sens. Porte aussi les deux regroupements
  d'affichage (familles + catégories, dans l'ordre de la maquette) et le pont nom→slug.
  **Un test par branche** (11 cas réservoir, 7 cas robinet).
- **1.1 — le résumé côté serveur** : `src/labuse/circuit_resume.py::composer()`. Trois groupes
  ordonnés, chaque ligne = `{n, couleur, titre, phrase, verbe, cible:{type, ids}}`, + quatre
  repères. **Un test par ligne possible** (quarantaine, réservoir plein, eau nouvelle, eau
  ancienne, jamais vérifiés, à revérifier, fuites, écarts règle, horloge, filtres KO, hors moteur,
  choix LABUSE, cadences). Zéro problème → `total = 0` (le front dira « Tout coule. »).
- **`GET /admin/circuit`** enrichi : chaque réservoir porte `etat`, `slug`, `taps` (robinets qu'il
  alimente), `chiffres_ids` ; chaque robinet porte `etat`, `hors_moteur` ; + `familles` et
  `categories` (groupées, ordonnées) + `resume` + `candidat`. Le front ne recalcule rien. Les clés
  d'origine sont conservées (l'ancien rendu tient jusqu'au lot 6).
- **1.2 — `GET /admin/circuit/journal?type=&depuis=&page=&taille=`** : `circuit_journal` porte
  DÉJÀ, en une table, la sonde/les contrôles (`job`), les filtres (`filtre`), les agents (`agent`),
  les crons qui touchent l'eau (`job`, par « cron ») et les gestes humains — une seule source
  suffit. Filtrable, paginé, le « qui » toujours présent (null → « système »).
- **1.3 — `GET /admin/circuit/reservoir/{id}` · `/robinet/{id}` · `/pompe`** : un appel focalisé
  chacun, **< 500 ms mesuré** (assertion dans le test). Réservoir : versions/filtre/veille + ce
  qu'il alimente + rapport d'agent. Robinet : fuites/eau ancienne en tête + chiffres (badges
  moteur/hors-moteur, tampon) + alimenté par + dernier contrôle. Pompe : run servi/candidat +
  résiduel + moteurs + pointeurs (alerte si multiples) + horloges (`TOUCHE_EAU`, 13).
- Refactor propre : la construction d'un réservoir est extraite en
  `dashboard._assembler_reservoirs(c, only_id=None)` — une seule vérité, partagée par l'endpoint et
  les pages de détail.

**Tests** : `tests/test_circuit_p_lot1.py` — 25 passed (21 unitaires + 4 DB). Existants circuit :
19 passed (aucune régression).

## Lot 2 — Résumé et onglets ✅ (commit `CIRCUIT-P lot 2`)

- Nouveau dossier `frontend/src/components/admin/circuit/` :
  - `style.ts` — la feuille de style, **portée fidèlement** de la v8, scopée sous `.cxp` ; cinq
    couleurs d'état, `--jaune` réservé au focus clavier ; `@media` réduit sans barre horizontale.
  - `types.ts` — les types du payload + `focusDeCible()` (une seule cible → détail ; plusieurs →
    groupe déplié).
  - `Resume.tsx` — rend le bloc `resume` serveur : titre (`N choses à regarder` ou « Tout coule. »),
    quatre repères, trois groupes, ligne de fin. Chaque ligne appelle `onCible`.
  - `Circuit.tsx` — **le conteneur** : trois onglets (Résumé par défaut, Circuit, Journal) + deux
    boutons à droite (« Envoyer les agents sur tout » — gardé désactivé, geste existant en attente
    de crédit API ; « Vérifier que tout coule » — geste réel `postAdminCircuitVerifier`). Les deux
    basculent sur l'onglet Circuit (2.2). Une ligne du Résumé pose le `focus` et bascule sur Circuit.
- `Donnees.tsx` importe désormais `./circuit/Circuit` (l'ancien `admin/Circuit.tsx` n'est plus
  référencé ; il est retiré au lot 6).
- Onglets Circuit / Journal : marqueurs « lot 3 / lot 5 » en attendant leur contenu (branche verte).
- **Test vitest** `Resume.test.tsx` (2.3) : zéro problème → « Tout coule. » (+ un « Rien. » par
  groupe) ; chaque type de ligne rend son verbe et clique vers sa cible. tsc vert.
- Vitest : **166 passed** (164 + 2). tsc : vert.

## Lot 3 — Le circuit par familles ✅ (commit `CIRCUIT-P lot 3`)

- `circuit/diagram.ts` — la logique **sans le DOM** (donc testable) : `koTank`/`koTap`,
  `construireMaps` (famille d'un réservoir, robinets→réservoirs), `nbConduits` (= familles +
  catégories + 2), `cheminsAllumes` (survol → familles + catégories du chemin).
- `circuit/CircuitDiagram.tsx` — blocs famille (gauche) / catégorie (droite) + pompe au centre ;
  pastilles (une par élément, colorée hors mint) + « n à regarder » / « tout va bien » ; accordéon
  **un bloc ouvert par colonne** ; deux lignes par élément (nom ; version · contrôle · cadence),
  **aucun nom tronqué** ; interrupteur « Ne montrer que ce qui cloche » (ON par défaut) ; recherche
  qui déplie les blocs contenant un résultat ; **survol** allume le chemin (famille → pompe →
  catégories) et estompe le reste. **Tuyaux SVG** : un stub par bloc + le collecteur→pompe et le
  distributeur→pompe **d'un seul trait chacun** → exactement `familles + catégories + 2` (règle
  3.3). Fuites en pointillé rouge, agrégées une par couple famille↔catégorie (famille retrouvée via
  `chiffre.reservoirs` → slug → famille). Redessin sur `resize` / `scroll` / `ResizeObserver` /
  dépliage.
- **La pompe** (3.2) : bloc collant, run servi + candidat, ce qui attend (résiduel), alerte rouge
  « N pointeurs de run au lieu d'un » tant que le manifeste n'est pas seul.
- Conteneur `Circuit.tsx` : gère `detail` (ouvert au clic d'une ligne — page au lot 4) et `groupe`
  (déplié depuis une ligne du Résumé à cibles multiples). Le clic sur une ligne / la pompe appelle
  `onOpen` (détail).
- **Test vitest** `CircuitDiagram.test.tsx` (3.3) : tuyaux = familles + catégories + 2 ; survol d'un
  réservoir/robinet allume les bons blocs (fixture de deux réservoirs) ; règles ko.
- Vitest : **170 passed** (+4). tsc : vert.

## Lot 4 — Les pages de détail ✅ (commit `CIRCUIT-P lot 4`)

- `circuit/Detail.tsx` — une PAGE (pas un tiroir) qui remplace le dessin, alimentée par les
  endpoints 1.3 (`useQuery` par `circuit-detail`). Trois variantes conformes à la v8 :
  - **Réservoir** : Versions (dans le réservoir / chez le producteur / dernier contrôle) ; gestes
    (Envoyer un agent — gardé désactivé, en attente crédit API ; Ouvrir la vanne = `injecter` ;
    Servir quand même / Revenir à la précédente si quarantaine) ; Filtre à l'entrée (verdict +
    contrôles) ; Rapport de l'agent ; « Ce qu'il alimente » (chips robinets) ; « Les chiffres qu'il
    nourrit ».
  - **Robinet** : fuites (deux valeurs face-à-face + cause) et eau ancienne EN TÊTE ; « Ce qu'il
    affiche » (badges moteur / hors moteur, portée run) ; « Alimenté par » (chips réservoirs) ;
    dernier contrôle. Emplacement « La règle derrière ces calculs » réservé (accroche CIRCUIT-4).
  - **Pompe** : ce qui attend (résiduel / candidat / précédent / pointeurs) ; gestes (Faire tourner
    = calculer, Basculer — **gaté par la lecture de la note de version**, Revenir) ; note de version ;
    moteurs ; horloges qui touchent l'eau.
- **Retour** par bouton « ← Retour au circuit » ET par **Échap** (listener clavier).
- **Deep-link** (4.1) : `circuit/hash.ts` (`parseCx`/`ecrireCx`) porte l'élément ouvert dans le hash
  `#…&cx=reservoir:42` (namespacé, **fusionné** sans écraser les filtres de l'app cliente). Lu au
  montage + sur `hashchange` ; écrit en `replaceState` à l'ouverture/fermeture. La navigation interne
  (journal, chips) passe par callbacks, jamais par le hash.
- **Chips navigables** (4.2) : « alimente » → robinet, « alimenté par » → réservoir (slug→id résolu
  via `data.reservoirs`), couleur = l'état de la cible.
- **Test vitest** `Detail.test.tsx` : parse/écrit `cx` sans écraser les autres paramètres ; rend
  nom/état/chip/bouton vanne ; retour + Échap ferment ; chip navigue. Vitest : **173 passed** (+3).

## Lot 5 — Le journal ✅ (commit `CIRCUIT-P lot 5`)

- `circuit/Journal.tsx` — tableau (quand · geste · cible · par · résultat) alimenté par
  `/admin/circuit/journal`. Filtres par type de geste avec **« tous » en premier à gauche** (filtre
  de journal, pas groupe de tri). Pagination simple (← / →, page X/Y, total). Couleur du point =
  résultat (ok mint, dry-run/lancé ambre, échec/refus rouge). **Une ligne dont la cible existe est
  un lien** vers sa page de détail (5.1) : cible résolue en réservoir (par nom/slug) ou robinet (par
  id/nom) via `data`.
- **Compteur de l'onglet** (5.2) : le Journal remonte `aujourdhui` au conteneur (`onAujourdhui`), qui
  affiche « aujourd'hui · N ».
- **Test vitest** `Journal.test.tsx` : tableau rendu, « tous » en premier, compteur du jour remonté,
  ligne → détail, filtre relance la requête. Vitest : **176 passed** (+3). tsc vert.

## Lot 6 — Recette navigateur + retrait de l'ancien rendu ✅ (commit `CIRCUIT-P lot 6`)

- **6.2 — ancien rendu retiré** : `frontend/src/components/admin/Circuit.tsx` (bandeau à pastilles +
  tiroir du bas + colonnes exhaustives) **supprimé** ; plus aucun composant mort (aucun import). Le
  store `tracage` vit ailleurs (`lib/trace.tsx`), intact. **Snapshots** vitest de chaque onglet :
  `onglets.snapshot.test.tsx` (Résumé, Circuit, Journal). Vitest : **179 passed**. tsc vert.
- **6.1 — recette navigateur (jouée)** : `qa/circuit_p_captures.mjs` rend la VRAIE page
  (`frontend/circuit-harness.html` + `src/circuit-harness.tsx`) avec l'API interceptée par des
  **fixtures réelles** de la base (`qa/fixtures/circuit_p/`) — zéro base touchée. 11 captures
  numérotées dans `RECETTE-CIRCUIT-P/` couvrant le parcours 6.1 : Résumé → clic de chaque type de
  ligne (détail + groupe) → retour → circuit déplié → **survol (chemins allumés, vérifié à l'œil :
  vert inverse + tuyau vert)** → journal filtré, + gestes de la pompe et « Vérifier ». Regardées :
  la DA est fidèle à la v8 (trois onglets, deux boutons, cinq couleurs, aucune barre horizontale,
  aucun nom tronqué). Rejeu : `README.md` du dossier.
- **6.1 — gestes réels (rejouable)** : `qa/circuit_p_recette.mjs` rejoue vanne → calcul → note →
  bascule → vérifier → **revenir** sur une app bootée (base réelle), avec vérification de
  restauration du run de départ — comme le lot 5 de CIRCUIT-1. Non joué ici (nécessite une app
  bootée `PYTHONPATH=src` ; l'env conda importe un `labuse` installé SANS les endpoints CIRCUIT-P —
  piège noté). Les gestes appellent les **mêmes endpoints** déjà éprouvés par la recette CIRCUIT-1
  et couverts par les tests backend ; seule la coquille d'UI a changé (gestes en pages de détail).
- **6.3 — accroches CIRCUIT-4** (points d'accroche exacts) :
  - Badge « La règle derrière ces calculs » du robinet → `Detail.tsx`, `DetailRobinet`, emplacement
    marqué par le commentaire `{/* CIRCUIT-4 (accroche) … */}` après le bloc « Ce qu'il affiche ».
  - Ligne « écarts à la règle » du Résumé → `circuit_resume.composer(regles_ecart=…)` (déjà câblée,
    0 live) ; état `écart à la règle` du robinet → `circuit_etats.etat_robinet` via
    `ctx['ecart_regle_robinets']` ; « choix LABUSE » → `regles_choix` / `ctx['choix_robinets']`.
  - Il suffira à CIRCUIT-4 de calculer, côté endpoint `/admin/circuit`, les ensembles
    `ecart_regle_robinets` / `choix_robinets` (chiffre × règle) et de les passer à `composer(...)` et
    au `ctx` d'`etat_robinet` ; le front les rend déjà.

## Définition de fini — atteinte

- Trois onglets ✅ · Résumé calculé côté serveur ✅ · chaque ligne mène quelque part (détail ou
  circuit déplié) ✅ · le circuit se lit par familles ✅ · le détail est une page (retour + Échap +
  deep-link) ✅ · le journal est filtrable + paginé ✅.
- Aucune barre horizontale · cinq couleurs seulement · aucun nom tronqué (vérifié captures) ✅.
- Recette jouée avec 11 captures · ancien rendu retiré · suites vertes · **rien mergé** ✅.

## Bilan des suites

- Backend : `test_circuit_p_lot1.py` 25 passed + circuit 1/2/3 = **44 passed** (0 régression).
- Frontend : **179 vitest passed** (départ 164 : +15 dont 3 snapshots), **tsc vert**.
- Commits (7, non mergés) : mandat+maquette · lot 1 · lot 2 · lot 3 · lot 4 · lot 5 · lot 6.

## Ce qui reste à Vic

Ouvrir la page, cliquer partout cinq minutes, dire ce qui gêne. Merger. « Ne merge pas » respecté.

## Accroches pour CIRCUIT-4 (lot 6.3, à confirmer au fil)

- Badges de règle du robinet → `Detail.tsx` (bloc « La règle derrière ces calculs »).
- Ligne « écarts à la règle » du Résumé → `circuit_resume.composer(regles_ecart=…)` ; l'état
  `écart à la règle` du robinet → `etat_robinet(ctx={ecart_regle_robinets})`.

---

# P2 — retours de recette du 06/09 (mandat MANDAT-CIRCUIT-P2.md)

Branche : `feat/circuit-page` (la même), worktree `~/Desktop/labuse-audit`. Rien n'est mergé.
Reprise : « continue CIRCUIT-P2 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-P.md ».
Commits (non mergés, un par lot) : mandat · lot 1 · lot 2 · lot 3 · lot 4 · lot 5.

## Décisions appliquées (Vic + Fable, 06/09) — sans les rediscuter
- La page **Données = le Circuit** : l'enrobage a disparu, le Catalogue n'existe plus, le CRON est
  reparti dans Pilotage. Un `passe_plat` est **neutre** (« hors moteur » = `sql_propre`/`front`
  seulement). Un **seul nombre de réservoirs partout**, calculé (68 en prod ; 82 sur la base de test).

## Lot 1 — Le ménage ✅ (commit « CIRCUIT-P2 lot 1 »)
- `Donnees.tsx` ne rend plus que `<CircuitSection/>`. Tout l'enrobage supprimé : bandeau « Mes
  données sont-elles à jour ? », ligne run/garde/surfaces, onglets Catalogue/CRON, paragraphes
  « Qui fait quoi » et « Les autres onglets sont des vues ». `grep` vide sur ces libellés (hors
  commentaires documentant le retrait).
- **Catalogue retiré** : `admin/Sources.tsx` (`Catalogue`/`SourcesSection`) + `Sources.veille.test.tsx`
  **supprimés** (code + test morts, plus aucun import). La **page Sources côté client**
  (`components/sources/SourcesPage.tsx`) reste intacte.
- **CRON hors Données** : `_rediriger` ne renvoie plus `cron` vers `donnees` ; `cron` redevient une
  page (CronSection inchangée) au rendu de l'admin, son **lien vit dans Pilotage** (« Horloge — les
  jobs planifiés (CRON) → »). `/admin/cron` inchangé.
- Onglet **« Journal »** sans « aujourd'hui · N » : le compteur du jour vit dans l'onglet, en petit,
  seulement s'il est > 0 (`Journal 78`).
- Snapshot vitest `Donnees.test.tsx` : un seul composant racine (`.cxp`), sans enrobage.

## Lot 2 — Les nombres ✅ (commit « CIRCUIT-P2 lot 2 »)
- `circuit_etats` : `passe_plat` **neutre** ; `HORS_MOTEUR_PREFIXES = (sql_propre, front)` +
  `est_hors_moteur()` ; `hors_moteur_de` recompté (0 live attendu depuis CIRCUIT-2). Test mis à jour.
- **`circuit_etats.compteurs()`** : la fonction UNIQUE des nombres — réservoirs + partition
  (à jour / à regarder / vides), **invariant testé `a_jour + a_regarder + vides = réservoirs`**,
  robinets. Le Résumé (kpis), l'en-tête de colonne du Circuit, la ligne de fin et l'en-tête
  « Robinets » LISENT cette fonction (plus de recalcul au front).
- Les lignes du Résumé sont dérivées du **libellé d'état** (source unique) : un réservoir = un état
  = une ligne ; ajout de la ligne « producteurs injoignables » (réciprocité). Test 2.4
  (`test_resume_circuit_coherents`) : chaque ligne pointe des « à regarder », et chaque « à
  regarder » a sa ligne (aller-retour).
- **`GET /admin/circuit/compteur`** + front `DetailCompteur` : le repère « N / 68 » (cliquable)
  ouvre la page — réservoirs par état, **définition « à jour et vérifiés »** (2.3), et « N lignes en
  base non servies » (retirées/doublons/hubs dormants).
- Détail robinet : tag **passe-plat neutre**, « hors moteur » (ambre) réservé à `sql_propre`/`front`.
- **Nombres non codés en dur** (68/130/11 = valeurs live) : tout est calculé — décision écrite ici,
  la base de test montre 82/130/10, la prod montrera 68/130/11.

## Lot 3 — Les commandes qui répondent ✅ (commit « CIRCUIT-P2 lot 3 »)
- **Interrupteur « Ne montrer que ce qui cloche »** : il filtrait déjà ; prouvé par test vitest
  (fixture 3 réservoirs, ON=2 lignes / OFF=3), et le **titre de colonne** lit désormais les
  compteurs → identique dans les deux positions (« 82, 72 à regarder »).
- **`circuit_taches.py`** : état/progression **file-based** (cross-worker, comme `run_progress`) des
  tâches longues (`verifier`, `agents`) + `reservoirs_en_route()`.
- **« Vérifier que tout coule »** : tâche détachée (`sonde_circuit.controle` + callback `progres`) ;
  le bouton passe « Contrôle en cours… » (désactivé), une **ligne de progression** apparaît sous les
  onglets (« Eau ancienne — 3 / 5 »), **reste visible en changeant d'onglet** (elle vit dans le
  conteneur), à la fin le **Résumé se rafraîchit seul**, un **message** dit le résultat, une ligne
  entre au journal (geste « contrôle », avec qui).
- **« Envoyer les agents »** (et « Envoyer un agent » en détail) : **jamais grisé sans mot**. Trois
  cas — sans crédit API (`ai.core.has_key`) → message « Crédit API épuisé — recharge, puis
  relance. », rien lancé ; en cours → « k / n agents revenus » + état **mauve « agent en route »**
  par réservoir dans le Circuit + Résumé (ligne « agents en route ») rafraîchis ; normal → agents
  sur les réservoirs dont le **contrôle manque** (jamais vérifié / à vérifier / injoignable, pas les
  68), journal alimenté. L'action concrète par réservoir : la **sonde amont réelle** (sentinelle) —
  décision écrite : l'agent LLM (crédit) viendra sur ce point d'accroche, la substance déterministe
  (aller lire chez le producteur) est déjà là ; un réservoir sans sonde amont journalise
  « sans_sonde » (agent LLM requis).
- Tests : `circuit_taches` (cycle, en_route), vérifier (tâche + journal), agents sans/avec crédit,
  mauve peint par `en_route`. Les gestes pré-existants (vanne/calcul/bascule/revenir/servir) écrivent
  déjà leur ligne de journal avec « qui » (code vérifié) et sont rejoués par la recette CIRCUIT-1.

## Lot 4 — Le journal lisible ✅ (commit « CIRCUIT-P2 lot 4 »)
- `circuit_journal` : colonne **`lot`** (passage groupé) + ALTER idempotent ; **catégories FR en
  ordre fixe** (vanne·calcul·bascule·agent·contrôle·filtre·sonde·cron), `GESTE_CATEGORIE`, `par_nom`
  (`cli`→système, `admin`→Vic, noms propres gardés), `nouveau_lot()`.
- Les batchs marquent un `lot` : `filtre toutes` (CLI) et la volée d'agents.
- **`GET /admin/circuit/journal` réécrit** : groupe par `lot` — un job de filtres sur N sources ou
  une volée d'agents tient sur **une ligne dépliable** (« filtre · 5 cibles · 3 ok, 1 avertissements,
  1 quarantaine · système »), un geste isolé reste une ligne. La cible porte son **nom affiché**
  (jamais l'identifiant technique), cliquable → détail. Filtre par **catégorie**, **50 lignes
  groupées/page**, Précédent/Suivant.
- `Journal.tsx` : filtres de catégorie (tous d'abord, présents même vides), lignes groupées
  dépliables, cibles cliquables par nom.
- Tests : mappings purs (catégories, `par_nom`), endpoint groupé + isolé + filtre (DB), `Journal.tsx`.

## Lot 5 — Vérification de bout en bout ✅ (commit « CIRCUIT-P2 lot 5 »)
- **5.2** `test_circuit_p2_lot5.py` : parcourt TOUS les endpoints — `/admin/circuit`, `/compteur`,
  `/journal`, `/pompe`, `/taches`, la page de détail de **chaque** réservoir (82) et **chaque**
  robinet (130) — chacun 200, sans erreur, **< 1 s**. + « un seul nombre de réservoirs partout ».
- **5.1** recette navigateur `qa/circuit_p2_captures.mjs` (fixtures réelles `qa/fixtures/circuit_p2`,
  **zéro base touchée**), **13 captures P2-01→P2-13** dans `RECETTE-CIRCUIT-P/` : Résumé sans
  enrobage → repère 31/68 → compteur → Circuit (interrupteur 2 positions) → Vérifier (progression →
  message) → Agents sans crédit → détail réservoir/robinet/pompe (+ Échap) → journal groupé
  (dépliage, filtre vide). **Regardées** : conformes ; le journal groupé, la progression, le message
  de crédit et le compteur unique s'affichent comme demandé.

## Bilan des suites
- Backend circuit : **71 passed** (`test_circuit_p2_lot2/3/4/5` neufs + circuit 1/2/3/P, 0 régression) ;
  modules liés (filtres/sentinelle/flux/bascule) 57 passed.
- Frontend : **173 vitest passed**, **tsc vert**.
- Pré-existant hors mandat : `test_non_contradiction.py` échoue en COLLECTION (WeasyPrint
  `libgobject` — contourné par `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`), sans rapport.

## Décisions prises en autonomie (récapitulatif)
1. **Nombres calculés, jamais codés en dur** — 68/130/11 sont des valeurs live ; le code calcule
   (base de test = 82/130/10). Un seul compteur nourrit tout.
2. **Catalogue supprimé** (code + test admin morts) — la page Sources CLIENT reste ; la couverture
   veille du catalogue admin est retirée (composant disparu).
3. **CRON** : redevient une page d'admin à part (rendue au clic d'un lien Pilotage), pas dans le rail
   — le mandat dit « son lien va dans Pilotage », pas « ajoute-le au menu ».
4. **Agents = sonde amont réelle** par réservoir (substance déterministe), gatés par `has_key()`
   comme demandé ; l'agent LLM branchera sur ce point quand le crédit sera là (sources sans sonde →
   « sans_sonde », journalisé).
5. **Progression du contrôle = par PHASE** (Robinets/Chemins/Neuf/Catégorielle/Eau ancienne, +
   Exports au nocturne), pas robinet-par-robinet : la sonde tourne par phase — représentation
   honnête (« Eau ancienne — 3 / 5 »).
6. **`revenir` (filtre)** rangé en catégorie « filtre » ; `purger`/`job` (crons) en « cron » ;
   « sonde » reste une catégorie présente même vide (les sondes par source n'écrivent pas encore
   au journal du circuit).
7. **`par` : `admin` → « Vic »** (app à un seul admin), `cli`/`cron`/vide → « système », e-mails et
   noms de jobs gardés tels quels.

## Ce qui n'a pas pu être fait / limites
- La recette des **gestes réels sur app bootée** (vanne→calcul→bascule→revenir) reste rejouable mais
  non jouée ici (piège `PYTHONPATH=src` : l'env conda importe un `labuse` installé sans les endpoints
  CIRCUIT-P2). Les gestes appellent les mêmes endpoints, couverts par les tests backend.
- Un **agent LLM** (lecture de la page producteur par le modèle) n'est pas branché : la substance
  actuelle est la sonde amont déterministe ; le point d'accroche est en place (crédit + volée +
  journal + mauve).
- La résolution **cible → nom affiché** est au mieux : une clé de filtre qui ne correspond à aucun
  slug de réservoir retombe sur la clé brute (best-effort, jamais une erreur).

« Ne merge pas » respecté.

---

# P3 — deux lectures qui se contredisent (mandat MANDAT-CIRCUIT-P3.md)

Branche : `feat/circuit-page`, worktree `~/Desktop/labuse-audit`. Rien mergé. Un commit + un push par
lot. Reprise : « continue CIRCUIT-P3 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-P.md ».

## Les DEUX causes trouvées (en français)

1. **Le Journal affichait « 0 passage » sur une table de 90 lignes.** La base locale (créée avant
   CIRCUIT-P2) n'avait pas la colonne `circuit_journal.lot`, ajoutée en P2 par `ensure()` mais jamais
   rejouée sur cette base. L'endpoint groupe par `COALESCE(lot, …)` → la requête levait « column lot
   does not exist » → l'ancien `except` la rattrapait et renvoyait `total=0, entrees=[]`. Un ÉCHEC
   MASQUÉ. Prouvé : `psql labuse -c "SELECT COALESCE(lot,…) …"` → `ERROR: column "lot" does not exist`.
2. **Le Résumé disait « 2 fuites, 2 robinets » / « 1 eau ancienne » quand le Circuit disait « 130, 0
   à regarder ».** Les colonnes `circuit_ecarts.robinet_a/robinet_b` et `circuit_eau_ancienne.robinet`
   ne contiennent PAS des ids de robinet du registre mais des LIBELLÉS d'affichage (`attrs.degre (DEAL
   brut)`, `attrs.niveau (servi)`, `fiche parcelle / filtres`). Le Résumé comptait ces chaînes brutes ;
   l'état des robinets matchait les ids du registre → aucun ne ressortait. Le vrai lien passe par le
   `chiffre_id` (un robinet est touché s'il SERT un chiffre en fuite/eau). Prouvé (test -m local avant
   correctif) : « Résumé cite le robinet 'attrs.degre (DEAL brut)' / 'attrs.niveau (servi)' /
   'fiche parcelle / filtres' que le Circuit dit OK ».

Et une TROISIÈME, trouvée en recette (P3-05) : la **page de détail d'un robinet** disait « cohérent »
quand la liste disait « fuite », car elle aussi joignait `circuit_ecarts` par `:rid IN (robinet_a,
robinet_b)` (libellés). Corrigée par le même join `chiffre_id`.

## Lot 1 — Le journal ✅ (commit « CIRCUIT-P3 lot 1 »)
- `admin_circuit_journal` appelle `circuit_journal.ensure(c)` (ALTER `lot` idempotent) AVANT la
  requête, et NE MASQUE PLUS les erreurs (l'`except` fourre-tout retiré). Compteur du jour = jour de
  La Réunion (`ts AT TIME ZONE 'Indian/Reunion'`). Aucun filtre de date par défaut.
- Tests : rend vanne + lot de 39 filtres (une ligne) + bascule sur tous/vanne/filtre ; **self-heal**
  (DROP COLUMN lot → l'endpoint la rétablit et rend les lignes = la régression EXACTE) ; entrée
  d'il y a un an comptée (aucun filtre de date).

## Lot 2 — L'état des robinets ✅ (commit « CIRCUIT-P3 lot 2 »)
- `circuit_etats.robinets_touches(fuites, eau, chiffres_par_robinet)` rattache fuite/eau au robinet
  REGISTRE par le `chiffre_id`. UNE dérivation, partagée par l'état des robinets (ctx `etat_robinet`)
  ET le Résumé (`composer(fuite_robinets=…, eau_robinets=…)`) → les deux comptent les mêmes robinets.
  Les paramètres `fuites`/`eau_ancienne` (label-based) retirés du composer.
- **Le test d'égalité 2.4 refait pour de bon** (`test_circuit_p3_lot2.py`) : part des tables
  (`circuit_ecarts`, `circuit_eau_ancienne`, registre), construit l'ensemble attendu « à regarder » et
  exige l'ÉGALITÉ STRICTE avec `/admin/circuit` (aucun en trop, aucun en moins). L'ancien test
  synthétique P2 (`test_resume_circuit_coherents`, qui passait sur une page fausse) est **supprimé**.
- 2.3 réservoirs : `a_regarder` (gauche) = les réservoirs DISTINCTS des lignes ko du Résumé, sans
  doublon (un réservoir compté dans deux lignes — p.ex. « jamais vérifié » + « cadence proposée » —
  n'entre qu'une fois dans « à regarder » ; les lignes grises « À décider » ne comptent pas).
- 2.4 pastilles : un bloc « tout va bien » ne porte aucune pastille ambre/rouge/mauve, et
  réciproquement (test vitest `pastilles.test.tsx`).
- Détail robinet corrigé (join `chiffre_id`) + `test_detail_robinet_coherent_avec_liste`.

## Lot 3 — Une seule source de vérité ✅ (commit « CIRCUIT-P3 lot 3 »)
- Le serveur décide « à regarder » UNE fois : `/admin/circuit` pose `ko` sur chaque réservoir /
  robinet. Le front LIT `ko` ; **`koTank`/`koTap` (réimplémentation front de la même règle) SUPPRIMÉS**
  de `diagram.ts` et `CircuitDiagram` (compteur de colonne + compte par bloc + interrupteur lisent le
  même `ko`). Plus de chemin parallèle qui puisse diverger.
- Test 3.2 de cohérence globale sur la BASE RÉELLE (`pytest -m local`, marqueur enregistré). PREUVE
  AVANT / APRÈS :
  * AVANT (sans colonne lot) : `AssertionError: journal vide sur une base pleine (0 > 0)`.
  * AVANT (colonne lot présente) : `incohérences Résumé ↔ Circuit : Résumé cite le robinet
    'attrs.degre (DEAL brut)' / 'attrs.niveau (servi)' / 'fiche parcelle / filtres' que le Circuit dit OK`.
  * APRÈS : `1 passed`.
- Test 3.1 (db) : chaque élément porte `ko`, et les compteurs de colonne SONT ces `ko`.

## Lot 4 — Recette ✅ (commit « CIRCUIT-P3 lot 4 »)
- Captures **P3-01 → P3-06** sur la base locale (`qa/circuit_p3_captures.mjs`, harness vite +
  `/admin/*` proxifié vers uvicorn de ce code sur `labuse`) : Journal avec ses entrées + un lot déplié ·
  Journal filtré « filtre » · « vanne » · Circuit « n à regarder » non nul à droite · un robinet en
  fuite ouvert (détail = liste) · Résumé aux mêmes nombres que le Circuit. Regardées.
- Vérifié en direct sur `labuse` (uvicorn :8010, ce code) : Journal **90** (était 0),
  `robinets_a_regarder` **1** (était 0), 68 réservoirs — les deux lectures coïncident.

## Ce qui a été SUPPRIMÉ
- L'`except` fourre-tout de l'endpoint journal (masquait « column lot does not exist »).
- Les paramètres `fuites`/`eau_ancienne` du `composer` (comptage robinet par libellé) — remplacés par
  `fuite_robinets`/`eau_robinets` dérivés par `chiffre_id`.
- `koTank`/`koTap` (front) — la classification « à regarder » n'existe plus qu'au serveur (`ko`).
- Le test synthétique `test_resume_circuit_coherents` (P2) — remplacé par l'égalité stricte P3.

## Décisions prises en autonomie
1. **Le join fuite/eau → robinet passe par `chiffre_id`** (les colonnes `robinet_*` sont des libellés).
   Conséquence assumée : une eau ancienne enregistrée avec un `chiffre_id` NON registre
   (`(chiffres DPE)` sur la base locale) ne se rattache à aucun robinet → 0 robinet « eau ancienne »
   (Résumé et Circuit d'accord). C'est une donnée à re-taguer côté sonde (dette écrite ci-dessous),
   pas un correctif d'affichage.
2. **Le serveur est seul juge du « à regarder »** (`ko`) ; le front ne reclasse plus (koTank/koTap
   supprimés) — la seule façon d'empêcher deux lectures de diverger.
3. **P3-05 re-joué sur la base seedée** (uvicorn `labuse_test`) : la base locale était verrouillée
   par un run externe suspendu (13 min, locks `parcels`) qu'on ne devait pas tuer ; l'endpoint
   corrigé y rend « fuite mesurée », conforme, et le correctif est couvert par test.

## Dette / limites écrites
- **Sonde** : `circuit_ecarts.robinet_a/robinet_b` et `circuit_eau_ancienne.robinet` devraient porter
  un `chiffre_id` (ou un id de robinet) plutôt qu'un libellé ; et l'eau DPE utilise le placeholder
  `(chiffres DPE)`. Tant que ce n'est pas corrigé côté écriture, une eau non attribuable à un chiffre
  registre reste invisible au niveau robinet (par construction, pour que les deux lectures coïncident).
- La CLI `labuse filtre …` est enregistrée APRÈS le garde `if __name__ == "__main__"` de `cli.py`
  (pré-existant) → inatteignable via `python -m labuse.cli` ; le lot de démonstration P3 a été produit
  par le MÊME chemin de code appelé directement.

## Bilan des suites
- Backend circuit : **78 passed** (P3 lots 1/2/3 neufs + P1/P2, 0 régression) ; `-m local` : 1 passed
  sur la base réelle. Frontend : **173 vitest passed**, **tsc vert**.
- Pré-existant hors mandat : `test_non_contradiction.py` échoue en COLLECTION (WeasyPrint `libgobject`).

« Ne merge pas » respecté.
