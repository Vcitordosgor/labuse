# ESTIMER-PRECISION-1 — un total plus juste : surface saisissable, comparables pondérés, fiabilité honnête

**Branche** `feat/estimer-precision-1` · worktree `~/Desktop/labuse-precision` · ports 9210/6410 · base locale
`labuse` (434 582 parcelles, DVF arrêté 2025-12-31). **Aucun merge, aucun accès prod.** Périmètre strict :
**« Estimer un bien », son PDF, son Doc et son banc.**

## L'objectif chiffré et le verdict, dit franchement

| Segment | Départ (total, surface auto) | Objectif | **Atteint ?** |
|---|---|---|---|
| **Appartement / copropriété** | 31 % | < 15 % | **OUI — 14,5 % (surface connue)** ✅ |
| **Maison** | 32 % | < 20 % | **NON — 27,2 % (plancher donnée)** ❌ |

Le banc (ci-dessous) **règle sur les ventes 2024** et **annonce sur les ventes 2025 jamais vues pendant le
réglage** ; aucune vente ne s'estime elle-même (comparables strictement `date < date_vente`, mutation jugée
exclue). **C'est la seule mesure qui compte.**

Deux leviers, deux résultats :

1. **La surface était le premier facteur d'erreur.** Le départ 32 %/31 % mélangeait l'erreur du prix au m²
   ET l'erreur de la *surface estimée* (emprise au sol × ratio). Dès que la **surface habitable est connue**
   (le champ saisissable, prérempli depuis la dernière vente DVF), l'erreur du total **se réduit à l'erreur
   du €/m²**. C'est le gain structurel du mandat.
2. **Les comparables pondérés tiennent l'objectif pour l'appartement** (€/m² 17,2 % → 14,5 %) **mais pas pour
   la maison** : son €/m² plafonne à ~27 % quelle que soit la méthode. Nous avons **testé un gradient boosting**
   (entraîné jusqu'à 2024, testé sur 2025, toutes les variables observables de la base) : **27,8 %, pire que
   les comparables**. Le prix d'une maison à La Réunion dépend d'une qualité/d'un état que DVF ne porte pas ;
   **aucune méthode ne descend sous 20 %** sur la donnée disponible. Décision retenue : **pas de modèle servi**
   (gain nul + rupture de la règle « pas de ML en prod »), et **une fiabilité honnête** (cf. §5).

## 1 — Surface habitable saisissable (écran = PDF = Doc)

Dans l'entrée par **adresse**, un champ facultatif **« Surface habitable »**, **prérempli** quand la dernière
vente DVF la donne (`estimation.surface_dvf_m2`). S'il est rempli, le total l'utilise, **libellé « surface
saisie »**. Le paramètre `surface_hab` voyage par le **point unique** `estimation_annonce` → `rapport_parcelle`
→ builder PDF/Doc : l'écran (`AnalyserAnnonce.tsx`), le PDF (`exports/blocs/annonce.py`) et le Doc
(`DocumentsView.tsx`, route `/analyse-annonce/{idu}.pdf?surface_hab=…`) lisent **exactement la même valeur**.

Priorité de la surface du total (`_surface_pour_total`) : **0. surface saisie** › 1. dernière vente DVF ›
2. emprise × ratio communal. Témoin **IE0241** : sans surface → 251 000 € (63 m² DVF) ; **avec 90 m² saisis →
359 000 €, libellé « Surface habitable saisie (90 m²) »**, identique à l'écran, au PDF et au Doc.

**Total quand la surface est connue (banc 2025, = erreur du €/m²)** : appartement **14,5 %**, copropriété
**14,8 %**, maison **27,2 %**. C'est le régime cible du mandat (« mesurer au banc le total quand la surface est
connue ») : l'appartement **tient l'objectif**.

## 2 — Comparables pondérés par la ressemblance

`marche_service.comparateur_bien` ne sert plus une **médiane simple** mais une **médiane PONDÉRÉE** : chaque
vente compte selon sa **distance** (gaussien), son **écart de surface** bâtie (laplacien), pour les **maisons**
son **écart de taille de terrain**, et son **ancienneté** (demi-vie). Les **prix sont ramenés** au comparable le
plus récent par un **indice local de dérive** (médiane €/m² de la commune, 2019-2024, figée, bornée
[−4 % ; +12 %]/an, facteur de ré-indexation clampé [0,7 ; 1,6]). Les **8 comparables affichés** sont désormais
**ceux qui pèsent le plus** (prix bruts affichés). Les €/m² aberrants de la commune restent écartés (filtre
z-MAD existant). Poids **réglés par segment sur 2024** (`_POIDS_SEGMENT`).

**Erreur du €/m² (banc 2025, AVANT médiane simple → APRÈS pondérée servie)** :

