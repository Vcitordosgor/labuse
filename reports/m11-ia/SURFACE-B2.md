# M11 · SURFACE B2 — Enrichissement de la recherche IA (`/ia/search`)

**Branche** : `feat/m11-surface-b2` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**Prérequis mergés** : socle §0, Surface A, Surface B1 (`main` : B1 `49d5633`, A `b6e8815`).
**Périmètre** : enrichissement de VALEUR (objectifs 3+4 du cadre) — B1 a réparé (mistraduction/drop),
B2 ajoute **2 filtres réels** (propriétaire personne morale, zonage PLU) + **les questions agrégées**.
Chaque filtre ajouté fait **rétrécir** `criteres_non_appliques` : un critère passe de « signalé non
appliqué » à « appliqué ».

**Zéro touche** scoring / cascade / étage 0 / run servi `q_v6_m8` (git : seuls API/front/tests modifiés ;
`app.py` = uniquement des clauses WHERE de filtre, aucune ligne de scoring).

---

## Lot 0 — Constat (vérifié avant code)

| Élément | Réel |
|---|---|
| `parcelle_personne_morale` | 82 701 lignes, **82 066 jointes** à `parcels` via `idu`. Colonnes **publiques DGFiP** : `siren`, `denomination`, `forme_juridique`, `groupe_label`. 12 605 SIREN. `classify_dgfip` → famille public/privé. |
| Zonage | `parcel_zone_plu` (427 419) filtrable par **famille** `zone_fam` = U (306 630) / A (73 946) / N (36 306) / AU (10 537). `zone_lib` = code brut variable → famille = granularité fiable. |
| Agrégats | Réels sur le run servi : Saint-Paul **28** brûlantes, Saint-Pierre 12, Saint-Denis/Saint-Leu 9… Brûlantes SP = 12 dont **6** personne morale. |
| Câblage | `_q_v2_where` (app.py) = builder WHERE partagé, 3 appelants (`/parcels`, `/stats`, `export.csv`). |

---

## Lot 1 — Filtre propriétaire PERSONNE MORALE

- **Filtre** : `personneMorale` (booléen) dans `FILTER_SCHEMA` ; côté serveur `_q_v2_where` ajoute
  `EXISTS (SELECT 1 FROM parcelle_personne_morale pm0 WHERE pm0.idu = p.idu)`. Paramètre `personne_morale`
  sur `/parcels`, `/stats`, `export.csv`.
- **Intégration B1** : `nl_semantics` retire « propriétaire personne morale » de `_UNSUPPORTED` (n'est plus
  signalé) et l'ajoute à `_BOOL_KW` (anti-mistraduction : `personneMorale:true` non justifié par un mot
  → retiré). Le prompt NL et le stub savent le produire.
- **Preuve (live)** : `« brûlantes de Saint-Pierre propriétaire personne morale »` →
  `filters:{commune:Saint-Pierre, tiers:[brulante], personneMorale:true}`, `criteres_non_appliques:[]`.
  `/parcels …&personne_morale=true` = **6** (vs 12 sans) — jointure correcte.

### PRIVACY (ligne rouge — respectée et prouvée)
- `parcelle_personne_morale` ne contient **QUE des personnes morales** (échantillon : familles `public`
  + `prive`, **aucune** personne physique ; formes = SARL/SCI/CCAS/EARL/COLL…).
- Le filtre est un **test de présence** (`EXISTS`) — il ne SELECT aucune donnée propriétaire dans les
  résultats. Une parcelle **absente** de la table (= particulier) est simplement **exclue**, jamais nommée.
- Champs pré-existants de la liste : `owner_type` = code de TYPE (`pm`/`pp`), `proprio` = dénomination
  **uniquement pour les PM** (public DGFiP). Vérifié : pour `owner_type='pp'` (particulier), **`proprio` = None**
  → aucune identité de personne physique n'est jamais exposée. B2 n'ajoute aucune donnée nominative.

---

## Lot 2 — Filtre ZONAGE PLU

- **Filtre** : `zonage` (array de familles `U`/`AU`/`A`/`N`) ; serveur `_q_v2_where` ajoute
  `EXISTS (… parcel_zone_plu z0 WHERE z0.idu=p.idu AND z0.zone_fam = ANY(:f_zonage))`.
- **Intégration B1** : « zonage PLU » retiré de `_UNSUPPORTED` ; gating par famille via `_ZONE_KW`
  (une famille non justifiée par la requête est retirée — anti-mistraduction).
- **Preuve (live)** : `« parcelles constructibles en zone U à Saint-Paul »` →
  `filters:{commune:Saint-Paul, zonage:[U]}`, `criteres_non_appliques:[]`. Filtrage : Saint-Paul chaudes
  = 231, zone U = **158**, zone A = **0** (les chaudes y sont urbaines — cohérent).

---

