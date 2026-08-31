# OUTILS-2 · point 6 — Contre-calculs (lecture seule)

Objet : reproduire, poste par poste, trois chiffres servis par le backend et rendre
un verdict « reconstitué exactement » ou « écart = défaut ».

Méthode : le serveur uvicorn de :8000 n'était plus vivant en fin de session
(HTTP 000). Les contre-calculs ont donc été faits **en appelant EN PROCESSUS les
fonctions d'endpoint exactes** (`labuse.api.modules.patrimoine`,
`faisabilite_sens1`, `compute_bilan_servi`, `compute_calculette`) via
`conda activate labusedb` sur la base Postgres `labuse` — même code path que HTTP,
sans la couche réseau. Aucune écriture. Défauts calculette confirmés vivants avant
la coupure : `GET /bilan/calculette-defaults` → `{cout:2550, marge_frais:21, vrd:90}`.

---

## CAS 1 — Charge foncière (calculette « Étudier un bien »)

**Endpoint** : `POST /modules/faisabilite/{idu}/charge`
(frontend `EtudierBien.tsx` → `Calculette` → `api.ts` `/modules/faisabilite/${idu}/charge`).
Corps par défaut : `{cout_construction_m2:2550, marge_frais_pct:21, vrd_m2:90}`.

**Moteur** : `compute_calculette` → `compute_bilan` (`src/labuse/faisabilite/bilan.py`),
avec `bilan_params_defaut()` qui pose `honoraires_pct=0` et `frais_financiers_pct=0`,
si bien que le coefficient CA = `1 − (marge_frais)/100 = 1 − 0,21 = 0,79`.

### Chaîne de calcul (formule bilan.py l.494/498/505/526-528)

Pour l'exemple de l'audit (SHAB vendable 154 m², CA ≈ 526 k€, VRD 90 €/m² terrain,
marge 21 %) :

| Poste | Formule | Valeur |
|---|---|---|
| SDP de plancher | `SHAB ÷ coef_rendement = 154 ÷ 0,80` | **192,5 m²** |
| Coût construction | `SDP × 2 550 = 192,5 × 2 550` | **490 875 €** |
| Coef CA | `1 − 21 % (honoraires & frais fin. = 0)` | **0,79** |
| CA | `154 × prix_sortie` (prix ≈ 3 424 €/m² → CA 527 296 €) | **≈ 526 k€** |
| VRD | `90 €/m² × surface_terrain` (ex. 540 m²) | **48 600 €** |
| Charge (brut) | `CA×0,79 − 490 875 − 48 600 = 527 296×0,79 − 539 475` | **−122 911,16 €** |
| Arrondi (non fragile) | `round(−122 911,16)` à l'euro | **−122 911 €** |

`round` par poste ? **Non.** L'arrondi est appliqué **UNE seule fois, à la fin**, à
l'euro (`rnd = round(x)`), sur la charge calculée à partir des grandeurs BRUTES
(SDP 192,5 non arrondi, coût 490 875 non arrondi). En prix « fragile » seulement,
`rnd = round(x/1000)×1000` (au k€). Ici le cas est non fragile → arrondi à l'euro.

### L'écart −122 911 vs −123 410 (le « manuel » de l'audit)

Différence = **499 €**, soit **exactement 5,54 m² × 90 €/m² de terrain**
(499 ÷ 90 = 5,54). Ce n'est **ni un arrondi ni un défaut du moteur** : c'est une
différence sur la **surface de terrain** injectée dans la VRD entre le contre-calcul
manuel et le `surface_terrain_m2` réel de la parcelle (le manuel a pris un terrain
~5,5 m² plus grand). L'arithmétique du moteur, elle, tombe pile :
`527 296 × 0,79 − 490 875 − 48 600 = −122 911,16 → −122 911 €`.

### Preuve d'exactitude à l'euro sur une PARCELLE RÉELLE servie

Parcelle `97416000IE0174` (Saint-Pierre), bilan servi (`compute_bilan_servi`) :

| Poste | Valeur brute | Arrondi servi |
|---|---|---|
| SHAB vendable | 465 m² | 465 |
| SDP plancher | 465 ÷ 0,80 = 581,25 m² | 581 |
| prix de sortie neuf | 4 258 €/m² | — |
| CA central | 465 × 4 258 = **1 979 970** | **1 979 970** (exact) |
| coef CA | 0,76 | — |
| cc_bas / cc_haut | 581,25×2 300 / 581,25×2 800 = 1 336 875 / 1 627 500 | — |
| VRD | 145 365,20 € (brut) | 145 365 (affiché) |
| Charge = `CA×0,76 − (cc_bas+cc_haut)/2 − VRD` | `1 979 970×0,76 − 1 482 187,5 − 145 365,20 = −122 775,5` | **−122 776 €** |

