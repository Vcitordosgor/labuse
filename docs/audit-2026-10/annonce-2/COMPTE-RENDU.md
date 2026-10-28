# ANNONCE-2 — « Analyser une annonce » (entrée LIEN) lit D'ABORD le Radar

**Branche** `feat/annonce-2` · worktree `~/Desktop/labuse-annonce2` · ports 8930 / 6130
**Base** `origin/main` (`4c38f525c`) · **Modèle** Opus · **Date** 2026-10-28
**Nature** construit, testé, PAS mergé. Aucun accès prod, rien de servi déployé, aucun écran neuf.

---

## Le problème

L'entrée « lien » d'Analyser une annonce (ANNONCE-1, en prod) faisait un **fetch one-shot** de la page
Leboncoin — bloqué par DataDome dans la vraie vie, donc l'outil échouait presque toujours. Or le **Radar
capture chaque soir** les annonces de toute l'île. L'outil doit donc lire d'abord ce que LABUSE a déjà
relevé, et ne tenter le réseau qu'en dernier recours.

## Ce qui a été fait

Tout tient dans **un endpoint** (`POST /radar/annonce/analyser`) et **une phrase** de message, sans
nouvelle table, sans nouvel écran, sans pont vers l'entrée adresse.

### 1 — Lookup Radar D'ABORD (`src/labuse/pige/api.py`)

- `_list_id_from_url(url)` extrait l'**identifiant Leboncoin** (`list_id`) de l'URL. Query (`?…`) et
  ancre (`#…`) ignorés ; dernier segment de chemin (avec ou sans `.htm`/`.html`), repli sur la plus
  longue suite de ≥ 8 chiffres. Rend `None` pour une page de recherche ou un lien malformé.
- `_annonce_depuis_radar(db, list_id, url)` cherche le bien par `pige_annonces.list_id` et, s'il existe,
  construit le rapport depuis les **tables existantes** `pige_annonces → pige_biens → pige_faits` —
  **aucun appel à Leboncoin**. Aucune table neuve, aucune colonne neuve.
- L'endpoint tente le lookup **avant** tout fetch. Un garde-fou de test (`test_lookup_radar_tente_avant_le_fetch`)
  verrouille cet ordre dans le source.

### 2 — Repli inchangé

Bien absent du Radar (`list_id` inconnu, ou URL sans identifiant) → `_fetch_page_oneshot` + parseur
`extraire_page_annonce`, **exactement le comportement d'ANNONCE-1**. Le calcul du marché est désormais
partagé par les deux voies (`_marche_commune`, idu=None → repère commune, fiabilité « limitée ») : un
seul moteur de prix, aucune divergence entre « relevé Radar » et « fetch ».

### 3 — Provenance = VRAIE date

La ligne « **Annonce Leboncoin · relevée le …** » (inchangée côté front) porte :
- rapport **Radar** → la **date de capture** (`date_derniere_confirmation`, à défaut `date_premiere_saisie`),
  convertie **au fuseau Réunion** (`labuse.tz`, jamais `date.today()`) ;
- rapport **fetch** → la **date du jour** (`today_reunion()`), comme avant.

Aucune autre mention technique : le front rendait déjà `releve_le` tel quel — seul le backend change ce
qu'il y met. (Preuve : capture #1 = `27/10/2026`, capture #3 = `29/10/2026`.)

### 4 — Message d'échec (`frontend/.../AnalyserAnnonce.tsx`)

Comme le lookup Radar est **tenté d'abord**, le code d'erreur `url_bloquee` ne survient plus QUE lorsque
le bien est **absent du Radar ET** que Leboncoin bloque le fetch. Sa phrase est donc celle du mandat,
**sans aucun code HTTP** :

> Cette annonce n'a pas encore été relevée par LABUSE et Leboncoin bloque sa lecture automatique.
> Entrez l'adresse du bien pour l'analyser.

## Garde-fous ANNONCE-1 tenus

Donnée absente → « non précisé dans l'annonce » ; champs non applicables au type masqués ; estimation
avec sa source et son échelle (repère commune, « limitée ») ; horloge via `labuse.tz` ; changer d'outil
vide la recherche (`setModule`, inchangé). Doctrine « faits + lien » : le rapport Radar ne ressert aucun
contenu d'annonce (titre = `None`, le titre affiché est recomposé depuis type + pièces + commune).

