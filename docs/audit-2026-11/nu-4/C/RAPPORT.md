# MANDAT AUDIT-NU-4 — Lot C : 500 parcelles contre les sources officielles

**Registre.** Audit **lecture seule** joué le 2026-11-04. Branche `audit/nu4-c`, worktree
`~/Desktop/labuse-nu4c`, API locale `:9650` (venv `labuse/.venv`, `PYTHONPATH=src` du worktree),
run servi **`q_v20`**, base Mac `labuse` (433 229 parcelles vivantes). Aucune écriture base, aucun
correctif, aucun merge. **Prod non consultée** (la base Mac suffit : c'est elle qui sert la fiche).
Les sources officielles ont été interrogées en HTTP sortant (`curl`, certs système). Tout le code,
les sorties brutes et le cache des réponses officielles sont sous `docs/audit-2026-11/nu-4/C/`
(`scripts/`, `out/`, `out/cache/`). Le harnais est **rejouable et reprenable** (voir § dernier).

> La question du mandat : **ce que LABUSE affiche colle-t-il aux sources officielles en ligne ?**
> Réponse courte : **oui, massivement.** Sur 500 parcelles tirées au sort dans les 24 communes,
> la **contenance** est juste au m² partout (495/495 = 100 %), la **zone PLU** opposable n'est
> jamais fausse (containment GPU 438/438 = 100 %), **aucune famille d'aléa n'est inventée**
> (460/460), **aucune vente n'est fabriquée**. Les **13 divergences** relevées ne sont **pas des
> faits faux** : 8 sont de la **fraîcheur** (millésime DVF) ou de la **méthode** (zone dominante vs
> centroïde), et 5 sont **à décharge** (LABUSE est *plus complet* que la geo-API DVF de contrôle).

---

## Les chiffres

| Chiffre | Valeur |
|---|---:|
| **Parcelles tirées** | **500** (≈21/commune × 24, variété forcée) |
| Fiches LABUSE relevées (API réelle `/parcels/{idu}`) | **500 / 500** |
| Sources officielles interrogées | cadastre.gouv · GPU (zone + servitudes) · DVF Etalab · Géorisques · BAN |
| Réponses officielles mises en cache | **2 524** (500 cadastre · 500 GPU-zone · 500 GPU-SUP · 500 DVF · 24 Géorisques · 500 BAN) |
| **Faits confrontés (comparables)** | **1 749** = contenance 495 + zone 438 + vente 72 + aléas 460 + adresse 284 |
| **Écarts bruts** | **13** |
| **Écarts = fait faux (fabrication / calcul)** | **0** |
| dont MINEUR (fraîcheur / méthode) | 8 |
| dont à décharge (source de contrôle incomplète) | 5 |
| dont GRAVE | **0** |

**Verdict de synthèse.** Les **faits-socle confrontables à un référentiel public collent au
monde** : la contenance cadastrale est exacte à l'unité sur 495/495 parcelles et dans les 24
communes ; la zone PLU servie est toujours une zone réellement présente au point interrogé
(containment GPU 100 %) ; les familles d'aléas servies sont toujours un sous-ensemble des risques
déclarés de la commune (0 invention) ; aucune dernière vente n'est inventée. Les seules divergences
tiennent à **deux causes établies, ni l'une ni l'autre un mensonge de l'app** : (1) l'**instantané
DVF** de LABUSE (horizon `2025-12-31`, distribution DGFiP/Cerema) est plus ancien et attaché
différemment que la geo-API `app.dvf.etalab` → 4 « dernières ventes » en retard d'un millésime et 5
ventes que LABUSE possède mais que la geo-API officielle **ne géolocalise pas** ; (2) sur une
parcelle **à cheval sur deux zones**, LABUSE sert la **zone dominante en surface** (et liste
`zones_all`) alors que le GPU répond la zone du **centroïde** → 4 libellés différents, la zone GPU
étant à chaque fois dans `zones_all`. Les confrontations qu'aucune API ouverte ne permet (bâti,
SCOT, RNIC, zonage fin PPR) sont déclarées comme telles au § Limites.

---

## Le tirage — 500 parcelles, 24 communes, variété forcée

