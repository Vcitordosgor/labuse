# AUDIT — LES DÉCOUPES DE LA CASCADE : MESURER LES FRONTIÈRES

*Audit pur, aucune correction. Contexte : refonte cascade — ne garder que l'impossible LÉGAL ou PHYSIQUE.
Mesures sur le run servi `q_v9_m81` (`config/served_run.txt`), univers 431 663, étage 0 = 340 752,
vivier figeable actuel = 90 911. Chaque chiffre porte sa requête et son `fichier:ligne`.*

---

## RÉSUMÉ DES FRONTIÈRES (ce que chaque découpe libère)

| Découpe | Frontière proposée | Libère (brut) | Reste exclu |
|---|---|--:|--:|
| **PPR rouge/bleu** | rouge inconstructible / bleu visible | **0** (déjà en place) | 44 764 (tous rouge) |
| **Foncier public** | équipement reste / ordinaire visible | **9 002** (public seul motif) | 27 377 (co-écartés physique/légal) |
| **Pente** | falaise 45° (100 %) | **10 016** | 4 815 (≥ 45°) |
| **Micro-parcelle** | plancher 40 m² | **19 686** | 18 902 (< 40 m²) |
| **Zonage sous-zones** | libérer STECAL/habitat | **~1 100** (calibration requise) | ~76 000 A/N strict + protection |
| **Prescription ER** | ER = fait affiché (servitude levable) | **5 125** | 15 (corridor/attente = gel réel) |

**Après dédoublonnage des chevauchements** (une parcelle libérée par la pente mais aussi bâtie reste
exclue), le NET est bien inférieur à la somme brute. **Voir la synthèse §5.**

---

## 1. PPR : rouge vs bleu

**Oui, nos couches distinguent le zonage réglementaire.** L'ingestion DEAL (WFS Lizmap) écrit le degré
dans **`spatial_layers.subtype`** : `INTERDICTION` (rouge, inconstructible) / `PRESCRIPTION` (bleu,
constructible sous prescriptions) — `layers_ingest.py:356-368` (« subtype = DEGRE »), avec `code_degre`
détaillé dans `attrs` (Rrtc, B…). En base : **74 INTERDICTION + 88 PRESCRIPTION + 2 « i »**.
```sql
SELECT subtype, count(*) FROM spatial_layers WHERE kind='ppr' GROUP BY subtype;
-- PRESCRIPTION 88 · INTERDICTION 74 · i 2
```

**La règle n'exclut QUE le rouge, et seulement au-delà de 50 % de recouvrement** — `phase1.py:514`
(`if i.subtype in red`, `red = ppr_red_subtypes = ['INTERDICTION']`, `cascade_rules.yaml:141`) puis
`phase1.py:525-529` (`cov_pct >= ppr_red_exclude_pct=50` → `hard_exclude`, `yaml:148`). Le bleu
(`PRESCRIPTION`) → `soft_flag`, **jamais exclu**.

**Sur les 44 764 exclues PPR : 100 % sont en rouge.** La découpe est donc **déjà faite** — il n'y a rien
à libérer côté bleu.
```sql
-- motif des exclusions risques : 45 036 lignes, toutes « PPR zone rouge » (44 764 parcelles distinctes)
SELECT count(*) FROM dryrun_cascade_results
WHERE run_label='q_v9_m81' AND result='HARD_EXCLUDE' AND layer_name='risques'; -- 45 036
-- parcelles intersectant chaque zonage (toute couverture) :
--   INTERDICTION (rouge) : 106 808  · dont ≥50 % → 44 764 exclues ; <50 % → 62 044 déjà visibles
--   PRESCRIPTION (bleu)  : 122 445  → toutes visibles (soft_flag), jamais exclues
```
**Conclusion #1** : rien à réingérer, rien à découper. Le rouge/bleu est déjà tranché, le bleu (122 445
parcelles concernées) est déjà visible. *(Nuance : 62 044 parcelles touchent du rouge < 50 % et sont déjà
visibles — la graduation de recouvrement M-I joue déjà.)*

---

## 2. Foncier public : équipement vs ordinaire

**Le motif (36 379) porte sur le PROPRIÉTAIRE, pas sur l'usage.** `foncier_public` exclut si le
propriétaire DGFiP est public — groupes 1-4/9 (`etage0_ext.py:65-76`, dict `GROUPES_PUBLICS` `:25`),
source `parcelle_personne_morale`. Ventilation par groupe :
```sql
SELECT pm.groupe, pm.groupe_label, count(DISTINCT p.id)
FROM parcels p JOIN parcelle_personne_morale pm ON pm.idu=p.idu
WHERE p.id IN (SELECT parcel_id FROM dryrun_cascade_results
  WHERE run_label='q_v9_m81' AND result='HARD_EXCLUDE' AND layer_name='foncier_public')
GROUP BY 1,2 ORDER BY 3 DESC;
```
| Groupe | Parcelles |
|---|--:|
| g4 Commune | 24 374 |
| g1 État | 5 778 |
| g3 Département | 3 936 |
| g9 Établissements publics | 2 202 |
| g2 Région | 89 |

