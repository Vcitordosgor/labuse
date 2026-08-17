# AUDIT M99 — Phase 1 : les graphies du zonage (mesure, STOP avant fusion)

Mesuré le 2026-08-17 sur `parcel_zone_plu` (run servi q_v9_m81), règlements croisés via
`plu_reglement_extrait` (verbatim) et les YAML calibrés `config/plu_*.yaml`.
**Aucune fusion appliquée — ce document arme l'arbitrage de Vic, paire par paire.**

## Le verdict de la mesure, en quatre faits

**Fait 1 — coexistence : ZÉRO.** Sur les **32 groupes** de graphies ne différant que par la
casse (31 paires + 1 triple `UAA/UAa/Uaa`), il n'existe **aucune commune** où deux graphies
du même groupe coexistent. La casse est un fait strictement **inter-communal** : chaque
commune écrit sa zone d'une seule façon.

```sql
-- 0 partout : communes_coexistence = 0 pour les 32 groupes
SELECT lower(zone_lib) cle, left(idu,5) insee, count(DISTINCT zone_lib)
FROM parcel_zone_plu GROUP BY 1,2 HAVING count(DISTINCT zone_lib) > 1;   -- → 0 ligne
```

Conséquence de doctrine : la fusion par casse ne peut **pas** mélanger deux zones distinctes
d'une même commune. Et entre communes, le filtre actuel fusionne DÉJÀ les zones de même
graphie (le « UB » de 9 communes est déjà une seule entrée) — la fusion de casse ne change
pas la nature du filtre, elle en corrige l'angle mort.

**Fait 2 — le règlement écrit en MAJUSCULES, partout où il est extrait.** Sur les 59 zones
verbatim distinctes de `plu_reglement_extrait`, **0 en casse mixte**. Croisement
graphie GPU × graphie règlement sur les zones des 32 groupes (176 couples commune×zone) :

| verdict | n |
|---|---|
| règlement non extrait pour cette zone | 116 |
| CONCORDE (GPU majuscule = règlement) | 13 |
| DIVERGE (GPU casse mixte vs règlement MAJUSCULE) | 47 |

Les 47 divergences vont **toutes dans le même sens** : le règlement écrit `UA`/`UB`/`UC`…,
le GPU/AGORAH porte `Ua`/`Ub`/`Uc`. Aucun cas inverse, aucun règlement en minuscules. La
casse mixte est une graphie de transcription SIG, pas une écriture réglementaire.

Nuance à connaître : les **YAML calibrés** (`config/plu_le_port.yaml`, `plu_cilaos.yaml`,
`plu_bras_panon.yaml`…) écrivent leurs clés de zone en casse mixte — ils suivent la graphie
GPU, pas le règlement — et `resolve_zone` normalise déjà en minuscules
(`faisabilite/plu_rules.py:81`) : **le moteur de faisabilité est insensible à la casse
depuis toujours**. Seul le filtre de recherche est sensible.

**Fait 3 — l'ampleur.** 196 840 parcelles portent une zone appartenant à un groupe à double
graphie. La graphie **minoritaire** de chaque groupe totalise **80 777 parcelles** —
invisibles aujourd'hui à un filtre posé sur la graphie majoritaire (et réciproquement :
116 063 invisibles à un filtre posé sur la minoritaire). Les 4 plus gros groupes (`ub`,
`uc`, `ua`, `ud`) pèsent à eux seuls 166 706 parcelles.

**Fait 4 — les autres variantes : AUCUNE.** La normalisation au-delà de la casse (espaces,
tirets, accents, ponctuation — `regexp_replace('[^a-z0-9]')`) ne regroupe **rien de plus** :
419 graphies brutes → 386 après pliage de casse → **386** après normalisation complète.
Le cas `U1lec` vs `U1LEC` cité au mandat n'existe pas en base : une seule graphie (`U1lec`,
Saint-Paul) y figure. Écart de compte à acter : le mandat parle de « 198 zones distinctes » ;
la base en porte **419 brutes / 386 après casse** (le 198 ne correspond à aucun découpage
mesuré ici — probablement un compte antérieur ou un autre périmètre).

## L'arbitrage demandé, paire par paire

Preuve disponible pour chaque groupe (annexe A) : graphies, volumes, communes de chaque
graphie, coexistence (toujours 0), et — quand le règlement est extrait — sa graphie.

