# ANNONCE-3 — « Analyser une annonce » gagne un export PDF, Docs gagne « Analyse d'annonce »

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
