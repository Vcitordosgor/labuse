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

---

## Lot 3 — rien de jeté en silence

Audit de chaque carte : une carte conditionnelle qui **disparaît** quand sa donnée est un creux légitime
= une information jetée en silence. Les creux nommés par le mandat (Radar sous seuil, QPV absent, ORT
hors) — plus le PLH absent — passent de **carte absente** à **carte toujours présente qui le dit** :

| Carte | Avant | Après (repli « sans objet ») |
|---|---|---|
| Annonces — Radar | absente si `!marche_annonces` (sinon phrase si sous seuil) | **toujours présente** — `data-annonces-sans-objet` : « **Pas d'annonce repérée sur cette commune** » (19/24 communes) |
| Quartiers prioritaires | absente si 0 QPV et 0 NPNRU | **toujours présente** — `data-qpv-sans-objet` : « **Aucun quartier prioritaire … ni périmètre NPNRU** » (12/24) |
| Revitalisation ACV/PVD/ORT | absente si `statut = hors` | **toujours présente** — `data-ort-sans-objet` : « **Hors dispositif — ni ACV, ni PVD, ni ORT** » (5/24) |
| Programme local — PLH | absente si l'EPCI n'a pas de PLH | **toujours présente** — `data-plh-sans-objet` : « **Aucun programme local de l'habitat recensé pour l'intercommunalité** » |

Chaque carte garde sa **ligne de source** même vide. Les autres cartes conditionnelles (loyer,
terrain nu, fiscalité, zonage…) portent un **trou de donnée** (source non ingérée), pas un creux
légitime ; le lot 4 les range dans les 10 cartes maquette toutes présentes. Front seul, `tsc -b` vert.

---

## Lot 4 — le rangement sur la maquette (19 → 10 cartes, 5 groupes)

Le corps de rendu de `ContextePanel` passe de **3 groupes / 19 cartes** à **5 groupes / 10 cartes**
(chirurgie `qa/commune_rangement2_lot4_surgery.py`, splice entre ancres, haut du fichier et pied
intacts). La grammaire `LigneCarte` (accordéon mémorisé) reste.

**En-tête** : bandeau **6 chiffres en 3 × 3** (`data-bandeau-chiffres`) — Parcelles (Cadastre) ·
Habitants (INSEE) · Permis/an (SITADEL) · Prix ancien €/m² (DVF) · Tendance 12 mois (DVF) · État du PLU
(GPU · Sudocuh) — puis l'action « Voir ses parcelles » et **3 raccourcis** (`data-raccourcis`) : **PLU ·
Communes · Étude de zone**. **Pas de rang comparatif.** Deux **portes dans les cartes** : PLU
(carte Urbanisme, `data-voir-plu`) · Étude de zone (carte Équipements, Shortcut).

### Correspondance carte actuelle → carte cible (ligne par ligne)