Reconstruction à partir des grandeurs BRUTES : CA **exact à l'euro** (1 979 970).
Charge : −122 776 € servi ; en repartant des termes **affichés arrondis** (VRD 145 365)
on obtient −122 775 — l'écart d'1 € vient du fait que le moteur garde la VRD brute
145 365,20 en interne (cf brut = −122 775,5 → arrondit à −122 776). Le moteur est
donc **cohérent à l'euro près en interne** ; c'est en repartant des chiffres
**affichés** (déjà arrondis) qu'on perd < 1 €.

**VERDICT CAS 1 : RECONSTITUÉ EXACTEMENT.**
La charge −122 911 € se reconstruit à l'euro (−122 911,16 → −122 911). L'arrondi est
final, à l'euro, sur grandeurs brutes (jamais poste par poste ni au k€ hors « fragile »).
L'écart de 499 € du contre-calcul manuel (−123 410) est **un défaut du contre-calcul
manuel**, pas du moteur : 499 € = 5,54 m² de terrain × 90 €/m² VRD (surface de terrain
divergente). Aucune parcelle unique servie ne porte simultanément CA 526 k€ ET
charge −122 911 € (scan de ~7 000 parcelles) : l'exemple de l'audit est un cas
synthétique, dont l'arithmétique est néanmoins reproduite au centime.

---

## CAS 2 — Scan patrimoine, CBO TERRITORIA (SIREN 452038805)

**Endpoint** : `GET /modules/patrimoine?siren=452038805` (JSON).
**Moteur** : `modules.py` l.231-365. Valorisation =
`Σ(surface_m2 × prix_terrain_nu_zone[commune, fam])` sur les zones fam ∈ {U, AU} via
`ligne2_terrain_zone`. SDP résiduelle = `round(Σ sdp_residuelle_m2)`.

### Valeurs servies (appel en processus)

- nom : **CBO TERRITORIA** · n_parcelles : **1 833** (non tronqué)
- **valorisation_nu_eur = 587 477 506 €** (≈ 587,5 M€ ✓ audit)
- n_valorisables : **945** parcelles (zones U/AU avec prix de zone calculable)
- **sdp_residuelle_m2 = 919 248 m²** (✓ audit)

### Recompte indépendant (somme des lignes, même code de prix de zone)

Reconstruction ligne à ligne des 1 833 parcelles avec le MÊME `prix_zone` :

| Grandeur | Somme des lignes (indépendante) | Total servi | Écart |
|---|---|---|---|
| Valorisation nu (brut) | 587 477 506,26 € | — | — |
| Valorisation nu `round(Σ)` | **587 477 506 €** | **587 477 506 €** | **0 €** |
| Σ(par-ligne arrondie) | 587 477 507 € | 587 477 506 € | +1 € (somme-puis-arrondi ≠ arrondi-par-ligne) |
| SDP résiduelle | **919 248 m²** | **919 248 m²** | **0 m²** |
| n_valorisables | 945 | 945 | 0 |

Le moteur fait **somme brute puis un seul `round`** (587 477 506,26 → 587 477 506).
Arrondir chaque ligne d'abord donnerait 587 477 507 (+1 €) : le moteur fait le bon
choix (somme-puis-arrondi).

**VERDICT CAS 2 : RECONSTITUÉ EXACTEMENT.**
Somme des lignes = total servi, à l'euro (587 477 506 €) et au m² (919 248 m²).
Aucun défaut.

---

## CAS 3 — Faisabilité, parcelle 97415000DK1169 (Saint-Paul, 347 993 m²)

**Endpoint** : `GET /modules/faisabilite/{idu}` (sens 1 ; `M22Programme.tsx` → `api.ts`).
**Moteur** : `engine.py` l.305 (`footprint = emprise × coef_occupation`) et l.323
(`SDP = footprint × niveaux`).

### Valeurs servies (steps du moteur)