Lecture d'ensemble soumise à Vic : **aucune des 32 paires ne présente le motif qui
interdirait la fusion** (deux graphies dans une même commune = deux zones réglementaires
distinctes). Le règlement, source qui prime, écrit en majuscules partout où il est extrait ;
les groupes sans extrait (116 couples) n'ont pas de contre-preuve réglementaire, et leur
coexistence intra-commune est nulle aussi. La fusion par pliage de casse est donc défendable
pour les 32 groupes — mais c'est l'arbitrage de Vic, paire par paire, pas le mien.

Points à trancher explicitement :
1. **Fusion des 32 groupes** (recommandation de la mesure) ou liste restreinte ?
2. Les groupes **sans extrait de règlement** (ex. `uf`, `uav`, `udp`…) : fusionner sur la
   foi de la non-coexistence seule, ou attendre l'extraction de leur règlement ?
3. La **graphie d'affichage** du filtre fusionné : majuscule réglementaire (`UC`) ou
   graphie majoritaire en base ? (La fiche, elle, continue d'afficher la graphie de SA
   commune — non négociable, interdit du mandat.)

## Annexe A — les 32 groupes (volumes et communes par graphie, INSEE)

| clé | graphies (n parcelles, communes) |
|---|---|
| ub | Ub=29 425 (10 com : 97401,02,03,06,07,10,19,22,23,24) · UB=27 155 (9 com : 97404,05,08,09,13,14,18,20,21) |
| uc | UC=31 109 (8 com : 97404,05,09,13,14,18,20,21) · Uc=24 782 (8 com : 97401,02,06,07,19,22,23,24) |
| ua | UA=14 999 (8 com : 97404,08,09,13,14,18,20,21) · Ua=14 482 (11 com : 97401,02,03,06,07,10,11,19,22,23,24) |
| ud | UD=13 867 (6 com : 97404,05,09,13,14,18) · Ud=10 887 (7 com : 97401,02,07,11,16,19,22) |
| uf | Uf=10 963 (97416) · UF=178 (97405,13) |
| uav | Uav=4 552 (97422) · UAv=176 (97408,20) |
| ud1 | UD1=1 982 (97414,18) · Ud1=150 (97401) |
| ue | Ue=1 102 (9 com) · UE=790 (7 com) |
| aub | AUb=755 (5 com) · AUB=610 (97408,13) |
| ur | Ur=931 (97406) · UR=328 (97418) |
| us | Us=848 (97407,16) · US=277 (97409,14) |
| uca | UCA=842 (97413) · Uca=117 (97407) |
| uem | UEm=663 (97408,18) · Uem=200 (97407) |
| uba | Uba=795 (97402) · UBa=48 (97408) |
| uc1 | UC1=667 (97414,18,20) · Uc1=100 (97401) |
| ad | AD=726 (97413) · Ad=17 (97405) |
| auc | AUC=208 (97413) · AUc=180 (4 com) |
| udp | Udp=343 (97411) · UDP=20 (97413) |
| aua | AUA=190 (97413) · AUa=39 (3 com) |
| aue | AUE=145 (97405,13) · AUe=39 (4 com) |
| nsc | NSC=153 (97413) · Nsc=3 (97402) |
| uep | UEp=139 (97418) · Uep=12 (97416) |
| uaa | UAA=57 (97413) · UAa=50 (97408) · Uaa=39 (97423) |
| aus | AUS=124 (97413) · AUs=18 (3 com) |
| uea | UEa=108 (97405,18) · Uea=32 (97416) |
| aud | AUd=78 (97401) · AUD=40 (97413) |
| uac | Uac=91 (97411) · UAc=14 (97420) |
| ut | UT=68 (6 com) · Ut=9 (97410,16) |
| uat | Uat=68 (97411) · UAT=8 (97413) |
| aut | AUt=16 (3 com) · AUT=4 (3 com) |
| nt | Nt=12 (3 com) · NT=3 (97413) |
| auf | AUf=5 (97416) · AUF=2 (97405) |

Observation transverse : Saint-Leu (97413) écrit systématiquement en MAJUSCULES ; les
communes « AGORAH » (97401, 97402, 97406, 97407…) portent la casse mixte — la graphie suit
le canal d'ingestion de la commune, pas une sémantique de zone.

## Annexe B — familles (pour la Phase 3, aucune décision ici)

