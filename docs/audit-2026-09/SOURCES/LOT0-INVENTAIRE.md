# LOT 0 — L'inventaire remis d'aplomb (S1–S4)

*SOURCES-AUDIT-1. Lecture seule sauf S2 (retraits en base, conditionnés). Tous les chiffres
sont mesurés sur la base `labuse` le jour du mandat ; le code est cité `fichier:ligne`.*

---

## S1 — Pourquoi le compteur de la page ne suit pas la base

### Le fait mesuré

- **Base `data_sources` : 116 lignes.** Réparties : 90 `connecte`, 10 `a_faire`, 5 `manuel`,
  5 `retiree`, 3 `alias`, 3 `hub`.
- **Page Circuit / catalogue affiché : 95 lignes aujourd'hui** (pas 68 — voir plus bas).
  Le « 68 » du mandat est le chiffre de l'époque CIRCUIT-5 ; le catalogue a grossi depuis
  (SOURCES-1 a ajouté les sources 100→142), et les trois compteurs ont grimpé ensemble.

### Le filtre qui produit l'écart

La page ne montre que les sources **en vitrine**. Le prédicat est unique et partagé :
`WHERE_AFFICHEES` dans `src/labuse/sources_catalog.py:36-41`, utilisé par l'endpoint
`/admin/circuit` (`src/labuse/api/dashboard.py:_assembler_reservoirs`, ~ligne 1958) :

```
status ∈ ('connecte','manuel')
  ET technical_notes NE COMMENCE PAS PAR 'DOUBLON' / 'RETIRÉ' / 'DORMANT'
  ET affichage_desactive = false
  ET name ∉ (masquées)      -- ensemble vide aujourd'hui
```

Décompte du jour : `connecte (90) + manuel (5) = 95` affichées ; **21 masquées** =
10 `a_faire` + 5 `retiree` + 3 `alias` + 3 `hub`. `116 − 21 = 95`. Aucun mystère : ce sont
des lignes qui n'ont **rien à montrer au client** (chantiers à venir, doublons de canal,
hubs de catalogue, sources retirées).

### Pourquoi le verrou « 68 = 68 » n'a pas sonné

Le verrou **V2a** (`src/labuse/circuit_verrous.py:276-305`, `verrou_sources_comptes`) ne
compare **pas** un nombre gravé. Il vérifie une **cohérence à trois voies** :

```
n_sql   = count(*) data_sources WHERE {WHERE_AFFICHEES}
n_py    = len([r for r in catalogue if est_affichee(r)])      # même prédicat, en Python
n_page  = len(flux.construire_flux(db)["sources"])            # ce que la page construit
verrou OK ⇔ n_sql == n_py == n_page
```

Quand SOURCES-1 a ajouté des lignes `connecte`, **les trois voies ont augmenté ensemble**
(elles lisent le même filtre) : 68 → … → 95. Le verrou n'a rien signalé **parce qu'il n'a
rien à signaler** : sa mission est de garantir que la vitrine SQL, le prédicat Python et la
page comptent la **même chose**, pas de figer une valeur. Le « 68 » n'existe que dans un
commentaire de test (`tests/verrous/test_lot2_sources.py`), jamais dans le runtime.

Le verrou frère **V2b** garde la discipline du catalogue (un doublon doit être noté DOUBLON,
un alias doit pointer une cible en vitrine, une `retiree` doit avoir date+raison, une
`a_faire` doit avoir un chantier) et le **pont** exige que chaque source affichée ait un slug
dans `NOM_VERS_SLUG` **et** une entrée dans `RESERVOIR_TABLES`. C'est ce triplet
(V2a + V2b + pont) qui a « accueilli » proprement les sources SOURCES-1.

### Ce qu'il faut pour que le nombre se *calcule* au lieu d'être gravé (sans le coder ici)

Le nombre affiché **est déjà calculé** (aucun littéral au runtime). Le vrai manque n'est pas
un bug de compteur, c'est que **la page ne dit jamais la vérité entière** : elle montre 95 et
tait les 21. Recommandation (mandat séparé) :

