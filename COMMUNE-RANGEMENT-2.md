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

---

## Lot 2 — les 13 données commune absentes

Les 13 données à la maille commune du registre qui n'apparaissaient dans aucune carte (calcul :
`registre/donnees.py` niveau=commune, non citées par un robinet `fiche_commune_*`, hors couches carte).
**Chacune placée ou motivée — zéro « on ne sait pas ».**

| Donnée | Décision | Carte maquette / motif |
|---|---|---|
| `prix_neuf_observe_eur_m2` | **PLACÉE** | **Prix** — « Neuf observé (ventes récentes) », notion scindée du VEFA à l'acte (la maquette Prix demande « observé · VEFA à l'acte »). Nouveau builder `fiche_commune.prix_neuf_observe(insee)` (niveau commune), servi live. |
| `pression_zan_ha` | **PLACÉE** (lot 1) | **Foncier et rareté** — « Consommation NAF (budget ZAN consommé) », même source Cerema ENAF que la pression ZAN du comparateur (via `motRarete.pct_budget_consomme`). |
| `acquisitions_pm_n` | motivée | doublon/coût — servie par l'**outil Communes** (endpoint dédié `/communes/{c}/acquisitions-pm`) ; RANGEMENT-1 lot 3 l'a sortie du payload pour son coût. La carte Activité y mène par **porte**, pas par recalcul. |
| `comparateur_composite` | motivée | **exclue par la maquette** (« Pas de rang comparatif », décision du 20/09). |
| `couverture_commune_pct` | motivée | **interne** — métrique qualité/admin (page Sources), pas un contexte promoteur. |
| `delai_vente_median_j` | motivée | **doublon Radar** — la carte Activité porte déjà le signal Radar (biens/écart) ; le délai de vente est un détail de l'outil Radar. |
| `n_extraits_plu` | motivée | **interne outil PLU** (compte d'extraits de règlement) ; la carte Urbanisme porte le calibrage (zones/règles validées). |
| `n_piscines` | motivée | **déjà visible** — compteur de la tuile Solaire (grille d'outils) ; agrégat maille parcelle, pas un fait communal. |
| `n_procedures_plu` | motivée | **doublon `statut_plu`** — la procédure en cours est servie par la carte Urbanisme (stade / procédure). |
| `parcelles_par_zone_n` | motivée | **doublon Zonage** — la carte Zonage porte la répartition U/AU/A/N ; le compte par zone est l'outil filtres. |
| `permis_5a_n` | motivée | **déjà visible** — ligne Permis « N sur 5 ans » (id vit sous le robinet comparateur). |
| `simulplu_resultat` | motivée | **interne** — résultat d'une simulation interactive de l'outil PLU. |
| `tranche_prix_vefa` | motivée | **doublon couche VEFA** — le neuf VEFA à l'acte est déjà sur la carte Prix ; `tranche_prix_vefa` est la couche carte (mêmes données en tranches). |

**Bilan : 2 placées (`prix_neuf_observe`, `pression_zan`), 11 motivées** (5 doublons · 3 internes · 1
exclue maquette · 1 coût/porte · 1 déjà visible via tuile). Le robinet de `prix_neuf_observe_eur_m2`
sur la fiche commune est déclaré au lot 5.
