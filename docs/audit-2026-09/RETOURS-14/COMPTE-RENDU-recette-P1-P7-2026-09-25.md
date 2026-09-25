# RETOURS-14 (recette Vic du 25/09) — COMPTE-RENDU · P1 à P7

> ⚠️ **Collision de dossier.** `docs/audit-2026-09/RETOURS-14/` contenait déjà un livrable
> ANTÉRIEUR et SANS RAPPORT (branche `fix/retours-12`, lots **S1–S11** : deux tableaux Communes,
> liens jaunes, annuaire PLU, taxe, permis orphelins…), avec son propre `COMPTE-RENDU.md` et 53
> captures `S*`. Cette recette-ci (P1–P7, du 25/09) porte le même numéro « RETOURS-14 » par
> hasard. Pour ne rien écraser : le `COMPTE-RENDU.md` existant est CONSERVÉ intact, les captures
> `S*` aussi ; le présent rapport vit sous un nom distinct et les captures de cette recette portent
> le préfixe `P1…P7`. À arbitrer avec Vic (renuméroter ? déplacer ?).

Branche `fix/retours-14` (worktree `labuse-retours14`, base main `952ff1ca`). Un commit par point,
poussés, **pas mergés**. Ports de recette 8435 (API) / 5635 (front).

Captures avant/après (1440 px) : `docs/audit-2026-09/RETOURS-14/captures/` (préfixes `P1…P7`,
suffixes `-avant` / `-apres`).

## Une ligne par point

- **P1–P2 — bouton « Demander à LABUSE » + version servie dans le bandeau** : FAIT (`f9b67d79`).
  Le libellé « Demander à LABUSE d'analyser la parcelle → » devient **« Demander à LABUSE »**
  (`strings.demanderAnalyse`, flèche retirée). La carte « Analyse LABUSE » est extraite dans
  `AnalyseLabuseCard` (testable) et affiche désormais **la version servie** : `data-analyse-version`
  = `SOURCE` (= `VITE_RUN_LABEL`, injecté au build depuis `config/served_run.txt` = `q_v11_m137`,
  le run de la page Données), **jamais codée en dur**. Le clic (`revelerVerdict`) ne révèle que la
  donnée lue par `getFiche(idu)` = `/parcels/{idu}?source=${SOURCE}`. Garde `AnalyseLabuseCard.test.tsx`
  (4 tests) : `getFiche` interroge `?source=SOURCE` ; la carte rend la version qu'on lui PASSE (deux
  versions → deux rendus) ; sans version, aucune mention fantôme. Captures `P1-fiche-bouton-*`,
  `P1-fiche-analyse-*` (après : « ANALYSE LABUSE · q_v11_m137 »).

- **P3 — en-tête sticky opaque jusqu'au bord haut** : FAIT (`6bffb993`). Cause : le conteneur
  défilant portait `pt-1` (4 px) ; le sticky `top:0` se calait au bord du padding → un liseré
  transparent de 4 px au-dessus laissait défiler le contenu derrière l'en-tête. Retrait du
  padding-haut → l'en-tête colle au bord ; coins hauts de `.tete-collee` passés **carrés** (les coins
  arrondis laissaient voir le contenu dans les arcs au ras du bord) + `border-top` retiré : fond plein
  jusqu'au bord, coins bas arrondis conservés. Espacement des tuiles porté par `gap-3` (inchangé).
  Captures `P3-fiche-entete-*` (avant : liseré ; après : bord franc).

