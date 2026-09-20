# COMMUNE-RANGEMENT-2 — La fiche commune au niveau de la fiche parcelle

**Branche** `feat/commune-audit-1`, départ **`ce303410`** (maquette v1 validée). Un commit par lot,
branche poussée. Cible = `docs/audit-2026-09/COMMUNE/maquette-v1/commune.html` (5 groupes · 10 cartes).
DA existante — le composant `ContextePanel` et sa grammaire restent.

**Objectif** : dire de la fiche commune ce qu'on dit de la fiche parcelle — tout ce qu'elle affiche est
déclaré, rien n'est jeté en silence, un même chiffre dit la même chose partout dans LABUSE.

---

## Lot 1 — cohérence avec le reste de l'app

Chaque donnée à la maille commune servie par la fiche commune ET ailleurs (comparateur/outil Communes,
fiche parcelle, Étude de zone, exports, Radar) comparée sur les **24 communes** : même id du registre ?
même valeur ? Méthode : `qa/commune_rangement2_lot1.py` (TestClient in-process), payloads figés dans
`qa/commune_rangement2_lot1.json`.

**Résultat : 0 divergence.** Les indicateurs partagés viennent tous d'un **moteur unique** —
`comparateur.raw_rows` (prix ancien/neuf, permis, vélocité, stock, terrain nu) et
`commune_contexte_sru` re-servi live par `_rafraichir_partages` (SRU statut/déficit) — donc chaque
chiffre est identique des deux côtés **par construction** (doctrine OUTILS-6 C2 / RETOURS-12 O8, déjà en
place). L'audit de mapping (un lecteur par notion, id + moteur) confirme : aucune notion n'est calculée
par deux chemins concurrents.

| Notion | fiche commune | autre surface | même valeur /24 |
|---|---|---|---|
| Prix ancien médian €/m² | `comparable.ancien_median_eur_m2` | comparateur `raw_rows.prix_ancien` | **24/24** |
| Prix neuf VEFA €/m² | `comparable.neuf_eur_m2` | comparateur `raw_rows.prix_neuf` | **24/24** |
| Permis 5 ans | `permis_bloc.permis_5a` | comparateur `raw_rows.permis` | **24/24** |
| Délai médian (mois) | `permis_bloc.delai_median_mois` | comparateur `raw_rows.velocite` | **24/24** |
| Stock opportunités (n) | `foncier.stock_opportunites.n` | comparateur `raw_rows.stock` | **24/24** |
| SRU statut | `sru.statut` | comparateur `sru_statut` | **24/24** |
| SRU déficit (pts) | `sru.deficit` | comparateur `deficit_sru` | **24/24** |
| Terrain nu €/m² (U/AU) | `foncier.prix_terrain_nu.par_zone` | comparateur `raw_rows.prix_terrain_nu` | **24/24** |

*Note SRU : le comparateur porte le statut + le déficit (comparés ci-dessus) ; le **taux LLS brut** n'est
servi QUE sur la fiche (et l'inventaire SRU) — pas une divergence, une donnée mono-surface.*

**Une donnée communale existant ailleurs mais pas sur la fiche → la faire entrer.** Le comparateur
porte la **pression ZAN** (consommation ENAF 2021-2024, `commune_conso_enaf`, Cerema) que la fiche ne
montrait pas explicitement. En fait `motRarete` transportait déjà la trajectoire ENAF
(`pct_budget_consomme`, `budget_zan_ha`) sans la rendre : une ligne **« Consommation NAF (budget ZAN
consommé) »** est ajoutée à la carte Enveloppe ZAN (même source Cerema ENAF — un seul chemin). Les
autres champs du comparateur absents de la fiche sont **exclus par la maquette** : `score_composite` /
`rang` (« Pas de rang comparatif », décision du 20/09).

**Corrections à la source : aucune** (les moteurs sont déjà uniques). Seule action : surfacer la conso
ENAF déjà transportée. Front seul, `tsc -b` vert.
