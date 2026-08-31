# PROJETS-FIX — corriger la livraison OUTILS-5

**Dossier** `~/Desktop/labuse` · **branche** `feat/outils-1` · arbre propre au départ.
**Golden non touché** (0 fichier scoring/qa modifié — prouvé `git diff --name-only`).
Référence : `docs/maquettes/projets-v3.html` (§03 projet ouvert, §04 accueil).

API + front redémarrés avant recette : `uvicorn labuse.api.app:app :8000` (env=local, auth
désactivée) sert le build `frontend/dist` sous `/socle/` ; `vite build` régénéré. Preuve au
JOURNAL d'exécution ci-dessous (health `/socle/`=200, `/projets`=200).

---

## D — DIAGNOSTIC (avant tout code)

Les deux projets créés par Vic, lus en base :

| id | nom | cadrage stocké | cadrage_total |
|----|-----|----------------|---------------|
| 235 | LABUSE TEST | `{"__de_zero__": true}` | 0 |
| 236 | LABUSTRE TEST 2 | `{communes:["Saint-Denis"], etatSol:["nu"], zonePlu:["UB"], signaux:["pm_privee"]}` | 0 |

**Le cadrage est stocké FIDÈLEMENT** (pas de corruption), **le run servi est bon**
(`q_v11_m137` présent, 431 663 lignes `parcel_p_score_v2`). La cause est double.

### Cause 1 — projet 236 : un vrai 0, une zone absente de la commune
Les quatre compteurs backend retournent **0** pour le cadrage 236 :
`_q_v2_stats.total=0 · _vivier_figeable=0 · _cadrage_total.total=0 · _cadrage_page_idus=0`.
Décomposition SQL clause par clause à Saint-Denis :

```
commune Saint-Denis ........ 38 138
+ pm_privee ................  4 221
+ terrain nu ..............  14 065
+ zone_filtre = 'UB' ......      0   ← ANNULE tout le cadrage
```