1. **Afficher les 116 par statut** (Connectées 90 · À faire 10 · Manuelles 5 · Retirées 5 ·
   Alias 3 · Hubs 3), le total et chaque sous-total **dérivés** d'une seule requête `GROUP BY
   status` — jamais un chiffre en dur, jamais une page « à part » qui pourrait diverger.
2. **Étendre V2a** d'une ligne : `count(*) total == somme des sous-totaux par statut` — pour
   que l'inventaire complet, pas seulement la vitrine, soit sous verrou.

---

## S2 — Les retraits décidés par Vic : **VÉRIFIÉS, et TOUS EN ATTENTE**

**Décision du mandat : aucun des quatre retraits n'est appliqué. La règle « si un moteur les
lit, le retrait attend » se déclenche pour les quatre.** Aucune écriture en base au lot 0.

Le mandat autorise une écriture — passer `BD ORTHO IRC`, `Office de l'eau — Chroniques`,
`Parkings OSM (loi APER)` et `Recherche d'entreprises (DINUM)` en `retiree` — **à la condition
expresse qu'aucun moteur ne les lise encore**. La vérification (grep du code + comptes en base
+ graphe du registre) montre que **les quatre sont lues EN DIRECT et servent une valeur au
client**. Le précédent fait foi : MOBPRO (id 87) n'a été retirée que parce que son lecteur
était **code mort** (« plus rien de servi ») ; ici, tout est servi.

| Source | Réservoir | Table lue (peuplée) | Lecteur vivant `fichier:ligne` | Chiffre servi | Où |
|---|---|---|---|---|---|
| **BD ORTHO IRC** (69) | `bd_ortho_irc` | `parcel_vegetation` (431 663) | `ingestion/solaire.py:311` (ombrage), `flash/data.py:650`, `scoring/p_model/sql.py:287` | `prod_spec_kwh_kwc` (moteur solaire) | fiche **Solaire**, PDF Flash, scoring P |
| **Office de l'eau** (68) | `office_eau_chroniques` | `anc_office_eau_commune` (6) | `anc_service.py:57-59` (en direct) | `part_logements_egout_pct` (moteur anc) | fiche **Réseaux** (6 communes 100 % ANC) |
| **Parkings OSM APER** (51) | `parkings_osm_aper` | `parkings_aper` (901) | `ingestion/ortho_pv.py:56`, `ingestion/ortho_tiles.py:112`, `flash/data.py:103` | `viabilisation_verdict` (passe-plat) | fiche **Réseaux/viabilisation**, PDF Flash |
| **Recherche d'entreprises DINUM** (45) | `recherche_entreprises_dinum` | `owner_enrichment` (9 730), `owner_denom_lookup` (2 650) | `scoring/score_v.py:90,98`, `proprietaire_facettes.py:70`, `api/app.py:4695` | `evenements_proprietaire_liste` (moteur v_score) | fiche **Propriétaire**, Scan patrimoine |

Chacun des quatre réservoirs est rattaché à un **chiffre servi** du registre, lui-même porté
par un **robinet de fiche/outil** (mesuré : Solaire, Réseaux, Propriétaire, Prospection
solaire). Les retirer sans d'abord débrancher ces lecteurs **masquerait au catalogue une
source réellement utilisée** — exactement ce que le catalogue est censé empêcher.

**Suite (chacune un mandat séparé, cf. REPARATIONS.md)** : d'abord débrancher le lecteur
(ou décider d'abandonner la fonction qu'il sert), *ensuite* retirer la source. Tant que
l'ombrage végétal nourrit le solaire, que l'Office de l'eau porte l'ANC de 6 communes, que
les parkings APER portent l'obligation d'ombrières et que l'enrichissement DINUM porte le
Score V, ces sources **restent au catalogue, à leur place**.

> Si la volonté de Vic reste de les retirer, le geste sûr est : 1) mandat qui coupe le
> lecteur, avec sa recette ; 2) puis `retiree` (date + raison + données conservées). Ce
> mandat-ci, en lecture seule, ne peut pas couper un lecteur vivant sans casse.

---

## S3 — Les doublons vivants : un verdict chacun

