# ETUDE-ZONE-1 — Outil « Étude de zone » : 2 corrections, vérif data, inventaire

Branche `fix/etude-zone-1` (worktree `labuse-etudezone`, base main `1c5fe81a`). Non mergé.
Outil : `frontend/src/components/outils/EtudeZone.tsx` (Z4) · moteur `src/labuse/zone.py` ·
endpoint `POST /outils/etude-zone` (`src/labuse/api/app.py:5459`).

Deux modes : **« Autour d'un point »** (isochrone IGN) et **« Zone dessinée »** (polygone).
Deux portes : **Zone de chalandise** (activité) et **Zone particulière** (contexte foncier).

---

## A1 — Zone dessinée : deux corrections front

Fichier unique : `EtudeZone.tsx`. `tsc` + `build` verts, `vitest` 178/178.

### 1. Instruction « appuyez sur Entrée » sous « Dessiner la zone »
Ajout, sous le bouton, d'une ligne d'instruction permanente :
> **Une fois la zone définie, appuyez sur Entrée.**
(rappelle la règle de dessin de l'app : une forme se valide par Entrée, Échap annule.)

### 2. « changer » (haut-droite) → bouton retour « ← Changer la zone » à gauche
Le lien `changer`, jusqu'ici en haut à **droite** du bloc, devient un **retour à gauche**
avec une **flèche gauche** — idiome des autres retours de l'app (`← Outils`, `← Secteurs`,
`← Comptes`…). Le badge de la porte (« Zone de chalandise ») passe à droite. Les attributs
`data-etude-changer-porte` / `data-etude-porte-active` sont conservés (tests inchangés).

| | Avant | Après |
|---|---|---|
| Bloc | `[Zone de chalandise ........ changer]` | `[← Changer la zone ........ ZONE DE CHALANDISE]` |
| Dessin | *(aucune instruction Entrée)* | *« Une fois la zone définie, appuyez sur Entrée. »* |

Captures : **`A1-avant.png`** (état main) · **`A1-apres.png`** (après). Prises sur l'app réelle
(back `:8325`, front `:5525`), navigateur → Outils → Étude de zone → Zone de chalandise →
onglet « Zone dessinée ».

---

## A2 — Autour d'un point / zone dessinée : les chiffres lisent-ils les bonnes sources ?

Recompte fait en base sur le **même polygone** que le moteur (buffer 900 m autour d'un point
urbain de Saint-Paul, 55.2707 / -21.0096 ; recompte SQL direct vs sortie de `zone.py`).

### Tableau bloc · source · millésime · recompte