`parcel_zone_plu` à Saint-Denis ne contient AUCUNE zone « UB » : le PLU dionysien nomme ses
zones UM (11 658), UI, UH, UD, UJ, UA… « UB » existe **ailleurs** (56 580 parcelles dans
d'autres communes) mais pas ici. Le sélecteur de zone a proposé « UB » à Saint-Denis alors
qu'elle n'y existe pas → cadrage légitimement vide.

### Cause 2 — le mirage « ~30 000 » : le wizard et le projet ne comptaient PAS pareil
Le wizard annonçait un grand nombre parce que **deux compteurs distincts** servaient « le vivier » :

- **Étape CADRAGE** (`FiltreFacettes`) appelait `getCadrageCompteur(cadrageFacettes)` — les facettes
  **SANS le périmètre** (la commune est une étape séparée du wizard, fusionnée seulement dans le
  cadrage final). Résultat : pendant qu'on cadrait Saint-Denis, le compteur affichait l'ÎLE ENTIÈRE
  (`pm_privee` île = **21 273** ≈ « ~30 000 »), jamais le vrai Saint-Denis.
- **Étape RÉCAP** lisait `r.total` = `_q_v2_stats.total`, le **total carte GONFLÉ** qui inclut
  ~79 % d'exclusions dures (étage 0) impossibles à trier : Saint-Denis brut = **38 138**,
  `pm_privee` île = **33 622**.

Pendant ce temps le projet ouvert servait « À trier » via `_cadrage_total.total` (score-joint,
plancher surface, hors étage 0). Preuve de l'écart des fonctions :

```
cadrage                     _vivier_figeable  _cadrage_total  _q_v2_stats  page_servie
pm_privee île                     21 273         21 273         33 622        21 273
Saint-Denis (sans facette)        29 628         29 628         38 138        29 628
Saint-Denis + pm_privee            3 503          3 503          4 221         3 503
```

`_vivier_figeable` == `_cadrage_total.total` == page réellement servie (le VRAI vivier) ;
`_q_v2_stats.total` est le total gonflé que le récap affichait. **Le wizard et « À trier »
sortaient de requêtes différentes** — c'est exactement le défaut que F1 corrige.

### Pourquoi la vérif OUTILS-5 (« vivier entier paginé, preuve SQL ») n'a pas vu ce cas
Elle a vérifié le chemin OUVERT en ISOLATION (`_cadrage_page_idus`/`_cadrage_total` paginent bien
le vivier). Elle n'a **jamais comparé le nombre AFFICHÉ DANS LE WIZARD au compteur du projet
ouvert**, et n'a pas exercé un cadrage **commune-scopé** (la divergence n'apparaît qu'avec une
commune sélectionnée que l'étape CADRAGE ignore) ni un cadrage **légitimement vide** dans la
commune choisie (zone absente). La preuve SQL portait sur la face servie, pas sur l'accord
wizard↔ouverture.

**Toutes les causes sont corrigibles dans le périmètre — je poursuis (pas d'arrêt).**

---

## F1 — VIVIER : un seul nombre, par construction

Règle posée : le compteur du wizard et le compteur « À trier » sortent de **LA MÊME requête**.

- **Backend** (`api/projets.py::projet_compteur`) : `vivier = _cadrage_total(db, cadrage)["total"]`
  — exactement ce que `/{pid}/parcelles` sert à « À trier ». Le champ `total` (`_q_v2_stats`
  gonflé) est **retiré** de la réponse : il était la source du mirage. On ne sert plus qu'UN nombre.
- **Frontend** :
  - `FiltreFacettes` reçoit un `compteurScope` (les communes) fusionné dans la requête du compteur
    vivant → l'étape CADRAGE compte désormais **ce que le projet servira**, pas l'île.
  - Le récap lit `r.vivier` (plus `r.total`).
  - `CadrageCompteur` : champ `total` retiré (TS).

**Preuve end-to-end** (API réelle, `/projets/compteur` vs ouverture) :

| cadrage | compteur wizard | ouverture « À trier » |
|---|---|---|
| île · pm_privée (projet 237) | 21 273 | 21 273 |
| Saint-Denis · nu · pm_privée (projet 238) | 862 | 862 |

**Test de régression** `tests/test_projets_fix_vivier.py` (4 tests, verts) : sur une base
synthétique (2 communes scorées), il verrouille `wizard == À trier == page servie` pour cinq
cadrages, dont les deux profils de Vic **+ un cadrage communes sans facette** (vivier > 0), la
sensibilité au périmètre (île=5 vs commune=3), et le cas vide légitime (0 des deux côtés → F4).

---

## F2 — PROJET OUVERT = MAQUETTE §03, PLEINE LARGEUR

`ProjetKanban.tsx` : les colonnes passaient de largeurs FIXES (`w-[340px]`/`w-[300px]`,
`flex overflow-x-auto`) — d'où le vide. Désormais **grille pleine largeur**
`md:grid-cols-[1.35fr_1fr_0.8fr]` (empilée sous 980 px), les trois colonnes remplissent l'espace.
En-tête aligné sur la maquette : nom + **étiquette périmètre** (une fois) + ligne unique
**« Vivier : N · valeurs au JJ/MM (run) · budget indic. »** + actions PDF · Renommer · Archiver.
Les chips de facettes redondantes de l'en-tête sont retirées (la maquette ne les porte pas).
Cartes (signal + Retenir/Écarter) et filtres de navigation en tête de colonne : inchangés.

Comparaison côte à côte : `captures/07-maquette-03-projet-ouvert.png` ↔
`captures/02-kanban-F2-vivier21273.png` (en-tête « TOUTE L'ÎLE », vivier 21 273, 3 colonnes
pleines).

---

## F3 — CARTE PROJET (ACCUEIL) = MAQUETTE §04

`ProjetsPanel.tsx` : la ligne « vivier » RÉPÉTAIT le périmètre (déjà en étiquette de titre) et
ajoutait « N facettes ». `ctxLine` → `budgetLine` : la ligne ne porte plus que le budget indicatif.
Une carte = **titre + étiquette périmètre**, une ligne **« vivier N classé · valeurs au JJ/MM ·
budget »**, la barre lisible (`N retenues · N écartées · N à explorer, classées`), le compteur
**RETENUES** à droite. Rien d'autre. Comparaison : `captures/08-maquette-04-accueil.png` ↔
`captures/01-accueil-F3.png`.

---

## F4 — ÉTATS VIDES (jamais un « 0 » nu)

Deux cas distingués dans la colonne « À trier » (`ProjetKanban.tsx`) :

- **Projet de zéro** (`cadrage.__de_zero__`) : message + bouton **« Ajouter des parcelles →
  carte »** qui pose un `projetCible` dans le store et bascule sur Cartes. Le bouton « Projet »
  d'une fiche, quand un `projetCible` est armé, **rattache DIRECTEMENT** à ce projet (libellé
  « + Ajouter à « nom » », plus de menu). `store/useApp.ts` + `fiche/Fiche.tsx::ProjetButton`.
  Capture `04-vide-de-zero-F4.png` (projet 235). La ligne « Vivier : 0 » est masquée pour un
  projet de zéro (aucune notion de vivier).
- **Cadrage sans résultat** (vivier = 0, cadrage réel) : message **« Aucune parcelle ne
  correspond à ce cadrage »** + lien **« Modifier le cadrage »** → éditeur inline
  (`CadrageEditor` : réutilise `FiltreFacettes` + `patchProjet`, périmètre passé au compteur).
  Capture `05-vide-cadrage-F4.png` (projet 236, zone UB absente de Saint-Denis).

---

## VÉRIFICATION

- `tsc -b` : **0 erreur**. `vite build` : **OK**. `vitest` : **108 passed**.
- `pytest` projets/sécu : `test_projet_m120` + `test_projet_m2` + `test_projets_fix_vivier` (4) +
  `test_audit_secu` (34, dont l'invariant liste==ouverture) — **verts**.
- **Golden intact** : 0 fichier scoring/qa touché ; `qa/golden_check.py` sur le run servi
  q_v11_m137 = **119/119 PASS, 0 FAIL**, GARDE-RUN OK (431 663/431 663 parcelles évaluées).
- Captures `docs/PROJETS-FIX/captures/` (1440×900 @2x) : accueil F3 · kanban F2 (×2) · deux états
  vides F4 · récap wizard F1 (vivier honnête) · maquette §03 & §04. `_report.json` : colCount=3,
  deZero=1, cadrageVide=1, vivier237=« 21 273 », errors=[].

**Ne merge pas.**

### Commande de merge (à exécuter par Vic, en dernier, isolé)
```
git checkout feat/outils-1 && git merge --no-ff <ce commit>
```
