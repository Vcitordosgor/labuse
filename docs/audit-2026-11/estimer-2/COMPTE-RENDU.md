# ESTIMER-2 — un total en euros plus juste, une nature lue sur la vente, une fiabilité par bien

**Branche** `fix/estimer-2` · worktree `~/Desktop/labuse-estimer` · ports 9170/6370 · base locale `labuse`
(434 582 parcelles, DVF arrêté 2025-12-31). **Aucun merge, aucun accès prod.** Périmètre strict :
**« Estimer un bien », son PDF et son Doc** — le marché DVF (médiane €/m²), le résiduel/SDP et les PPR
sont des sessions sœurs (MARCHE-UNIQUE-1, SDP-UNIQUE-1, PPR-UNIQUE-1), non touchés ici.

## La décision de Vic

Le total en euros de la maison **reste affiché**. Il devait devenir **plus juste**, et porter une
**mention d'incertitude** quand la surface habitable n'est pas connue. Cinq correctifs du registre NU-1
(lots D et E) ont été exécutés, tous dans l'outil Estimer.

## Ce qui était faux (registre NU-1)

- **D-009 / E-021** — la « valeur indicative » = **emprise au sol BD TOPO × €/m² HABITABLE** : deux
  surfaces hétérogènes. L'emprise au sol d'une maison vaut en moyenne ~2× sa surface habitable ; pour
  un immeuble en copropriété, l'emprise du bâti entier × le €/m² d'un seul appartement donnait des
  totaux **jusqu'à ×15**. Témoin IE0241 : 422 000 € affichés à côté d'une dernière vente à 205 000 €.
- **E-022** — la **nature** du bien était lue sur l'**état actuel de la parcelle** (`taux_emprise_pct`),
  pas sur le bien **vendu**. Un terrain vendu nu posé sur une parcelle portant un petit bâti était
  valorisé en mini-maison (BN2939 : 59 000 € au lieu de 140 000 €).
- **E-026** — la branche **copropriété** passait *après* la branche « terrain nu » : un lot de copro à
  faible emprise sortait en terrain.