Tirage déterministe (ordre `md5(idu||"nu4c-v1")`), ≈21 par commune, **greedy** maximisant la
couverture d'axes de variété (PPR, copro, AU, RNU, vendue récente, grande/petite, A/N/U, bâti/nu),
puis coupe déterministe à 500 (`scripts/01_sample.py`, `out/sample500.json`). Répartition : 21/commune
pour 19 communes, 20 pour 5 (Saint-André, Sainte-Marie, Bras-Panon, Sainte-Rose, Les Trois-Bassins).
Profils représentés : bâties/nues, copro, les familles de zones U/A/N/AU, RNU, PPR, ventes récentes,
grandes (≥3000 m²) et petites (<200 m²).

---

## Méthode — « ce que LABUSE affiche » vs la source officielle

**Côté LABUSE (l'affiché, pas une relecture SQL).** Pour chaque parcelle on appelle le **point
d'entrée réel du front** `GET /parcels/{idu}?source=q_v20` (c'est `api.ts getFiche`) et on relève
les champs portés à l'écran : `contenance_m2`/`surface_terrain_m2`, la zone dominante
`reglement_plu.zones[].zone` (+ `zones_all`), `dvf_parcelle.derniere_mutation`, `adresse`,
`aleas.liste[].nature`, `le_bien.nb_batiments`, `coproprietes`, `scot` (`scripts/02_labuse.py`,
`out/labuse.json`, fiches brutes sous `out/cache/fiche/`).

**Côté source officielle (confrontation machine).** Un appel par parcelle, caché et rejouable
(`scripts/03_external.py`, `out/external500.json`, `out/cache/<source>/`) :

| Fait LABUSE | Source officielle | Requête | Verdict |
|---|---|---|---|
| contenance | **cadastre.gouv** | apicarto `/cadastre/parcelle` → `contenance` | égalité entière |
| zone PLU | **Géoportail de l'urbanisme** | apicarto `/gpu/zone-urba` (centroïde) → `libelle` | égalité + containment `zones_all` |
| dernière vente | **DVF Etalab** | `app.dvf.etalab /mutations3` filtré `id_parcelle` | date de la dernière mutation |
| adresse | **BAN** | `api-adresse /reverse` (centroïde) | cohérence de voie (indicatif) |
| aléas (familles) | **Géorisques** | `/api/v1/gaspar/risques` (commune) | containment (LABUSE ⊆ commune) |
| servitudes (SUP) | **GPU** | apicarto `/gpu/assiette-sup-s` | présence (descriptif, § Limites) |

Un **écart** = LABUSE ≠ source sur un fait **comparable** (les deux renseignés). Normalisation **de
forme seulement** (casse, espaces, arrondi entier) : 1567 ≠ 1568 **reste** un écart.

---

## Taux d'exactitude par fait

| Fait | Comparables | Exacts | **Taux** | Lecture |
|---|---:|---:|---:|---|
| **Contenance** (cadastre.gouv) | 495 | 495 | **100,00 %** | juste à l'unité, 24 communes |
| **Zone PLU** — dominante (GPU centroïde) | 438 | 434 | **99,09 %** | 4 écarts = parcelles à cheval |
| **Zone PLU** — containment (GPU ∈ `zones_all`) | 438 | 438 | **100,00 %** | LABUSE n'invente jamais une zone |
| **Aléas** — familles (Géorisques, containment) | 460 | 460 | **100,00 %** | 0 famille inventée |
| **Dernière vente** — date exacte (DVF) | 72 | 63 | **87,50 %** brut | 9 divergences, **0 fausse vente** (voir ci-dessous) |
| **Adresse** (BAN, indicatif *fuzzy*) | 284 | 284 | **100,00 %** | jamais incohérente avec la BAN |

**Couverture des sources** (pour lire les dénominateurs honnêtement) : contenance cadastre trouvée
496/500 ; zone GPU opposable au centroïde 438/500 (62 en RNU ou partition GPU non servie) ; DVF — 72
parcelles sur 500 ont au moins une vente (428 n'en ont **aucune** des deux côtés = concordance, non
comptée pour ne pas gonfler le taux) ; adresse servie par LABUSE 284/500 ; BAN 475/500 ; Géorisques
24/24 communes.

