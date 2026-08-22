# M130-12 — La hauteur PLU ne dépend pas du résiduel

Garde-fou OK : `feat/m130-pdf-projet @ b08fcc66`. Livré sur `feat/m130-pdf-projet`,
poussé sur origin. CC ne merge pas. PDF via `generer_pdf_qa.py` (gitignorés).

---

## A — Tableau de couverture (PLU calibré)

Toutes les zones interrogées portent une règle de hauteur (directe, par renvoi,
ou secteur) — **aucune zone constructible « non renseignée »**.

**Le Tampon (97422, 11/08/2023)** :

| Zone | égout / faîtage | Source |
|---|---|---|
| Uc | 9 / 13 | Art. Uc10.2, p.46 |
| Ub | 13 / 17 | Art. Ub10.2, p.31 |
| Ua | 21 / 25 | Art. Ua10.2, p.16 |
| Uav | 16 / 20 | Art. Ua10.2, p.16 (secteur Uav) |
| Ucm | 9 / 13 | Art. Uc10.2, p.46 (indice « m ») |
| 1AUa | 21 / 25 | Art. Ua10.2, p.16 **via renvoi** (AUindicée p.83) |
| 1AUb | 13 / 17 | Art. Ub10.2, p.31 **via renvoi** |
| 1AUc | 9 / 13 | Art. Uc10.2, p.46 **via renvoi** |
| 1AUe | 12 / — | Art. Ue10.2, p.75-76 **via renvoi** |
| 2AUb · 2AUc · 2AUd · 2AUe | — / 4 | ZONE AUindicée, Art. 2.2.3, p.84 |

**Saint-Pierre (97416, 25/06/2024)** :

| Zone | égout / faîtage | Source |
|---|---|---|
| Uf | 6 / 11 | Art. Uf3.5, p.119 |
| Ucv | 15 / 20 | Art. Ucv3.5, p.65 |
| UfCA | 6 / 7,5 | Art. Uf3.5, p.119 (secteur UfCa) |
| Ug | 7 / 12 | Art. Ug3.5, p.103 |
| Ud | 15 / 20 | Art. Ud3.5, p.84 |
| Up | 6 / 11 | Art. Up3.5, p.147 |
| Uazi | 16 / 21 | Art. Ua3.5, p.177 |
| Ut | 9 / 12 | Art. Ut3.5, p.162 |
| Us | — / 4 | Us1 p.130 (source `Art. AU01` = **dette EP1044 / M130-6 F.2**, hors périmètre) |

Seules les zones **A / N** (agricole / naturelle) sortent « non renseignée au PLU
calibré » → consignées dans `qa/m130/DETTE_HAUTEUR_PLU.md`.

---

## B — Le point exact du couplage, et le découplage

**Couplage (introduit par moi en M130-11 §B, dans `pdf_projet._lignes_donnees`)** :

```python
buildable = prefix_case or bool(it.get("sdp_chiffree"))     # ← le RÉSIDUEL entre ici
if buildable and (he is not None or hf is not None): … servie …
elif (it.get("he_m") … ): "Hauteur PLU : sans objet (aucune capacité constructible…)"
```

La hauteur était écrasée en « sans objet » dès que `sdp_chiffree` était faux
(résiduel nul) — un faux négatif.

**Découplage (M130-12)** : une fonction dédiée `_ligne_hauteur(it)` dont la SEULE
entrée est *zones + PLU calibré* (elle ne lit **aucun** champ de résiduel :
`sdp_chiffree`, `sdp_indispo`, `sdp_m2`, modulations…). Trois sorties :
1. règle trouvée → hauteur servie + source exacte ;
2. règle sur une part non dominante → idem + préfixe « part X — » (M130-11 §A) ;
3. règle absente → « non renseignée au PLU calibré ».