| Carte actuelle (19) | → Carte cible (10) | Groupe |
|---|---|---|
| Mairie & service urbanisme (adresse/tél/e-mail/site/annuaire + contacts) · quartiers IRIS (ex-Population) · intercommunalité (ex-en-tête) | **Identité** | Le territoire |
| Population & logement (habitants/ménages/niveau de vie/logements) · Parc social RPLS · barres occupation & typologie · **SRU** (ex-carte SRU : taux/objectif/lecture) | **Population et logement** | Le territoire |
| Prix & tendance (ancien/neuf VEFA/**neuf observé**/tendance) · **Terrain nu** (U/AU) · **Loyers** | **Prix** | Le marché |
| Annonces — Radar (biens/prix demandé/écart + sans objet) · mutations (ex-Prix) | **Activité** | Le marché |
| Permis & délais (12 m/5 ans/délai/offre/dormants) | **Permis et rythme** | La construction |
| Foncier repéré (parcelles/stock/densifiables/SDP) · **Enveloppe ZAN** (conso NAF/reste/rythme/horizon) | **Foncier et rareté** | La construction |
| Règles d'urbanisme (statut PLU) · **Zonage** (répartition U/AU/A/N) · **PLH** (objectif/part sociale) | **Urbanisme** | Les règles |
| Taxe foncière (TFPB/TFPNB/TEOM) · **Zonage ABC** · **ZFANG/FRR** · **Revitalisation ORT** · **Quartiers prioritaires** (QPV/NPNRU) | **Fiscalité et dispositifs** | Les règles |
| Risques (PPR/mvt/CatNat + détail/AZI-TRI/Parc National) | **Risques et contraintes** | Le cadre de vie |
| *(nouvelle — équipements/transport/fibre/solaire renvoient à l'Étude de zone via porte)* | **Équipements et desserte** | Le cadre de vie |

### Recomptage automatique — 0 ligne perdue

`qa/commune_rangement2_census.py` extrait chaque libellé de ligne (`RowT`) et de barre (`Bar`) du bloc
de rendu, avant (`census_before.json`) et après (`census_after.json`) :

| | Avant | Après | Perdues | Ajoutées |
|---|---|---|---|---|
| Libellés de ligne (`RowT`) | 40 | 41 | **0** | 1 (« Intercommunalité ») |
| Libellés de barre (`Bar`) | 9 | 9 | **0** | 0 |

**0 ligne perdue** ; la seule addition est « Intercommunalité » (ex-sous-titre d'en-tête, désormais une
ligne déclarée). Les blocs sur mesure (SRU, terrain nu, foncier, détail CatNat, coordonnées mairie,
barres) sont tous repris. L'ancienne **grille d'outils** est dissoute : ses accès vivent dans les
raccourcis (PLU/Communes/Étude de zone), les portes de cartes (Permis/Densifier/Radar en Shortcut) et
le lien « Voir tous les outils → ». `tsc -b` vert.

---

## Lot 5 — tout par déclaration + verrou V5e

Chaque ligne des 10 cartes est déclarée dans **`declarations/commune/`** (5 fichiers, un par groupe),
sur le modèle de `declarations/fiche/` : `quoi` (id registre) · `ou {rang, etat, section=carte}` ·
`comment {libelle, format, i}` · `absence` · `absence_type` · `pourquoi`. Générées depuis le registre
(`qa/commune_rangement2_gen_declarations.py` — libellé/définition = `donnees.py`, une seule vérité) :
**43 lignes** déclarées (Identité 2 · Population et logement 7 · Prix 5 · Activité 4 · Permis et rythme
3 · Foncier et rareté 5 · Urbanisme 6 · Fiscalité et dispositifs 7 · Risques et contraintes 4).
`registre.verifier()` : **0 violation de format**. Catégorie `fiche_commune` ajoutée à `CATEGORIES`.

**Nouveau verrou `V5e`** (`circuit_verrous.verrou_fiche_commune_cartes`, groupe 5) — le pendant commune
du `V5d` de la fiche parcelle : *« toute donnée à la maille commune servie sur la fiche commune
(robinet `fiche_commune_*`) est déclarée dans `declarations/commune/` avec sa carte »*. Le neuf observé
(`prix_neuf_observe_eur_m2`, lot 2) est ajouté au robinet `fiche_commune_prix` (couple multi-robinet
couvert par `NON_SONDES` — scission neuf mesurée par `verifier_scission_neuf`).

**Prouvé cassé → vert :**

```
V5e (déclarations masquées) : CASSÉ — 43 donnée(s) commune sans carte
  - donnée commune « annonces_actives_n » servie sur la fiche sans carte déclarée
  - … (43 câbles muets nommés)
V5e (déclarations présentes) : OK — 43 données maille commune servies sur la fiche commune,
                                    toutes déclarées avec une carte
```

Test : `tests/verrous/test_commune_cartes.py` (vert sur le registre réel · prouve cassé sur une donnée
commune nue) — 2 tests verts, aux côtés des 2 tests V5d.

---

## Preuves globales

- **`tsc -b` vert** à chaque lot.
- **`labuse circuit verrous -w G8` vert** : **29 joués** (21 verrous + 8 garanties, V5e ajouté) —
  « tout va bien », V5c/V5d/**V5e**/V6a ✓ ; G8 en avertissement non bloquant (environnemental,
  pré-existant).
- **`pytest tests/` complet — 0 échec NOUVEAU.** Établi par comparaison avec le commit de départ
  `ce303410` (worktree, même base) : les 6 échecs registre-doc/infra restants
  (`test_chaque_passe_plat_declare_sa_table`, `test_traçage_des_classes_pose`,
  `test_graphe_exact_dans_les_deux_sens`, `test_decoupe_un_module_par_section`,
  `test_f7_marche_ne_porte_plus_le_socio_eco`, `test_les_24_se_jouent_toujours_tous` — verrous lourds
  V7a/V1b qui pendent sur l'infra) **échouent déjà sur `ce303410`**. `test_ops_healthz::test_jamais_vu`
  est environnemental (cron `backup-postgres` « en_retard », sans rapport avec ce mandat). Les **2
  seuls tests cassés par ce mandat** (V5e ajouté au registre des verrous) — `test_verrous_md_se_lit`
  (VERROUS.md) et `test_lot6_porte::…couvre_tous_les_lots` (`len==21`) — plus le
  `test_documents_commites` (doc `FICHES-DONNEES.md` régénérée pour les chiffres commune) sont
  **corrigés et verts**. Verrou-liste `test_les_24` et count `test_la_commande` mis à jour pour V5e.

## Captures

`captures/commune-rangement2/{saint-denis,cilaos}/` — les **10 cartes dépliées** + le bandeau 6 chiffres,
avant (`captures/commune-audit/` = fiche 19 cartes à `7b411d7b`) / après (10 cartes). Saint-Denis (ORT
hors) et Cilaos (**sans QPV → carte Fiscalité « aucun quartier prioritaire »**). Script
`frontend/qa/commune_rangement2_cap.mjs`.

**« Ne merge pas. »**