| Paire | Fait foi | Qui lit l'autre | Pour n'en garder qu'une |
|---|---|---|---|
| **Potentiel foncier Région** — `potentiel` (15) vs `urbanisme` (9) | **15** (couche `potentiel_foncier`+`sar`, 4 906 objets, slug `potentiel_foncier_region`) | 9 (`potentiel_foncier_ods`) n'alimente aucun chiffre distinct ; c'est la même donnée Région ODS rangée deux fois | Retirer **9** (redondant, 0 chiffre), garder 15 ; clarifier la licence Région (« à confirmer »). |
| **DVF** — Etalab (5) vs Région (119) | **5** (géo-DVF Etalab 2021-2025 + archives DGFiP, cœur du marché) | 119 (`region_dvf`) n'a **pas de table** : il ne sert que d'**échantillon** au filtre DVF (`filtres/echantillons/dvf.json`), jeu figé 2014→mi-2021 | Garder 5 comme canonique ; **119 = témoin de contrôle producteur**, à conserver discret (hors vitrine) ou à retirer si le témoin ne sert plus. |
| **SIRENE** (21) vs **SIRENE établissements** (86) | **Les deux, par usage distinct** | 21 = API `recherche-entreprises` interrogée **en direct** (Scan, Copilote), sans table ; 86 = **snapshot géolocalisé mensuel** (couche/zone) | Ne PAS fusionner : ce sont deux canaux (temps réel sans géo vs géo figée). Documenter le rôle de chacun dans leur `i` ; éviter qu'un client croie à deux sources. |
| **ZNIEFF** — INPN/MNHN (76) vs INPN/Région (80) | **76** (162 objets, maj 29/08/2025) | 80 (canal Région ODS) : endpoint vivant, **0 donnée** — **déjà retirée** le 06/09/2026 | Rien à faire : le doublon est déjà résolu (80 `retiree`, canonique = 76). |

**Doublons de canal déjà propres (alias, pour mémoire)** : Cadastre Etalab (2)→API Carto (1) ;
RGE ALTI 5 m (65)→RGE ALTI (6) ; GPU assainissement info-surf (67)→GPU assainissement (63).
Les trois sont des `alias` correctement pointés — ce ne sont pas des doublons à trancher.

---

## S4 — Les familles dédoublées : proposition canonique

La colonne `data_sources.category` (28 valeurs fines) porte plusieurs paires qui désignent la
même chose. `circuit_etats.FAMILLE_DE_CATEGORIE` les range **déjà** en familles lisibles ;
la proposition ci-dessous **fusionne les slugs fins** (sans rien modifier ici — geste d'un
mandat séparé, car `category` est lu par le regroupement d'affichage et par plusieurs vues).

| Slugs actuels (doublés) | Sources concernées | Canonique proposé | Raison |
|---|---|---|---|
| `fiscal` / `fiscalite` | fiscal : 38, 72, 73 · fiscalite : 98, 127, 131 | **`fiscalite`** | Même domaine (zonages fiscaux + taxes). Une seule famille « fiscalité ». |
| `reglement` / `reglementaire` | reglement : 44, 46, 47 · reglementaire : 43 | **`reglementaire`** | Une seule famille pour les textes/servitudes réglementaires. |
| `terrain` / `topographie` | terrain : 65, 70 · topographie : 6, 17, 96 | **`topographie`** | Terrain = sous-ensemble de la topographie/altimétrie. |
| `assainissement` / `reseaux` | assainissement : 66, 67, 68 · reseaux : 26, 126, 134 | **`reseaux`** (sous-thème assainissement) | L'assainissement est un réseau ; la famille d'affichage les réunit déjà. |
| `occupation_sol` / `imagerie` | occupation_sol : 22, 83 · imagerie : 61, 69 | à **garder distincts** | Occupation du sol (classes) ≠ imagerie (ortho brute) — usages différents. |

**Liste canonique des familles fines proposée** (23 au lieu de 28) : `cadastre, potentiel,
proprietaire, foncier, urbanisme, fiscalite, reglementaire, risques, environnement, agricole,
patrimoine, signal, marche, dynamique, logement, reseaux, energie, acces, attractivite,
economie, topographie, occupation_sol, imagerie, hub`. (Les familles d'AFFICHAGE de
`circuit_etats` restent inchangées — elles regroupent déjà correctement.)

**Effet de bord à surveiller** dans le mandat qui appliquera la fusion : `FAMILLE_DE_CATEGORIE`,
les vues admin, et tout `WHERE category=` doivent être migrés en même temps que la colonne.
