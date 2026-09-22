# FICHE-COUCHES-1 — Inventaire du croisement parcelle × couches

Branche `feat/couches-tuyau`, départ `0e4b0181`. **Inventaire en lecture seule — aucune correction, aucune tuile touchée.** Ce document servira à écrire le mandat de correction.

## Le constat, expliqué

La fiche parcelle affiche, dans la section **« Risques et protections »**, un compteur « **N couches évaluées** » (`frontend/src/components/fiche/risques.tsx:33`). Ce nombre n'est **pas** le total des couches croisées : c'est le nombre de **lignes de l'onglet `risques`** (`f.lines.filter(l => l.onglet === 'risques')`, résultats `SOFT_FLAG | HARD_EXCLUDE | PASS | UNKNOWN`).

- L'onglet `risques` regroupe exactement **14 couches de cascade** (`served_cascade._ONGLET["risques"]`) : `risques (PPR+aléas), sol_pollue (SIS/CASIAS), cavite, icpe, mvt, pente, ravine, trait_de_cote, abf, ens (ENP), eau, bruit_route, cinquante_pas, sup`. Sur une parcelle peu contrainte, la plupart passent en `PASS` → **≈ 14 lignes → « 14 couches évaluées »**. (Sur une parcelle très contrainte le compteur monte — plusieurs SUP/aléas = plusieurs lignes ; cf. capture, compteur = 18.)
- Le **tuyau sert 56 couches** (`GET /map/tuyau/couches`). L'écart 14 → 56 n'est donc pas « 42 couches oubliées » : le « 14 » ne compte qu'**un seul onglet**. En réalité la fiche interroge **40** des 56 couches, réparties sur plusieurs onglets et blocs (risques, règles, marché, réseaux, propriétaire) **et** des blocs structurés hors-cascade (proximités KNN, fiscal, sols, aléas, dispositifs, équipements). **16** couches ne sont interrogées nulle part.

## Les trois raisons (définitions appliquées)

Pour chaque couche **non interrogée**, une raison en un mot :

- **`repère/fond`** — *volontairement exclue (fond de plan, repère)* : couche de base ou de repère, jamais une contrainte à évaluer (familles `reperes` et `fond_de_plan`).
- **`pas de croisement`** — *pas de croisement spatial implémenté* : la fiche traite **déjà le thème** via une couche sœur qui, elle, est croisée ; il ne manque que le croisement spatial de **cette** couche. Le correctif = **étendre** un handler existant.
- **`non déclarée`** — *couche non déclarée côté fiche* : **aucun** handler du thème n'existe dans la fiche (ni cascade, ni bloc). Le correctif = **déclarer** un handler neuf, puis croiser.

## Les trois cas connus

| Couche | Interrogée ? | Raison | Pourquoi |
|---|---|---|---|
| **Lignes HTA** (`ligne_mt`) | non | **pas de croisement** | Le thème « ligne électrique » EST traité : `_proximites_block` croise `ligne_ht` (HTB) en KNN (`app.py:4473`). La HTA (`ligne_mt`) n'est pas branchée — il suffit d'étendre ce handler. |
| **Bassins versants** (`bassin_versant`) | non | **non déclarée** | `bassin_versant` n'apparaît **nulle part** dans la construction de la fiche (ni cascade, ni bloc) — seulement comme couche carto (`_MAP_LAYER_KINDS`). Aucun handler « hydrographie / bassin » à étendre. |
| **Zones d'activité** (`zone_activite`) | non | **non déclarée** | Idem : `zone_activite` n'est référencée que côté carte. Aucun handler « zone d'activité » côté fiche. |

## Le tableau des 56 couches