| Bloc affiché | Table / champ lu | Millésime | Même source que la fiche | Recompte (module = base) |
|---|---|---|---|---|
| Habitants | `filosofi_carreaux_200m.ind` (centroïde ∈ zone) | Filosofi **2021** | ✅ point de calcul UNIQUE Filosofi | **OK** 3490 = 3490 |
| Ménages | `filosofi_carreaux_200m.men` | Filosofi 2021 | ✅ | **OK** 1470 = 1470 |
| Revenu médian | `Σ ind_snv / Σ ind` (winsorisé) | Filosofi 2021 | ✅ (ESTIMÉ ; « approché » si majorité de carreaux `i_est_200='1'`) | **OK** 22 466 = 22 466 |
| Postes salariés (fourchette) | `sirene_etablissements.tranche_effectif` (bornes) | SIRENE **2026-08** | ✅ | **OK** (443 avec tranche, min 4139) |
| Entreprises / établissements | `sirene_etablissements` (actifs, GROUP BY naf) | SIRENE 2026-08 | ✅ | **OK** (comptes exacts par famille) |
| Étab. d'enseignement (BPE) | `spatial_layers` kind=`amenite_bpe` subtype=`C` | BPE **2025** | ✅ | **OK** |
| Arrêts (GTFS/OSM) | `spatial_layers` kind ∈ (`pole_echange`,`transport_arret`) | GTFS 2025-12→2026-08 / OSM | ✅ | **OK** |
| Ventes 12 mois | `dvf_mutations_parcelle` JOIN `parcels` (centroïde ∈ zone) | DVF **2021→2025** | ✅ | **OK** 20 |
| Médiane €/m² bâti (36 m) | idem, `valeur_fonciere / surface_reelle_bati` | DVF 2021→2025 | ✅ après fix (doctrine `marche_service`) | **CORRIGÉ** 100 888 → **4 750** |
| Annonces actives (Radar) | `pige_biens` JOIN `parcels` | Radar (pige manuelle, partielle) | ✅ (servi comme *minimum*, jamais un total) | **OK** |
| Permis 36 mois | `sitadel_permits` (géoloc.) | SITADEL **jusqu'à 2026-07** | ✅ | **OK** 49 |
| Trafic RN | `trafic_rn` (DISTINCT ON route, dernier `annee`) | Région (par tronçon : ⚠ **2011** sur N1) | ✅ | **OK** N1 = 36 246 véh/j |
| Zones PLU en % | `spatial_layers` kind=`plu_gpu_zone` | PLU/GPU | ✅ après fix (token du libellé) | **CORRIGÉ** (voir ci-dessous) |
| Destinations autorisées par zone | module `plu.destinations` (YAML calibrés) | PLU calibré (Saint-Paul millésime **2025-12-17**) | ✅ après fix | **CORRIGÉ** « calibration en cours » → verdicts réels |
| Logements autorisés (36 m) | `sitadel_permits.raw->>'nb_lgt'` | SITADEL 2026-07 | ✅ | **OK** 72 |
| Zones AU | `spatial_layers` kind=`plu_gpu_zone` subtype LIKE `AU%` | PLU/GPU | ✅ | **OK** |

### Points précis demandés

**a) L'isochrone (IGN) est-il bien le polygone d'agrégation ? — OUI.**
Dans `etude_de_zone()` (`zone.py:546`), la géométrie servie à TOUS les agrégateurs est
`zone = res["geom_geojson"]` (le polygone IGN mis en cache), via `_zone2975()` =
`ST_Transform(ST_GeomFromGeoJSON(:zone), 4326→2975)`. **Aucun cercle** : les bandes
concentriques (`bandes_isochrones`) ne servent QU'À dater les POI (temps de trajet), jamais à
compter. Échec IGN → statut `indisponible`, rien n'est compté (dégradé honnête). Mode polygone :
la géométrie dessinée court-circuite l'isochrone et sert de zone directement.

**b) « 1 106 étab. sans effectif renseigné » — normal SIRENE, PAS une perte de jointure.**
`emplois_zone()` lit une **seule** table (`sirene_etablissements`, GROUP BY `tranche_effectif`) —
il n'y a **aucune jointure** à perdre. Île entière : **85,6 %** des établissements actifs
(135 667 / 158 515) ont `tranche_effectif = 'NN'` (non renseigné). C'est la norme SIRENE :
micro-entrepreneurs, non-employeurs, holdings, professions libérales ne déclarent pas de tranche.
Les « sans effectif » sont donc comptés **à part** et **dits** (jamais additionnés à la
fourchette) — comportement correct, rien à corriger.

**c) « 100 888 €/m² médian bâti » (zone dessinée) — BUG DE CALCUL, corrigé.**
Cause : `dvf_mutations_parcelle` **répète la valeur foncière de TOUTE la mutation sur CHAQUE
parcelle** de la mutation. Exemples réels (Saint-Paul, 36 mois) :
- mutation `2023-1321481` = **9 597 713 €** répartie sur **91 parcelles** → 9,6 M€ ÷ 45 m² de
  bâti d'un appartement = **213 283 €/m²** ;
- mutation `2024-1188637` = **10 814 215 €** sur **1 008 parcelles** → **204 042 €/m²**.

