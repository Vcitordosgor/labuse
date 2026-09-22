# PHASE 1.A — GATE GPU : le PLU de Saint-Paul est-il exploitable sur le Géoportail de l'Urbanisme ?

> **Mission v2, point de départ imposé** : « lecture du code existant → Phase 1.A (test GPU
> sur 3 parcelles témoins) → RAPPORT → STOP ». Ce document est le livrable de ce GATE.
> Lecture seule, aucune écriture en base, aucune modification de la cascade.
>
> **Script de test** : `scripts/gpu_witness_test.py` (retry + backoff exponentiel + cache
> disque). **Données brutes** : `reports/phase1a_gpu/gpu_witness_report.json` (+ `cache/`).
> **Date du test** : 2026-06-12.

---

## 1. Verdict du GATE — ✅ PASS

**Le PLU de Saint-Paul EST dématérialisé sur le Géoportail de l'Urbanisme, au format CNIG,
interrogeable en direct via l'API Carto GPU.** Le plan B (PEIGEO/AGORAH, TCO, open data) n'est
**pas nécessaire**. Tous les endpoints visés au brief répondent en HTTP 200 sur les 3 témoins.

| Endpoint | Résultat sur Saint-Paul |
|---|---|
| `/municipality?insee=97415` | 1 feature · `name=SAINT-PAUL` · **`is_rnu=false`** (la commune a bien un document d'urbanisme, pas de RNU) |
| `/document?geom=<point>` | document rattaché · `partition=DU_97415` · `gpu_status=production` |
| `/zone-urba?geom=<polygone>` | **zone renvoyée sur 100 % des 3 témoins** (typezone + libelle CNIG) |
| `/prescription-surf?geom=` | **2 à 3 prescriptions surfaciques par parcelle** (ER, mixité sociale, eaux pluviales) |
| `/prescription-lin` · `/prescription-pct` | 0 feature sur ces 3 témoins (pas d'erreur — simplement aucune prescription lin/pct ici) |
| `/assiette-sup-s?geom=` | 0 feature sur ces 3 points témoins |

### Fraîcheur & couverture (preuve)
- **`idurba = 97415_PLU_20251217`** → paquet PLU dématérialisé du **17/12/2025** (le plus récent).
- **`datvalid = 20120927`** → PLU approuvé le **27/09/2012** — **exactement** le document que cite
  déjà `config/plu_saint_paul.yaml` (approbation 2012-09-27, édition mars 2026).
- **`gpu_status = production`**, snapshot GPU **2026-03-09** (≈ 3 mois avant ce test).
- Conclusion : donnée **officielle, en production, fraîche et cohérente** avec le règlement
  écrit déjà exploité par le moteur de faisabilité.

---

## 2. Les 3 parcelles témoins (sélection déterministe en base, zone dominante > 95 %)

| Parcelle | Surface | **GPU live** `zone-urba` (typezone / libelle) | Prescriptions GPU surfaciques | Zonage déjà ingéré (`plu_gpu_zone`) | Verdict cascade ACTUEL |
|---|---|---|---|---|---|
| **97415000BV0912** *(U / centre)* | 3 948 m² | `U` / **`U6c`** | eaux pluviales (modérée) · **Clause logements aidés** · **ER 81 — chemin de la Cigale, élargissement à 6 m** | `U` (cov 1.00) | `zonage_plu_gpu = POSITIVE` « U constructible » · `sar = PASS` |
| **97415000BV0405** *(A / agricole)* | 1 991 m² | `A` / **`A`** (+ `U6c` en bordure) | eaux pluviales · Clause logements aidés | `A` (cov 1.00) | `zonage_plu_gpu = SOFT_FLAG moyen` « A agricole — SAFER » · `sar = PASS` |
| **97415000BV1431** *(AU / à urbaniser)* | 2 274 m² | `AUc` / **`AU6c`** (+ `U6c` en bordure) | Clause logements aidés (×2) · eaux pluviales | `AUc` (cov 1.00) | `zonage_plu_gpu = POSITIVE` « AUc constructible » · **`sar = SOFT_FLAG fort` « espace naturel 98 % »** |

### Lecture des résultats
1. **Le zonage GPU live = le zonage déjà ingéré** : typezone identique sur les 3 (U, A, AUc).
   L'ingestion `plu_gpu_zone` est donc **fidèle et à jour**. Pas de dérive constatée.
2. **Le GPU fournit un `libelle` plus fin (`U6c`, `AU6c`) que le `subtype` stocké (`U`, `AUc`)**.
   Or c'est ce libelle fin qui porte la vraie règle PLU (hauteur, recul, stationnement…). Le
   moteur de **faisabilité** le résout déjà correctement (il lit la colonne `name` → `U6c`,
   `AU6c` → règle exacte de `plu_saint_paul.yaml`). Mais la **cascade** d'exclusion, elle, ne
   raisonne que sur le typezone grossier (`U`/`A`/`N`/`AU`).
3. **BV1431 = le cas le plus instructif** : PLU **constructible** (`AU6c`) MAIS proxy SAR
   « espace naturel à 98 % ». C'est exactement le type de conflit PLU↔SAR que le brief veut
   arbitrer — et aujourd'hui le SAR n'est qu'un **proxy de démo** (sous-type `vocation_*`),
   pas la donnée SAR réglementaire.
4. **Les prescriptions GPU portent de vraies contraintes que la cascade NE lit PAS** :
   emplacement réservé **ER 81** (BV0912 partiellement grevée pour élargir le chemin de la
   Cigale), **secteur de mixité sociale** (« Clause logements aidés »), **zonage eaux
   pluviales**. Disponibles en live, non ingérées.

---

## 3. ⛔ STOP & VALIDATE — contradiction majeure brief ↔ code existant (§0.3)

> Le §0 du brief impose : « Si un point de ce brief contredit le code existant : **STOP, poser
> la question, ne pas trancher seul.** » C'est le cas, et de façon structurante. **Je n'implémente
> rien de la Phase 1.B et au-delà avant ta réponse.**

**La prémisse du brief — « aujourd'hui on n'a qu'un proxy SAR, il faut bâtir le vrai PLU + la
capacité + le bilan inversé » — ne correspond pas à l'état réel du dépôt.** L'essentiel des
Phases 1 et 2 est **déjà implémenté, sourcé et câblé à l'UI/aux exports** :

| Brief v2 demande de… | État réel dans le dépôt | Preuve |
|---|---|---|
| **1.A** tester le PLU sur le GPU | ✅ fait (ce rapport) — et le GPU était **déjà** la source d'ingestion | `connectors/gpu.py`, `ingestion/layers_ingest.py::ingest_gpu_zones` |
| **1.B** intégrer le vrai zonage PLU | ✅ **déjà ingéré** dans `plu_gpu_zone` + couche cascade dédiée | `ZonagePluGpuLayer` (`cascade/layers/phase1.py`) |
| **1.C** créer un `plu_rules.yaml` | ✅ **existe déjà** : `config/plu_saint_paul.yaml`, zone par zone, **chaque valeur sourcée article + page du règlement** | fichier de 240 lignes, 40+ zones |
| **2** capacité (SDP / logements / niveaux / stationnement) | ✅ **fait et tracé** : chaque étape cite l'article PLU (emprise via `ST_Buffer` reculs réels en EPSG:2975, niveaux, pleine terre, plafond densité) | `faisabilite/engine.py` |
| **2** bilan **inversé** (charge foncière admissible vs marché DVF) | ✅ **fait et affiché** dans la fiche + exports | `faisabilite/bilan.py` (`compute_bilan`, `charge_fonciere`, `sector_price` DVF) ; `api/resume.py`, `api/export.py`, `web/app.js` |
| **2.A-bis** détecter le bâti existant | ✅ **fait** (chantier R1) : couche BD TOPO + déclassement gradué | `labuse/bati.py`, `AUDIT_R1_BATI_CORRECTION.md` |

Autrement dit : **le « DONE » visé par le brief est, sur le papier, en grande partie déjà
atteint.** Lancer les phases telles qu'écrites reviendrait à reconstruire de l'existant — ce que
le hors-périmètre du brief interdit explicitement (« refactors non demandés », « toute
fonctionnalité non listée sans validation »).

### Là où le brief contredit *vraiment* le code (décisions qui t'appartiennent)

**Q1 — Orientation générale.** Vu l'état ci-dessus, sur quoi je travaille réellement ?
  - (a) **Durcir/compléter l'existant** sur les écarts concrets listés Q2→Q6 (recommandé) ;
  - (b) refaire à l'identique ce qui existe (déconseillé — interdit par le hors-périmètre) ;
  - (c) autre cap que tu précises.

**Q2 — N/A : exclure ou signaler ?** Le brief 1.B veut **N et A → HARD_EXCLUDE**. Le code
**soft-flag** aujourd'hui (`N` → flag fort, `A` → flag moyen — `config/cascade_rules.yaml`),
choix assumé « ne vaut ni interdiction ni constructibilité ». Or sur le GPU, `A`/`N` sont
réellement non-constructibles (cf. `plu_saint_paul.yaml` : « zones non constructibles : A, N »).
→ **Je bascule N/A en HARD_EXCLUDE** (aligné brief + réalité PLU), ou **je garde le soft-flag**
(prudence actuelle) ? *(impact mesuré : ~304 parcelles à dominante A/N — 23 en A, 281 en N —
passeraient en « exclue » / « faux positif » ; impact modéré, pas brutal.)*

**Q3 — SAR : proxy ou donnée réglementaire ?** Le brief veut le **SAR rétrogradé en informatif**.
Le code peut aujourd'hui **HARD_EXCLUDE** sur SAR (`espace_naturel`, `coupure_urbanisation`).
Mais le SAR ingéré est un **proxy de démo** (`vocation_*`), pas la donnée SAR officielle. Deux
sujets distincts : (a) confirmes-tu que **le SAR ne doit jamais exclure seul** (informatif) ?
(b) veux-tu qu'on **remplace le proxy par le vrai SAR** (PEIGEO) — nouvelle source, hors GPU ?

**Q4 — Finesse de zone (libelle vs typezone).** La cascade ne lit que `U/A/N/AU` ; le GPU livre
`U6c/AU6c` (et la faisabilité s'en sert déjà). Veux-tu que **l'ingestion stocke le libelle fin**
et que la cascade s'aligne (ex. distinguer une sous-zone N constructible d'une Nr stricte) ?

**Q5 — Prescriptions GPU (vraies contraintes non lues).** ER (emplacement réservé), secteur de
mixité sociale, zonage eaux pluviales sont **live sur le GPU mais non ingérés**. C'est le gisement
le plus utile et le plus aligné avec l'esprit du brief (« cascade complète »). Je l'ouvre en
**Phase 1.B réelle** (ingestion `prescription-surf/lin/pct` → nouvelles couches cascade) ?
*(c'est la seule « vraie » nouveauté de valeur que ce test fait apparaître.)*

**Q6 — Ingestion : bbox unique vs mailles.** Le brief 1.B décrit une ingestion **par mailles
~1 km + dédup** ; le code fait **un seul appel `zone-urba` sur la bbox commune** (et ça
fonctionne : **7 532 zones ingérées**, couverture 100 % sur les témoins). Je **re-architecture en
mailles** (utile surtout si on craint un plafond de features de l'API), ou **je garde le bbox
unique** tant qu'aucune troncature n'est constatée ?

---

## 4. Ce que je propose (si tu me suis sur Q1.a)

Ordre de valeur décroissante, chacun gaté par ta validation :
1. **Q5 — prescriptions GPU** (ER / mixité / eaux pluviales) : la vraie cascade « complète »,
   100 % alignée GPU, zéro reconstruction d'existant.
2. **Q2 — trancher N/A** (exclude vs flag) : une ligne de config, gros impact statut, à
   **décider** avant de relancer une évaluation.
3. **Q4 — libelle fin** dans la cascade : petit coût, fiabilise les sous-zones.
4. **Q3 — SAR** : clarifier proxy vs réglementaire (potentielle nouvelle source).
5. **Q6 — mailles** : seulement si on veut blinder l'ingestion contre un plafond API.

**Je m'arrête ici. Aucune écriture cascade / ingestion tant que tu n'as pas répondu (au moins Q1,
Q2, Q5).** Dès ta réponse, je traite point par point, toujours avec STOP & VALIDATE entre phases.