| Segment | AVANT | APRÈS | ±20 % |
|---|---|---|---|
| **Appartement** | 17,2 % | **14,5 %** | 57 % → 62 % |
| **Copropriété** | 17,3 % | **14,8 %** | 57 % → 62 % |
| **Maison** | 26,8 % | 27,2 % (neutre) | 39 % |
| Terrain nu (méthode inchangée) | — | 36,2 % | 32 % |

**Contribution de chaque terme (ablation 2025, appartement)** : dérive **1,1 pt** (le plus fort), ancienneté
**0,6 pt**, distance **0,5 pt**, surface **0,1 pt**. L'**écart d'altitude** du mandat (« les Hauts et le
littoral n'ont pas le même marché ») a été mesuré via la **distance au trait de côte** (le MNT RGE ALTI n'est
**pas chargé** sur cette base : 2 dalles de 2 km² qui ne couvrent aucune des 24 communes ; le trait de côte, lui,
couvre toute l'île et l'altitude croît avec l'éloignement de la mer sur une île volcanique) : **contribution
0,1 pt**. Elle n'est **pas servie** — elle ne justifie pas un index spatial au serve-time. C'est dit franchement.

Pour la **maison**, tous les termes sont **neutres** (~27 %) : la pondération ne nuit pas (on sert une
pondération douce et cohérente) mais ne peut rien gagner — l'erreur tient à une hétérogénéité (qualité, état,
micro-emplacement) que DVF ne décrit pas.

## 3 — Le modèle (gradient boosting) : testé, écarté

Le mandat autorise un modèle **si le point 2 n'atteint pas l'objectif** — c'est le cas de la maison. Nous l'avons
donc **mesuré** (hors servi, `scikit-learn` déjà déclaré en `[ml]/[ci]`) : `HistGradientBoostingRegressor`
entraîné jusqu'à **2024**, testé sur **2025**, sur toutes les variables observables (surface, terrain, distance
côte, x/y, commune, médiane comparable du secteur).

| Segment | Comparables pondérés | **GBM** | GBM × comparables |
|---|---|---|---|
| **Maison** | 27,2 % | **27,8 %** (pire) | 26,6 % |
| Appartement | 14,5 % | 13,5 % | 14,4 % |