**1 494 lignes sur 3 123** dépassent 12 000 €/m². Un petit polygone qui tombe sur une de ces
méga-mutations pousse la médiane à six chiffres (100 888). L'ancienne requête ne filtrait que
`valeur_fonciere > 0 AND surface_reelle_bati > 0` — sans aucun garde-fou.

**Correctif** (`marche_zone`, `zone.py`) : on aligne sur le **point de calcul UNIQUE du marché**
(`marche_service._filtre_comparables` / `config/dvf_profils.yaml`) — (a) `DISTINCT`
(id_mutation, id_parcelle) : la table contient des doublons exacts ; (b) `nature_mutation ILIKE
'vente%'` + `surface_reelle_bati >= 20` ; (c) ratio borné au domaine de bon sens
**[1 000 ; 12 000] €/m²** (artefacts DVF). Résultat : **4 750 €/m²** (valeur réaliste Réunion).
*Le compte « ventes 12 mois » n'est PAS touché* (ce n'est pas le bug ; il compte les mutations,
pas un prix).

**d) « U · calibration en cours » sur Saint-Paul (PLU calibré/validé) — MAUVAIS CHEMIN DE
LECTURE, corrigé.**
Saint-Paul est **entièrement calibré** (`config/plu_destinations/97415_saint_paul.yaml`,
millésime 2025-12-17, 67 zones : `U1a`, `U2c`, `Usdu`, `AU3c`…). Mais `contraintes_plu()` servait
la zone depuis **`spatial_layers.subtype`**, qui est le **typezone GPU générique** (`U`, `A`, `N`,
`AUc`) — le libellé précis (`Usdu`, `U2c`…) vit dans **`attrs->>'libelle'`**. La requête passait
donc `"U"` au verdict destinations ; le YAML n'a **pas** de zone `"U"` → `non_lu` → « calibration
en cours » à tort. La **fiche**, elle, résout le **token du libellé**
(`split_part(attrs->>'libelle',' ',1)`, cf. `app.py:5132`, EXPORTS-REBRANCHEMENT-1) — d'où sa
lecture correcte des destinations validées.

Preuve module : `verdict('Saint-Paul','U',…)` → *calibration en cours* ;
`verdict('Saint-Paul','U2c',…)` → *Restauration : autorisée* ; `'Usdu'` → *interdite*.

**Correctif** (`contraintes_plu`, `zone.py`) : on lit la zone par la **même expression que la
fiche** — `COALESCE(NULLIF(rtrim(split_part(btrim(attrs->>'libelle'),' ',1),':'),''),
split_part(btrim(name),' ',1), subtype)`. L'outil affiche désormais les zones précises et les
verdicts validés. Vérifié via l'endpoint live sur Saint-Paul :
`Nerl→interdit, U1a/U1b/U1c/U1f→autorise, N→interdit` (restauration).

### Ce qui a été corrigé (résumé)
| # | Correctif | Fichier | Nature |
|---|---|---|---|
| A2-c | Médiane €/m² bâti : filtre vente% + bâti≥20 + bornes [1000;12000] + dedup | `zone.py` `marche_zone` | bug de calcul |
| A2-d | Zones PLU + destinations lues par le **token du libellé** (comme la fiche), plus par `subtype` | `zone.py` `contraintes_plu` | mauvais chemin de lecture |

Décrits **sans corriger** (écarts de données/fraîcheur, hors mandat de fix) : le trafic RN peut
porter un millésime ancien par tronçon (N1 = 2011) ; le Radar est une pige manuelle partielle
(servi comme minimum) ; SIRENE « sans effectif » (85,6 % île entière, normal).

---

## B — Tout ce qu'on sait d'une zone (lecture seule, base d'ETUDE-ZONE-2)

Constat de Vic : l'app expose ~130 sources (`seed_sources.py`) et **~50 couches** servies dans
`spatial_layers` (toutes en géométrie 4326 + `geom_2975`, donc agrégeables sur un polygone
arbitraire par `ST_Intersects`/`ST_Area(ST_Intersection)`), plus des tables à la parcelle et à
l'IRIS. L'outil n'en montre aujourd'hui qu'une douzaine. Inventaire de ce qui **peut** s'agréger
sur un polygone et **n'y est pas** :