La chaîne « sans objet (aucune capacité constructible en l'état) » est
**supprimée** — aucun chemin de code ne peut plus la produire (grep dans le rendu
= 0). La constructibilité reste dite par la ligne SDP, seule.

---

## C — Vérification au rendu (P1–P4)

| Contrôle | Attendu | Obtenu |
|---|---|---|
| 1. « sans objet » | 0 partout | **0** (P1/P2/P3/P4) |
| 2. P2 muettes → servies | ≥ 16 / 31 | **31 / 31** (P2 : 60 servies, 0 non renseignée) |
| 3. P3 muettes → servies | ≥ 20 / 44 | **44 / 44** converties (P3 : 51 servies = 5 déjà servies + 2 parts + 44 converties ; 9 non renseignée = les 9 A/N pré-existantes) |
| 4. BI 1097 (1AUe) | Ue10.2 via renvoi, sans préfixe | « égout 12 m · faîtage non réglementé (… **Art. Ue10.2, p.75-76 via renvoi** …) » ✅ |
| 5. CW 1056 (AU3a→U3a) | non muette, 15/19 | « égout 15 m · faîtage 19 m (… Zone U3a, Art. 10.2, p.110-112 · via renvoi …) » ✅ |
| 6. « part X — » | 5, inchangé | **5** (BV2471 Ua · CL1113 Uc · DH0211 Uc · CX1483 Uf · EX0280 Uf) |
| 7a. « peut exister » | 0 | **0** |
| 7b. « restent à instruire » (générique) | 0 | **0** (« reste à instruire » toujours après une part nommée) |
| 7c. BV 2471 | « aucune autre part nommée » + agrégat dernier | ✅ |
| 7d. en-tête P3 | incise « voir toutefois… » | **présente** |

Cas emblématique résolu : `HY0897` était « sans objet » → sert désormais
« égout 7 m · faîtage 12 m (Art. Ug3.5, p.103) », alors que sa ligne SDP dit
toujours « aucune — résiduel nul ». Deux questions, deux réponses, aucune ne ment.
Idem la zone 1AUb (BD3436 servie / DH0676 / DH0771 muettes → **les trois servies**,
même règle).

ruff : 0 erreur nouvelle (I001 restantes = imports pré-existants décalés).

---

## Hors périmètre (non touché)

Lignes SDP · cascade · vivier · scoring : inchangés. EP 1044 (`Us`, source
`Art. AU01`) : dette data connue (M130-6 F.2), non traitée ici. Aucun verdict /
score / rang ; l'IA ne produit aucun chiffre.

**Critère de merge (arbitrage) : le document ne ment plus.** Le merge `--no-ff`
reste à la main de Vic depuis `~/Desktop/labuse` ; CC ne merge jamais.

---

## Vérifications avant merge (demandées après M130-12)

### 1. EP 1044 (P3, Us) — ligne « Hauteur PLU » intégrale, telle que rendue

> Hauteur PLU : égout non réglementé · faîtage 4 m (Sourcé — PLU calibré ·
> **Préambule Us p.129 + Art. Us1 (tableau) p.130**)

**`Art. AU01, p.200` N'A PAS été réinjecté.** Le nettoyage M130-11
(`_hauteur_src_dezone`) reste actif en M130-12 : 0 occurrence de « AU01 » dans P3.
L'article cité (`Us1`) est celui de la zone `Us` → **pas de faux positif au niveau
de la source**. (La question du *chiffre* 4 m — issu ou non des annexes AU0 —
reste la dette data EP 1044 / M130-6 F.2, hors périmètre.)

### 2. Table des sources servies (P1–P4) — recherche d'un article hors-zone

**Aucune** source servie ne cite un article d'une **autre famille de zone** que la
sienne, une fois le nettoyage appliqué. Les 5 zones à contrôler :

| Zone | Source servie | Verdict |
|---|---|---|
| `Us` (St-Pierre) | Art. Us1 (tableau) p.130 | OK (AU01 retiré) |
| `Uazi` (St-Pierre) | Art. Ua3.5, p.177 (règle générale) | OK — sous-secteur de la famille `Ua` |
| `Ut` (St-Pierre) | Art. Ut3.5, p.162 | OK |
| `Up` (St-Pierre) | Art. Up3.5, p.147 | OK |
| `Ucm` (Le Tampon) | Art. Uc10.2, p.46 (indice « m ») | OK — sous-zone `Uc` documentée |

Toutes les autres zones servies sont soit **même famille** (`Uf→Uf3.5`,
`Ug→Ug3.5`, `Ud→Ud3.5`…), soit **renvoi documenté** (`1AUb→Ub10.2 via renvoi`,
`AU3a→U3a`…), soit **estimation générique** (communes non outillées, sans
article). Aucune source servie ne cite l'article d'une autre zone.

---

## Rattrapage — le repli `zones_au_st` fabriquait un « faîtage 4 m » (corrigé amont)

Après relecture : le défaut de fond n'était pas `Us` mais le **mécanisme
`zones_au_st`** (`plu_rules.py:204`), qui servait `hf_m = float(st.get(
"hauteur_max_m", 4))` — un **4 m codé en dur** quand le YAML ne définit pas
`hauteur_max_m` (aucune commune ne le fait). Ce 4 m, que le YAML Saint-Pierre
déclare lui-même **INEXACTE**, contaminait `Us` (Saint-Pierre) **ET** `2AU*`
(Le Tampon) — même repli, deux communes.

**Correctif amont** (pas en aval) : absence de `hauteur_max_m` = absence de règle
→ `hf_m = None` (« non renseignée au PLU calibré »). La capacité
(`constructible_neuf=False`) reste exacte. Vérifié sans casse en aval
(`collect_report_data`, `parcel_faisabilite` OK sur 2AUd et Us).

**Contrôle C (rattrapage), P1–P4** :

| Contrôle | Obtenu |
|---|---|
| « faîtage 4 m » | **0** partout (aucune commune ne porte `hauteur_max_m: 4` sourcé) |
| 2AU de P2 → « non renseignée » | **8 / 8** (AD0250, AK0945, AP1250, AX1253, AX1477, AX1478, AX1479, CX0670) |
| EP 1044 (Us) → « non renseignée » | ✅ |
| non-régression | sans objet=0 · peut exister=0 · restent=0 · « part X — »=5 · BI1097 & CW1056 intacts · incise P3 |

Dette : `qa/m130/DETTE_HAUTEUR_PLU.md` — mécanisme + zones + **valeurs réelles
connues non gravées** (`Us` = 6/11 au chap. 2 p.130 ; `2AU` Le Tampon à instruire),
rejoint M130-6 F.2 ; + dette cosmétique renvois (`Uazi`, `Ucm`).