**La nature (équipement vs ordinaire) n'est PAS dans le signal propriétaire.** Le proxy mesurable : une
parcelle publique est-elle AUSSI écartée par une couche physique/légale (donc emprise d'équipement /
voirie / zone protégée qui reste exclue) ou est-elle écartée UNIQUEMENT parce que publique (donc
« ordinaire » — délaissé/réserve foncière négociable) ?
```sql
-- foncier_public SEUL motif vs co-écarté par une autre couche HE
WITH fp AS (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
            WHERE run_label='q_v9_m81' AND result='HARD_EXCLUDE' AND layer_name='foncier_public'),
     autres AS (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                WHERE run_label='q_v9_m81' AND result='HARD_EXCLUDE' AND layer_name<>'foncier_public')
SELECT count(*) FILTER (WHERE parcel_id NOT IN (SELECT parcel_id FROM autres)) seul,   -- 9 002
       count(*) FILTER (WHERE parcel_id IN (SELECT parcel_id FROM autres)) co         -- 27 377
FROM fp;
```
- **27 377 restent exclues** — co-écartées par une couche physique/légale (zonage A/N 10 870, surface
  7 529, PPR 6 461, bâti 6 083, emprise linéaire 3 364, forêt 3 254, pente 2 808, parc 2 671…).
- **9 002 deviennent visibles** — public SEUL motif (majorité `COM` communes : 6 508, puis EPIC 539,
  ÉTAT 466, COLL 460, DEPT 407…). Ce sont les délaissés / réserves communales négociables.

*Réserve honnête* : un équipement public (école, cimetière) NON détecté par nos couches physiques (absent
d'OSM/bâti) tomberait à tort dans les 9 002. Borne haute de libération, à affiner à l'ortho si besoin.

**La facette propriétaire ne sait PAS encore filtrer le public.** `proprietaire_type` accepte `pm` /
`bailleur` (HLM/SEM) / `pp` (personne physique) — **pas de valeur « public »** (`app.py:1078-1088`). La
facette « PM privée » filtre explicitement le **groupe MAJIC 0** (arbitrage Vic : hors communes/État,
`app.py:976-984`). **Mais la classification publique EXISTE déjà** (`proprietaire_type.py:15-20` :
commune/état/collectivité/EPF/établissement public/SEM → `public=True`) — servie en fiche, pas offerte en
filtre. **→ à ÉTENDRE** : ajouter une valeur « public négociable » à `proprietaire_type` (la brique de
classification est là, seul le filtre manque).

---

## 3. Pente : le seuil falaise

**Seuil actuel = 60 % de pente** (`seuil_faux_positif_pct`, `cascade_rules.yaml:195`, lu `phase1.py:657-662`).
*Correction au mandat : ce seuil est en **config**, pas « en dur » — les « en dur » relevés sont
`bati.py` et `etage0_ext.py`. 60 % de pente = **31°**.* La pente vient de `spatial_layers` kind=`pente`
(`attrs.slope_pct`), servie par parcelle dans le detail du verdict (« Pente NN % »).

Distribution des 14 831 exclues, convertie en degrés (`deg = atan(pct/100)`) :
```sql
SELECT (regexp_match(detail,'Pente (\d+) %'))[1]::int AS pct, count(*)
FROM dryrun_cascade_results
WHERE run_label='q_v9_m81' AND result='HARD_EXCLUDE' AND layer_name='pente' GROUP BY 1;
```
| Tranche | Parcelles | (pente %) |
|---|--:|---|
| 15-25° | 0 | (le seuil 60 %=31° ne descend jamais si bas) |
| 25-35° | 4 632 | 60-70 % |
| 35-45° | 5 384 | 70-100 % |
| 45°+ | 4 815 | ≥ 100 % |

**Propositions chiffrées** (repères : 35° = 70 %, 45° = 100 %) :
- **Falaise 45° (100 %)** : restent exclues **4 815** (≥ 45°) · **libérées 10 016** (les 31-45°).
- **Falaise 35° (70 %)** : restent exclues **10 199** (35-45° + 45°+) · **libérées 4 632** (les 31-35°).

---

## 4. Micro-parcelle : le plancher

**Seuil actuel = 100 m²** (`faux_positif_max_m2`, `cascade_rules.yaml:283`, lu `phase1.py:812-817` —
config, PLACEHOLDER « à calibrer »). En deçà → `hard_exclude` « aucun programme possible ».

Distribution des 38 588 exclues :
```sql
SELECT CASE WHEN surface_m2<40 THEN '0-40' WHEN surface_m2<50 THEN '40-50'
            WHEN surface_m2<100 THEN '50-100' END, count(DISTINCT p.id)
FROM parcels p JOIN dryrun_cascade_results cr ON cr.parcel_id=p.id
WHERE cr.run_label='q_v9_m81' AND cr.result='HARD_EXCLUDE' AND cr.layer_name='surface' GROUP BY 1;
```
| Tranche | Parcelles |
|---|--:|
| 0-40 m² | 18 902 |
| 40-50 m² | 3 680 |
| 50-100 m² | 16 006 |

**Propositions** :
- **Plancher 40 m²** : restent exclues **18 902** (< 40) · **libérées 19 686** (40-100).
- **Plancher 50 m²** : restent exclues **22 582** (< 50) · **libérées 16 006** (50-100).

---

## 4-bis. Zonage N/A : les sous-zones constructibles

**La règle lit la LETTRE de famille (N/A), pas la sous-zone.** `phase1.py:263-283` : `classe(libelle)`
appelle `est_famille(subtype, ['A','N'])` sur **`subtype` = la famille** (U/AU/A/N) ; le libellé fin
(Nh, Nco, STECAL) vit dans `name`, **non lu** par la branche d'exclusion A/N (seule la branche « éco »
U/AU habitat-interdit lit le libellé fin via `resolve_zone`, `phase1.py:296-313`). Champ GPU utilisé =
la famille ; table servie `parcel_zone_plu` (`zone_fam` / `zone_lib`).

