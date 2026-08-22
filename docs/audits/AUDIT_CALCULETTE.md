# Audit — outil « Calculette foncière » (M23). CONSTAT SEUL, aucune correction.

Endpoint `POST /modules/faisabilite/{idu}/charge` (`src/labuse/api/modules.py:949`) →
`compute_calculette` (`src/labuse/faisabilite/bilan.py:647`) → `compute_bilan`. Front :
`CalculetteFonciere.tsx` réutilise le composant `Calculette` de la fiche (`fiche/Fiche.tsx:652`).

## VERDICT EN UNE LIGNE
Outil HONNÊTE et JUSTE : SDP + prix + terrain sont sourcés (pas de legacy), le calcul est
EXACT (119 k€ = 118 627 vérifié) et c'est BIEN « le même calcul que la fiche » (même moteur,
même SDP, même prix neuf). Trois réserves : (a) le coût s'applique au PLANCHER (270 m² = 216÷0,8),
pas à la SDP vendable affichée (216) → un calcul « à la main » naïf donne ~256 k€, pas 119 ; (b)
le central s'affiche DEUX fois (doublon léger) ; (c) pas de VRD → ce n'est pas encore un vrai
bilan promoteur, et il double en partie le scoreur d'adresse.

---

## 1. Branchement

- **Tables** : `parcels` (`modules.py:968` — id, surface) + **`parcel_faisabilite`** (SDP, moteur
  déterministe) + **`resolve_prix_sortie_servi`** → `dvf_prix_sortie_neuf` (prix) + `sector_price`
  (comparables/fiabilité). **PAS scopé q_v10_m129** — et c'est normal : la calculette ne lit NI
  tier NI score ; c'est de la faisabilité déterministe + DVF, pas le run servi.
- **Ni `_q_v2_fiche` ni `_build_fiche`** : elle lit `parcel_faisabilite` EN DIRECT (la MÊME source
  que `fiche_payload`). Le défaut du comparateur ne s'applique pas ici.
- **« SDP vendable 216 m² »** : `parcel_faisabilite(...).fourchette["shab_vendable_m2"]`
  (`modules.py:972`) — capacité RÉELLE calculée (post rendement/plafond). Sourcé, pas legacy.
- **« prix de sortie bâti 4 730 €/m² »** : `resolve_prix_sortie_servi` (`modules.py:981`) → prix
  **NEUF** de `dvf_prix_sortie_neuf`. Préséance (`dvf_prix_neuf.py`) : override bassin sourcé >
  local secteur (section) > local commune > **REPLI ÎLE** (médiane marché) > **non calculable**
  (communes social-dominantes). **Local pour 5 communes seulement** (Saint-Denis, Saint-Pierre,
  Saint-Paul + 2) ; ailleurs = repli île. Le champ `prix_neuf_label` + `prix_neuf_repli_ile`
  DISENT lequel → honnête (jamais un local inventé). Donc « 4 730 » = soit un local (5 communes),
  soit la médiane île (selon le label servi).
- **« terrain 600 m² »** : `parcels.surface_m2` (`modules.py:968`) — contenance cadastrale, exacte.
- **Vestiges de matrice** : NÉANT (aucun q_score/opportunity/tier).
- **LIMIT caché** : NON (une parcelle à la fois, pas de cap).
- **Test « ne lève pas »** : PARTIEL. L'arithmétique est testée (`compute_calculette` pur,
  `tests/test_bilan.py::test_calculette_arithmetique_independante`). **Aucun test de l'endpoint**
  `/modules/faisabilite/{idu}/charge` (ni du succès, ni des branches `calculable:false` —
  capacité non résolue / prix non calculable).

## 2. La vérité du calcul

- **Formule** (`compute_bilan`, `bilan.py`) : `CF_central = CA×coef − SDP_plancher×coût − VRD`, avec
  `CA = SDP_vendable × prix_sortie`, `coef = 1 − (marge + honoraires + frais_fin)/100`, et surtout
  **`SDP_plancher = SDP_vendable ÷ coef_rendement`** (0,8 → ×1,25 ; `bilan.py:491`, M128-3).
- **« Le même calcul que la fiche » — VRAI.** `compute_bilan_servi` (fiche, `bilan.py:273`) et la
  calculette partagent : MÊME SDP (`parcel_faisabilite`), MÊME prix neuf (`resolve_prix_sortie_servi`),
  MÊME moteur (`compute_bilan`). Seule différence : la fiche prend les hypothèses résolues par
  secteur ; la calculette laisse SAISIR coût & marge. Même moteur, mêmes intrants sourcés. ✓
- **Prix de sortie DVF** : NEUF, maille **secteur (section) → commune** pour 5 communes, sinon
  **repli île** (médiane marché), sinon **non calculable** (social-dominant). Il ne couvre la
  parcelle localement QUE pour ces 5 communes ; ailleurs c'est le repli île, DIT par le label.