- **D-012** — une parcelle **non mesurée** (taux d'emprise inconnu) était affirmée « bâtie, maison » et
  recevait un ordre de grandeur bâti fabriqué.
- **E-024** — la fiabilité était un **±% FIXE par segment** (« ±28 % pour toute maison »), indépendant
  du nombre de comparables et de leur dispersion.

## Les correctifs (tous dans `src/labuse/pige/api.py` — point unique écran == PDF == Doc)

1. **Surface du total (D-009, E-021)** — `_surface_pour_total`, DANS CET ORDRE :
   1. la **surface bâtie de la dernière vente DVF** de la parcelle si elle existe ;
   2. sinon **emprise au sol × le ratio médian (surface vendue / emprise)** mesuré sur les ventes de
      **maisons de la commune** (ratio + assise **journalisés** : `log.info`).
   **Plus jamais l'emprise brute × un prix habitable.** Le libellé dit quelle surface a servi ; quand
   elle est estimée : *« Surface habitable estimée d'après l'emprise au sol : total indicatif »* + le
   ratio et son assise. Libellé et note sont **servis par le back** (`valeur_indicative.ligne`/`note`),
   lus à l'identique par l'écran (`AnalyserAnnonce.tsx`) et le PDF (`exports/blocs/annonce.py`).

2. **Nature depuis la dernière mutation DVF (E-022)** — `_derniere_mutation_dvf` lit la dernière vente
   (`'Vente'` / `'Vente terrain à bâtir'`) et en déduit **maison / appartement / terrain** + la surface
   bâtie vendue. La nature de l'estimation suit cette mutation ; à défaut de vente, l'état de la parcelle
   (emprise). Un terrain vendu nu n'est plus valorisé comme une maison.

3. **Copro avant terrain nu (E-026)** + **non mesuré (D-012)** — `estimation_annonce` teste la
   copropriété **en premier** (comparateur appartements, pas de total bâti), puis le terrain, puis le
   bâti. Une parcelle non mesurée reste **« Bâti non mesuré »** (jamais « bâtie, maison ») ; sans surface
   disponible, aucun total n'est fabriqué.

4. **Fiabilité bien par bien (E-024)** — `_fiabilite_bien(n, médiane, q1, q3, repli)` : bandes sur le
   **nombre de comparables** et leur **dispersion** (IQR relatif (q3−q1)/médiane), calibrées sur le banc.
   Le **±% affiché est l'écart médian réellement mesuré** de la bande (honnête), plus un ±28 % collé à
   toute maison.

L'arête de lecture `dvf_mutations_parcelle ← pige/api.py` est **déclarée** au registre
(`registre/lectures.py`) — le graphe reste exact dans les deux sens.

## Témoins — AVANT / APRÈS (écran == PDF, prouvé champ par champ)

| Parcelle | AVANT | APRÈS | Vente réelle |
|---|---|---|---|
| **CT1164** maison, aucune vente DVF | 784 000 € (emprise 239 m² × 3 280, *Limitée ±28 %*) | **400 000 €** — « Surface habitable estimée d'après l'emprise au sol (122 m²) », ratio 0,51 sur 1 759 ventes, *Moyenne ±23 %* | — (audit ≈ 295 000) |
| **BN2939** terrain vendu nu | 59 000 € — **classé MAISON** (26 m² × 2 285, *Limitée ±28 %*) | **117 000 €** — **terrain nu** (649 m² × 180), *Moyenne ±19 %* | **140 000 €** (DVF 2025) |
| **AV0167** copropriété | appartement 4 500 €/m², pas de total, *Moyenne ±17 %* | appartement 4 500 €/m², pas de total, **fiabilité par bien → Élevée ±18 %** | — |
| **IE0241** maison vendue 63 m² | 422 000 € — **classé APPARTEMENT** (196 m² × 2 152, *Moyenne ±17 %*) | **220 000 €** — **maison** (surface bâtie DVF 63 m² × 3 485), *Élevée ±18 %* | **205 000 €** (DVF 2024) |

`écran == PDF` vérifié pour les 4 (mêmes `valeur_indicative`, `median`, `fiabilite_mot`, `precision_pct`
issus du point unique `estimation_annonce`, rendus par le même `rendu_parcelle`).

## Recette — banc rejoué sans fuite (méthode ESTIMATION-BANC-2)

`docs/audit-2026-11/estimer-2/banc.py` — réutilise la machinerie **point-in-time** du banc 2 (comparables
strictement `date < date_vente` + exclusion de la mutation jugée). Univers : **5 892 ventes DVF 2025**
mono-parcelle des 24 communes. Garde-fou de surface : la surface du total APRÈS n'utilise **jamais** la
vente jugée (dernière vente **antérieure**, sinon emprise × ratio communal).

### Erreur du TOTAL en € — le chiffre sur lequel le client s'ancre (AVANT → APRÈS)

| Segment | médian \|écart\| | part à ±20 % |
|---|---|---|
| Toutes ventes bâties | **246 % → 31 %** | 8 % → 32 % |
| Maison | **86 % → 32 %** | 14 % → 32 % |
| Appartement | **1 409 % → 31 %** | 1 % → 33 % |
| Copropriété (parcelle) | **1 462 % → 31 %** | 1 % → 34 % |

Surface servie APRÈS : 2 162 via la dernière vente DVF, 2 147 via emprise × ratio (≈ moitié / moitié).
L'erreur du total chute d'un facteur **≈ 3** pour les maisons et d'**un à deux ordres de grandeur** pour
les appartements/copropriétés (où l'emprise du bâti entier gonflait un total d'appartement).

### Nature (E-022)

**757 / 1 217 (62 %)** des ventes de **terrain nu** 2025 reposent sur une parcelle que l'ancienne règle
« emprise » aurait valorisée en **bâti** — exactement le défaut que la lecture de la mutation corrige
(cf. BN2939). (L'erreur €/m² par segment est, elle, quasi inchangée — la médiane €/m² reste la médiane
de secteur de MARCHE-UNIQUE-1 ; mon périmètre est la **surface** et la **nature**, pas le prix au m².)

### Calibration des bandes de fiabilité (E-024) — « Élevée » tient ce qu'elle promet

Sur les 4 324 estimations bâties du banc, par bande servie :

| Bande | n | médian \|écart €/m²\| | ±20 % |
|---|---|---|---|
| **Élevée** (n≥15 · dispersion ≤0,30) | 1 292 | **18,0 %** | 54 % |
| **Moyenne** | 2 884 | 22,2 % | 45 % |
| **Limitée** (n<8 · dispersion >0,75 · repli commune) | 148 | 36,2 % | 30 % |

Le **plancher d'erreur €/m² de l'estimateur** (médiane de secteur, pas un AVM) est **~18 %** même dans
la meilleure bande : « Élevée » **sert ce ±18 % mesuré** — elle tient sa promesse parce que le ±% affiché
**est l'écart réel**, et non un « <15 % » que l'estimateur ne peut pas tenir. Les trois bandes sont
monotones et distinctes (18 / 23 / 36 %) ; les seuils sont posés en constantes nommées
(`_FIAB_N_ELEVEE`, `_FIAB_DISP_ELEVEE`, `_FIAB_N_MIN`, `_FIAB_DISP_LIMITEE`, `_FIAB_ECART`).

## Tests

- **pytest** (famille unitaire `-m "not db and not local and not reel and not network"`) :
  **2 781 passés**. 1 échec **pré-existant et environnemental** (`test_boot_verrou_1` —
  `OperationalError: failed to resolve host 'None'`, base applicative non configurée sur ce Mac ;
  reproduit à l'identique en `git stash` de mes changements).
- `tests/test_reparations1_lot2.py` (graphe des arêtes exact) : **vert** après déclaration de l'arête
  `dvf_mutations_parcelle ← pige/api.py`.
- `tests/test_annonce_pdf.py` : **vert** (fixture + assertions mises à jour au nouveau libellé de surface
  et à la note d'incertitude).
- **tsc -b** : 0 erreur. **vitest** : **305 passés / 64 fichiers**.

## Garde-fous & choix assumés

- **No-leak** : le banc exclut la vente jugée et le futur du vivier de comparables **et** de la surface
  (dernière vente *antérieure* seulement). La **nature** du bien (terrain vs maison) est une propriété
  observable du sujet, pas la cible prédite ; elle est traitée comme telle dans la mesure de E-022.
- La **médiane €/m²** n'est pas touchée (session MARCHE-UNIQUE-1) ; mon total = **surface corrigée ×**
  cette médiane. Quand MARCHE-UNIQUE-1 sera mergé, le total s'améliorera encore via la médiane.
- La **fourchette** du total garde la largeur ±% du segment (précision €/m²) ; la **note** porte la
  réserve propre à la surface estimée (D-009). Le badge communique la fiabilité du **€/m²**.
- Rien touché hors Estimer : résiduel/SDP, PPR, scoring, Radar inchangés.

## Fichiers

| Fichier | Correctif |
|---|---|
| `src/labuse/pige/api.py` | `_derniere_mutation_dvf`, `_ratio_surf_emprise_commune`, `_surface_pour_total`, `_fiabilite_bien` ; `estimation_annonce` réordonnée (copro→terrain→bâti) ; `rapport_parcelle` libellé « Bâti non mesuré » |
| `src/labuse/exports/blocs/annonce.py` | `_valeur_indicative` lit le libellé/note servis (écran == PDF) |
| `frontend/src/components/outils/AnalyserAnnonce.tsx` + `lib/api.ts` | lit `valeur_indicative.ligne`/`note`/`surface_source` |
| `src/labuse/registre/lectures.py` | arête `dvf_mutations_parcelle ← pige/api.py` déclarée |
| `tests/test_annonce_pdf.py` | fixture + assertions au nouveau libellé |
| `docs/audit-2026-11/estimer-2/banc.py`, `METRIQUES.json`, `PAR-VENTE.csv` | banc rejoué + mesures |

Rejeu banc : `LABUSE_DATABASE_URL=postgresql+psycopg:///labuse <venv>/python docs/audit-2026-11/estimer-2/banc.py`