`zone_fam` mesuré : U=306 630 · A=73 946 · N=36 306 · AU=10 537 (identique au mandat).

---

## Arbitrage rendu (Vic, 17/08/2026) et exécution

**Décision : fusion des 32 groupes sans exception ; graphie d'affichage du filtre =
MAJUSCULE réglementaire ; la fiche garde la graphie officielle de sa commune.**

### Condition d'arbitrage n°2 — les 19 groupes fusionnés SANS verbatim de règlement

Fusionnés sur la seule preuve structurelle (coexistence intra-commune nulle), **à revérifier
si une extraction future de règlement les couvre** :

`ad · aua · aub · auc · aud · auf · nsc · nt · uaa · uac · uat · uav · uba · uc1 · uca ·
ud1 · udp · uea · uep`

(Les 13 autres — `aue aus aut ua ub uc ud ue uem uf ur us ut` — ont au moins un verbatim,
toujours en majuscules.)

### Point 4 — périmètre du défaut, confirmé surface par surface

| surface | comparateur | état AVANT M99 | preuve |
|---|---|---|---|
| Recherche `/filtre?zone_plu=` | `upper(zone_lib) = ANY(upper(entrée))` | DÉJÀ insensible — mais la normalisation vivait ad hoc DANS le filtre (interdit doctrine) | app.py:1050-1052 ; mesuré : Uc/UC/uc → 55 891 identiques |
| Facettes familles (`zonagePlu`) | `zone_fam` | insensible par nature | app.py:951 |
| Recherche IA (`nl_semantics`) | familles U/AU/A/N, regex `re.I` | insensible | nl_semantics.py:66-69 |
| Copilote `compter_parcelles` | délègue à `filtre()` | insensible (hérite) | copilote_v2/outils.py:48-64 |
| Carte | `zone_lib` en ÉTIQUETTE seule (text-field), aucun filtrage par zone | insensible par nature ; graphie officielle affichée = voulu | MapView.tsx:485-527 |
| 4 documents / faisabilité | `resolve_zone` → `normalize_key` (lower) | insensible depuis toujours | faisabilite/plu_rules.py:81 |
| au_statut / au_ouverture | `normalize_key` + jointures internes même graphie | insensible / cohérent | au_ouverture.py:88,153 |
| **Changement PLU (simulplu)** | `cr.detail LIKE '%« zone »%'` sur le verbatim cascade | **SENSIBLE — seul comparateur servi trouvé** ; risque réel faible (la liste `/simulplu/zones` sert la graphie brute que le match retrouve) | moteurs.py:70 → corrigé ILIKE (M99) |
| copilote/moteurs.py:235 | dict `.get(zone_lib)` sur les règles YAML | sensible en théorie, cohérent par construction (YAML suit la graphie GPU de SA commune) — et module SANS importeur (dormant) | mesure YAML/GPU + grep imports |

**Nuance de prémisse, dite en clair** : le faux négatif de l'énoncé (« filtrer Uc cache les
31 109 UC ») n'était **pas reproductible sur `/filtre`** — l'upper() ad hoc du filtre le
couvrait déjà. Le défaut réel : la normalisation vivait au mauvais endroit (dans le filtre),
le seul comparateur sensible était simulplu, et la saisie libre du front scindait l'offre en
419 graphies sans compte ni liste.

### Ce qui a été livré (Phases 2-3)

- **Phase 2** : colonne `zone_filtre = upper(zone_lib)` écrite AU POINT DE LECTURE — le
  builder `tiles.build_parcel_zone_plu` (natif) + migration idempotente
  `models.ensure_zone_filtre` (backfill sans rebuild spatial, index). Le filtre lit la
  colonne (app.py — plus d'upper() sur la colonne dans la requête). `zone_lib` d'origine
  **jamais écrasé** — la fiche, la carte et les documents affichent la graphie officielle.
  simulplu passe en ILIKE. 386 zones normalisées (419 graphies brutes).
- **Phase 3** : endpoint `/zonage/zones` (familles triées par volume réel, comptes calculés,
  portée île/communes) + sélecteur par famille dans le panneau Filtres (déroulante
  recherchable par famille, cocher la famille = toute la famille, portée dynamique dite en
  bandeau, zone à 0 dans la portée = absente de la liste — comportement explicite). La
  saisie libre est retirée.