Colonne « Interroge » : la fiche croise-t-elle la parcelle contre cette couche (n'importe quel onglet/bloc). « Mécanisme / Raison » : le code qui croise (si oui) ou la raison (si non).

| # | kind | famille | nom | Interroge | Mécanisme (oui) / Raison (non) |
|---|------|---------|-----|:---------:|--------------------------------|
| 1 | zfang | dispositifs | ZFANG (zone franche activités) | oui | bloc fiscal — régime commune (`_territoire_fiscal_block`) |
| 2 | frr | dispositifs | FRR (revitalisation rurale) | oui | bloc fiscal — commune + `frr_position` spatial (`app.py:4341`) |
| 3 | tva_primo | dispositifs | TVA réduite primo-accédant | oui | bloc fiscal — `ST_Intersects` kind=`tva_primo` (`app.py:4350`) |
| 4 | qpv | dispositifs | Quartiers prioritaires (QPV) | oui | bloc fiscal — `ST_Intersects` kind=`qpv` (`app.py:4346`) |
| 5 | anru | dispositifs | Rénovation urbaine (ANRU / NPNRU) | oui | bloc fiscal — `ST_Intersects` kind=`anru` (`app.py:4354`) |
| 6 | parc_national | environnement | Parc national | oui | cascade `parc_national` (`phase1.py:103`) |
| 7 | bassin_versant | environnement | Bassins versants (hydrographie) | **non** | **non déclarée** (aucun handler fiche) |
| 8 | znieff | environnement | ZNIEFF (type I & II) | **non** | **pas de croisement** (thème environnement croisé via ENP/parc/zone humide) |
| 9 | enp | environnement | Espaces naturels protégés | oui | cascade `ens` (`phase1.py:860`) — kind virtuel `enp`→`ens` |
| 10 | zone_humide | environnement | Zones humides | oui | cascade `zone_humide` (`phase1.py:730`) |
| 11 | foret_publique | environnement | Forêts publiques | oui | cascade `foret_publique` (`phase1.py:132`) |
| 12 | amenite_bpe | equipements | Équipements INSEE (BPE) | oui | bloc équipements KNN (`_PROX_EQUIP`, `app.py:4586`) |
| 13 | amenite | equipements | Équipements et services (OSM) | oui | cascade `amenites` (`etage1.py`) |
| 14 | sar | foncier | SAR — vocations / potentiel Région | oui | cascade `sar` (`phase1.py:154`) |
| 15 | safer | foncier | Foncier agricole — RPG / SAFER | oui | cascade `safer` (`phase1.py:508`) |
| 16 | zone_activite | foncier | Zones d'activité | **non** | **non déclarée** (aucun handler fiche) |
| 17 | friche | foncier | Friches (Cartofriches) | oui | cascade `friche` (`etage1.py:36`) |
| 18 | piscine_cosia | foncier | Piscines (3 niveaux de confiance) | **non** | **non déclarée** (recensement, aucun handler contrainte) |
| 19 | batiment | fond_de_plan | Bâti 3D (extrusion) | **non** | **repère/fond** (fond de plan, bouton 3D) |
| 20 | vefa_neuf | marche | Prix du logement neuf (VEFA) | **non** | **non déclarée** (aplat commune, aucun croisement fiche) |
| 21 | cimetiere | patrimoine | Cimetières | **non** | **non déclarée** (aucun handler fiche) |
| 22 | abf | patrimoine | Périmètres ABF / monuments | oui | cascade `abf` (`phase1.py:839`) |
| 23 | limites_communes | reperes | Limites communes | **non** | **repère/fond** |
| 24 | limites_parcelles | reperes | Limites parcelles (contour cadastral) | **non** | **repère/fond** |
| 25 | ligne_mt | reseaux | Lignes moyenne tension (HTA) | **non** | **pas de croisement** (sœur `ligne_ht` croisée en KNN) |
| 26 | ligne_ht | reseaux | Lignes haute tension (HTB) | oui | proximité KNN `ligne_ht` (`app.py:4473`) |
| 27 | tri_zone | risques | TRI — zones inondables | **non** | **pas de croisement** (thème inondation croisé via PPR/aléas) |
| 28 | alea_inondation | risques | Aléa inondation | oui | cascade `risques` → `georisque_alea` (bloc `aleas`) |
| 29 | alea_mvt | risques | Aléa mouvement de terrain | oui | cascade `risques`/`mvt` → `georisque_alea` (bloc `aleas`) |
| 30 | construction_surfacique | risques | Barrages, ponts et dalles | **non** | **non déclarée** (aucun handler ouvrage) |
| 31 | casias | risques | Anciens sites industriels (CASIAS) | oui | cascade `sol_pollue` → bloc `sols` (kind virtuel `casias`) |
| 32 | bruit_carte | risques | Cartes de bruit — dépassements | **non** | **pas de croisement** (sœur `bruit_route` croisée) |
| 33 | bruit_route | risques | Classement sonore (bruit routier) | oui | cascade `bruit_route` (`etage1.py`) |
| 34 | peb | risques | Plan d'exposition au bruit (PEB) | oui | cascade `peb` → bloc `dispositifs.peb` |
| 35 | endiguement | risques | Systèmes d'endiguement | **non** | **pas de croisement** (thème inondation croisé via PPR/aléas) |
| 36 | construction_lineaire | risques | Murs de soutènement | **non** | **non déclarée** (`emprise_lineaire` teste la forme de parcelle, pas ce kind) |
| 37 | trait_de_cote | risques | Érosion côtière (trait de côte) | oui | cascade `trait_de_cote` (`phase1.py:770`) |
| 38 | dpf | risques | Ravines et reculs (DPF) | oui | cascade `dpf` (`phase1.py:641`) |
| 39 | ppr | risques | PPR multirisque | oui | cascade `risques` (`phase1.py:563`) |
| 40 | icpe | risques | Installations classées (ICPE) | oui | cascade `icpe` (`etage1.py`) |
| 41 | sis | risques | Secteurs d'information sur les sols (SIS) | oui | cascade `sol_pollue` → bloc `sols` (kind virtuel `sis`) |
| 42 | cavite | risques | Cavités souterraines | oui | cascade `cavite` (`etage1.py`) |
| 43 | tcsp | transport | TCSP / stationnement allégé | oui | proximité `tcsp_station` (`app.py:4481`) |
| 44 | axe_structurant | transport | Axes structurants | oui | proximité KNN `axe_structurant` (`app.py:4516`) |
| 45 | transport_ligne | transport | Transport public — lignes | **non** | **pas de croisement** (arrêts/pôles croisés en KNN, pas les tracés) |
| 46 | telepherique | transport | Téléphérique | oui | proximité KNN `telepherique` (`app.py:4472`) |
| 47 | pole_echange | transport | Pôles d'échange | oui | proximité KNN `pole_echange` (`app.py:4471`) |
| 48 | transport_arret | transport | Transport public — arrêts | oui | proximité KNN `transport_arret` (`app.py:4470`) |
| 49 | zonage_parcelle | urbanisme | Zonage PLU par parcelle (calibré) | oui | zone PLU de la parcelle via `plu_gpu_zone` (`app.py:4928`) |
| 50 | plu_gpu_zone | urbanisme | Limites officielles du PLU (GPU) | oui | cascade `zonage_plu_gpu` + `ST_Intersects` (`app.py:4928`) |
| 51 | cinquante_pas | urbanisme | 50 pas géométriques | oui | cascade `cinquante_pas` (`etage1.py`) |
| 52 | artificialisation | urbanisme | Artificialisation (OCS GE) | oui | cascade `ocs_ge` (`phase1.py:910`) |
| 53 | dpu | urbanisme | Droit de préemption urbain (DPU) | oui | cascade `dpu` → bloc `dispositifs.dpu` |
| 54 | sup | urbanisme | Servitudes d'utilité publique (SUP) | oui | cascade `sup` → bloc `dispositifs.sup` |
| 55 | er | urbanisme | Emplacements réservés (ER) | oui | cascade `prescription_plu` (05) → bloc `dispositifs.er` |
| 56 | ebc | urbanisme | Espaces boisés classés (EBC) | oui | cascade `prescription_plu` (01) → bloc `dispositifs.ebc` |

## Synthèse

- **Interrogées : 40 / 56.** Mécanismes : cascade (intersection) ≈ 27 ; proximité KNN 7 (transport_arret, pole_echange, telepherique, ligne_ht, tcsp, axe_structurant, amenite_bpe) ; fiscal (intersection/commune) 5 (qpv, anru, tva_primo, frr, zfang) ; zonage PLU 1 (zonage_parcelle, mutualisé avec plu_gpu_zone).
- **Non interrogées : 16 / 56**, réparties en :
  - **pas de croisement spatial implémenté (6)** — sœur du thème déjà croisée : `ligne_mt`, `znieff`, `tri_zone`, `bruit_carte`, `endiguement`, `transport_ligne`.
  - **couche non déclarée côté fiche (7)** — aucun handler du thème : `bassin_versant`, `zone_activite`, `piscine_cosia`, `vefa_neuf`, `cimetiere`, `construction_surfacique`, `construction_lineaire`.
  - **volontairement exclue — fond de plan / repère (3)** : `batiment`, `limites_communes`, `limites_parcelles`.

## Preuves

- **Le tableau des 56 lignes** : ci-dessus.
- **Capture** : `captures/fiche-couches/fiche_contrainte.png` — parcelle `97410000AN0347` (Saint-Benoît, littorale), choisie pour toucher beaucoup de couches (PPR + tri_zone + cinquante_pas + trait_de_côte + SUP + DPU + aléas + sols + proximités). La fiche montre ce qui remonte réellement (aléas, sols, vigilances, dispositifs, proximités) et le **compteur** de la section « Risques et protections » = **18 couches évaluées** (18 lignes de l'onglet `risques` ; 8 vigilances).

Origine des données : `GET /map/tuyau/couches` (56 couches) ; `_build_fiche` / cascade (`src/labuse/cascade/`, `config/cascade_rules.yaml`) ; blocs `_proximites_block`, `_proximites_equipements_block`, `_territoire_fiscal_block`, `_sols_block`, `_aleas_block` (`src/labuse/api/app.py`). Stack de lecture `:8055/:5255`. `tsc -b` vert (aucun code TS modifié).