**La dernière vente, après enquête : 0 fausse vente.** Les 9 divergences se répartissent ainsi
(`scripts/05_validate.py`, `out/findings.json`) :

- **5 à décharge** — LABUSE affiche une vente **réelle** (id DGFiP p.ex. `2021-1673877`) que la
  geo-API `app.dvf.etalab` **ne renvoie pas** pour cette parcelle alors qu'elle sert d'autres
  parcelles de la même section. LABUSE est **plus complet** que la source de contrôle.
- **4 fraîcheur** — DVF live porte une mutation **plus récente** que l'instantané LABUSE (horizon
  `2025-12-31`) : BL0026 (vente 2026-02 de 2,255 M€ postérieure à l'horizon), AO0534 (2026-02),
  IE0152 (2026-02), AX0036 (2025-12-23, publiée dans une vague DVF postérieure à l'ingestion).

Preuve de la cause : pour une même vente, l'id de mutation **diffère** entre LABUSE (`2025-1270201`)
et etalab (`2025-1338297`) → **deux distributions DVF distinctes** (DGFiP/Cerema vs app Etalab),
de millésimes et d'attachement parcellaire différents. Aucune de ces 9 lignes n'est une erreur de
calcul ou une invention de LABUSE.

---

## Taux d'exactitude par commune (faits confrontables)

`out/accuracy_by_commune.json`. Contenance = **100 % dans les 24 communes**. Zone = 100 % sauf les 4
parcelles à cheval (Entre-Deux, Petite-Île, Saint-Joseph, Sainte-Marie). « Vente » compte les
divergences adjugées ci-dessus comme non-exactes (donc sous-estime : ce sont de la fraîcheur, pas
des erreurs).

| Commune | Contenance | Zone | Vente | | Commune | Contenance | Zone | Vente |
|---|---:|---:|---:|---|---|---:|---:|---:|
| Bras-Panon | 19/19 | 20/20 | 1/2 | | Saint-Joseph | 21/21 | 20/21 | 3/3 |
| Cilaos | 20/20 | 21/21 | 3/3 | | Saint-Leu | 21/21 | — | 1/1 |
| Entre-Deux | 21/21 | 20/21 | 4/4 | | Saint-Louis | 21/21 | 21/21 | 4/5 |
| L'Étang-Salé | 21/21 | 21/21 | 3/3 | | Saint-Paul | 21/21 | 21/21 | 3/3 |
| La Plaine-des-Palmistes | 20/20 | 21/21 | 1/2 | | Saint-Philippe | 20/20 | — | 2/2 |
| La Possession | 21/21 | 21/21 | 4/4 | | Saint-Pierre | 21/21 | 21/21 | 2/3 |
| Le Port | 21/21 | 21/21 | 2/3 | | Sainte-Marie | 20/20 | 19/20 | 2/2 |
| Le Tampon | 21/21 | 21/21 | 4/4 | | Sainte-Rose | 20/20 | 20/20 | 2/3 |
| Les Avirons | 21/21 | 21/21 | 4/4 | | Sainte-Suzanne | 21/21 | 21/21 | 2/2 |
| Les Trois-Bassins | 20/20 | 21/21 | 4/4 | | Salazie | 21/21 | 21/21 | 3/3 |
| Petite-Île | 21/21 | 20/21 | 2/3 | | Saint-André | 20/20 | — | 1/2 |
| Saint-Benoît | 21/21 | 21/21 | 4/4 | | Saint-Denis | 21/21 | 21/21 | 2/3 |

« — » = GPU n'a pas servi de zone opposable au centroïde des parcelles tirées dans cette commune
(partition GPU non couverte) : ce n'est pas un écart, c'est l'absence de la **source** de contrôle.

---

## Les écarts classés par gravité (`out/ecarts_valides.csv`)

**0 GRAVE.** 8 MINEUR + 5 à décharge. Chaque ligne porte les deux valeurs, la source et la cause
établie.

### MINEUR — fraîcheur DVF (4) : la « dernière vente » servie est en retard d'un millésime

| Parcelle | Commune | LABUSE | DVF officiel | Cause |
|---|---|---|---|---|
| 97411000BL0026 | Saint-Denis | *(aucune)* | 2026-02-11 (2,255 M€) | vente **postérieure à l'horizon** DVF de LABUSE (2025-12-31) |
| 97409000AO0534 | Saint-André | 2024-12-26 | 2026-02-19 | mutation 2026 non encore ingérée |
| 97416000IE0152 | Saint-Pierre | 2025-09-22 | 2026-02-20 | mutation 2026 non encore ingérée |
| 97405000AX0036 | Petite-Île | 2025-08-02 | 2025-12-23 | vente fin-2025 publiée après l'instantané LABUSE |

> Effet client : sur ces 4 parcelles, la tuile « dernière vente » n'est pas fausse mais **pas la
> plus récente**. Amélioration : rapprocher l'horizon d'ingestion DVF de la dernière publication
> Etalab (le décalage observé est de l'ordre d'un à deux trimestres).

### MINEUR — méthode zone (4) : zone dominante (LABUSE) vs centroïde (GPU)

| Parcelle | Commune | LABUSE (dominante) | GPU (centroïde) | `zones_all` | GPU ∈ `zones_all` |
|---|---|---|---|---|:--:|
| 97403000AL0187 | Entre-Deux | Nr (58,6 %) | A | [Nr, A] | ✅ |
| 97405000AI1075 | Petite-Île | A (60,9 %) | N | [A, N] | ✅ |
| 97412000AR0304 | Saint-Joseph | A (82,4 %) | N | [A, N] | ✅ |
| 97418000BL0173 | Sainte-Marie | A (55,1 %) | UD1 | [A, N, UD1] | ✅ |

> Ce n'est pas une erreur : LABUSE sert la zone **majoritaire en surface** et **liste toutes les
> zones** de la parcelle ; le GPU, interrogé en un point, tombe parfois dans une sous-zone
> minoritaire. Dans les 4 cas, la zone du GPU **est** dans `zones_all`. Amélioration : signaler plus
> fortement le caractère « à cheval » quand la part dominante est faible (ex. 55 %).

### À DÉCHARGE — la geo-API DVF de contrôle est incomplète (5)

97402000AI0640 (Bras-Panon, 2021-03-30) · 97406000AM0852 (La Plaine, 2021-02-03) · 97407000AO1199
(Le Port, 2021-02-24) · 97414000DS0385 (Saint-Louis, 2021-06-21) · 97419000AP0408 (Sainte-Rose,
2021-05-24). Dans les 5 cas LABUSE porte une mutation DGFiP réelle que `app.dvf.etalab` ne sert pas
pour la parcelle. **LABUSE a raison.**

---

## Les limites de la confrontation (ce qui n'a PAS pu être confronté, et pourquoi)

Honnêteté de périmètre : certains faits du mandat **n'ont pas de référentiel tiers interrogeable par
parcelle** via API ouverte. Ils sont déclarés ici, non comptés dans les taux.

- **Bâti (cadastre).** L'endpoint `apicarto/cadastre/batiment` **n'existe pas** (404). La source
  autoritative du bâti est **BD TOPO® / CoSIA** — que LABUSE utilise déjà (`le_bien.source_bati`) ;
  il n'existe pas de tiers indépendant à opposer. Non confronté (311/500 parcelles portent un
  `nb_batiments`).
- **SCOT.** `apicarto/gpu/scot` répond **404** sur le périmètre réunionnais. LABUSE sert un SCOT sur
  377/500 depuis sa propre ingestion ; non confrontable via GPU.
- **RNIC (copropriété).** Pas d'API publique **par parcelle** (le registre est clé par n°
  d'immatriculation / adresse, sans IDU). Non confronté (24/500 copro côté LABUSE) — limite assumée,
  à traiter par un rapprochement adresse hors ligne dans une campagne dédiée.
- **PPR rouge/bleue au niveau parcelle.** Géorisques `gaspar` est **communal** ; le zonage fin
  rouge/bleu vient de la **DEAL** (ingéré par LABUSE en `spatial_layers kind='ppr'`), sans API tierce
  par parcelle. Confronté au niveau **famille** (containment 100 %), **pas** au niveau du trait
  rouge/bleu. (La fiche distingue bien « zone bleue / zone rouge » — ex. 97411000BZ1065 « zone bleue
  sur 100 % » — mais sans source tierce opposable.)
- **Servitudes (SUP).** Le GPU `assiette-sup-s` répond (SUP présente pour 180/500), mais la fiche
  parcelle n'expose pas une **liste SUP propre et comparable** → confrontation **descriptive**, pas
  de taux.
- **Couverture des sources de contrôle elles-mêmes** : GPU zone muet pour 62/500 (RNU / partition
  non servie), cadastre apicarto muet pour 4/500 (97424000AE2541, 97406000AM0976, 97423000AE1116,
  97417000AL0132 — vraisemblablement parcelles cadastrales récentes), geo-API DVF Etalab incomplète
  (cf. les 5 à-décharge). **La source officielle n'est pas toujours la vérité la plus fraîche ni la
  plus complète.**

---

## Ce qui est sain (à décharge)

- **Contenance : 100 % (495/495), dans les 24 communes.** Le fait le plus sur-exposé du produit
  (7 surfaces d'après `FAITS.md`) est juste à l'unité partout.
- **Zone opposable : containment 100 % (438/438)** — LABUSE n'affiche jamais une zone qui ne soit
  pas réellement présente au point ; il ajoute l'information « parcelle à cheval » via `zones_all`.
- **Aléas : 0 famille inventée (460/460)** — jamais un risque que la commune ne déclare pas.
- **Dernière vente : 0 fabrication** ; LABUSE est même **plus complet** que la geo-API DVF officielle
  sur 5 parcelles.
- **Adresse : jamais incohérente** avec la BAN sur les 284 adresses servies.
- La seule dette réelle est de **fraîcheur** (instantané DVF en retard d'un à deux trimestres sur la
  publication Etalab), pas de véracité.

### Note de fiabilité (non bloquante)

Pendant le relevé des 500 fiches **en parallèle (8 requêtes simultanées)**, 5 fiches ont d'abord
renvoyé un 500 transitoire (`statement timeout` sur la vue spatiale `v_parcel_dvf_last`). **En appel
isolé, les 5 répondent 200.** Ce n'est donc pas une fiche en panne, mais une **latence de la vue DVF
sous forte concurrence** — à surveiller côté charge (cf. dette perf `fix/nu3-3`).

---

## Le harnais — rejouable et reprenable

`docs/audit-2026-11/nu-4/C/scripts/` (lire dans l'ordre) :

1. `01_sample.py` → `out/sample500.json` (tirage déterministe, seed `nu4c-v1`).
2. `02_labuse.py` → `out/labuse.json` (relevé de l'affiché via l'API réelle ; cache `out/cache/fiche/`).
3. `03_external.py` → `out/external500.json` (sources officielles ; **cache par source** sous
   `out/cache/<source>/` : **relancer ne refait que les trous**).
4. `04_compare.py` → `out/ecarts.csv`, `out/accuracy_by_fait.json`, `out/accuracy_by_commune.json`,
   `out/stats.json` (confrontation brute).
5. `05_validate.py` → `out/findings.json`, `out/ecarts_valides.csv` (causes établies, gravité revue).

Rejeu complet (API `:9650` démarrée, venv `labuse/.venv`, `PYTHONPATH=src`) :
```
python scripts/01_sample.py && python scripts/02_labuse.py && \
python scripts/03_external.py && python scripts/04_compare.py && python scripts/05_validate.py
```
Déterministe (même tirage), idempotent (cache), seul `03` dépend du réseau sortant.

---

## Verdict en une phrase

**Sur 500 parcelles des 24 communes, LABUSE n'affiche aucun fait-socle faux face aux sources
officielles** — contenance 100 %, zone opposable 100 % en containment, 0 aléa inventé, 0 vente
fabriquée ; **les 13 divergences sont de la fraîcheur DVF (4), de la méthode zone-dominante (4) ou
une geo-API de contrôle moins complète que LABUSE (5)** — jamais un mensonge de l'application.