- **P4 — « 3D » devient un menu Relief (même composant que « Sombre »)** : FAIT (`85f34435`).
  Le chip « ✓ Bâtiments » disparaît. « 3D » est un menu déroulant identique au sélecteur de fond de
  carte, **trois entrées exclusives** (une seule active à la fois) : **Aucun (2D)** · **Relief seul** ·
  **Relief + bâtiments** (défaut à l'activation, `batiVisible=true`). Même rendu, même survol
  (`hover-fill`), même état actif. Le bouton porte « 3D » (+ le mode courant en suffixe, comme le
  millésime ortho). **Aucune mention de LiDAR** : caption « Relief RGE ALTI · bâtiments BD TOPO ».
  Nouveau setter store `setTerrain3d` (le menu choisit un mode précis). ⚠ Vic a tranché « Aucun (2D) »
  comme 3ᵉ entrée pour préserver le retour au 2D (les deux entrées demandées étaient toutes deux du
  relief 3D). Captures `P4-carte-3d-chip-batiments-avant` / `P4-carte-menu-3d-ouvert-apres`.

- **P5 — Filtre : retrait « Depuis un programme » + regroupement « Affiner la recherche »** : FAIT
  (`3e1b5a7a`). (a) Le bloc repliable « Depuis un programme… » quitte « 3 · Capacité » — dimensionner
  un programme est le rôle de l'outil Faisabilité, qui le porte déjà ; aucune logique déplacée (le
  filtre reste `sdpMin`/`capaciteMin` en saisie directe ; `AideProgramme` supprimé). (b) Nouvelle
  section repliable **« Affiner la recherche »**, fermée par défaut, tout en bas, chevron de la charte,
  titre au style des autres sections : y sont regroupés — sans qu'aucun filtre ne soit supprimé —
  **ZFANG** et **FRR** (qui quittent « 2 · Le terrain ») et les **Signaux de vie** (qui quittaient
  « 4 » ; le préfixe « 4 · » tombe, l'ordre 1/2/3 reste cohérent). Persistance URL des filtres
  inchangée (`filters.test.ts` 6/6). Captures `P5-filtre-capacite-*`, `P5-filtre-affiner-ouvert-apres`.

- **P6 — deux comptes de parcelles réconciliés (430 813 vs 431 663)** : FAIT (`2c4286bf`).
  **Cause exacte (vérifiée en base)** : le bouton « Voir les N parcelles » lit `/filtre` →
  `_q_v2_stats(exclure_slivers=True)`, qui masque les micro-parcelles « sliver » de surface
  **< 2 m² (`MIN_DISPLAY_SURFACE_M2`)** → **430 813**. La page Sources lit `/sources/couverture` →
  `SELECT count(*) FROM parcels` (total ingéré) → **431 663**. Écart = **850 parcelles < 2 m²**
  (0 sans surface ; `count(*) FILTER (WHERE surface_m2 < 2) = 850`). Écart **légitime et volontaire**
  (règle d'affichage du filtre, FIX-FILTRES F2). Plutôt que deux totaux muets qui se contredisent, on
  l'ÉCRIT là où le grand nombre apparaît : `couverture_sources` sert désormais `parcelles_filtrables`
  (count ≥ 2 m² ou NULL) et la page Sources affiche « **431 663 parcelles couvertes, dont 430 813
  d'au moins 2 m² explorables au filtre — les 850 micro-parcelles (moins de 2 m²) sont écartées de
  l'exploration.** ». Garde pytest `test_couverture_reconcilie_slivers` : `parcelles -
  parcelles_filtrables` vaut EXACTEMENT le nombre de parcelles < 2 m² (règle recomptée à la main) ;
  clé ajoutée aux formes `test_q11_sources_couverture` + `test_couverture_nulls_gardes` (3/3 verts).
  Captures `P6-sources-sans-note-avant` / `P6-sources-reconciliation-apres`.

- **P7 — titrer les deux rangées de chips** : FAIT (`e8b701b8`). Les deux rangées
  (Excellente/Bonne/À étudier/Faible/Tous ; Fort/Moyen/Faible/Tous) portent désormais leur vrai nom
  (libellés SCORING-5) **en tête de rangée**, sur leur propre ligne, au style des autres titres de
  section (`label-caps`) : rangée 1 → **« Score LABUSE »**, rangée 2 → **« Signal de mutation »**. Le
  titre passe sur sa propre ligne (il ne tenait pas inline à côté des 5 mots entiers). Puces, data-attrs
  et « Tous » en dernier inchangés. Captures `P7-deux-rangees-sans-titre-avant` /
  `P7-deux-rangees-titrees-apres`.

## Vérifications

- `tsc -b` : **exit 0**.
- `vite build` : **OK** (bundle produit).
- Vitest : **192/192** (188 base + 4 nouveaux `AnalyseLabuseCard.test.tsx`).
- Pytest P6 (base test) : `test_couverture_reconcilie_slivers`, `test_couverture_nulls_gardes`,
  `test_q11_sources_couverture` → **3/3**.
- Recette LIVE (API 8435 / front 5635) : chaque point vérifié dans le DOM réel avant capture
  (libellés, présence/absence des blocs, `parcelles_filtrables=430813` servi par l'API).

## Notes d'environnement (recette)

- `node_modules` du worktree = symlink vers `~/Desktop/labuse/frontend/node_modules` (le worktree
  n'en avait pas). Backend lancé via `PYTHONPATH=src` + venv `~/Desktop/labuse/.venv`, DB
  `postgresql://openclaw@localhost:5432/labuse`.
- **Backend instable en recette** : l'uvicorn sur la base partagée `labuse` est mort plusieurs fois
  (exit 144, contention DB connue). Sur base froide (cache tuiles vide), la carte MapLibre ne se met
  jamais au repos → le screenshot MCP expire ; il faut un **contexte navigateur neuf** (ne PAS
  provoquer de `WEBGL_lose_context`, qui dégrade la session entière). Toutes les captures ont fini par
  être obtenues.
