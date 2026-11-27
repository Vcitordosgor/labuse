# OUTIL-ASSEMBLAGE-FIX-1 — compte-rendu

> Worktree `~/Desktop/labuse-assemblage-fix`, branche `fix/outil-assemblage-1` (depuis `origin/main`).
> Périmètre = la **liste fermée (7 points)** du contre-audit `05-ASSEMBLAGE-ASTRA.md`.
> Base locale **partagée** `labuse` en lecture seule (requêtes légères uniquement).
>
> **Captures** dans `~/Desktop/outil-assemblage-fix-1/` (app servie ports 7560/10360, arrêtée en fin) :
> `01-CV-trio-bilan-reconcilie.png` (LOT 1 bords mesurés + LOT 3 charge +178 k€ + LOT 4 marché zone AU3c /
> propriétaires / maîtrise) · `02-DH-trio-par-zone.png` (LOT 2 table par zone U2b/U2h = 32 174 m², reculs
> voie/limite, retranchements hors-zone 193 / rouge 458, existant partiel 2/3) · `03-contact-ponctuel-pas-un-seul-tenant.png`
> (LOT 1 « reliées — pas d'un seul tenant » + caveat). Comparer/DH0098 : vérifié par rejeu (LOT 4).

---

## LOT 0 — lecture seule (rendu AVANT toute écriture de code)

Trois questions touchant du **code partagé** avec des écrans/documents déjà validés. Objectif :
savoir ce qu'on casse avant de corriger.

### a. Mixité sociale — `faisabilite/bilan.py`

**Le défaut, précisément.** La clause (`_clause_mixite`, `bilan.py:598`) se déclenche sur
`eco["sdp_max_m2"]`, posé en `bilan.py:543` / `:581` à `fourchette["surface_plancher_m2"]`.
Or `surface_plancher_m2` (`engine.py:1128` = `round(sdp)`) est la **SDP du gabarit** (emprise ×
niveaux), tandis que le CA, lui, est pondéré sur `surf = shab_vendable_m2` (`engine.py:1134` =
`sol_central × logt_moyen`), c.-à-d. le **programme réellement retenu** (après plafond de densité et
stationnement au sol). On déclenche donc sur une capacité théorique brute, puis on valorise un
programme plus petit. Témoin du relecteur : trio CV → déclenché sur **3 060 m²** de gabarit alors que
le programme chiffré vaut ~**1 583 m²** de plancher.

**Qui passe par ce code.** Le cœur `compute_bilan` (`bilan.py:635`, qui contient la clause) est
atteint par **tout le monde** :

| Écran / document | Chemin | Fichier:ligne |
|---|---|---|
| Fiche parcelle | `compute_bilan_servi` | `api/modules.py:2093` |
| Comparer | `compute_bilan_servi` (recalc) + payload fiche | `api/modules.py:2866` |
| IA / « ce bilan » | `compute_bilan_servi` | `api/modules.py:2966` |
| Classement (scoreur) | `compute_bilan_servi` | `api/scoreur.py:144`, `:208` |
| Calculette (recalcul instantané) | `compute_bilan` direct | `bilan.py:1021` |
| **Assemblage** | `compute_bilan_servi` sur la zone dominante de l'union | `assemblage.py:245` |
| Bilan PDF / Excel, Argumentaire, Rapport | rendent le payload fiche (bilan ci-dessus) | `exports/*` |

→ **Ce n'est pas un défaut propre à l'Assemblage** : il est dans le cœur partagé.

**Sur une parcelle seule, même défaut ?** **Oui, structurellement identique** : la fiche pose
`sdp_max_m2 = surface_plancher_m2` (gabarit) et pondère le CA sur `shab_vendable_m2`. Le
déclenchement d'une parcelle seule utilise donc la même grandeur théorique que l'union. La seule
raison pour laquelle on le voit surtout sur l'Assemblage : une parcelle isolée atteint rarement le
seuil SDP (ex. CV1506 seule, terrain 1 533 m², gabarit < 1 500), alors que l'**union** le franchit.

**Sens de la correction (important pour « ne rien casser »).** Comme `shab_vendable ≤ shab` (scénario
retenu ≤ gabarit), le programme chiffré est **toujours ≤** la capacité théorique. Déclencher sur le
programme ne peut donc que **retirer** des déclenchements abusifs, jamais en ajouter : aucune fiche
validée ne deviendra *plus* pessimiste ; certaines deviendront *moins* négatives (CA relevé). La
correction va dans le sens prudent.

**Combien de parcelles de l'île changeraient de bilan ?** **Non mesurable depuis les données
matérialisées, et non mesurable sans faire tourner le moteur sur l'île (requête lourde interdite sur
la base partagée).** Raisons vérifiées :

- `parcel_residuel.sdp_max_m2` (la grandeur de déclenchement) est **NULL** sur toute l'île — seul
  `sdp_residuelle_m2` (reconstruction/conservé) est persisté. Le gabarit n'existe qu'au calcul live.
- `shab_vendable_m2` (le programme chiffré) **n'est persisté nulle part**.

Donc le nombre exact exige un passage moteur par parcelle. **Bornage léger** obtenu à la place
(communes à mixité = Saint-Denis / Saint-Paul / Saint-Pierre, seuils 1 500 m² SDP · 20 logts ·
6 000 m² terrain, 30 % LLS, prix LLS 2 900 €/m²) :

| Commune | Terrain > 6 000 m² (déclenché par le critère TERRAIN, inchangé par la correction) | Terrain 1 200–6 000 m² (candidats au critère SDP) | Constructibles |
|---|---:|---:|---:|
| Saint-Denis | 865 | 4 164 | 9 433 |
| Saint-Paul | 828 | 4 686 | 3 441 |
| Saint-Pierre | 357 | 2 799 | 9 450 |

Le critère **terrain > 6 000 m²** (≈ 2 050 parcelles) déclenche indépendamment du programme : la
correction ne les touche pas. L'effet de la correction se concentre sur les parcelles/unions dont le
*gabarit* ≥ 1 500 m² mais dont le *programme chiffré* < 1 500 m² — sous-ensemble des candidats
ci-dessus, non chiffrable sans le moteur.

**Proposition (LOT 3) pour ne rien casser.**
1. Déclencher le critère SDP sur **`shab_vendable / coef_rendement`** (programme chiffré), pas sur
   `surface_plancher_m2`. Correction du cœur partagé, dans le sens prudent (cf. ci-dessus).
2. Mesurer l'impact **exactement** par un passage moteur **sur une base dédiée** (modèle
   `labuse_scanfix`), **jamais** sur `labuse` partagée — et en faire un **test de valeur** (le trio
   CV et la paire BZ chiffrés).
