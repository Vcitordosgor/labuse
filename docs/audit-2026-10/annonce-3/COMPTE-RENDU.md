# ANNONCE-3 — « Analyser une annonce » gagne un export PDF, Docs gagne « Analyse d'annonce »

> ## ANNONCE-3-FIX-3 (retours Vic) — appliqué sur la même branche
>
> **La parcelle entière est TOUJOURS visible dans le plan, quelle que soit sa forme.** Le cadre est large
> (pleine largeur, ~48 mm, aspect ~3,6) ; `build_situation_map` rend une fenêtre FIXE 720×450 → pour une
> parcelle HAUTE, le recadrage à cet aspect, borné à la fenêtre, rognait le contour en haut/bas (CX0800).
> **Règle appliquée** : on recule le zoom (`_choisir_cadre_plan`, zooms 0 → −3) jusqu'à ce que TOUT le
> contour tienne dans le cadre, marge comprise — pour une parcelle haute, l'emprise HORIZONTALE s'élargit
> d'elle-même (plus de contexte) et toute la hauteur tient. La vérification est pure et testée
> (`_parcelle_dans_cadre`). L'image remplit toujours le cadre (`width:100%`), sans bandes blanches.
>
> **Tests ajoutés** (`test_annonce_pdf.py`, 12 → **15**) : `_parcelle_dans_cadre` (débordement haut/bas,
> gauche/droite, cas contenu) + **parcelle allongée VERTICALEMENT** (rognée au zoom serré → cadre reculé
> retenu, parcelle entière) + **parcelle allongée HORIZONTALEMENT** (idem). **Recette** : CX0800 (nue) et
> BN2715 (bâtie) régénérés — plan pleine largeur, **contour entier visible avec marge**, 1 page, outil==docs.
> tsc 0 · vitest **301/301** · pytest hook **2604 passed, 0 failed**. Commit FIX-3 sur la branche.
>
> ---
>
> ## ANNONCE-3-FIX-2 (retours Vic) — appliqué sur la même branche
>
> 1. **Plan de situation pleine largeur, sans bandes blanches** — l'image REMPLIT le cadre
>    (`width:100%;height:auto`, plus d'`object-fit:contain` qui letterboxait) ; le cadrage `plan_ortho`
>    est calé sur l'aspect de la boîte (`target_aspect=3.6`, `crop_margin_m=16`) → **parcelle entière,
>    centrée, avec marge**, jamais rognée (l'axe déficient s'élargit). La variante parcelle reste 1 page.
> 2. **Estimation « terrain nu » montre sa source comme la variante bâtie** — médiane + **nombre RÉEL de
>    ventes** (`n = 78`, plus « n ≥ 3 ») + **périmètre** (secteur cadastral / commune) + **période**
>    (`2021–2025`). Lu via le lecteur DÉCLARÉ `api/mon_secteur._terrain_section` (même méthode que le
>    §Marché de la fiche, `dvf_secteur_medianes`) — pas une relecture directe de la table (garde-fou du
>    graphe de lectures `test_graphe_exact_dans_les_deux_sens` vert). **Note en casse normale** (« terrain
>    nu », plus de capitales) **close par un point** (plus de minuscule après le point). Même rendu écran/PDF.
>
> **Recette FIX-2** : CX0800 (NUE) → « Estimation 495 €/m² · Fiabilité Élevée · 78 ventes de terrain ·
> secteur cadastral · 2021–2025 · Parcelle nue — comparée aux ventes de terrain nu (repère €/m² de
> terrain). » — **identique à l'écran et au PDF**, 1 page, plan pleine largeur sans bandes. BN2715 (BÂTIE)
> inchangée (bâti : 1 859 €/m², fourchette 1 549–1 962, 9 ventes, rayon 1 500 m). `outil==docs` (pdftotext).
> tsc 0 · vitest **301/301** · pytest hook **2601 passed, 0 failed**. Commit FIX-2 sur la branche.
>
> ---
>
> ## ANNONCE-3-FIX (retours Vic) — appliqué sur la même branche
>
> Sept points, tous tenus (rien de servi touché : le CSS de mise en page est injecté **seulement**
> pour ce document via `page_extra_css`, les 8 autres documents sont inchangés) :
>
> 1. **Plan de situation** — la parcelle ENTIÈRE, CENTRÉE, avec une MARGE autour du contour
>    (`plan_ortho(crop_margin_m=22, target_aspect=2.4)` : cadre centré sur l'emprise + marge, l'axe
>    déficient s'élargit, la parcelle n'est jamais rognée). Hauteur réduite au rendu (~30 mm,
>    `width:auto`+`height`, pas d'`object-fit:cover`) → **la variante parcelle tient sur UNE page**.
> 2. **En-tête variante parcelle** — adresse (ou commune si la fiche n'en résout pas), IDU, date.
> 3. **Titre de la section des tuiles** — « La parcelle » (au lieu de « Analyse d'annonce »).
> 4. **Badge de fiabilité** — trois niveaux seulement (« Élevée » / « Moyenne » / « Limitée »), le badge
>    ne porte QUE le niveau, l'étiquette « Fiabilité » est à côté — à l'écran ET dans le PDF.
> 5. **Pagination « 1 / 2 » sur une seule ligne** (@bottom-right `white-space:nowrap`, scopé) ; la
>    variante parcelle tient sur une page → « 1 / 1 ».
> 6. **Estimation selon la nature de la parcelle** — point UNIQUE `estimation_annonce` (lu par l'écran
>    via `GET /radar/annonce/estimation/{idu}` ET par le PDF) : parcelle NUE → repère €/m² de TERRAIN NU
>    (`_prix_terrain_local`, secteur→commune) ; BÂTIE → comparateur bâti (prix_ancien). **La note dit
>    lequel est utilisé**, même règle à l'écran et dans le PDF.
> 7. **Nouvelle capture du bouton** (`captures/bouton-exporter-pdf-outil.png`) — CX0800 en « Parcelle nue ».
>
> **D'où vient la nature (correction, lecture seule — psql, sans session app, sans écriture ; la base
> servie Mac EST la donnée de production, PROD=LOCAL ; pas d'accès VPS séparé, prod gelée).** Le champ
> `etat_bien` de la FICHE est calculé en direct (CASE sur `parcel_residuel.taux_emprise_pct`) mais la
> fiche SERVIE le rend `None` (**0 parcelle servie le porte**, sur 30 sondées puis vérifié). En revanche
> l'INDICATEUR sous-jacent — `parcel_residuel.taux_emprise_pct` (part bâtie BD TOPO, celui du résiduel
> et du scoring) — est peuplé sur **253 764 / 434 582 parcelles** (27 695 **nues** < 5 %, 226 069 bâties).
> → `estimation_annonce` ne dépend PLUS de `etat_bien` : `_nature_parcelle(db, idu)` lit `taux_emprise_pct`
> en direct (même CASE : NULL→non mesuré, < 5 %→nu, sinon bâti). **CX0800 : `taux_emprise_pct = 0 → nue`**,
> secteur avec médiane DVF terrain (495 €/m², n=78) → l'outil ET le PDF sortent « Parcelle nue — comparée
> aux ventes de TERRAIN NU · 495 €/m² », **sans injection**. La capture forcée est supprimée (plus utile).
>
> **Recette FIX** (uvicorn :8940 redémarré — ⚠ sans redémarrage il sert le code périmé) :
> `outil-parcelle.pdf`/`docs-parcelle.pdf` (CX0800 **NUE → terrain 495 €/m²**, **1 page**, outil==docs),
> `outil-parcelle-batie.pdf`/`docs-parcelle-batie.pdf` (`97422000BN2715` **BÂTIE → bâti 1 859 €/m²**, 1 page,
> identiques), `outil-commune.pdf`/`docs-commune.pdf` (1 page, « 1 / 1 »). Écran == PDF vérifié (CX0800 :
> 495 €/m², Fiabilité Élevée, « Parcelle nue — comparée aux ventes de terrain nu »). tsc 0 · vitest
> **301/301** · pytest hook **2601 passed, 0 failed** (`test_annonce_pdf.py` 12 cas, nature lue de
> `parcel_residuel`). Commit FIX sur la branche.
>
> ---

**Branche** `feat/annonce-3` · worktree `~/Desktop/labuse-annonce3` · base `origin/main` (`472e292fd`,
qui contient déjà ANNONCE-1 et ANNONCE-2 mergés). Ports 8940/6140. Aucun merge, rien de servi touché,
aucun accès prod. DA existante, **aucun nouveau composant, aucune nouvelle couleur**.

Règle de Vic tenue : **le PDF sorti de l'outil et celui sorti de Docs sont identiques, mêmes chiffres
que l'écran** — parce qu'ils appellent la MÊME route, qui lit les MÊMES endpoints que l'écran. Aucun
moteur neuf : on réutilise la chaîne PDF déjà en place pour Étude de zone / Gabarit / Comparer.

---

## Ce qui a été fait

### 1 — Bouton dans l'outil
`frontend/src/components/outils/AnalyserAnnonce.tsx` : un composant `ExportPdf` (charte `Bouton`
`secondaire`/`vert`, **une seule ligne**, pleine largeur) en **bas de chaque rapport** :
- rapport **parcelle** → `docAnalyseAnnonceUrl(idu)` = `/analyse-annonce/{idu}.pdf` ;
- rapport **annonce** → `docAnalyseAnnonceLienUrl(a.url)` = `/analyse-annonce.pdf?url=…`.
Ouverture propre (fetch + blob + attente + message FR) via le hook partagé `useOuvrirDocument` — comme
les boutons « Exporter en PDF » de Gabarit / Comparer / Étude de zone.

### 2 — Docs : nouveau document « Analyse d'annonce »
- `catalogue.ts` : 9ᵉ carte, nouveau `DocKind` **`annonce`** (deux entrées, comme l'outil).
- `DocumentsView.tsx` : variante de porte `annonce` (une **adresse** → rapport parcelle ; **OU** un
  **lien** d'annonce → rapport commune, même séparateur « OU » que l'outil) ; cas `urlDocument` et
  filtre « Mes documents ». Pour le lien, **même chemin que l'outil** (Radar d'abord → fetch → **même
  message d'échec**), car la porte tape exactement la même route que le bouton de l'outil.
- `api.ts` : `DocType += 'analyse-annonce'`, helpers `docAnalyseAnnonceUrl` / `docAnalyseAnnonceLienUrl`.
- L'entrée **adresse** (IDU stable) s'inscrit à « Mes documents » et se régénère ; l'entrée **lien**
  n'a pas d'objet LABUSE stable à mémoriser → produite mais non inscrite (best-effort, comme la règle
  « la bibliothèque n'empêche jamais de produire le PDF »).

### 3 — Backend (chaîne PDF existante, aucun moteur neuf)
- `exports/blocs/annonce.py` (NOUVEAU) : deux rendus purs, miroir EXACT de l'écran —
  `rendu_parcelle` (6 tuiles + « Estimation du prix » + « Le foncier ») et `rendu_commune`
  (« Ce que dit l'annonce » + « Prix face au marché » + « La commune »). Formats FR mirroir de
  `frontend/src/lib/format.ts` (fmtInt / fmtM2 → ha ≥ 1 ha).
- `exports/builder.py` : `construire_analyse_annonce_parc` (lit `parcel_fiche`, `parcel_exposition`,
  `radar_annonce_classement` — **la bande du run SERVI + vocabulaire gravé**), et
  `construire_analyse_annonce_lien` (sorties EXACTES de `radar_annonce_analyser` + `commune_contexte`).
  Plan de situation parcelle = `_plan_situation_html` (MÊME composant que le Dossier : contour parcelle).
  `_LABEL` / `_FOOT` + `numeros.PREFIXE['analyse-annonce'] = 'AA'`.
- `api/documents.py` : `GET /analyse-annonce/{idu}.pdf` et `GET /analyse-annonce.pdf?url=…` (enveloppe
  `_pdf_response` partagée : mention d'attribution, nom de fichier humain, `no-store`). Le lien en échec
  rend 422 + **la phrase exacte de l'outil** (`_ANNONCE_ECHEC`, mot pour mot `messageErreur`).
- `api/documents_bibliotheque.py` : `analyse-annonce` ajouté à `DOC_TYPES` + `DOC_LABEL`.
- `frontend/vite.config.ts` : `/analyse-annonce` ajouté à `apiPaths` (proxy dev) — gardé par
  `test_proxy_dev_couvre_routes_api.py`.

### Garde-fous du mandat
- **« jamais un champ vide imprimé »** : une tuile / ligne sans valeur n'est PAS imprimée (ni « — » ni
  case vide) ; les champs non applicables au type restent masqués (pilotage par type identique à l'écran).
- **Formats FR**, aucun code brut. Défaut corrigé en recette : le numéro de rapport de la variante lien
  prenait `idu[-4:]` d'un nom de commune (« …-noît » pour Saint-Benoît : **texte tronqué** + octet
  non-ASCII qui cassait l'en-tête) → il prend désormais l'**identifiant d'annonce** (list_id, chiffres
  de l'URL), ASCII et stable → `AA-20261029-3003`.
- **Classement LABUSE** lu sur le run servi avec le vocabulaire gravé (via `radar_annonce_classement`).
- **Verrou de comptage** : aucun verrou ne compte les documents de Docs ni les robinets (vérifié). Le
  seul comptage dur (`test_lot5_concepts.py` : 16 outils) porte sur les OUTILS du menu — ANNONCE-3
  n'ajoute PAS d'outil → inchangé. Les documents frères (gabarit/comparatif/étude-zone/faisabilité)
  n'ont **pas de robinet** → `analyse-annonce` n'en a pas non plus (V5c/V5f restent verts).

---

## Recette

Harnais `docs/audit-2026-10/annonce-3/_recette_serveur.py` + génération HTTP réelle (uvicorn :8940 sur
la base locale `postgresql:///labuse`, lecture seule) :

```
curl /analyse-annonce/97413000CX0800.pdf          → outil-parcelle.pdf / docs-parcelle.pdf  (105 ko)
curl "/analyse-annonce.pdf?url=…3260743003.htm"   → outil-commune.pdf  / docs-commune.pdf   (17 ko)
```

**Les 4 PDF (captures/, git-ignorés) :**
| fichier | variante | origine |
|---|---|---|
| `outil-parcelle.pdf` | parcelle (adresse) | bouton de l'outil |
| `docs-parcelle.pdf`  | parcelle (adresse) | porte Docs |
| `outil-commune.pdf`  | commune (lien)     | bouton de l'outil |
| `docs-commune.pdf`   | commune (lien)     | porte Docs |

**Outil == Docs** (preuve par `pdftotext -layout`, texte comparé) :
```
[parcelle] outil == docs : TEXTE IDENTIQUE ✓
[commune]  outil == docs : TEXTE IDENTIQUE ✓
```
(identique par construction : l'outil et Docs tapent la MÊME route → le même builder.)

**PDF == écran** (parcelle `97413000CX0800`, Saint-Leu) — vérifié chiffre pour chiffre :

| | écran (outil) | PDF |
|---|---|---|
| Surface | 1 819 m² | 1 819 m² |
| Zone PLU | UD | UD |
| SDP restante | 1 412 m² | 1 412 m² |
| Classement LABUSE | C · À étudier | C · À étudier |
| Risques | 4 aléas | 4 aléas |
| Exposition | Ouest | Ouest |
| Estimation | 3 291 €/m² · de 2 953 à 3 518 · élevée · 12 ventes · 500 m · 2022–2025 | idem |
| Le foncier | Zone UD · hauteur 6 m · SDP 1 412 m² | idem |

Variante commune (lien `3260743003`, Saint-Benoît, Radar d'abord sans réseau) : « Maison 4 pièces ·
Saint-Benoît » · « Annonce Leboncoin · relevée le 27/09/2026 » · −7,4 % face au repère maisons
1 948 €/m² · Fiabilité limitée · phrase « Localisez la parcelle… » · La commune (532 ventes 2021–2025,
PLU à jour, aléas inondation/mouvement de terrain/parc national). Pied : « Estimation comparative …
ce n'est pas un avis de valeur. Sources : DVF · Radar LABUSE ».

**Capture du bouton dans l'outil** : `captures/bouton-exporter-pdf-outil.png` (rapport parcelle, bouton
« Exporter en PDF » en bas).

---

## Vérifications (hook)

- **Front** : `tsc -b` → 0 · `vitest run` → **301/301** (dont `AnalyseAnnonceDoc.test.tsx` neuf et
  `EtudeDocs.test.tsx` inchangé).
- **Backend** : famille hook `pytest -m "not db and not local and not reel and not network"` →
  **2599 passed, 0 failed** (dont `tests/test_annonce_pdf.py` neuf, 10 cas). Les 2 `test_donnees_etat_fix1`
  ERROR = base de test locale absente (rôle `labuse` inexistant sur ce Mac) — passent dès qu'une base
  est jointe ; sans rapport avec ANNONCE-3.
- **Non régression DB** : lancé avec la base locale, 6 tests de données échouent (`test_enrichment`,
  `test_geom_2975`, `test_marche_commune`, `test_pau_cosia`, `test_sar`) — **identiques sur `main`**
  avec la même base (base locale stale, PROD=LOCAL) → pré-existants, pas ANNONCE-3.
- Garde proxy dev (`test_proxy_dev_couvre_routes_api.py`) → vert après ajout de `/analyse-annonce`.

## Fichiers

Neufs : `src/labuse/exports/blocs/annonce.py` · `tests/test_annonce_pdf.py` ·
`frontend/src/components/documents/AnalyseAnnonceDoc.test.tsx` · ce dossier.
Modifiés : `exports/builder.py` · `exports/numeros.py` · `api/documents.py` ·
`api/documents_bibliotheque.py` · `frontend/.../outils/AnalyserAnnonce.tsx` ·
`frontend/.../documents/{catalogue.ts,DocumentsView.tsx}` · `frontend/src/lib/api.ts` ·
`frontend/vite.config.ts`.

**Le merge est un geste de Vic, après recette.**

## Comment relancer
```
# API (lecture seule, base locale)
PYTHONPATH=src LABUSE_ENV=local LABUSE_DATABASE_URL=postgresql+psycopg:///labuse \
  ~/Desktop/labuse/.venv/bin/python -m uvicorn labuse.api.app:app --port 8940
# Front
cd frontend && LABUSE_API_DEV=http://127.0.0.1:8940 npx vite --port 6140   # app à /socle/
# Recette 4 PDF + comparaison outil==docs
PYTHONPATH=src LABUSE_ENV=local LABUSE_DATABASE_URL=postgresql+psycopg:///labuse \
  ~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/annonce-3/_recette_serveur.py
# Tests hook
PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python -m pytest tests/test_annonce_pdf.py -q
cd frontend && npx tsc -b && npx vitest run
```