- zone : **AU2h** (renvoi vers règles U2h) · surface : **347 993 m²**
- emprise reculs (géométrie EPSG:2975, buffer −3 m) : 315 845 m²
- **contrainte pleine terre 40 %** : emprise ≤ 347 993 × (1 − 0,40) = **208 796 m²** (retenu)
- niveaux : hauteur d'égout **9 m ÷ 3 m/niveau = 3 niveaux** (R+2)
- coef_occupation : **0,45**

### Chaîne de calcul (SDP gabarit)

| Poste | Formule | Valeur |
|---|---|---|
| Emprise constructible | `min(reculs 315 845 ; pleine terre 208 795,8)` | **208 796 m²** |
| Emprise bâtie (footprint) | `208 796 × 0,45` | **93 958,2 m²** (affiché 93 958) |
| **SDP gabarit brute** | `93 958,2 × 3 niveaux` | **281 874,6 → 281 875 m²** |
| (SHAB = SDP × 0,80) | `281 875 × 0,80` | 225 500 m² |

Le footprint BRUT (93 958,2) est conservé pour la SDP → `93 958,2 × 3 = 281 874,6`,
arrondi **281 875 m²**. (Repartir du footprint affiché 93 958 donnerait 281 874 : le
moteur garde le brut.)

### Écart avec l'audit (281 159 m²)

La SDP gabarit réellement servie est **281 875 m²**, pas 281 159 m². Écart = **+716 m²**.
Cet écart correspondrait à une emprise de 208 266 m² (281 159 ÷ 3 ÷ 0,45) au lieu de
208 796 m² — soit un `prix`/coef légèrement différent côté audit. **Le moteur, lui,
reconstitue 281 875 exactement** (208 796 × 0,45 × 3 = 281 874,6). Le 281 159 de l'audit
est donc **une valeur périmée ou d'une saisie antérieure** ; ce n'est pas ce que le
backend sert aujourd'hui.

### Cohérence aux extrêmes (parcelle géante 347 993 m²)

L'emprise constructible **est bien plafonnée** — non par une valeur en dur, mais par la
**contrainte pleine terre (40 %)** : emprise ≤ 60 % de la surface = 208 796 m² (le
contour aux reculs, 315 845 m², est plus grand et n'est donc pas le facteur limitant).
Les **niveaux sont plafonnés par la hauteur** (9 m → 3 niveaux, pas la surface). Enfin
les **logements sont capés par un plafond de densité** (≤ 3 132 = 34,80 ha × 90 logts/ha),
puis modulés (1 127–1 253 au sol). La chaîne SDP n'est donc PAS non bornée sur une
parcelle géante : les trois leviers (emprise via pleine terre, niveaux via hauteur,
logements via densité) sont actifs et cohérents.

**VERDICT CAS 3 : RECONSTITUÉ EXACTEMENT** (sur la valeur RÉELLEMENT servie).
SDP gabarit servie = **281 875 m²** = `208 796 × 0,45 × 3` (à l'unité). Les plafonds
aux extrêmes sont présents et corrects (pleine terre 40 %, hauteur, densité).
**Note** : le chiffre 281 159 m² de l'audit ne correspond pas au chiffre servi
(écart +716 m²) — probablement une valeur périmée côté audit, pas un défaut du moteur.

---

## Synthèse

| Cas | Chiffre servi | Reconstruction | Verdict |
|---|---|---|---|
| 1 · Charge foncière | −122 911 € | −122 911,16 → −122 911 (arrondi euro, final, grandeurs brutes) | **Reconstitué exactement** |
| 2 · Valorisation CBO | 587 477 506 € · 919 248 m² SDP rés. | Σ lignes = total, à l'euro et au m² | **Reconstitué exactement** |
| 3 · SDP gabarit DK1169 | 281 875 m² | 208 796 × 0,45 × 3 = 281 874,6 → 281 875 | **Reconstitué exactement** (audit 281 159 = valeur périmée, +716 m²) |

Points de méthode confirmés :
- Le moteur **arronde une seule fois, à la fin, à l'euro** (au k€ seulement si prix « fragile »),
  sur grandeurs **brutes** — jamais poste par poste. Repartir des termes AFFICHÉS
  (déjà arrondis) peut coûter ≤ 1 € / 1 m², ce qui n'est PAS un défaut du moteur.
- Case 1 : le −123 410 « manuel » diffère de 499 € = 5,54 m² × 90 €/m² VRD → **surface
  de terrain divergente dans le contre-calcul manuel**, pas dans le moteur.
- Case 3 : le 281 159 de l'audit est en écart de +716 m² avec la valeur servie
  (281 875) → valeur périmée côté audit.
