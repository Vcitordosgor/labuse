# APPORTEUR PACK — refonte du pack apporteur d'affaires (point 17)

**Branche** : `feat/apporteur-pack` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**Commits séparés** (A–E) + 1 infra. **Zéro touche scoring/cascade/étage 0/run** (git : 2 fichiers —
`partners.py` le pack, `flash/carte.py` les tuiles). On lit les facteurs déjà calculés, on ne recalcule rien.

Le pack apporteur (M20) = **page publique `/p/{token}`** (lien partageable filigrané, lecture seule).
Avant : IDU + surface/commune + **liste brute de facteurs**, sans adresse ni visuel. Après : un one-pager
crédible — **le haut vend** (adresse + photo + points clés), **le bas prouve** (détail sourcé).

| # | Commit | Fix |
|---|---|---|
| — | `01d5e18` | infra : `build_situation_map` paramétrable (source de tuiles) + ortho IGN |
| A | `e5bbbfb` | adresse BAN en évidence (+ fallback) |
| B | `6840436` | photo aérienne IGN (ortho) + contour |
| C | `51a1f35` | points clés dérivés des facteurs |
| D | `309825b` | mise en page + détail sourcé condensé |
| E | `c005d95` | parité vue↔export (PDF) |

---

## Lot 0 — Constat (validé avant code)
- Pack = `share_public` (`partners.py`), HTML rendu serveur à `/p/{token}`.
- Adresse BAN = `f["adresse"]` (None pour ~0,01 %). Géométrie = `ST_AsGeoJSON` de `parcels`.
- Photo : réutilise `build_situation_map` (`flash/carte.py`) — tuiles positionnées (data-URI) + contour SVG.
- Facteurs = `f["lines"]` : `{layer, weight (signé/None), result, detail, source, date}`.

## FIX A — Adresse en évidence
Adresse BAN affichée **sous l'IDU, en gras blanc 17 px** (ce qu'un apporteur regarde en premier) ; l'IDU
passe en gris technique. **Fallback honnête** : parcelle sans adresse → IDU + commune seuls, **jamais**
d'adresse inventée (preuve : `pack-fallback-sans-adresse.png`).

## FIX B — Photo aérienne (tuiles IGN + contour)
Vue aérienne via les **tuiles ORTHO IGN** (Géoplateforme WMTS, grille PM = même Z/X/Y qu'OSM, **libre,
aucune clé Maps**), centrée sur la parcelle, **contour** en surimpression (violet, comme le halo de
sélection de l'app). **Image STATIQUE** : `build_situation_map` (paramétré `tile_url`/`tile_mime`/
`cache_prefix`/`attribution`) renvoie des tuiles data-URI + polygone SVG, mis à l'échelle de la largeur
du pack → **imprimable**, pas de carte interactive. Défensif : réseau/géométrie absents → pas de photo,
jamais d'erreur. Preuve : `pack-B-photo-adresse.png`, `pack-complet.png`.

## FIX C — Points clés (déterministe, équilibré, honnête)
`_points_cles(lines)` — **pur formatage des facteurs, AUCUNE IA** :
- **Forces** = facteurs de poids `> 0` (top 5) → titre de pitch par couche (`zonage_plu_gpu` → « Terrain
  constructible », `sitadel` → « Dynamique de construction active », `dvf` → « Marché porteur », `amenites`
  → « Équipements à proximité »…) + le `detail` tracé.
- **Attentions** = facteurs de poids `< 0` (top 4, plus fort d'abord) → `residuel_socle` → « SDP résiduelle
  limitée », `parc_national` → « Zonage protégé », `risques` → « Aléa naturel »…
**Honnêteté prouvée** (97401000AI1188) : la pénalité `residuel_socle -10` **apparaît** en attention
(« SDP résiduelle 166 m² — une maison — hors cible collectif ») + Parc national + aléa. Le pack ne survend pas.

## FIX D — Mise en page + détail sourcé
Structure maquette : identité (IDU + **adresse**) → **photo aérienne** → 3 stats (qualité/accessibilité/
complétude) → **POINTS CLÉS** → **DÉTAIL SOURCÉ** (en-tête + « chaque donnée porte sa source — pour le
promoteur qui vérifie » + la liste des facteurs, chacun avec sa source PLU/GPU, OSM, DVF, SITADEL,
Géorisques…). Badge de traçabilité (« identifié par… le… · consulté le… · lien traçable ») conservé.
Charte sombre + mono pour l'IDU/technique. Preuve : `pack-complet.png`.

## FIX E — Parité vue↔export
Le pack `/p/{token}` **est** un document HTML **auto-porté** (photo en data-URI, aucun réseau au rendu) →
l'**impression PDF rend l'identique** (adresse, photo IGN + contour, points clés, détail sourcé). Aucun
code d'export dédié nécessaire — la vue EST l'export partageable. Preuve : `pack-export.pdf`
(2 pages, page 1 identique à l'écran).

---

## Non-régression & garanties
- **Zéro touche scoring** : `git diff` = `partners.py` (pack) + `flash/carte.py` (tuiles, paramétrage
  rétro-compatible — le pré-dossier reste sur OSM par défaut). Aucun fichier scoring/cascade/étage 0/engine.
- Traçabilité (badge « identifié par… lien traçable ») conservée. Filigrane/horodatage/compteur de vues intacts.
- Défensif : photo absente (réseau/géométrie) → pack valide sans photo ; adresse absente → fallback propre.
- `ruff` : seul l'`E402` pré-existant subsiste.

*Commits séparés sur `feat/apporteur-pack`. Pas de merge.*