---

## Mesure demandée — biens Radar en base et part retrouvable par identifiant

Base pige réellement alimentée = **base Mac** `postgresql:///labuse` (la prod ne reçoit plus de capture
depuis le 06/10, cf. [[radar-etat-1]] ; mesure identique à l'audit [[annonce-audit-1]]).

| Mesure | Valeur |
|---|---|
| Biens Radar en base (`pige_biens`) | **416** |
| Biens avec au moins un `list_id` (`pige_annonces`) | **416** |
| **Part retrouvable par identifiant** | **416 / 416 = 100 %** |
| Annonces (`pige_annonces`) | 428 |
| Annonces avec `list_id` | 428 / 428 = 100 % |

**Chaque bien capturé porte son `list_id` Leboncoin** : un lien d'annonce présent au Radar est
retrouvable à coup sûr, sans aucun appel réseau. (La contrainte `uq_pige_annonces_list_id` garantit
l'unicité du lookup.)

---

## Recette — 3 captures navigateur

App lancée en local (uvicorn :8930, Vite :6130) sur la base Mac, via le harnais de recette
`_recette_serveur.py` (hors code servi) qui **simule** le fetch Leboncoin : fixture locale pour le cas
« réussi », `RuntimeError` (DataDome) pour tout autre lien absent — **aucun appel réseau sortant**.

| # | Scénario | Lien | Résultat | Capture |
|---|---|---|---|---|
| 1 | **Présent au Radar** | `…/ventes_immobilieres/3228901746` | Rapport depuis le Radar · « relevée le **27/10/2026** » (date de capture) · Appartement 2 pièces Saint-Denis · prix 175 000 € · +33,1 % | `recette/01-present-radar.png` |
| 2 | **Absent + fetch bloqué** | `…/ventes_immobilieres/9000000009` | Phrase du mandat, **sans code HTTP** | `recette/02-absent-bloque.png` |
| 3 | **Absent + fetch réussi** (fixture) | `…/ventes_immobilieres/9000000003` | Rapport depuis le fetch · « relevée le **29/10/2026** » (jour, fuseau Réunion) · Terrain La Possession · prix 195 000 € · +6,7 % | `recette/03-absent-fetch-fixture.png` |

> Les PNG vivent en local sous `recette/` : les captures d'audit sont ignorées par `.gitignore`
> (`docs/audit-*/**/*.png`, anti-bloat MENAGE-1) et ne sont pas commitées.

## Tests — suite du hook verte

- **Nouveau** `tests/test_annonce_lien.py` (5 tests) : extraction `list_id` sur toutes les formes d'URL +
  cas None ; garde « lookup Radar avant fetch » ; garde « phrase d'échec exacte » ; rapport Radar
  end-to-end (date de capture, pas de contenu) ; identifiant inconnu → `None`. **Tous verts.**
- **Hook pre-push** (famille `not db`) : `2589 passed, 163 skipped` ; **tsc -b 0** ; **vitest 299/299**.
  (Les 2 `ERROR` observés hors DB joignable sont l'artefact « role labuse » de l'environnement, verts dès
  que la base de test est atteignable — sans rapport avec ce mandat.)
- **Pré-existant, non introduit par ce mandat** : `tests/test_pige_socle.py::test_aucune_requete_portail_dans_le_depot`
  (marqué `db`, **hors hook pre-push**) est **déjà rouge sur `main`** — il signale les chaînes
  « Leboncoin » d'affichage/validation d'ANNONCE-1 (vérifié ligne à ligne : mêmes 6 lignes sur `main`).
  Ce mandat **n'ajoute aucune nouvelle violation**. Le toucher = modifier la liste blanche d'un garde
  **légal** → laissé à Vic, hors périmètre ANNONCE-2.

## Fichiers touchés

- `src/labuse/pige/api.py` — lookup Radar + helpers `_list_id_from_url`, `_annonce_depuis_radar`,
  `_marche_commune` ; endpoint réécrit (repli inchangé).
- `frontend/src/components/outils/AnalyserAnnonce.tsx` — message `url_bloquee` (phrase du mandat).
- `tests/test_annonce_lien.py` — neuf.
- `docs/audit-2026-10/annonce-2/` — ce compte-rendu + harnais de recette + captures (locales).

**Merge = geste de Vic après recette.**
