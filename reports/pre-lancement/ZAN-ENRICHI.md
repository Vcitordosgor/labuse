# ZAN ENRICHI (point 41) · `feat/zan-enrichi`

**NON mergée.** Ingestion opendata + outil. **Zéro touche scoring** (nouvelle table d'enrichissement +
endpoints outil ; `git diff` = `scripts/ingest_conso_enaf.py`, `api/moteurs.py`, front, QA).
**Boussole tenue** : Sourcé (observé) vs Estimé (dérivé) **strict et visible**, caveat loi TRACE
systématique, **zéro fabrication**.

## Lot 0 — Source
**CONSOENAF 2009-2024** — Portail national de l'artificialisation / **Cerema**, calculée sur les Fichiers
fonciers, **publié 12/05/2025**, **Licence Ouverte 2.0**. data.gouv.fr → dataset
`consommation-despaces-naturels-agricoles-et-forestiers-du-1er-janvier-2009-au-1er-janvier-2024`.
CSV national `conso2009-2024-resultats-com.csv` (+ fichier dédié 974). Colonnes : `idcom` (INSEE),
`idcomtxt`, flux annuels `nafYYartZZ` (ENAF consommé, **m²**) + destination habitat `artYYhabZZ`.
**Complétude : 24/24 communes 974 présentes.**

## Lot 1 — Ingestion
`scripts/ingest_conso_enaf.py` → table **`commune_conso_enaf`** (insee, commune, conso 2011-2021,
conso 2021-2024, habitat, source, millésime). **24/24 ingérées**, valeurs **vérifiées vs CSV**
(Les Avirons 373 950 / 148 010 m² · Bras-Panon 322 233 / 125 711…). Garde 24-communes (STOP si manquante).

## Lot 2 — Indicateur commune (Sourcé + Estimé)
`/moteurs/zan` → `indicateurs` par commune :
- **Consommé 2011-21** & **2021-24** = **Sourcé** (observé).
- **Budget 2021-31** = consommé 2011-21 / 2 (**règle -50 %**) = **Estimé**.
- **Reste théorique** = budget − consommé 2021-24 = **Estimé** (peut être **négatif** → affiché
  honnêtement : Cilaos **-6,2 ha** = rythme déjà dépassé). Le « reste » n'est **jamais** un droit à
  construire ferme. **Caveat loi TRACE** attaché.

## Lot 3 — Signal parcelle (robuste, sourcé)
`/moteurs/zan/parcelle/{idu}` — déterministe, indépendant des quotas :
- **Aligné ZAN** : déjà **artificialisé** (OCS-GE) OU **friche** (Cartofriches) OU **zone U**.
- **Sous contrainte ZAN** : sol **naturel/agricole** (OCS-GE) en **zone AU** (extension ENAF).
- **Exemption SRU** : commune **carencée** → « logement social exempté du décompte ZAN jusqu'en 2036
  (loi TRACE) » (source SRU du mode bailleur réutilisée). Chaque raison **Sourcée**.

## Lot 4 — Outil (UI honnête)
M17 **mène avec le signal parcelle** (badge aligné/contrainte + exemption SRU), puis le **contexte
commune** (indicateur), avec **étiquettes Sourcé (vert) / Estimé (ambre)** partout et le **caveat loi
TRACE bien visible** + provenance de l'observé.

## Preuves (`reports/pre-lancement/captures/`)
- `zan-contrainte-exemption.png` — Saint-Leu : **Sous contrainte ZAN** (agricole+AU) + **★ exemption
  SRU** ; indicateur Consommé **Sourcé** / Budget+Reste **Estimé** ; **caveat loi TRACE** ; provenance Cerema.
- `zan-aligne.png` — **Aligné ZAN** (artificialisé + zone U).
- Testé aussi Cilaos (reste **négatif** affiché honnêtement).

## Non-régression & garanties
- **Zéro touche scoring** : table d'enrichissement + endpoints outil uniquement.
- **Mode bailleur non régressé** : la source SRU (`commune_contexte_sru`) est **réutilisée**, pas dupliquée.
- **Zéro fabrication** : 24/24 communes réelles ; le « reste » toujours Estimé + caveat, jamais un droit ferme.
- `tsc`/build verts, endpoints testés live.

## Merge
`git -C /Users/openclaw/Desktop/labuse checkout main && git merge --no-ff feat/zan-enrichi`
(puis `python scripts/ingest_conso_enaf.py` pour peupler la table + redémarrer l'API). **Pas de merge par CC.**
