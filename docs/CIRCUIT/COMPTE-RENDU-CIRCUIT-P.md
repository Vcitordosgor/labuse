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

## Lot 6 — à venir

- Lot 6 — Recette navigateur + retrait de l'ancien rendu + snapshots.

## Accroches pour CIRCUIT-4 (lot 6.3, à confirmer au fil)

- Badges de règle du robinet → `Detail.tsx` (bloc « La règle derrière ces calculs »).
- Ligne « écarts à la règle » du Résumé → `circuit_resume.composer(regles_ecart=…)` ; l'état
  `écart à la règle` du robinet → `etat_robinet(ctx={ecart_regle_robinets})`.