Légende coût : **trivial** = compte/somme sur une couche déjà en base · **moyen** = jointure ou
% de surface · **lourd** = calcul dérivé (bande LABUSE, ST_Union multi-couches, dédup mutation).

### Population & démographie
| Donnée | En base | Agrégeable polygone | Utilité | Coût |
|---|---|---|---|---|
| RP 2022 par IRIS (âge, évolution 2016→2022, vacance, âge du bâti) | oui (`iris_rp` + `spatial_layers` kind=`iris_insee`) | oui (IRIS intersectés — déjà lu partiellement par `population_zone`) | **fort** — structure de la population | moyen |
| Prix par type maison / appartement / terrain (au lieu d'une seule médiane) | oui (`dvf_mutations_parcelle.type_local`) | oui | **fort** — un €/m² unique masque 3 marchés | moyen |
| Loyers OLL / DHUP | oui (attributs commune) | non (maille commune) | moyen — dit à la maille commune | trivial |

### Économie
| Donnée | En base | Agrégeable | Utilité | Coût |
|---|---|---|---|---|
| Établissements par tranche d'âge (créations récentes, dynamique) | oui (`sirene_etablissements.date_creation`) | oui | moyen — vitalité économique | trivial |
| BODACC procédures collectives (santé des entreprises de la zone) | oui (`bodacc_procedures` par SIREN) | via géoloc. établissement | moyen | moyen |

### Immobilier / marché
| Donnée | En base | Agrégeable | Utilité | Coût |
|---|---|---|---|---|
| Permis **par type** (logement / commerce / activité) | oui (`sitadel_permits.raw`) | oui | **fort** — nature de l'urbanisation | moyen |
| Acquisitions récentes de PM (qui achète dans la zone) | oui (`pm_proprietaires_millesimes` 2019→2024) | oui (via parcelles) | fort — pression d'acteurs | moyen |
| VEFA / neuf | oui (maille commune) | non | faible | trivial |

### Foncier
| Donnée | En base | Agrégeable | Utilité | Coût |
|---|---|---|---|---|
| Parcelles à potentiel (**bande LABUSE**) dans la zone | oui (`parcel_evaluations` / score) | oui (parcelles ∈ zone) | **fort** — cœur du métier | lourd |
| Nu constructible en ha (zones U/AU × non bâti) | oui (`spatial_layers` plu + `parcels`/OCS) | oui | **fort** | lourd |
| Propriétaires PM dominants (top 5 par surface) | oui (`parcelle_personne_morale`, SIREN) | oui | **fort** — cf. Scan patrimoine | moyen |
| Consommation d'espaces NAF | oui (`commune_conso_enaf`) | non (maille commune) | moyen | trivial |

### Contraintes
| Donnée | En base | Agrégeable | Utilité | Coût |
|---|---|---|---|---|
| Risques PPR par niveau (% de la zone) | oui (`spatial_layers` `ppr`, `georisque_alea` FAIBLE/MOYEN/FORT) | oui (% ST_Union) | **fort** — cf. [[pieges-risques-2]] | moyen |
| Assainissement collectif vs ANC (% de la zone) | oui (`spatial_layers` `zonage_assainissement` + `anc_maille_taux`) | oui | **fort** — viabilisation | moyen |
| Espaces protégés (ZNIEFF, ENS, Parc National) | oui (`spatial_layers` `znieff`/`ens`/`parc_national`) | oui (% surface) | **fort** | trivial |
| ZFANG / FRR (fiscalité) | oui (`spatial_layers` `zfang`/`frr`) | oui (recouvrement) | **fort** — avantage fiscal | trivial |
| QPV / ORT / ACV / PVD | oui (`spatial_layers` `qpv`, + attrs commune ACV/ORT/PVD) | QPV oui (polygone) ; ORT/ACV/PVD maille commune | fort — dispositifs | trivial / moyen |
| Fibre Arcep | oui (attributs commune) | non (maille commune) | moyen | trivial |
| Lignes HTA / TCSP | oui (`spatial_layers` `ligne_mt`/`ligne_ht`/`tcsp_*`) | oui | moyen — réseaux | trivial |
| SUP, bruit, ICPE, sols pollués, cavités, trait de côte | oui (`spatial_layers` `sup`/`bruit_*`/`icpe`/`sol_pollue`/`cavite`/`trait_de_cote`) | oui | moyen | trivial |

### Équipements
| Donnée | En base | Agrégeable | Utilité | Coût |
|---|---|---|---|---|
| BPE **complet** (santé, commerces, sport, services — pas seulement enseignement) | oui (`spatial_layers` `amenite_bpe`, domaines A–G) | oui (déjà lu partiellement en « plus proches ») | **fort** — équipements = attractivité | trivial |
| RPLS logements sociaux & déficit SRU | RPLS non ingéré / SRU maille commune (`commune_contexte_sru`) | non (commune) | fort mais maille commune | moyen |

### Proposition d'organisation en sections
L'outil gagnerait à s'organiser en **7 sections** (accordéons), chacune ne servant que des
**faits sourcés et datés** (doctrine : jamais une projection) :

1. **Population** — habitants, ménages, revenu (existant) + âge/évolution RP par IRIS *(ajout)*.
2. **Économie** — postes, entreprises par famille (existant) + créations récentes, BODACC *(ajout)*.
3. **Immobilier** — ventes + **prix par type** *(ajout)*, annonces Radar (existant) + permis **par
   type** *(ajout)*.
4. **Foncier** — **bande LABUSE, nu constructible ha, top 5 PM** *(ajout entier)*.
5. **Contraintes** — PLU/zones + destinations (existant) + **PPR par niveau %, assainissement %,
   espaces protégés, ZFANG/FRR, QPV** *(ajout)*.
6. **Équipements** — **BPE complet par domaine** *(ajout)* + arrêts (existant).
7. **Dynamique** — acquisitions PM récentes, permis par type, loyers *(ajout)*.

Priorités (fort × coût raisonnable) : **BPE complet** (trivial), **PPR par niveau** (moyen),
**assainissement %** (moyen), **prix par type** (moyen), **espaces protégés / ZFANG-FRR / QPV**
(trivial), **top 5 PM** (moyen). Les mailles-commune (loyers, fibre, SRU, ACV/ORT) restent
servies **à la maille commune, dites comme telles** (pas de fausse précision zonale) — même
doctrine que MOBPRO déjà abandonné dans l'outil.

Ne rien coder ici : c'est la base du mandat **ETUDE-ZONE-2**.

---

## Tests
- Front : `tsc --noEmit` **vert** · `npm run build` **vert** · `vitest` **178/178**.
- Back : `pytest` zone (`test_zone_donnees`, `test_zone_recette`, `test_zone1`,
  `test_zone_moteur`, `test_zone_norm`) **29/29** (fixture `test_lot7` mise au contrat réel :
  la zone servie = token du libellé GPU). `test_plu_destinations` **25/26** — l'unique échec
  `test_module_unique_aucune_autre_lecture` est **PRÉ-EXISTANT** (offenders `circuit_dependance.py`,
  `gabarit_implantation_m2.py`, `api/app.py`, non touchés par ce mandat).

## Recette navigateur (environnement)
Backend `:8325`, front `:5525`. ⚠ Comme dans les mandats précédents, un run
`build-intersections` réel tenait un verrou `parcels` → `ensure_schema` bloquait le démarrage.
Contournement documenté : `lock_timeout=5000` **temporaire** dans `db.py` (le heal échoue vite,
l'app démarre, `/readyz` le dit) — **réverté avant commit** (`db.py` sans diff). Captures via
**node playwright direct** (chromium-1217) après retrait de la carte WebGL (le screenshot MCP
expire dessus). Fichier de capture jetable supprimé.
