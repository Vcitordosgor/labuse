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

## Lots 2→6 — à venir

- Lot 2 — Résumé et onglets (`Circuit.tsx` conteneur + `Resume.tsx`).
- Lot 3 — Le circuit par familles (`CircuitDiagram.tsx`, tuyaux `familles + catégories + 2`).
- Lot 4 — Les pages de détail (`Detail.tsx`, deep-link hash).
- Lot 5 — Le journal (`Journal.tsx`).
- Lot 6 — Recette navigateur + retrait de l'ancien rendu + snapshots.

## Accroches pour CIRCUIT-4 (lot 6.3, à confirmer au fil)

- Badges de règle du robinet → `Detail.tsx` (bloc « La règle derrière ces calculs »).
- Ligne « écarts à la règle » du Résumé → `circuit_resume.composer(regles_ecart=…)` ; l'état
  `écart à la règle` du robinet → `etat_robinet(ctx={ecart_regle_robinets})`.