- **Le calcul à la main (capture : SDP 216 × 4 730, marge 21 %, coût 2 550 → 119 k€)** :
  - **servi = 118 627 € → « ~119 k€ » EXACT** (vérifié : `compute_calculette(216, 600, 4730, 2550, 21)`
    = central 118 627).
  - Détail : `CA = 216×4730 = 1 021 680` ; `×0,79 = 807 127` ; **construction = (216÷0,8=270) × 2 550
    = 688 500** ; `CF = 807 127 − 688 500 = 118 627`.
  - ⚠ **Le coût s'applique au PLANCHER 270 m², pas à la SDP vendable 216 affichée.** Un calcul naïf
    « 216 × 2 550 » donnerait CF ≈ 256 k€ — d'où l'écart apparent. Le résultat servi est JUSTE ; mais
    l'écran montre « SDP vendable 216 » sans dire que le coût porte sur 270 → non transparent pour
    qui refait le calcul de tête.
- **« ~119 k€ » affiché deux fois** : OUI, doublon léger. Le central apparaît (1) en GROS comme
  résultat principal (`principal`, `Fiche.tsx` num-key mint, `data-calc-cf`) ET (2) en petit dans
  « Détail — charge foncière calculé : {central} · fourchette … » (`data-calc-cf`). Quand le central
  est positif, `principal == central` → même nombre deux fois. La ligne « Détail » ajoute la
  fourchette (utile), mais répète le central. (En négatif, seul le verdict s'affiche — pas de doublon.)

## 3. Ce qui manque pour un vrai bilan promoteur

**Déjà en base, NON utilisé par la calculette :**
- **Prix terrain nu de la zone** (`marche_commune` `prix_terrain_nu_par_zone`, M79) — la référence
  MARCHÉ du foncier, absente : impossible de confronter la charge calculée au prix observé du terrain.
- **CA + comparables** : `compute_calculette` renvoie déjà `ca` (bas/haut) et les comparables
  VEFA/ancien (`_comparables`) — le front n'affiche que la charge. Data calculée, cachée.
- **VRD / pente / assainissement** : `compute_bilan` les gère (`maj_pente`, `maj_assain`,
  `cout_vrd_base`) mais la calculette les laisse à 0 (non calibré) → **le coût réel est sous-estimé**.
- **`score_e.prix_probable_foncier`** (référence foncier déjà calculée) — non montrée en regard.

**Manque vraiment pour un bilan promoteur :** VRD/viabilisation réaliste, frais financiers (défaut 0),
taxes (TA/redevances), phasage & actualisation dans le temps, analyse de sensibilité / scénarios,
et la fourchette CA + comparables SERVIES (elles sont calculées, masquées).

**Double emploi avec le scoreur d'adresse ? OUI, partiel.** Les deux dérivent le foncier du MÊME
moteur `compute_bilan` :
- **Scoreur** (`scoreur.py`) : entrée ADRESSE + prix demandé → CONSTAT (prix probable du foncier +
  écart + marge à ce prix), hypothèses FIXES (méthode documents), aucun réglage.
- **Calculette** : entrée PARCELLE + hypothèses SAISIES (coût, marge) → charge foncière OU
  **prix d'achat max** (mode `achat_max`).
- Le mode `achat_max` de la calculette ≈ le « prix d'achat max admissible » du scoreur. L'écart
  réel : le point d'entrée (adresse vs parcelle) et le fait de régler ou non les hypothèses.
  **Candidat à consolidation** (un seul moteur foncier, deux entrées) plutôt que deux outils qui
  répondent à la même question par deux chemins.

---

## Synthèse
| # | point | constat |
|---|-------|---------|
| 1 | source | SDP=parcel_faisabilite · prix=neuf DVF (5 communes local / repli île, DIT) · terrain=cadastre. Sourcé, pas legacy. Ni _q_v2_fiche ni _build_fiche. Pas de vestige, pas de LIMIT. |
| 1 | test | arithmétique OK ; **endpoint /charge non testé** (branches calculable:false comprises) |
| 2 | exactitude | **119 k€ = 118 627 EXACT** ✓ · « même calcul que la fiche » VRAI ✓ |
| 2 | transparence | le coût porte sur le PLANCHER 270 (=216÷0,8), pas sur les 216 affichés → calcul de tête trompeur |
| 2 | doublon | central affiché 2× (gros `principal` + petit « Détail … calculé ») |
| 3 | manque | VRD/frais fin./taxes ; CA+comparables déjà calculés mais masqués ; prix terrain nu zone non confronté ; **double emploi partiel avec le scoreur** (même moteur, achat_max ≈ prix achat max) |

Aucun défaut BLOQUANT (le chiffre est juste, honnête). Les leviers : transparence du coût-plancher,
retrait du doublon d'affichage, et — si tu veux en faire un vrai outil de bilan — surfacer le CA +
la fourchette + le prix terrain de zone, ajouter la VRD, et trancher le double emploi scoreur.