Ventilation des 103 722 exclues zonage :
```sql
WITH ex AS (SELECT DISTINCT p.idu FROM dryrun_cascade_results cr JOIN parcels p ON p.id=cr.parcel_id
            WHERE cr.run_label='q_v9_m81' AND cr.result='HARD_EXCLUDE' AND cr.layer_name='zonage_plu_gpu')
SELECT z.zone_fam, count(*) FROM ex JOIN parcel_zone_plu z ON z.idu=ex.idu GROUP BY 1;
-- A 71 009 · N 30 259 · U 1 913 (éco) · AU 541
```
Découpe strict vs sous-zone :
| Catégorie | Parcelles |
|---|--:|
| **A/N STRICT** (libellé = « A » ou « N ») | **77 118** — exclusion juste (agricole/naturel pur) |
| **A/N SOUS-ZONE** (libellé fin ≠ lettre nue) | **24 150** — à examiner |
| famille U/AU (éco habitat interdit) | 2 454 |

**MAIS les 24 150 sous-zones ne sont PAS 24 150 sur-exclues.** Croisées avec les libellés réels, la
grande majorité sont des sous-zones de **protection**, légitimement inconstructibles : Nco (corridor
écologique) 4 342, APF 3 105, Npnr (parc naturel régional) 2 884, Acu 2 669, Nr 1 642, Nli 1 169, Nce
846, Ntvb (trame verte/bleue) 309, Ncor 249… La calibration PLU existante (`resolve_zone`) **ne couvre
aucune** de ces sous-zones (elle est bâtie pour l'exception éco U/AU, pas pour les N/A) :
```
sur 24 150 : calibrée habitat-autorisé 0 · calibrée interdit 0 · NON calibrée 24 150
```
Heuristique par libellé (marqueur habitat/hameau/STECAL — le « h ») :
| Signal | Parcelles | Exemples |
|---|--:|---|
| **habitat/STECAL probable (SUR-EXCLUE)** | **~1 119** | AD 709, NH 183, Arh 88, NL 55, Nrh 50, Ntoh 19 |
| protection (corridor/TVB/parc/agri spécialisé) | 21 520 | Nco, Npnr, Ntvb, Acu… |
| indéterminé (à calibrer) | 1 511 | An, Ac, Ntc, Na… |

**Conclusion 4-bis** : la sur-exclusion réelle est **petite (~1 100, borne haute ~2 600)**, PAS 24 150 —
la règle famille-seule est grossière mais tombe juste sur l'essentiel. Pour trancher précisément les
STECAL/hameaux, il faut **calibrer les sous-zones N/A** commune par commune (le PLU calibré actuel ne les
couvre pas). Chiffre à confirmer par cette calibration, pas au jugé.

---

## 4-ter. Prescription PLU : bloc ou par type

**La règle exclut DÉJÀ par type, pas en bloc.** `phase1.py` : seuls **l'emplacement réservé ≥ 50 %**
(`:428-437`) et **deux VETO nommés ≥ 50 %** (corridor écologique L151-23, périmètre d'attente L151-41,
`:417-423`) excluent. EBC (`:443-446`), patrimoine bâti (`:447-450`), mixité/OAP/eaux (`:454-465`) →
`soft_flag`/`passed`, **jamais exclus**.

Ventilation des 5 140 exclusions :
```sql
SELECT CASE WHEN detail ILIKE '%emplacement réservé%' THEN 'ER'
            WHEN detail ILIKE '%corridor%' THEN 'corridor écologique'
            WHEN detail ILIKE '%attente%' THEN 'périmètre attente' END, count(DISTINCT parcel_id)
FROM dryrun_cascade_results WHERE run_label='q_v9_m81' AND result='HARD_EXCLUDE'
  AND layer_name='prescription_plu' GROUP BY 1;
```
| Type | Exclues | Interdit vraiment de construire ? |
|---|--:|---|
| **Emplacement réservé (ER)** | **5 125** | Non — servitude **LEVABLE** (motif dit déjà « à réévaluer si l'ER est abandonné ») |
| Corridor écologique (L151-23) | 6 | **Oui** — protection biodiversité, gel réel |
| Périmètre d'attente (L151-41) | 9 | **Oui** — constructibilité gelée (projet d'ensemble) |

Contraintes déjà en **fait affiché** (soft, correct) : EBC 36 205, ER partiel < 50 % 32 468, patrimoine
bâti 3 830, périmètres divers…

**Proposition de tri (chiffrée)** :
- **Restent cascade** (interdiction réelle) : corridor + attente = **15**. *(À considérer aussi : l'EBC
  interdit toute construction sur l'emprise boisée — actuellement soft ; sous-exclusion possible, mais
  emprise souvent partielle → laisser en fait affiché est défendable.)*
- **Deviennent fait affiché** (servitude levable, pas une impossibilité) : **ER = 5 125 libérées**.

---

## 5. LA SYNTHÈSE CHIFFRÉE — FRONTIÈRES ARBITRÉES (Vic)

**Frontières fixées** : **PPR** rouge (inchangé, découpe déjà en place) · **foncier public** = les 9 002
« public seul motif » deviennent visibles · **pente** falaise **45°** (au-delà = exclu) · **micro**
plancher **40 m²** (en dessous = exclu, même en fusion ça ne pèse rien) · **prescription** ER → fait
affiché (corridor/attente 15 → restent) · **zonage sous-zones** ~1 100 noté (calibration N/A plus tard,
non bloquant). Décisions SANS découpe (restent cascade) : parc national, eau/ravines, forêt publique,
trait de côte, 50 pas, emprises voirie/OSM, **bâti**.

**« Saturé » N'EST PAS une exclusion (arbitrage Vic).** Une parcelle sans droits résiduels reste
**VISIBLE** — on peut raser, on peut fusionner. « SDP résiduelle nulle » devient un **FAIT AFFICHÉ** en
fiche et une **FACETTE** (« droits résiduels : oui / non ») : le score dit la probabilité, le client
décide. **Aucune soustraction au vivier.**

**Le NET n'est pas la somme des libérations** : une micro-parcelle aussi bâtie, ou un ER en zone A, reste
exclu. Calcul ensembliste (`libérées = étage0 − toute-couche-gardée`) :
```
KEEP = {eau, parc_national, foret_publique, trait_de_cote, bati, risques, osm_faux_positif,
        emprise_lineaire, emprise_routiere, zonage_plu_gpu, prescription(veto), pente≥100%, surface<40}
libérées = étage0(340 752) − KEEP ;  foncier_public & ER & pente<100% & surface≥40 = NON gardés
```

| Étape | Parcelles |
|---|--:|
| Vivier figeable **actuel** | **90 911** |
| + libérées par les découpes (**net, dédoublonné**) | **+20 460** |
| = **VIVIER CIBLE** (« saturé » reste visible) | **111 371** |

**✅ VIVIER FINAL CONFIRMÉ = 111 371.** C'est le nombre que le client verra.

D'où viennent les **20 460** (motifs présents parmi les libérées — se chevauchent, l'union unique = 20 460) :
| Motif libéré | Parcelles libérées le portant |
|---|--:|
| Foncier public (devenu négociable) | 11 468 |
| Micro-parcelle 40-100 m² | 9 085 |
| Emplacement réservé (fait affiché) | 2 147 |
| Pente 31-45° | 797 |

**Enseignement honnête** : la pente ne pèse que **797 net** (sur 10 016 bruts) — la quasi-totalité des
terrains en pente 31-45° sont AUSSI en zone N/A ou bâtis (gardés). De même l'ER : 2 147 net sur 5 125
bruts. Les deux gros contributeurs réels sont le **foncier public** (11 468) et la **micro-parcelle**
(9 085). Relâcher la pente seule ne libérerait presque rien.

*Reste ouvert, non bloquant : la calibration des sous-zones N/A (4-bis) ajouterait ~1 100 (borne haute
~2 600) une fois les STECAL/hameaux distingués commune par commune.*

---

*Aucune correction, aucun découpage, aucune réingestion. Branche `audit/cascade-decoupes`, non mergée.*
