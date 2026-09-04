# DIAGNOSTIC O2 — d'où sortent les nombres de « Faisabilité / Étudier un bien »

> Écrit AVANT toute ligne de code (exigence du mandat RETOURS-12, O2). Trace la chaîne de calcul
> exacte, fichier:ligne, et confirme/infirme l'hypothèse du mandat sur le prix saisi.
> Ancré sur une parcelle réelle : **97411000AB0060** (Saint-Denis, terrain 1 593 m²), appel réel
> `/scoreur-adresse` (prix demandé 500 000 €). La capture de Vic (−219 123 €, −135 €/m², 526 k€,
> 123 m²) est le MÊME calcul sur une parcelle plus petite ; les formules sont identiques.

## 1. Les 4 nombres de la capture — origine exacte

| Nombre (capture Vic) | Ce que c'est | Formule | Fichier:ligne |
|---|---|---|---|
| **123 m² vendables** | `shab_vendable_m2` — surface habitable vendable, sortie de la faisabilité (post-rendement, plafond de densité, modulation) | issu de `_q_v2_fiche` → `fourchette.shab_vendable_m2` | `scoreur.py:188` · `bilan.py:482,499` |
| **526 k€ CA visé** | `ca_central` — chiffre d'affaires potentiel | `CA = shab_vendable × prix_de_sortie_médian` (≈ 123 × 4 275) | `bilan.py:542` (`ca_cen = surf * _px(med)`) |
| **−219 123 €** | `charge_fonciere.central` — charge foncière supportable (bilan à rebours) | `cf = CA × coef − coût_construction − VRD` avec `coef = 1 − (marge + honoraires + frais_fin)/100` | `bilan.py:603-605` |
| **−135 €/m²** | `par_m2_terrain` — la charge ramenée au m² de terrain | `par_m2 = charge_centrale / surface_terrain` | `bilan.py:615` |

**Détail du bilan à rebours** (`bilan.py:603-605`) :
```
coef        = 1 − (marge_cible + honoraires + frais_financiers)/100     # ≈ 0,79 (défaut 21 %)
cc_bas/haut = sdp × coût_m2 × (1 + maj_pluvial)   ; sdp = shab_vendable / coef_rendement (≈ ÷0,8)
cout_vrd    = vrd_base_m2 × (1 + maj_pente+assain) × surface_terrain
cf_central  = CA × coef − (cc_bas+cc_haut)/2 − cout_vrd
```
**Pourquoi la charge est NÉGATIVE** : sur ces parcelles, `CA × coef` (≈ CA − 21 %) couvre à peine le
coût de construction, et la **VRD** (proportionnelle à la surface de TERRAIN, souvent grande) fait
basculer le solde sous zéro. La charge foncière admissible négative signifie « à ces hypothèses
génériques, un promoteur ne pourrait pas payer le terrain, même gratuit il perdrait de l'argent ».
C'est **arithmétiquement exact** mais **illisible** pour qui n'a pas posé ces hypothèses.

## 2. Vérification sur parcelle réelle (97411000AB0060, terrain 1 593 m²)

Appel réel `/scoreur-adresse` (prix 500 000 €), sortie servie :
```
constat.sourced      : shab_vendable 1 039 m² · sdp_plancher 1 299 m² · coef_rendement 0,8
                       prix_sortie_median 4 275 €/m² (« Estimé — médiane locale, 77 ventes »)
constat.charge_calibree : central −115 314 € · par_m2_terrain −72 €/m² · ca_central 4 441 725 €
prix.charge_fonciere_supportable_eur : −115 314 €
prix.marge_a_ce_prix_eur             : −615 314 €     ←  = charge (−115 314) − prix (500 000)
```
Les proportions sont identiques à la capture : `par_m2 = charge/terrain` (−115 314/1 593 = −72),
`CA = shab × prix_sortie` (1 039 × 4 275 ≈ 4,44 M€), `marge_a_ce_prix = charge − prix`.

## 3. CE QUE DEVIENT LE PRIX SAISI — hypothèse du mandat CONFIRMÉE

Le mandat suppose : « le bilan à rebours donne une charge foncière admissible négative, et le prix
demandé est ensuite SOUSTRAIT de cette charge, ce qui produit un déficit cumulé arithmétiquement
exact mais illisible ». **C'est exactement ce qui se passe.**

- Backend `scoreur.py:80` : `out["marge_a_ce_prix_eur"] = round(charge − prix)`
  → −115 314 − 500 000 = **−615 314 €** (dans la capture : −219 123 − 500 000 = **−719 123 €**).
- Front `EtudierBien.tsx:67` : `ecart = prix − chargeCourante` → 500 000 − (−115 314) = **+615 314 €**,
  rendu « Le prix demandé 500 000 € dépasse de 615 314 € ce que la charge supporte ».

Les deux disent la même chose (même magnitude) : **le prix saisi est mis en relation avec une charge
déjà négative**, si bien que l'utilisateur voit un « −719 k€ » (ou « dépasse de 719 k€ ») qui MÊLE
deux choses hétérogènes — un résultat d'opération négatif ET le prix du terrain — sans jamais dire
que le premier est le fruit d'hypothèses génériques qu'il n'a pas posées.

## 4. Le double-compte de surface (point 8 du mandat) — à trancher en O2

- L'écran lit `shab_vendable_m2` du CONSTAT servi (`_q_v2_fiche.fourchette.shab_vendable_m2`).
- Les exports (Dossier/Flash) passent par `compute_bilan_servi` / `bilan_params_defaut` — même
  `shab_vendable` en principe. Le « 123 vs 127 » signalé vient probablement d'un **arrondi/rendement
  appliqué à deux moments** (vendable affiché vs sdp_plancher = vendable ÷ 0,8). À vérifier et, si un
  recalcul en double existe, le supprimer (source unique). *(Vérification faite en O2.)*

## 5. Conclusion pour la refonte O2

1. **Premier niveau, sans argent** : ce que porte la parcelle (zone, SDP constructible, emprise,
   hauteur, nombre de logements plausible, ce qui est bâti, ce qui contraint). Descriptif, neutre —
   utile agence/notaire/particulier. AUCUN nombre négatif à l'accueil.
2. **Repères de marché à côté, jamais un verdict** : terrain nu de zone (`terrain_zone` = 485 €/m²
   ici, déjà servi), ancien/neuf du secteur, avec `n` et fiabilité.
3. **Second niveau, ouvert par un geste** (« analyser une opération sur cette parcelle ») : là
   seulement le bilan à rebours, la charge, la marge — APRÈS que l'utilisateur a posé ses hypothèses.
4. Le prix demandé est **comparé, jamais additionné** : « prix demandé 500 000 € · une opération
   pourrait en payer 0 € · écart 500 000 € ». Quand la charge est ≤ 0 : « à ces hypothèses, une
   opération de ce type ne dégage rien pour le terrain » — et **on ne descend pas plus bas** en
   soustrayant le prix (fini le « marge_a_ce_prix » négatif cumulé au premier niveau).
5. Un seul moteur (`compute_bilan`/`compute_calculette`), un seul vocabulaire, mêmes libellés écran +
   PDF FINANCIER (le second niveau EST le moteur du document financier).