3. Le régime Saint-Paul (seuils 1 500 / 1 800 m², cas ZAC, règlement pages 106-107) est aujourd'hui
   réduit à un **seuil plat 1 500** dans le YAML (`plu_zonage.yaml:1680`) et un **30 % forfaitaire** :
   c'est la vraie question réglementaire du LOT 3, distincte de la grandeur de déclenchement.
   ⚠️ **Décision requise** (cf. fin) : corriger le régime touche la clause *de toutes les communes à
   mixité*, pas seulement l'Assemblage.

### b. Parcelle à cheval sur deux zones — moteur d'une parcelle seule

**Même comportement que l'Assemblage : zone DOMINANTE par surface appliquée à toute la parcelle.**
Vérifié : `faisabilite/db.py:77` et `:303-307` → `zone_servie.zone_dominante` ; le SQL
(`zone_servie.py:66-73`) prend la zone de part de surface maximale (`ORDER BY pct DESC`). Le moteur
ne **clippe** que l'**emprise** à la portion U/AU (`ST_Intersection`, `db.py:11`, `:49`), mais les
**règles** (emprise %, hauteur, reculs) sont celles de la **seule zone dominante**, étendues à toute
l'assiette constructible — exactement le reproche fait à l'Assemblage (témoin Uj/Uh BZ0246+BZ1488).

Infrastructure déjà présente mais **inexploitée pour la capacité** : `ZoneServie` porte un drapeau
`a_cheval` (aucune zone ≥ 90 %) et une liste `parts = [{zone, fam, pct}]`. Comparer l'affiche déjà en
transparence (`app.py:9796`, « A 70 % · N 28 % ») ; la capacité, elle, ne l'utilise pas.

→ **Conséquence pour le LOT 2** : le calcul « par zone » n'est pas une spécificité Assemblage, c'est
une correction du moteur partagé. Faire du par-zone **uniquement dans l'Assemblage** le fait
**diverger** de toutes les fiches mono-parcelle validées (qui resteront en zone dominante).
⚠️ **Décision requise** (cf. fin).

### c. Comparer omet DH0098 sans le dire — `app.py:9714`

**Confirmé, mécanisme localisé.** `app.py:9887` :

```python
ignores = [i for i in ids if i not in _rendus and pid_of.get(i) is None]
```

Un IDU **résolu en `pid`** (donc trouvé) mais qui **échoue au build** de sa fiche
(`except HTTPException: continue` `app.py:9782-9783`, ou exception du préchargement parallèle
`:9764`) est :
- absent de `parcels` (jamais `out.append`),
- **exclu de `ignores`** car `pid_of.get(i) is not None`.

Il disparaît des deux côtés → « une seule colonne et une liste `ignores` vide », exactement le
constat du relecteur. DH0098 **existe** (Saint-Paul, 7 717 m², fiche/Bilan = 1 491 m²) donc il suit
le chemin « trouvé-puis-échoué », pas « introuvable ».

**Proposition (LOT 7, risque faible).** Lister dans la réponse **tout** identifiant demandé non
rendu, en distinguant deux causes : `introuvable` (`pid is None`) vs `echec_calcul` (trouvé mais
build KO). Techniquement : retirer la condition `and pid_of.get(i) is None` et classer par cause.
À couvrir par le témoin DH0098 + EP0971 et la sélection à 3 dont un introuvable.

---

### Décisions requises avant d'écrire (LOT 2 & LOT 3)

1. **Capacité par zone (LOT 2)** — l'appliquer **à l'Assemblage seul** (il diverge alors des fiches
   mono-parcelle validées, mais c'est là que les unions multizones et l'enjeu « opération d'un seul
   tenant » sont concentrés) **ou** au **moteur partagé** (corrige aussi la fiche mono à-cheval, mais
   touche des milliers de résultats validés) ?
   *Recommandation :* helper par-zone **partagé**, **branché d'abord dans l'Assemblage** (périmètre du
   mandat) + transparence `a_cheval`/`parts` affichée ; la bascule de la **fiche mono** par-zone =
   étape séparée **quantifiée** (mandat de suivi), pour ne pas muter en silence les fiches validées.

2. **Régime de mixité (LOT 3)** — se limiter à **corriger la grandeur de déclenchement** (programme
   chiffré, cœur partagé, sens prudent) **ou** aussi **réécrire le régime Saint-Paul** (1 500/1 800,
   ZAC) dans le YAML, ce qui change la clause de **toutes** les communes à mixité ?
   *Recommandation :* les deux, mais mesurés sur base dédiée et couverts par des tests de valeur ;
   réécriture du régime = changement de config commune, à valider explicitement.

**Décisions validées (24/11).** LOT 2 : helper par-zone partagé, branché d'abord dans l'Assemblage ;
fiche mono en suivi. LOT 3 : grandeur + régime, avec trois conditions — (1) régime Saint-Paul écrit
pour SP seul, toute autre commune à mixité inchangée sauf citation de SON règlement (sinon « non
vérifiée ») ; (2) **ARRÊT avant commit LOT 3** avec tableau avant/après par commune (clause, nb
parcelles changées, écart médian + maximal €) + trio CV + paire BZ ; (3) mesures sur **base dédiée
uniquement**, jamais `labuse` partagée.

---

## LOT 1 — contiguïté (bloquant 1) ✅

**Défaut.** Le graphe d'adjacence (`moteurs.py`, ancien) reliait toute paire à ≤ 0,5 m par `ST_DWithin`,
sans distinguer un bord partagé d'un contact ponctuel ou d'un petit vide → un contact ponctuel et un
vide de 32 cm recevaient le même « contiguës » qu'une mitoyenneté vérifiée.

**Correction.** `assemblage.classer_lien(dist, bord)` rend trois verdicts (mesure PostGIS :
`ST_Distance` + longueur de la part LIGNE de `ST_Intersection`) :

| Verdict | Condition | Sens |
|---|---|---|
| `bord` | bord commun ≥ `SEUIL_BORD_M` (0,5 m) | **seule** vraie mitoyenneté → « contiguës », d'un seul tenant (porte `longueur_bord_m`) |
| `point` | se touchent (dist ≤ 0,01 m) mais bord ~0 | contact par un point — reliée, PAS d'un seul tenant |
| `vide` | 0 < dist ≤ `ADJ_BUFFER_M` (0,5 m) | petit vide cadastral (porte `vide_m`) — reliée, PAS d'un seul tenant |

