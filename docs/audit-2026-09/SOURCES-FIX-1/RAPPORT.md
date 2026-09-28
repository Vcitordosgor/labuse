# SOURCES-FIX-1 — les 3 écarts de SOURCES-AUDIT-2 + les 5 mortes

**Branche** `fix/sources-fix-1` (base `origin/main`). Worktree `/Users/openclaw/Desktop/labuse-sources`.
Référence : `docs/audit-2026-09/SOURCES-AUDIT-2/RAPPORT.md` (origin/audit/sources-2).

## Ce qui a été fait

### 1. DVF — une seule médiane (écart E1)
- Nouveau point de calcul UNIQUE : **`src/labuse/dvf_mediane.py:mediane_bati`** — médiane €/m² bâti sur un
  périmètre (zone GeoJSON **ou** commune), sur **`dvf_mutations`** (maille MUTATION), ventes bâties
  (surface réelle bâtie ≥ 20 m²), fenêtre 36 mois, ratio borné [1 000 ; 12 000], seuil n = 5.
- `zone.marche_zone` (Étude de zone, ex-`zone.py:435`) ne lit **plus** la table éclatée
  `dvf_mutations_parcelle` (l'artefact du « 100 888 €/m² ») : il passe par `mediane_bati`.
- `zone.prix_par_type_zone` (bloc Marché) : maison/appartement passent par le même point de calcul.
- **Résultat (3 communes témoins, base réelle)** : Étude de zone == point de calcul unique == périmètre
  commune, à l'euro près —
  **Sainte-Suzanne 2 462 €/m² · Les Avirons 3 280 €/m² · La Possession 3 063 €/m²**.
- Note : le **baromètre commune** (`api.moteurs._BAROMETRE_RETENUE`, tout l'historique, plancher lâche
  à 100) reste un métrique VOLONTAIREMENT distinct (doctrine moteurs.py:713-716) ; il lit déjà
  `dvf_mutations`. Le **Radar** mesure le prix **demandé** (annonces), pas l'acté DVF — concept distinct,
  laissé tel quel. Plus aucune médiane de zone/marché ne lit `dvf_mutations_parcelle`.

### 2. Les 5 sources mortes (écart E3)
- Les 5 étaient **déjà** `retiree` avec un motif durable en code (`seed_sources.RETRAITS`,
  posé en base dans `data_sources.retiree_raison`) : EDF SEI (410 Gone), ODRÉ (jamais branché),
  MOBPRO (abandonnée), BDNB (0 ligne 974), Office de l'eau (remplacée par INSEE RP2022 EGOUL).
  Aucune table supprimée. Elles restent hors des **actives** (statut `retiree`).
- **Commentaire faux corrigé** : `sources_catalog.py:6-8` affirmait « Office de l'eau est SERVIE à la
  fiche depuis M95 » — **faux** depuis SOURCES-3 (plus aucun lecteur). Corrigé. Le `technical_notes`
  d'Office de l'eau (seed + base) portait la même affirmation périmée → réécrit (« RETIRÉ … plus servie »).

### 3. Trois contraintes ajoutées à la fiche parcelle (écarts A1/A2/A3)
Mêmes couches que la carte (`spatial_layers`), intersection LIVE, même libellé, producteur
`api/fiche_blocs3.py` :
- **Zone EnR interdite hors toiture (APER)** → §Risques (`enr_exclue_toiture`, kind `enr_exclue_hors_toiture`).
- **Mesures compensatoires (GéoMCE)** → §Risques (`mesures_compensatoires`, kind `mesures_compensatoires`).
- **SCOT** (nom + date d'approbation) → §Urbanisme (`scot`, kind `scot`).

Chaîne complète : fiche JSON (`api/app.py`) → front (`risques.tsx`, `Fiche.tsx`, types) → **registre**
(`donnees.py` + robinets `fiche_parcelle_contraintes_env`/`fiche_parcelle_droit_sols`) → **Dossier PDF**
(déclarations `risques.yaml`/`sections_restantes.yaml` + extracteurs `robinet_fiche.py`). Le Dossier est
le **miroir** de la fiche : les 3 lignes y entrent (section Risques / Urbanisme).

## Pourquoi le compte d'actives est 123 et non 125
Le catalogue `data_sources` est passé de 125 à **128 lignes** depuis l'écriture du mandat (sources
ajoutées) ; **5** sont `retiree` (les 5 mortes) → **actives = 128 − 5 = 123** ; **affichées = 98** (inchangé).

## Vérifications
- **pytest** ciblé : `test_sources_fix1.py` (4 passés, 1 skip DVF sur base de test creuse — prouvé LIVE),
  `test_registre.py` + `test_circuit2_lot1.py` (verrous registre/robinets **verts**),
  exports/zone/marché (88 passés). DVF unifié prouvé sur 3 communes réelles (voir §1).
- **frontend** : `tsc -b` exit 0 · `vitest` **218 passés** · `vite build` exit 0.

## Captures avant/après (Dossier = miroir de la fiche)
`DOSSIER-{AVANT,APRES}-{enr-aper,mesures-comp,scot}.png` — parcelles témoins :
- EnR (APER) : **97424000AI0287** (Cilaos) → « Parc national (Parc national de La Réunion) ».
- Mesures compensatoires : **97401000AT0401** → « C2 - Restauration / Réhabilitation — Nouvelle route du littoral ».
- SCOT : **97401000AE0047** (Les Avirons) → « SCOT TCO — approuvé le 2022-10-03 ».

APRÈS : la ligne apparaît, peuplée, dans le Dossier (§Urbanisme / §Risques). AVANT : sur `origin/main`
ces trois lignes **n'existent pas** (0 occurrence de `enr_exclue_parcelle`/`mesures_compensatoires_parcelle`/
`scot_parcelle` dans `donnees.py` et les déclarations — vérifié `git show origin/main`). La fiche écran
rend les mêmes données (`f.scot`, `f.enr_exclue_toiture`, `f.mesures_compensatoires` — couvert par tsc+vitest).