**Conclusion** : le GBM n'atteint pas l'objectif maison (27,8 % > 20 %) et n'apporte rien à l'appartement que
les comparables (explicables) ne donnent déjà. L'intégrer imposerait `scikit-learn` **sur le serveur de prod**
(contraire à l'architecture « la prod sert des scores pré-calculés, jamais de ML »). **Décision (validée) :
aucun modèle servi, aucune dépendance ajoutée.**

## 4 — Recette banc 2025 par zone et par commune (total surface connue, méthode servie)

**Zone (distance au trait de côte : littoral ≤ 1 km, Hauts ≥ 4 km)** :

| Zone | Maison | Appartement |
|---|---|---|
| Littoral | 29,6 % | 15,5 % |
| Médians | 28,8 % | **13,8 %** |
| Hauts | 24,8 % | 15,3 % |

**Commune la mieux / la moins bien servie (maison, n ≥ 30)** : mieux **97414 → 19,3 %** (n=164, **sous 20 %**),
97404 → 20,0 %, 97408 → 22,8 % ; moins 97407 → 36,3 %, 97411 → 37,0 % (n=278), 97424 → 51,7 % (n=35). La maison
**atteint l'objectif dans les secteurs denses** (ex. 97414) — ce qui justifie la fiabilité ciblée du §5 plutôt
qu'une promesse uniforme intenable.

## 5 — Fiabilité recalibrée sur la nouvelle méthode (honnête)

`_fiabilite_bien` est désormais **par segment** et recalibrée sur la **grille (n × dispersion) du banc 2025**.
Le **±% servi EST l'écart médian mesuré** de la bande — « Élevée » ne s'affiche que là où le banc le **tient**.

- **Appartement / copropriété** : « Élevée » = n ≥ 15 **et** dispersion ≤ 0,40 → mesuré **~14 % → ±15 %**
  (tient l'objectif) ; « Moyenne » → ±18 % ; « Limitée » (n < 8, dispersion > 0,75, repli commune) → ±30 %.
- **Maison** (plancher ~27 %) : « Élevée » **réservée** au régime dense + homogène où le banc confirme < 20 %
  (**n ≥ 40 et dispersion ≤ 0,25** → mesuré ~13-21 % → ±20 %) ; partout ailleurs **« Moyenne » ±26 %** ou
  **« Limitée » ±36 %**, avec une **fourchette large**. On ne promet jamais une précision que la donnée
  n'autorise pas.

## 6 — Les quatre témoins : écran = PDF = Doc (prouvé champ par champ)

| Témoin | Nature | €/m² | Total | Fiabilité | Avec surface saisie |
|---|---|---|---|---|---|
| **CT1164** `97416000CT1164` | maison, sans vente DVF | 3 920 | 478 000 € (122 m², emprise×ratio) | Moyenne ±26 % | — |
| **BN2939** `97422000BN2939` | terrain nu | 180 | 117 000 € | Moyenne ±19 % | — |
| **AV0167** `97404000AV0167` | copropriété | 2 971 | — (lot inconnu) | Moyenne ±18 % | — |
| **IE0241** `97411000IE0241` | maison, vente 63 m² | 3 990 | 251 000 € | Moyenne ±26 % | 90 m² → **359 000 €** |

Pour les quatre, `écran (estimation_annonce)` == `rapport_parcelle` (PDF/Doc) == HTML rendu, à l'euro près
(médiane, total, mot de fiabilité). IE0241 vendu 205 000 € en 2024 ; l'estimation « à l'état de marché le plus
récent » le situe 22 % au-dessus — **dans la bande ±26 % de la maison**, honnête (c'est le plancher assumé).

## 7 — Tests

- **Banc** `docs/audit-2026-11/estimer-precision-1/banc.py` (réglage 2024 → annonce 2025, no-leak ;
  `METRIQUES.json`, `PAR-VENTE-2025.csv`).
- **pytest** (famille unitaire `-m "not db and not local and not reel and not network"`) : **2 801 passés**,
  49 skipped. **4 échecs PRÉ-EXISTANTS et ENVIRONNEMENTAUX**, reproduits à l'identique après `git stash -u`
  (base applicative non configurée → `host 'None'` ; `anthropic` absent → `ModuleNotFound` / modèle introuvable ;
  montages de routes conditionnels non chargés → allowlist). **0 échec introduit.**
- `tests/test_estimer_precision1.py` (neuf, 9 tests) : surface saisie prioritaire + libellé, bandes de
  fiabilité par segment, médiane/quantiles pondérés — **verts**.
- `tests/test_annonce_pdf.py` : **17 verts**.
- **tsc -b** : 0 erreur. **vitest** : **301 passés / 63 fichiers**.
- Recette témoins écran == PDF == Doc : **4/4 cohérents** (cf. §6).

## 8 — Écart final à l'objectif, dit franchement

- **Appartement / copropriété : objectif ATTEINT** — 14,5 % / 14,8 % du total quand la surface est connue
  (< 15 %), contre 31 % au départ. Levier : surface saisissable + médiane pondérée (dérive + ancienneté +
  distance).
- **Maison : objectif NON ATTEINT — 27,2 %** du total surface connue, pour 20 % visés. **Ce n'est pas un
  défaut de réglage** : la médiane simple (26,8 %), la médiane pondérée (27,2 %) et un gradient boosting
  (27,8 %) convergent toutes vers ~27 %. **La donnée DVF ne porte pas ce qui fait le prix d'une maison** (état,
  prestations, exposition fine). L'objectif **est atteint dans les secteurs denses** (97414 : 19,3 %) — c'est
  exactement là que la fiabilité « Élevée » maison est accordée, et nulle part ailleurs. Partout ailleurs, le
  total maison est servi en **fourchette large avec une réserve explicite**, jamais une fausse précision.

## 9 — Fichiers

| Fichier | Changement |
|---|---|
| `src/labuse/marche_service.py` | `comparateur_bien` → médiane **pondérée** (distance/surface/terrain/ancienneté) + indice local de dérive + 8 comparables = plus gros poids ; `_drift_commune`, `_med_quantiles_pondere`, `_POIDS_SEGMENT` |
| `src/labuse/pige/api.py` | `_surface_pour_total` priorité 0 « surface saisie » ; `_fiabilite_bien` **par segment** recalibré ; `estimation_annonce`/`rapport_parcelle`/endpoints `surface_hab` ; `surface_dvf_m2` exposé |
| `src/labuse/exports/builder.py`, `src/labuse/api/documents.py` | `surface_hab` filé jusqu'au PDF/Doc |
| `frontend/.../AnalyserAnnonce.tsx`, `documents/DocumentsView.tsx`, `lib/api.ts` | champ « Surface habitable » (outil + Doc), prérempli, filé au PDF |
| `tests/test_estimer_precision1.py` | garde-fous unitaires (neuf) |
| `docs/audit-2026-11/estimer-precision-1/` | banc + `METRIQUES.json` + `PAR-VENTE-2025.csv` + ce compte-rendu |

Rejeu banc : `LABUSE_DATABASE_URL=postgresql+psycopg:///labuse <venv>/python docs/audit-2026-11/estimer-precision-1/banc.py`