`verdicts_contiguite` (partagée écran + `/assemblage/study`) construit deux graphes : **bords seuls**
→ `tenant_unique`/`contigu` (strict) ; **tout lien** → `relie` (gate du chiffrage). `lien_faible =
relie ∧ ¬tenant_unique` déclenche `tenant_avertissement` (« Assiette NON d'un seul tenant — … Le
chiffrage fusionne les polygones réels sans combler ce vide »). Au-delà de 0,5 m → aucun lien →
isolée → « pas d'assemblage possible » (rue/chemin/ravine du relecteur, 0,68–43 m). L'écran dit
chaque lien par son nom et sa mesure, et n'annonce « contiguës » que pour `tenant_unique`.

**Contrôle (paires du relecteur, mesure rejouée sur `labuse`, lecture seule) :**

| Paire | dist (m) | bord (m) | Verdict | Relecteur |
|---|---:|---:|---|---|
| BZ0824 / BZ0381 | 0,000 | 26,38 | **bord** | bord réel ✓ |
| DH0076 / DH0120 | 0,000 | 8,22 | **bord** | bord réel ✓ |
| CV0085 / CV0876 | 0,000 | 0,00 | **point** | contact ponctuel ✓ |
| CV0157 / CV0095 | 0,000 | 0,00 | **point** | contact ponctuel ✓ |
| CV0107 / CV1287 | 0,000 | 0,00 | **point** | contact ponctuel ✓ |
| CV0186 / CW0182 | 0,315 | 0,00 | **vide** (0,32 m) | petit vide ✓ |

Requête rejouable (mesure d'un lien) :
```sql
SELECT ST_Distance(a.geom_2975,b.geom_2975) dist,
       ST_Length(ST_CollectionExtract(ST_Intersection(a.geom_2975,b.geom_2975),2)) bord
FROM parcels a JOIN parcels b ON a.idu='97415000CV0085' AND b.idu='97415000CV0876';
```

**Tests (valeur, nouveaux).** `tests/test_assemblage.py` : `classer_lien` paramétré sur les 21 cas du
relecteur (3 bords 10,51/42,73 + réels, 3 contacts ponctuels, 3 petits vides 0,315–0,322) ; 4 tests
d'endpoint sur géométries synthétiques métriques (bord 30 m → contiguës ; coin commun → point,
reliée non-tenant + avertissement ; vide 0,32 m → vide ; vide 0,69 m > tolérance → isolée). Front
`Assemblage.test.tsx` : cas lien faible (point) → « pas d'un seul tenant » + liens mesurés + caveat +
bilan présent (réservé, pas bloqué). **17 back + 10 front passent.**

---

## LOT 2 — assiette, reculs et capacité par zone (bloquant 2) ✅

**Défaut.** La capacité de l'union prenait la zone DOMINANTE et appliquait SES règles (emprise, hauteur,
recul) à TOUTE l'assiette ; la « surface constructible » était une proportion après recul, non une
intersection directe.

**Correction (`assemblage._capacite_union`, réécrit).** Calcul **zone par zone** : pour chaque zone U/AU
de l'union, on insète l'union de **son** recul (contour extérieur seulement — `ST_Buffer` sur l'union ne
touche pas la limite interne entre zones, donc « sans recréer de recul entre zones »), on clippe U/AU, on
intersecte **sa** zone, on retranche les grèves, puis `estimate_capacity` avec **ses** règles → SDP de la
portion ; on **additionne**. La fourchette agrégée (SDP, surface vendable, logements — chaque zone ayant
subi SON plafond) nourrit **une** charge foncière. `surface_constructible_m2` = intersection **directe**
de l'union avec U/AU. Le recul séparatif est appliqué au contour, le recul sur voie « s'ajoute sur la
façade sur rue » (bord non identifiable au cadastre) — **par zone**, comme la fiche. Les contraintes
retranchées (hors zone, zone rouge, emplacement réservé, EBC) sont servies **en m²** et affichées.

**Contrôle (rejoué sur `labuse`, lecture seule, via `_capacite_union`) — reproduction à l'euro :**

| Assemblage | Zones | SDP servie (avant) | **SDP par zone (après)** | Attendu ASTRA |
|---|---|---:|---:|---:|
| DH0076+DH0119+DH0120 | U2b (R+5) · U2h (R+3) | 34 110 | **32 174** | 32 174 ✓ |
| BZ0088+BZ0550 | Um (R+2) · Uj (R+3) | 1 074 | **1 460** | 1 460 ✓ |
| BZ0246+BZ1488 | Uj (R+3) · Uh (R+1) | 1 477 | **1 007** | 1 007 ✓ |
| CV0724+CV1506+CV1507 | AU3c (mono) | 3 060 | **3 060** | inchangé ✓ |
| BZ0824+BZ0381 | Uh (mono) | 159 | **159** | inchangé ✓ |

