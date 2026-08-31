# SECTEUR-2 — compte-rendu

Branche `feat/secteur-1` (corrige SECTEUR-1 + deux ajouts), arbre propre à l'ouverture. **Un seul commit
de plus. Ne pas merger.** Golden non touché · un seul moteur · API + front redémarrés avant recette
(preuves : `docs/SECTEUR-2/captures/`).

---

## T1 — Mon secteur : méthode « état de l'art » dans le moteur commun + visuel

**Visuel** (`MonSecteur.tsx`) : les chiffres ne se coupent plus — grammaire de l'**en-tête à 4 chiffres
des fiches** (`.stats` / `.stat` / `.stat-l` / `.stat-v`, `tabular-nums` + `whitespace-nowrap`). Le bâti
est un bandeau de 4 cases alignées (Bâti secteur · Rayon · Ventes · Tendance 12 m) ; les médianes par
type aussi.

**Méthode, dans le moteur COMMUN** (`faisabilite/bilan.py::sector_price` — servi par la fiche « Marché et
secteur » ET Mon secteur ; `pige/signaux.py::_ref_local` — la référence Radar ; `mon_secteur._terrain_local`).
Un seul jeu de règles, partagé :
- **Exclusion des 5 % extrêmes** (`trim_extremes_5pct` : 2,5 % à chaque queue ; sous ~20 ventes, rien
  n'est retiré) — remplace l'ancien Tukey IQR, garde-fou de domaine [1000 ; 12000] conservé.
- **Segments homogènes type × période** : période RÉCENTE (5 ans) préférée, élargie seulement si
  l'échantillon récent ne tient pas ; type appartement → mixte → commune.
- **Rayon adaptatif jusqu'à n minimum** (`MIN_N_SECTEUR = 8`, constante) — le **rayon effectif est
  affiché** (`radius_m`).
- **Distributions avant/après** rendues (`distribution` : {avant, après, n_exclus_extremes, n_min_vise}).

**Preuve de cohérence** (`tests/test_mon_secteur_coherence.py` + mesure) — Mon secteur = « Marché et
secteur » de la fiche, à l'identique (même appel `sector_price`) :

| Parcelle | Mon secteur | fiche `sector_price` | rayon | écart commune |
|---|---|---|---|---|
| 97411000AW0735 (Saint-Denis) | 2 262 €/m² | 2 262 €/m² | 500 m | secteur 500 m · commune 2 556 (−12 %) |
| 97416000CR1129 (Saint-Pierre) | 2 758 €/m² | 2 758 €/m² | 1 000 m | commune 2 739 (+1 %) |
| 97422000BN2556 (Le Tampon) | 1 885 €/m² | 1 885 €/m² | 1 500 m | commune 1 693 (+11 %) |

L'écart avec la commune est expliqué en **une ligne** dans l'outil (« secteur 500 m · commune entière
2 556 €/m² (−12 %) »). Distribution visible (ex. AW0735 : 356 → 338 retenues, 18 extrêmes exclus, max
7 856 → 3 875 €/m²).

## T2 — Veille promoteurs = les OPÉRATIONS, pas le patrimoine

Refonte complète (`api/veille_promoteurs.py` + `VeillePromoteurs.tsx`) : l'outil montre ce que les
promoteurs / bailleurs / SEM **construisent**.

- **Opération = groupe de permis** (Sitadel) sur parcelles **contiguës**, **même propriétaire moral**
  (MAJIC), **même période** — règle en constantes documentées : `OP_CONTIG_M = 250` (centroïdes des
  permis ≤ 250 m), `OP_PERIODE_MOIS = 24`. Regroupement par SIREN puis union-find (contiguïté × période).
- Chaque opération : **un point sur la carte** (kind `operation`, ambre ; **menthe si une annonce neuve
  du Radar la cite** — copropriété rattachée), promoteur, commune, **logements** (somme), dates, état ;
  **nom** = citée par une annonce Radar sinon **libellé factuel** « N logements · Commune · AAAA ».
- **Par promoteur** : **frise par année** (opérations, logements) + **lien vers son Scan patrimoine**
  (`/{siren}/frise` renvoie `scan_patrimoine` ; `/{siren}/acquisitions` = le patrimoine) — les deux
  outils **se renvoient, ne se dupliquent pas**.
- **Recette** : 650 opérations / 3 742 logements depuis 2023. **CBO TERRITORIA** : 20 op / 226 lgt
  (2023 : 2 op·5 lgt … 2026 : 3 op·140 lgt). **SIDR** (SOCIETE IMMOBILIERE DEPARTEMENT REUNION) : 80 op /
  2 117 lgt. Captures `03`, `04`.

## T3 — Radar : un vrai bouton dans l'en-tête

`RadarView.tsx` — **« + Publier une annonce »** est un vrai bouton dans l'en-tête du Radar, **visible
admin** (détection `/moi`, même convention qu'AdminView ; un client connecté ne le voit pas), mention
« drapeau fermé — invisible des clients » quand le drapeau est fermé. Clic → Tour de contrôle, section
Radar (deep-link store `goAdminSection('radar')`, consommé au montage d'AdminView). La garde reste au
backend. Capture `05`.

## T4 — Couche VEFA / ECLN (diagnostic d'abord)

**Diagnostic** : l'**ECLN** (SDES) est **métropole seule → N/A pour le 974** (jamais à la parcelle,
secret statistique ; renoncement déjà documenté RAPPORT-KF-2 L2). **Écartée** — aucun **stock** n'est
servi (l'ECLN seule le porterait), jamais extrapolé. Ce que le 974 porte : les ventes **VEFA** de DVF
(`nature_mutation = 'Vente en l'état futur d'achèvement'`), maille **commune**, fenêtre 3 ans.

Couche `vefa_neuf` (`ingestion/vefa_neuf.py` + CLI `vefa-neuf-build` + `spatial_layers`, servie par
`/map/layers.geojson`) : **médiane €/m² bâti VEFA + n ventes** en **aplat commune choropleth** (tranche
de prix dans `subtype`). Peinte **seulement** là où **≥ 10 ventes** soutiennent la médiane — sinon la
commune est **absente** (jamais un chiffre inventé). Millésime (VEFA DVF, 3 ans, dernière vente
2025-12-31) et **source dans le « i »** ; le stock y est dit non couvert. **7 communes peintes** sur 24
(Saint-Denis 5 850, Saint-Pierre 5 524 … La Possession 4 169 €/m²), 17 sous le seuil. Capture `06`.

## T5 — « Zones du PLU officiel (brut) » → sous-option

**Mesure** : sur 431 663 parcelles, **42 648 (9,9 %)** sont réellement à cheval sur ≥ 2 zones PLU (2
zones couvrant chacune ≥ 10 % de la parcelle) ; 26,3 % en comptant les simples contacts de bord. Les
aplats bruts (non rattachés au cadastre) se lisaient mal contre la couche calibrée.

`LeftPanel.tsx` : la couche `zonage` **quitte le menu** (retirée de `LAYERS` + famille « Les zonages »)
et devient une **sous-option « Afficher les limites officielles (GPU brut) »** de la couche « Zonage PLU
par parcelle », **désactivée par défaut**, visible seulement quand la couche calibrée est active. Couper
la couche par parcelle éteint aussi la sous-option (jamais un aplat orphelin). Clé de store, MapView et
Legend inchangés. Capture `07`.

---

## Vérifications

- **tsc** 0 · **vitest** 108/108 · **vite build** OK.
- **pytest** : **2032 passed, 0 failed**, 32 skipped. Les **5 tests HTML périmés** signalés en SECTEUR-1
  sont **mis à jour** (`test_front_m2.py`, `test_front_reliquats.py`) vers les marqueurs réels de l'UI
  actuelle (TriCard → LigneParcelle/MiniLigne ; filtre « à analyser » retiré ; badge hors-critères et
  chips filtrants/indicatifs supprimés ; colonne « à analyser » du kanban retirée) — plus **aucun échec**.
- **Golden** : **119/119 PASS**, 0 FAIL, GARDE-RUN OK (431 663/431 663, `q_v11_m137`). **Intact** — le
  moteur `sector_price` reste **documentaire** (le prix de sortie NEUF gouverne le bilan/scoring, M-N
  P2-47) ; 0 fichier de scoring touché.
- **API + front redémarrés** (uvicorn :8000, build servi sous `/socle/`), recette Playwright → 7 captures
  `docs/SECTEUR-2/captures/`, **0 erreur JS**.

## Fichiers

Nouveaux : `src/labuse/ingestion/vefa_neuf.py`, `tests/test_mon_secteur_coherence.py`,
`frontend/qa/secteur2_captures.mjs`.
Modifiés : `faisabilite/bilan.py` (trim 5 % + segments + distribution), `pige/signaux.py` (`_ref_local`),
`api/mon_secteur.py` (écart commune + distribution + terrain), `api/veille_promoteurs.py` (opérations +
frise), `api/app.py` (`_MAP_LAYER_KINDS` + vefa router déjà monté), `cli.py` (`vefa-neuf-build`),
`frontend/src/lib/api.ts`, `.../outils/MonSecteur.tsx`, `.../outils/VeillePromoteurs.tsx`,
`.../outils/RadarView.tsx`, `.../outils/registry.ts`, `.../admin/AdminView.tsx`, `.../panel/LeftPanel.tsx`,
`.../map/MapView.tsx`, `.../map/Legend.tsx`, `.../lib/layers.ts`, `frontend/src/store/useApp.ts`,
`tests/test_front_m2.py`, `tests/test_front_reliquats.py`.
