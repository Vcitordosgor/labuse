# Lot C — Captures & preuve DOM

Rendu réel : API worktree sur `127.0.0.1:8000` (base `labuse`, `parcel_blocs` bâtie par le batch),
front vite `localhost:5180/socle/`, pilotage Playwright. Les captures d'écran (viewport) sont dans
`captures/` ; comme le panneau outil est petit à l'échelle du viewport et que la carte est un canvas
WebGL, la **preuve DOM** ci-dessous (texte réellement rendu, lu du DOM) fait foi.

## Captures
- `captures/blocs-00-accueil.png` — l'app au chargement.
- `captures/blocs-01-menu-outils.png` — le menu Outils (« 17 outils fonciers ») avec la nouvelle entrée.
- `captures/blocs-02-liste.png` — l'outil ouvert, la liste des blocs.
- `captures/blocs-03-detail.png` — un bloc déplié (ses parcelles).
- `captures/blocs-04-etat-vide.png` — l'état vide honnête.

## Preuve DOM

**Entrée du menu Outils** (`button` réellement présent) :
> « Blocs fonciers — Les assiettes d'un même propriétaire, sur toute l'île. »

**Bandeau doctrine** (haut du panneau) :
> « Les parcelles contiguës d'un même propriétaire regroupées en une assiette — ce qu'un promoteur ne
> voit pas parcelle par parcelle. **Personnes morales seulement (SIREN)** : les particuliers n'ont pas
> d'identité stable d'une parcelle à l'autre. »

**Entrée** : sélecteur `Périmètre` (Toute l'île + les 24 communes) · filtres à paliers
`Surface totale` (peu importe / ≥ 1 000 m² / ≥ 5 000 m² / ≥ 1 ha / ≥ 5 ha) ·
`Résiduel` (peu importe / ≥ 200 / ≥ 500 / ≥ 1 000 / ≥ 5 000 m²) · `Parcelles` (≥ 2 / ≥ 3 / ≥ 6 / ≥ 11).

**Bandeau de tête** (île entière) :
> « **11 225 blocs** · signal **propriétaires PM DGFiP** (millésime 2025) au 07/09/2026 — toute l'île »

**Première carte** (tri résiduel décroissant) :
> CBO TERRITORIA · **323 345 m²** [Estimé] · 118 parcelles · 2 782 076 m² · Saint-Paul · A AU2c AU2h …

**Détail déplié** (118 membres, chacun IDU + surface + zone + résiduel + « Voir la fiche → ») :
> `97415000DK1169` 347 993 m² · AU2h — 281 159 m² — Voir la fiche →
> `97415000DE1136` 27 965 m² · U2h — 22 652 m² — Voir la fiche →
> `97415000DK1002` 19 669 m² · AU2h — 8 583 m² — Voir la fiche →

**Gestes présents** (comptés dans le DOM) : `Assembler ce bloc →` (1), `Scan patrimoine →` (par carte),
118 × `Voir la fiche →`, `✉ Préparer les courriers (N) →`. L'emprise du bloc est mise en surbrillance
sur la carte tant que le détail est ouvert (mécanisme `useModuleMap`, IDU des membres).

**État vide honnête** (Cilaos + surface ≥ 5 ha + résiduel ≥ 5 000 + ≥ 11 parcelles) :
> « Aucun bloc de deux parcelles ou plus à **Cilaos** (surface ≥ 50 000 m²) (résiduel ≥ 5 000 m²)
> (≥ 11 parcelles) au 07/09/2026. » — jamais de zéros, le périmètre et la date sont nommés.

## Propriétaires publics écartés par défaut (ajout)

Classification par la **catégorie juridique de la source** (`proprietaire_type.classify_dgfip` :
groupe DGFiP + forme juridique — commune, État, collectivité, établissement public/EPF, SEM), **jamais
une liste de SIREN/noms en dur**. Île entière : **6 361 privés servis, 4 864 publics écartés**.

Preuve DOM (le screenshot expire sur le canvas WebGL — garde-fou → preuve DOM) :
- Case `Inclure les propriétaires publics` présente, **décochée par défaut**.
- Bandeau par défaut :
  > « **6 361** blocs · signal propriétaires PM DGFiP (millésime 2025) au 07/09/2026 — toute l'île ·
  > **4 864 propriétaires publics écartés** »
- Case cochée → bandeau « **11 225** blocs … » (mention « écartés » retirée), 200 lignes.
- Endpoint réel : défaut `total=6361, n_publics=4864, inclure_publics=false` ; `inclure_publics=true`
  → `total=11225`. Premier privé servi : **CBO TERRITORIA** (`is_public=false`) ; classés publics :
  COMMUNE DE…, ETS PUBLIC FONCIER DE LA REUNION, SEM d'aménagement.

## Perf (mesurée sur la même base, endpoint réel)
| Périmètre | Liste (page 200) | Total | Détail |
|---|---|---|---|
| Toute l'île | 22,2 ms | 11 225 | 2,2 ms |
| Saint-Denis (dense) | 20,9 ms | 1 533 | 1,0 ms |
| Salazie (rurale) | 21,5 ms | 147 | 0,9 ms |
| Cilaos (rurale) | 21,0 ms | 143 | 0,9 ms |