Décomposition DH (valeurs SERVIES par l'endpoint — `figures_cr.py`) : U2b 30 673 m² (emprise **17 544**,
R+5) + U2h 1 501 m² (emprise 1 112, R+3) = **32 174**. `surface_constructible` DH **servie = 21 638 m²**
(part constructible rapportée à la contenance cumulée ; l'intersection directe du dessin ∩ U/AU vaut
~21 516 m², mesure ASTRA — l'écart ~122 m² tient au référentiel contenance vs dessin, non à un recul).
[CORRIGÉ FIX-2 LOT 5 — FIX-1 avait noté par erreur 21 516 / 17 897, chiffres d'un diagnostic à recul
unique superseded ; les valeurs ci-dessus sortent de `figures_cr.py`, sortie brute au rapport FIX-2.] Contraintes retranchées rejouées : DH0191+DH0098 **zone rouge 935 m²** (= ASTRA 935) ;
EP0971+EP0762 **emplacement réservé 2 386 m²** (= ASTRA 2 386), SDP **1 404** (= ASTRA 1 404). Les
assemblages mono-zone sont **inchangés** (non-régression) ; un assemblage multizone sans contrôle chiffré
du relecteur (DH0191+DH0098, U2h/U2d) passe correctement de 2 450 (dominante) à 881 (par zone).

**Écran.** Tableau « Capacité par zone » (code, emprise, niveaux, recul limites/voie, SDP) dès que
l'assiette est à cheval sur ≥ 2 zones constructibles ; bloc « Contraintes sur l'assiette » (hors zone,
zone rouge, ER, EBC en m²).

**Tests (valeur, nouveaux).** `test_capacite_union_par_zone_valeurs_astra` (5 témoins, à l'euro),
`test_surface_constructible_est_intersection_directe_uau` (DH 21 516) — lus sur la base de l'île en
lecture seule, skippés hors île (CI). Front : table par zone + retranchements. **23 back + 11 front.**

---

## LOT 3 — bilan / mixité (bloquant 3) — code ✅, MESURE EN ATTENTE (ARRÊT)

**Défaut.** La clause de mixité se déclenchait sur la capacité THÉORIQUE (gabarit `surface_plancher_m2`)
et appliquait un **régime plat** (30 % LLS @ 2 900 €/m²), sans montrer les prix ni le programme
déclencheur ; le trio CV sortait à −349 965 € sans explication.

**Correction (cœur partagé `bilan._clause_mixite` + `compute_bilan`, régime gaté sur la commune).**
Décisions du 24/11 respectées :
- **Déclenchement sur le PROGRAMME chiffré** (`sdp_programme_m2` = surface vendable ÷ rendement), plus
  le gabarit. Le compte de logements du scénario silo optimiste ne déclenche plus à lui seul.
- **Régime à bandes Saint-Paul SEULEMENT** (nouveau seuil `mixite_sdp_seuil_haut_m2: 1800`, cité
  « Art. 2 règlement PLU Saint-Paul, pp. 106-107 ») : programme ≥ 1 800 → plein régime (30 % LLS
  pondéré) ; 1 500 ≤ programme < 1 800 → **bande intermédiaire** (accession sociale, quota au nombre de
  logements, **non chiffré** faute de calibrage → CA au prix marché, réserve affichée) ; < 1 500 → non
  déclenchée. Critère terrain > 6 000 m² conservé (réglementaire, indépendant du programme).
- **Autres communes à mixité (Saint-Denis, Saint-Pierre) : INCHANGÉES** (pas de seuil haut → clause
  historique sur le gabarit), **listées « non vérifiée »** faute de citation de LEUR règlement (condition
  du 24/11). Vérifié : Saint-Denis byte-identique.
- **Prix affichés** : plein régime → « prix libre X · prix aidé Y · part aidée Z % · pondéré W » ; bande
  intermédiaire → réserve explicite.

**Réconciliation (mesurée via `_capacite_union`, lecture seule) :**

| Assemblage | Programme chiffré | Avant | **Après** | Lecture |
|---|---:|---:|---:|---|
| Trio CV (Saint-Paul) | ~1 583 m² (bande 1500–1800) | −349 965 € | **+178 261 €** | = +178 261 € du relecteur (valorisation plein prix) ; cohérent avec la somme des fiches (+157 415 €) |
| Paire BZ (Saint-Denis) | — | −26 019 € | **−26 019 €** | hors régime à bandes → inchangé (le relecteur : « sans effet de seuil ») |

Le trio CV n'est plus pondéré au plein régime (son programme chiffré ~1 583 m² tombe dans la bande
intermédiaire) : le −349 965 € était l'application du régime ≥ 1 800 à un programme qui n'y est pas.

**Tests (valeur, nouveaux).** `test_clause_mixite_regime_a_bandes_saint_paul` (plein/intermédiaire/non),
`test_clause_mixite_autres_communes_inchangee` (Saint-Denis sur gabarit), `test_bilan_union_mixite_reconcilie`
(CV +178 261, BZ −26 019). Golden-standard + faisabilité + mixité PLU existants : **verts** (42 + 7).

### Mesure île avant/après (condition du 24/11 — passe LECTURE SEULE sur `labuse`, approuvée)

`labuse` = 38 Go + 15 connexions → clone impossible ; `labuse_scanfix` sans les tables requises. Décision
du 24/11 : **une** passe **LECTURE SEULE** throttlée sur `labuse`, avec preuve d'enforcement.

**Preuve read-only** (avant la passe) : `SET default_transaction_read_only = on` → `CREATE TABLE` et
`INSERT` refusés (« cannot execute … in a read-only transaction »). Aucune table temporaire. Une seule
connexion. Contention mesurée pendant la passe : `wait_event_type='Lock'` = **0** (aucune autre session
ralentie). Méthode : pour chaque parcelle, `parcel_faisabilite` une fois, puis `compute_bilan_servi`
deux fois — régime NOUVEAU vs régime HISTORIQUE (seuil haut forcé à 0) — comparaison de la charge.

**Tableau avant/après — île entière, commune par commune** (charge foncière centrale, régime NOUVEAU
vs HISTORIQUE ; Δ = NEW − OLD, toujours **positif** = charge moins négative, sens prudent) :

| Commune | Testées | **Changées** | Δ médian | Δ max |
|---|---:|---:|---:|---:|
| **Saint-Paul** (terrain 600–6 000 m², candidats) | 1 410 | **129** | **+394 292 €** | **+600 408 €** |
| Saint-Paul terrain > 6 000 m² (éch. 55) | 55 | 0 | — | — |
| Saint-Paul terrain < 600 m² (éch. 60) | 60 | 0 | — | — |
| Saint-Denis (éch. 40) | 40 | 0 | — | — |
| Saint-Pierre (éch. 38) | 38 | 0 | — | — |
| Saint-Benoît (éch. 38) | 38 | 0 | — | — |
| Saint-Louis (éch. 37) | 37 | 0 | — | — |
| Le Tampon (éch. 40) | 40 | 0 | — | — |
| Saint-André (éch. 18) | 18 | 0 | — | — |

**Lecture.** **Seul Saint-Paul bouge** (régime à bandes) ; toutes les autres communes à mixité ou non =
**0 changée** (vérifié empiriquement en plus de la garantie par construction : clause identique quand
`mixite_sdp_seuil_haut_m2 = 0`). Les 129 parcelles Saint-Paul qui changent sont de **grands terrains dont
le gabarit ≥ 1 500 m² déclenchait l'ancienne clause, alors que leur programme chiffré est bien plus petit
(< 1 500 m²)** → l'ancien bilan appliquait à tort la décote sociale (30 % @ 2 900 €/m²). Exemples
rejoués : AS0904 gabarit 4 276 / programme 1 262 → **OLD −258 233 € → NEW +163 179 €** ; AS0610 gabarit
2 222 / programme 656 → **OLD −135 825 € → NEW +83 226 €**. Les parcelles terrain > 6 000 m² ne changent
pas (critère terrain réglementaire conservé), ni les petites (< 600 m², gabarit sous le seuil).
Réconciliations d'assemblage : **trio CV −349 965 € → +178 261 €**, **paire BZ −26 019 € (inchangée)**.

Durée de la passe : **1 802 s** (30 min), lecture seule, une connexion, 0 lock sur les autres sessions.
Script : `/tmp/mesure_lot3.py` (hors dépôt) — recalcule chaque parcelle avec le seuil haut forcé à 0
(historique) vs présent (nouveau).

> **✅ Tableau validé par le mandant (24/11)** — commit du LOT 3 autorisé avec les autres lots.

### Détail des 129 parcelles Saint-Paul qui changent

Fichier brut : [`lot3-129-parcelles.csv`](lot3-129-parcelles.csv) (idu, zone, gabarit, programme, seuil,
bilan avant, bilan après, Δ). **99** ont un programme chiffré **< 1 500 m²** (clause retirée) ; **30**
sont dans la bande **1 500–1 800 m²** (plein régime retiré). Somme des hausses : **+51 659 312 €**.
Programme chiffré de **489 à 1 799 m²** — tous avaient un **gabarit théorique ≥ 1 500 m²** qui
déclenchait l'ancienne clause. Tableau complet en fin de document.

### Cinq cas déroulés à la main — pourquoi la décote ne s'applique pas

Référence : **Art. 2 du règlement PLU de Saint-Paul, pp. 106-107** (seuils de déclenchement de la clause
de mixité, lus du contre-audit ASTRA). Le quota de logements aidés se calcule **sur le programme** :
**≥ 1 800 m²** → plein régime (30 % LLS @ 2 900 €/m²) ; **1 500–1 800 m²** → bande intermédiaire
(accession sociale, quota au nombre de logements — **pas** le 30 % plein) ; **< 1 500 m²** → **pas de
clause**. L'ancien moteur comparait le **gabarit théorique** (capacité maximale table rase) au seuil,
d'où une décote plein régime appliquée à des programmes qui n'y tombent pas.

| Cas | IDU | zone | gabarit | programme | seuil Art. 2 | bilan avant | bilan après | pourquoi la décote tombe |
|---|---|---|--:|--:|---|--:|--:|---|
| **Plus grosse hausse** | 97415000AW1880 | U4b | 2 318 | **1 799** | bande 1500-1800 | −289 863 € | **+310 545 €** | programme 1 799 < seuil haut 1 800 → bande intermédiaire ; le 30 % LLS (réservé ≥ 1 800) ne s'applique pas. L'ancien le déclenchait sur le gabarit 2 318. |
| Gros gabarit, bande | 97415000AZ1115 | U4b | 3 347 | 1 755 | bande 1500-1800 | −352 801 € | +233 004 € | gabarit 3 347 (table rase) ≫ programme chiffré 1 755 ; programme en bande → pas de plein régime. |
| Bande, U1a | 97415000BP0228 | U1a | 1 948 | 1 741 | bande 1500-1800 | −161 158 € | +420 057 € | idem : programme 1 741 dans la bande, décote plein régime retirée. |
| **Juste sous 1 500** | 97415000AY1666 | U4b | 2 890 | **1 494** | aucun (< 1500) | −304 421 € | **+194 180 €** | programme 1 494 < seuil bas 1 500 → **aucune** clause ; l'ancien déclenchait sur le gabarit 2 890. |
| Juste sous 1 500, petit gabarit | 97415000BO0011 | U1a | 1 609 | **1 485** | aucun (< 1500) | −137 218 € | +358 463 € | gabarit à peine au-dessus de 1 500 (1 609) mais programme 1 485 < 1 500 → pas de clause. |

Chaque cas est **rejouable en lecture seule** : `parcel_faisabilite` + `compute_bilan_servi` (seuil haut
présent) vs le même avec `mixite_sdp_seuil_haut_m2 = 0` (régime historique). Direction toujours
**positive** (décote erronée retirée).

---

## LOT 4 — points à corriger 4 à 7 ✅

**Pt 4 — mesure absente / zéro / total partiel.** Nouveau drapeau `existant_partiel` (≥ 1 parcelle sans
bâti mesuré, ex. DH0120, CV1504) + `existant_mesurees`. L'écran dit « Existant · N m² (partiel — X
parcelles mesurées sur Y) », distinct d'un zéro mesuré ; « Si conservé » affiche alors « ajout non
déterminé (existant partiel) » (plus de « + » précis dérivé d'un total partiel). « Si conservé » porte un
libellé explicite (plancher constructible en gardant le bâti = capacité − existant).

**Pt 5 — « prix connu » et « marché de la zone ».** La ligne « Prix connu pour N parcelle sur M »
(compteur qui valait 1 dès que l'union avait un CA, infobulle fausse) est **retirée**. « Marché de la
zone » devient « Marché du terrain nu · zone `<zone>` » avec sa règle de choix (zone la plus représentée
en nombre de parcelles) + nombre de ventes, et dit que ce repère **n'entre pas** dans la charge foncière.
Le trio CV se lit désormais : marché terrain **387 €/m²**, prix de sortie **4 730 €/m²** — et plus de
**4 181 €/m²** caché (c'était le régime plein erroné, corrigé au LOT 3).

**Pt 6 — propriétaires + hypothèse de maîtrise.** On compte les **personnes morales identifiées** et on
qualifie les parcelles restantes « **N parcelles sans personne morale identifiée** » (`n_parcelles_sans_pm`),
**jamais « N particuliers »** (plusieurs parcelles peuvent appartenir au même propriétaire ; aucun
particulier nommé). L'**hypothèse de maîtrise foncière** (acquisition de toute l'assiette, disparition des
limites internes) est affichée **avant le résultat** (`data-asm-maitrise`).

**Pt 7 — identifiants écartés + Comparer DH0098.** `/compare` distingue désormais `echecs` (trouvée mais
fiche non calculable — ex. DH0098) de `ignores` (introuvable) : **tout identifiant demandé non rendu est
nommé** (`app.py:9889`). L'écran Comparer affiche un bandeau nommant chaque parcelle écartée et sa cause.
Rejeu (lecture seule) :
```
app.compare(idus="97415000DH0098,97415000EP0971,97415000ZZ9999")
→ parcels=[EP0971] · echecs=[DH0098] · ignores=[ZZ9999]   (avant : DH0098 disparaissait en silence)
```

**Tests.** Back : `test_clause_mixite_*`, `test_bilan_union_mixite_reconcilie` (LOT 3). Front :
`Assemblage.test.tsx` cas par-zone + liens + maîtrise. Comparer `echecs` vérifié en rejeu.

---

## État des tests (avant push)

- **Front** : **347 passent** (69 fichiers) ; `tsc` sans erreur.
- **Python, famille unitaire du hook** (`not db and not local and not reel and not network`) : **5028
  passent**. 3 régressions révélées par la passe complète ont été corrigées :
  - `mixite_source_ref` Saint-Paul **laissé inchangé** (« Art. 2 règlement PLU ») — la précision
    « pp. 106-107 » vit dans les commentaires de code et ce compte-rendu, pas dans la chaîne SOURCÉE
    affichée (tests `test_mn_faisabilite` verts) ;
  - `assemblage.py` ne **lit plus** `logements_au_sol`/`sous_sol` (LOGEMENTS-SOURCE-UNIQUE) : la
    fourchette agrégée garde les logements de la zone représentative — exact en mono-zone (cas chiffrés
    CV/BZ), le VRD stationnement d'une union multizone est une approximation mineure (dit).
- **Python DB** `tests/test_assemblage.py` : **27 passent** (valeurs LOT 1/2/3 à l'euro), 1 skip (run
  résiduel absent de `labuse_test`).
- **Golden standard + faisabilité + mixité PLU** : verts.

---

## Annexe — tableau complet des 129 parcelles Saint-Paul (Δ décroissant)

| # | IDU | zone | gabarit m² | programme m² | seuil appliqué | bilan AVANT € | bilan APRÈS € | Δ € |
|--:|---|---|--:|--:|---|--:|--:|--:|
| 1 | 97415000AW1880 | U4b | 2 318 | 1 799 | intermédiaire (1500-1800) | -289 863 | 310 545 | +600 408 |
| 2 | 97415000AZ1115 | U4b | 3 347 | 1 755 | intermédiaire (1500-1800) | -352 801 | 233 004 | +585 805 |
| 3 | 97415000BP0228 | U1a | 1 948 | 1 741 | intermédiaire (1500-1800) | -161 158 | 420 057 | +581 215 |
| 4 | 97415000AW0299 | U4b | 2 356 | 1 740 | intermédiaire (1500-1800) | -286 311 | 294 487 | +580 798 |
| 5 | 97415000AW1766 | U4b | 3 357 | 1 735 | intermédiaire (1500-1800) | -351 340 | 227 789 | +579 129 |
| 6 | 97415000AW0742 | U4b | 3 355 | 1 734 | intermédiaire (1500-1800) | -351 249 | 227 463 | +578 712 |
| 7 | 97415000AX0857 | U4b | 2 736 | 1 730 | intermédiaire (1500-1800) | -331 445 | 246 015 | +577 460 |
| 8 | 97415000EY0712 | U3a | 3 437 | 1 712 | intermédiaire (1500-1800) | -248 954 | 322 664 | +571 618 |
| 9 | 97415000BP0213 | U1a | 1 911 | 1 711 | intermédiaire (1500-1800) | -155 801 | 415 401 | +571 202 |
| 10 | 97415000AY1437 | U4b | 3 292 | 1 701 | intermédiaire (1500-1800) | -339 110 | 228 754 | +567 864 |
| 11 | 97415000AW0307 | U4b | 2 268 | 1 675 | intermédiaire (1500-1800) | -274 507 | 284 594 | +559 101 |
| 12 | 97415000AV0149 | U4b | 2 382 | 1 668 | intermédiaire (1500-1800) | -326 879 | 229 719 | +556 598 |
| 13 | 97415000AX1059 | U4b | 2 859 | 1 664 | intermédiaire (1500-1800) | -326 605 | 228 741 | +555 346 |
| 14 | 97415000BO0273 | U1a | 1 912 | 1 660 | intermédiaire (1500-1800) | -153 375 | 400 719 | +554 094 |
| 15 | 97415000BS0126 | U1a | 1 901 | 1 660 | intermédiaire (1500-1800) | -153 375 | 400 719 | +554 094 |
| 16 | 97415000AY0059 | U4b | 2 225 | 1 642 | intermédiaire (1500-1800) | -272 542 | 275 711 | +548 253 |
| 17 | 97415000BP0219 | U1a | 1 783 | 1 628 | intermédiaire (1500-1800) | -147 900 | 395 347 | +543 247 |
| 18 | 97415000BO0313 | U1a | 1 819 | 1 622 | intermédiaire (1500-1800) | -147 663 | 393 914 | +541 577 |
| 19 | 97415000BO0246 | U1a | 1 702 | 1 611 | intermédiaire (1500-1800) | -147 131 | 390 692 | +537 823 |
| 20 | 97415000AY1354 | U4b | 3 101 | 1 604 | intermédiaire (1500-1800) | -322 222 | 213 097 | +535 319 |
| 21 | 97415000AZ0088 | U4b | 2 280 | 1 596 | intermédiaire (1500-1800) | -302 144 | 230 671 | +532 815 |
| 22 | 97415000AT0257 | U4b | 2 930 | 1 590 | intermédiaire (1500-1800) | -321 218 | 209 512 | +530 730 |
| 23 | 97415000AY0140 | U4b | 3 017 | 1 560 | intermédiaire (1500-1800) | -319 026 | 201 689 | +520 715 |
| 24 | 97415000BO0030 | U1a | 1 709 | 1 534 | intermédiaire (1500-1800) | -139 525 | 372 428 | +511 953 |
| 25 | 97415000AX0856 | U4b | 2 072 | 1 530 | intermédiaire (1500-1800) | -249 992 | 260 710 | +510 702 |
| 26 | 97415000AY0609 | U4b | 2 955 | 1 528 | intermédiaire (1500-1800) | -306 887 | 202 980 | +509 867 |
| 27 | 97415000BO0326 | U1a | 1 628 | 1 519 | intermédiaire (1500-1800) | -138 815 | 368 131 | +506 946 |
| 28 | 97415000BP0176 | U1a | 1 712 | 1 514 | intermédiaire (1500-1800) | -138 579 | 366 699 | +505 278 |
| 29 | 97415000EY0616 | U3a | 6 258 | 1 511 | intermédiaire (1500-1800) | -232 169 | 272 274 | +504 443 |
| 30 | 97415000BO0309 | U1a | 1 697 | 1 504 | intermédiaire (1500-1800) | -138 105 | 363 834 | +501 939 |
| 31 | 97415000AY1666 | U4b | 2 890 | 1 494 | aucun (<1500) | -304 421 | 194 180 | +498 601 |
| 32 | 97415000AT0515 | U4b | 2 132 | 1 492 | aucun (<1500) | -284 800 | 213 384 | +498 184 |
| 33 | 97415000BO0011 | U1a | 1 609 | 1 485 | aucun (<1500) | -137 218 | 358 463 | +495 681 |
| 34 | 97415000EY1715 | U3a | 2 121 | 1 485 | aucun (<1500) | -208 964 | 286 717 | +495 681 |
| 35 | 97415000BP0218 | U1a | 1 626 | 1 442 | aucun (<1500) | -131 269 | 350 226 | +481 495 |
| 36 | 97415000EY0739 | U3a | 1 770 | 1 435 | aucun (<1500) | -144 724 | 334 268 | +478 992 |
| 37 | 97415000AY1487 | U4b | 2 762 | 1 428 | aucun (<1500) | -289 817 | 186 671 | +476 488 |
| 38 | 97415000AW0327 | U4b | 1 783 | 1 410 | aucun (<1500) | -226 987 | 243 659 | +470 646 |
| 39 | 97415000AW0151 | U4b | 1 905 | 1 408 | aucun (<1500) | -234 711 | 235 101 | +469 812 |
| 40 | 97415000AT0672 | U4b | 2 419 | 1 398 | aucun (<1500) | -277 860 | 188 614 | +466 474 |
| 41 | 97415000AW1089 | U4b | 2 272 | 1 379 | aucun (<1500) | -266 725 | 193 490 | +460 215 |
| 42 | 97415000EY1187 | U3a | 1 650 | 1 362 | aucun (<1500) | -136 497 | 318 294 | +454 791 |
| 43 | 97415000AW1360 | U4b | 1 842 | 1 360 | aucun (<1500) | -223 965 | 229 992 | +453 957 |
| 44 | 97415000AY1425 | U4b | 2 623 | 1 356 | aucun (<1500) | -274 847 | 177 859 | +452 706 |
| 45 | 97415000AW0743 | U4b | 2 622 | 1 355 | aucun (<1500) | -274 755 | 177 533 | +452 288 |
| 46 | 97415000AY1148 | U4b | 2 609 | 1 349 | aucun (<1500) | -274 299 | 175 903 | +450 202 |
| 47 | 97415000EY0696 | U3a | 2 354 | 1 340 | aucun (<1500) | -187 500 | 259 781 | +447 281 |
| 48 | 97415000AT0355 | U4b | 4 509 | 1 331 | aucun (<1500) | -273 020 | 171 340 | +444 360 |
| 49 | 97415000BP0485 | U1a | 1 507 | 1 316 | aucun (<1500) | -121 357 | 317 997 | +439 354 |
| 50 | 97415000AW0242 | U4b | 2 542 | 1 314 | aucun (<1500) | -261 977 | 176 542 | +438 519 |
| 51 | 97415000AW1441 | U4b | 2 517 | 1 301 | aucun (<1500) | -261 064 | 173 283 | +434 347 |
| 52 | 97415000EY0781 | U3a | 1 860 | 1 301 | aucun (<1500) | -185 678 | 248 669 | +434 347 |
| 53 | 97415000EY0613 | U3a | 1 570 | 1 296 | aucun (<1500) | -129 895 | 302 783 | +432 678 |
| 54 | 97415000AW1323 | U4b | 2 498 | 1 291 | aucun (<1500) | -260 333 | 170 676 | +431 009 |
| 55 | 97415000AV0780 | U4b | 2 175 | 1 290 | aucun (<1500) | -250 477 | 180 115 | +430 592 |
| 56 | 97415000AS0904 | U4b | 4 276 | 1 262 | aucun (<1500) | -258 233 | 163 179 | +421 412 |
| 57 | 97415000AZ0776 | U4b | 2 419 | 1 250 | aucun (<1500) | -257 320 | 159 920 | +417 240 |
| 58 | 97415000AW1886 | U4b | 1 693 | 1 250 | aucun (<1500) | -209 440 | 207 800 | +417 240 |
| 59 | 97415000AW1240 | U4b | 1 692 | 1 249 | aucun (<1500) | -209 364 | 207 458 | +416 822 |
| 60 | 97415000EY1904 | U3a | 3 118 | 1 248 | aucun (<1500) | -175 827 | 240 578 | +416 405 |
| 61 | 97415000AY0068 | U4b | 2 391 | 1 236 | aucun (<1500) | -246 551 | 166 100 | +412 651 |
| 62 | 97415000AT0402 | U4b | 1 721 | 1 205 | aucun (<1500) | -234 503 | 167 717 | +402 220 |
| 63 | 97415000AX0669 | U4b | 1 598 | 1 196 | aucun (<1500) | -198 316 | 200 983 | +399 299 |
| 64 | 97415000AW1398 | U4b | 2 088 | 1 190 | aucun (<1500) | -233 407 | 163 806 | +397 213 |
| 65 | 97415000AX0099 | U4b | 1 952 | 1 181 | aucun (<1500) | -232 768 | 161 524 | +394 292 |
| 66 | 97415000AY0047 | U4b | 1 686 | 1 180 | aucun (<1500) | -232 676 | 161 198 | +393 874 |
| 67 | 97415000AX0890 | U4b | 2 276 | 1 176 | aucun (<1500) | -242 167 | 150 455 | +392 622 |
| 68 | 97415000AW0873 | U4b | 1 583 | 1 169 | aucun (<1500) | -196 653 | 193 466 | +390 119 |
| 69 | 97415000AY0699 | U4b | 2 251 | 1 164 | aucun (<1500) | -241 254 | 147 196 | +388 450 |
| 70 | 97415000AY0103 | U4b | 1 567 | 1 158 | aucun (<1500) | -188 098 | 198 266 | +386 364 |
| 71 | 97415000AY1082 | U4b | 1 565 | 1 155 | aucun (<1500) | -187 947 | 197 583 | +385 530 |
| 72 | 97415000AT0203 | U4b | 2 200 | 1 138 | aucun (<1500) | -229 572 | 150 117 | +379 689 |
| 73 | 97415000EY1790 | U3a | 1 624 | 1 136 | aucun (<1500) | -155 950 | 223 321 | +379 271 |
| 74 | 97415000AZ1226 | U4b | 1 616 | 1 131 | aucun (<1500) | -219 350 | 158 252 | +377 602 |
| 75 | 97415000AX0689 | U4b | 1 530 | 1 130 | aucun (<1500) | -186 436 | 190 749 | +377 185 |
| 76 | 97415000AW1362 | U4b | 1 526 | 1 128 | aucun (<1500) | -186 285 | 190 066 | +376 351 |
| 77 | 97415000EY0705 | U3a | 4 729 | 1 118 | aucun (<1500) | -169 716 | 203 297 | +373 013 |
| 78 | 97415000AW0899 | U4b | 2 124 | 1 098 | aucun (<1500) | -226 650 | 139 687 | +366 337 |
| 79 | 97415000AW1028 | U4b | 1 799 | 1 082 | aucun (<1500) | -215 789 | 145 541 | +361 330 |
| 80 | 97415000AW0196 | U4b | 2 088 | 1 080 | aucun (<1500) | -215 606 | 144 889 | +360 495 |
| 81 | 97415000EY0718 | U3a | 2 315 | 1 075 | aucun (<1500) | -160 394 | 198 432 | +358 826 |
| 82 | 97415000AT0255 | U4b | 2 070 | 1 070 | aucun (<1500) | -214 876 | 142 282 | +357 158 |
| 83 | 97415000AW0380 | U4b | 2 043 | 1 056 | aucun (<1500) | -213 871 | 138 697 | +352 568 |
| 84 | 97415000AY1351 | U4b | 1 661 | 1 041 | aucun (<1500) | -203 010 | 144 551 | +347 561 |
| 85 | 97415000AW1985 | U4b | 2 009 | 1 039 | aucun (<1500) | -212 593 | 134 134 | +346 727 |
| 86 | 97415000AT0151 | U4b | 1 826 | 1 028 | aucun (<1500) | -202 006 | 140 965 | +342 971 |
| 87 | 97415000AT0101 | U4b | 1 864 | 1 010 | aucun (<1500) | -200 728 | 136 402 | +337 130 |
| 88 | 97415000AZ0426 | U4b | 1 944 | 1 005 | aucun (<1500) | -200 362 | 135 099 | +335 461 |
| 89 | 97415000AX0415 | U4b | 1 926 | 995 | aucun (<1500) | -199 632 | 132 491 | +332 123 |
| 90 | 97415000AY0062 | U4b | 1 919 | 991 | aucun (<1500) | -199 358 | 131 514 | +330 872 |
| 91 | 97415000AZ0113 | U4b | 1 634 | 989 | aucun (<1500) | -189 410 | 140 627 | +330 037 |
| 92 | 97415000EY1509 | U3a | 2 390 | 989 | aucun (<1500) | -149 016 | 181 021 | +330 037 |
| 93 | 97415000AY0251 | U4b | 1 911 | 988 | aucun (<1500) | -199 084 | 130 536 | +329 620 |
| 94 | 97415000AZ1114 | U4b | 1 892 | 978 | aucun (<1500) | -198 353 | 127 928 | +326 281 |
| 95 | 97415000AY1066 | U4b | 1 719 | 976 | aucun (<1500) | -198 262 | 127 602 | +325 864 |
| 96 | 97415000AW1443 | U4b | 1 865 | 975 | aucun (<1500) | -198 171 | 127 276 | +325 447 |
| 97 | 97415000AW0715 | U4b | 1 749 | 962 | aucun (<1500) | -197 258 | 124 017 | +321 275 |
| 98 | 97415000AT0102 | U4b | 1 596 | 962 | aucun (<1500) | -187 493 | 133 782 | +321 275 |
| 99 | 97415000AW1741 | U4b | 1 861 | 961 | aucun (<1500) | -197 166 | 123 691 | +320 857 |
| 100 | 97415000AX0023 | U4b | 1 713 | 950 | aucun (<1500) | -186 579 | 130 523 | +317 102 |
| 101 | 97415000AW0711 | U4b | 1 786 | 924 | aucun (<1500) | -184 662 | 123 679 | +308 341 |
| 102 | 97415000AW0716 | U4b | 1 700 | 924 | aucun (<1500) | -184 662 | 123 679 | +308 341 |
| 103 | 97415000AW1982 | U4b | 1 748 | 904 | aucun (<1500) | -183 201 | 118 464 | +301 665 |
| 104 | 97415000AT0083 | U4b | 1 733 | 896 | aucun (<1500) | -182 653 | 116 508 | +299 161 |
| 105 | 97415000AY1167 | U4b | 1 721 | 890 | aucun (<1500) | -182 196 | 114 879 | +297 075 |
| 106 | 97415000AY1426 | U4b | 1 706 | 881 | aucun (<1500) | -181 557 | 112 597 | +294 154 |
| 107 | 97415000AS1789 | U4b | 1 644 | 870 | aucun (<1500) | -180 735 | 109 664 | +290 399 |
| 108 | 97415000EY1988 | U3a | 1 547 | 866 | aucun (<1500) | -121 285 | 167 862 | +289 147 |
| 109 | 97415000AW0712 | U4b | 1 671 | 864 | aucun (<1500) | -180 279 | 108 034 | +288 313 |
| 110 | 97415000AW1397 | U4b | 1 648 | 852 | aucun (<1500) | -169 692 | 114 866 | +284 558 |
| 111 | 97415000AW0391 | U4b | 1 624 | 840 | aucun (<1500) | -168 779 | 111 607 | +280 386 |
| 112 | 97415000AT0661 | U4b | 1 617 | 836 | aucun (<1500) | -168 505 | 110 629 | +279 134 |
| 113 | 97415000AT0633 | U4b | 1 513 | 816 | aucun (<1500) | -167 044 | 105 414 | +272 458 |
| 114 | 97415000AY0022 | U4b | 1 577 | 815 | aucun (<1500) | -166 952 | 105 088 | +272 040 |
| 115 | 97415000AV0147 | U4b | 2 693 | 795 | aucun (<1500) | -165 491 | 99 873 | +265 364 |
| 116 | 97415000AW1296 | U4b | 1 525 | 789 | aucun (<1500) | -165 035 | 98 244 | +263 279 |
| 117 | 97415000AY0021 | U4b | 1 522 | 788 | aucun (<1500) | -164 943 | 97 918 | +262 861 |
| 118 | 97415000AW0857 | U4b | 1 517 | 784 | aucun (<1500) | -164 670 | 96 940 | +261 610 |
| 119 | 97415000AT0423 | U4b | 2 086 | 680 | aucun (<1500) | -137 560 | 89 418 | +226 978 |
| 120 | 97415000AY1115 | U4b | 1 681 | 672 | aucun (<1500) | -137 012 | 87 463 | +224 475 |
| 121 | 97415000AS0610 | U4b | 2 222 | 656 | aucun (<1500) | -135 825 | 83 226 | +219 051 |
| 122 | 97415000AT0004 | U4b | 1 594 | 638 | aucun (<1500) | -124 691 | 88 102 | +212 793 |
| 123 | 97415000AS1210 | U4b | 2 083 | 615 | aucun (<1500) | -123 047 | 82 235 | +205 282 |
| 124 | 97415000AT0019 | U4b | 1 764 | 615 | aucun (<1500) | -123 047 | 82 235 | +205 282 |
| 125 | 97415000AT0099 | U4b | 1 983 | 585 | aucun (<1500) | -120 855 | 74 413 | +195 268 |
| 126 | 97415000AT0011 | U4b | 1 736 | 532 | aucun (<1500) | -107 255 | 70 489 | +177 744 |
| 127 | 97415000AT0137 | U4b | 1 721 | 509 | aucun (<1500) | -105 520 | 64 296 | +169 816 |
| 128 | 97415000AT0020 | U4b | 1 674 | 495 | aucun (<1500) | -104 516 | 60 711 | +165 227 |
| 129 | 97415000AT0008 | U4b | 1 654 | 489 | aucun (<1500) | -104 059 | 59 082 | +163 141 |