## Lot 3 — Questions AGRÉGÉES (nouveau type de réponse)

Un agrégat n'est PAS une liste filtrée : le client veut un **nombre**. Module `nl_aggregate.py`.

- **Détection** (`is_aggregate`) : mots de quantité/superlatif (`combien`, `nombre de`, `quelle commune`,
  `le/la plus`, `répartition`, `classement`…) — absents d'une requête de filtre. Routé en tête de `ia_search`.
- **Exécution SQL déterministe** : `COUNT` / `GROUP BY commune ORDER BY count DESC`, avec la MÊME définition
  de tier que la carte (`parcel_p_score_v2.tier` du run v2 servi, hors étage 0 dur). **Aucun calcul par le modèle.**
- **Réponse via le socle** : le résultat SQL devient le **contexte autorisé** (chiffres étiquetés SOURCÉ) →
  `core.complete(validate=True, require_sources=True)`. La **couche 2** vérifie que chaque chiffre de la
  prose figure au contexte SQL.
- **Types couverts** : compte (`combien de {tier} à {commune}`), superlatif (`quelle commune a le plus de
  {tier}` → tête + mini-classement), répartition (`… par commune`).
- **Preuve (live)** : `« combien de brûlantes à Saint-Paul ? »` → `nombre=28` (COUNT réel), texte
  « Saint-Paul compte 28 parcelles brûlantes. », `sources:[nombre]`, `rejected:false`.
  `« quelle commune a le plus de brûlantes ? »` → tête Saint-Paul 28, classement complet SQL.

### La RÈGLE DE FER prouvée — un faux compte est REJETÉ
`validate_output` avec un contexte `{nombre: 28}` :
- prose « … 28 … ⟨src:nombre⟩ » → **ok=True** ;
- prose « … 35 … ⟨src:nombre⟩ » → **ok=False**, raison « chiffre non sourcé « 35 » (absent du contexte) ».
Un compte inventé/arrondi/halluciné n'est jamais servi. (NB socle : les petits entiers 0-12 sont tolérés
comme bruit rédactionnel — le garde-fou mord sur les comptes réels > 12, cas des volumétries.)

---

## Lot 4 — Front (page IA)

- **Filtres (Lots 1-2)** : rien de neuf visuellement — ils s'appliquent aux résultats existants ; le critère
  **disparaît** de la bannière « critères non appliqués ». `Filters` (useApp) gagne `personneMorale`+`zonagePlu`,
  câblés dans `filterParams` (api.ts) et `filtresToFilters` (useApplySearch).
- **Agrégées (Lot 3)** : nouveau format — une **carte chiffrée** (pas une liste), texte + étiquette
  **Sourcé** ; pour un superlatif, un **mini-classement** (`data-ia-aggregate` / `data-ia-classement`).
  La vue IA reste montée (aucun filtre appliqué).
- **Captures** (`reports/m11-ia/captures/`) :
  - `b2-a-personne-morale-sans-signalement.png` — recherche PM appliquée, **aucune bannière** « non appliqués ».
  - `b2-b-agregat-source.png` — « Saint-Paul compte 28 parcelles brûlantes. » + Sourcé.
  - `b2-b-classement-source.png` — superlatif + mini-classement (28/12/9/9/8/8), Sourcé.

---

## Lot 5 — Tests & preuves

- `tests/test_nl_semantics.py` (mis à jour B1→B2) : PM/zonage **supportés** (appliqués, PAS signalés) ;
  anti-mistraduction (PM/zonage injectés sans mot → retirés) ; critères ENCORE non supportés (DPE,
  assainissement) **toujours signalés** (non-régression B1) ; mistraduction passoire→risques toujours tuée.
- `tests/test_nl_aggregate.py` : distinction filtre/agrégat ; détection de tier ; **le socle rejette un
  faux compte** / accepte le vrai / refuse sans source / valide un classement.
- **37/37 verts** (12 B1 + agrégat + sémantique). Filtres prouvés en live (jointures : PM 12→6, zonage U 158/A 0).
- **Zéro touche scoring** (git diff). `CONTEXT_VERSION` **non bumpé** : `_ask_context` (contexte de la barre
  de fiche, seul salé par cette version) est INCHANGÉ ; l'agrégat est un contexte neuf, non caché par `ia_cache`.

---

## Synthèse — l'écart donnée↔filtre se referme
`criteres_non_appliques` rétrécit : « propriétaire personne morale » et « zonage » passent de *signalés*
à *appliqués*. Restent signalés (honnêtement) : DPE, viabilisation/assainissement, âge/succession, BODACC,
piscine, jardin, pente, végétation, solaire — cibles d'un futur lot. Les questions agrégées, jusqu'ici
refusées ou converties en filtre, reçoivent un **chiffre SQL réel, sourcé et validé**.

*Commit sur `feat/m11-surface-b2`. Pas de merge.*
