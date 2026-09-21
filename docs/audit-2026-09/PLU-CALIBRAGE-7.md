# PLU-CALIBRAGE-7 — deux formes de règle que le schéma doit porter

**Date : 21/09/2026 · Branche : `feat/plu-calibrage-6` (à la suite de `d3036756`) · worktree `~/Desktop/labuse-plu6`.**
**Rien de mergé, aucun `residuel-serve`, rien de servi ne change.** `q_v11_m137` reste servi.

Décision Vic : on ÉTEND le schéma plutôt que d'acter ~8 471 « non calculable » sur des règles qu'on
sait lire (PLU-CALIBRAGE-6 §5). Deux formes sont ajoutées, les feuilles concernées validées, le
moteur les lit, l'impact est rejoué.

Livrables : ce rapport · `config/plu_destinations/974*.yaml` (22 feuilles passées `valide`) ·
`src/labuse/faisabilite/{zonage,engine}.py` (schéma + moteur) · `tests/test_plu_calibrage7_formes.py` ·
`qa/plu_calibrage7_appliquer.py` · `captures/plu-calibrage7/` (TABLE-22, SONDAGE-5, RELECTURE,
applied_log, impact7.py + impact_avant/apres).

---

## 1. Les deux formes ajoutées au schéma (`config/plu_destinations`)

Le schéma des feuilles `regles` accepte désormais **deux formes**, et **aucune autre** (pas
d'élargissement) :

### Forme 1 — recul « à l'alignement » / « en limite séparative » = recul 0 EXPLICITE

```yaml
retraits:
  voie:                       # (idem limites_separatives)
    min_m: 0
    forme: alignement         # marqueur : 0 est un recul RÉGLEMENTÉ, jamais « absent »
    article: "6.2"
    page_pdf: 110
    citation: "Les constructions devront être implantées à l'alignement."
    statut: valide
```

Lu par `zonage._recul_alignement` → `ZoneRules.recul_voirie_alignement` /
`recul_limites_alignement`. Le moteur (`engine.py`) prend **recul 0** et l'annonce sourcé (« recul
0 m, sourcé »), jamais l'hypothèse prudente par défaut. `forme: alignement` sur une feuille encore
`propose` déclenche toujours la non-calculabilité (garde PLU-CALIBRAGE-6 intacte).

### Forme 2 — pleine terre COMPOSÉE « X % d'espaces verts dont Y % de pleine terre »

```yaml
pleine_terre:
  pct:
    espaces_verts_pct: 30     # X — littéral au règlement
    pleine_terre_part: 50     # Y — littéral au règlement
    # pct dérivé = X × Y / 100 = 15 % : CALCULÉ par le moteur, JAMAIS stocké
    article: "Ua 11.1"
    page_pdf: 27
    citation: "…au minimum 30% de la superficie…éco-aménageables dont au moins 50% de pleine terre…"
    statut: valide
```

Lu par `zonage._pleine_terre_val` (calcule `X × Y / 100`) et `_pleine_terre_compose` (porte les deux
chiffres) → `ZoneRules.pleine_terre_pct` + `pleine_terre_compose`. Le moteur applique la contrainte
et **montre les deux chiffres sourcés** dans l'étape (« espaces verts 30 % dont 50 % de pleine terre
= 15 % »). Les deux chiffres passent la garde anti-invention (littéraux) ; le produit ne l'est pas et
n'est donc jamais gravé.

Le schéma **refuse toute autre forme nouvelle** : le seul cas restant hors de ces deux formes
(Saint-Pierre Uep, CES exprimé en « 20 m²/ha ») reste `propose` (cf. §5).

---

## 2. Feuilles validées / restées propose (méthode PLU-CALIBRAGE-5)

Deux agents internes (un par forme) ont relu chaque feuille au **règlement PDF authentique**, suivi
les renvois `1AU→U`, et retenu la citation littérale. **Relecture indépendante**
(`captures/plu-calibrage7/RELECTURE.json`) : **22 vérifiées, 22 accords, 0 désaccord**.

Sur les 23 `propose` numériques restées après PLU-CALIBRAGE-6 : **22 validées** (14 forme 1 + 8
forme 2) · **1 reste propose** (hors des deux formes). Table complète :
`captures/plu-calibrage7/TABLE-22.csv`.

### Forme 1 — 14 feuilles (recul 0 « alignement »)

Saint-Pierre Up (1 461 parc.), Ucv (906), Uazp (369), Uazpc (10) · Saint-Paul U4a (508), U3a (400),
U5a (234), U6a (214) · Le Port Ud *en limite* (386) · La Possession UAm (215) · Petite-Île UZ voie +
limites (131) · Saint-Joseph U1 (98) · Sainte-Marie 1AUb (26).
Exceptions relevées (RN/RD/ZAC/voies piétonnes) notées mais **non généralisées** — la règle générale
de zone est l'alignement, recul 0. La relecture a écarté le piège des zones-sœurs en « b »
(U3b/U4b/U5b/U6b) qui, elles, imposent un recul obligatoire de 3 m — les zones auditées en « a » sont
bien à l'alignement.

### Forme 2 — 8 feuilles (Le Port, pleine terre composée)

Uc (5 524 parc., 20 %×50 %), Ua (1 932, 30 %×50 %), Uca (117, 20 %×50 %), Us (61, 20 %×50 %),
1AUa (70, 30 %×50 %, renvoi→Ua), 1AUm (13, 20 %×50 %, article propre), 1AUc (6, →Uc), 1AUs (3, →Us).

### 1 restée `propose` (hors formes)

Saint-Pierre **Uep** `emprise_sol.ces` : le règlement fixe « 20 m² par ha » (densité surfacique
≈ 0,2 %), pas un CES en pourcentage. Aucune des deux formes ne la porte → reste `propose` (§6 : pas
d'élargissement). ~12 parcelles concernées (cf. §4, seul résiduel « règle non validée »).

**Sondage de 5 pour Vic** : `captures/plu-calibrage7/SONDAGE-5.md` (seed=7, 3 forme 1 + 2 forme 2),
chaque feuille avec valeur, article/page et citation verbatim.

Bilan statuts : `valide` 1897 → **1919** (+22) · `propose` 78 → **56** (= 55 non-numériques hors
mandat + Uep).

---

## 3. Moteur + tests

`engine.py` lit les deux formes : recul 0 « à l'alignement » (source dédiée, pas de défaut prudent) ;
pleine terre composée (étape montrant `X % dont Y % = Z %`). `tests/test_plu_calibrage7_formes.py`
(7 cas, verts) — un test dédié par forme (lecture + effet sur l'emprise) + un test que la garde
PLU-CALIBRAGE-6 reste active (une feuille de forme 1/2 encore `propose` → non calculable).

Non-régression : `test_plu_calibrage7_formes` + `test_plu_calibrage6_garde` +
`test_plu_calibrage2_branchement` + `test_faisabilite` + `test_plu_calibrage_lot2` +
`test_mn_faisabilite` + `test_prospect` = **63 verts** (sur le YAML appliqué). Aucune régression de
code (les échecs du sweep large sont tous « role labuse » de la base de test absente + le
`test_retours11f4` pré-existant, identiques à PLU-CALIBRAGE-6).

---

## 4. Impact rejoué (lecture seule, même méthode que PLU-CALIBRAGE-6 §4)

`captures/plu-calibrage7/impact7.py` — `compute_residuel` sur le MÊME échantillon reproductible
(id-ordonné, ≤40/zone) des 22 zones rendues non calculables par PLU-CALIBRAGE-6, avant (YAML formes
`propose`) et après (formes `valide`). Extrapolation par cause (taux échantillon × taille de zone) :

| cause du résiduel sur les 22 zones (12 696 parcelles) | AVANT (PLU-6) | APRÈS (PLU-7) |
|---|---:|---:|
| **regle_plu_non_validee** (« règle PLU non validée ») | **~12 696** | **~12** |
| calculable | 0 | ~8 471 |
| terrain_exigu (géométrie — NC réelle, indépendante) | — | ~3 746 |
| habitat_interdit (zone à vocation économique — NC réelle) | — | ~443 |
| redhibitoire | — | ~24 |

**Les ~8 471 parcelles que PLU-CALIBRAGE-6 avait passées « non calculable » sont TOUTES redevenues
calculables.** Le reliquat des 22 zones (~4 213) n'était PAS un problème de règle non validée : ce
sont des parcelles NC pour une cause RÉELLE (terrain trop exigu, habitat interdit) que le moteur
signalait déjà — la cause exacte apparaît maintenant que la zone se calcule (avant, elle était
masquée par `regle_plu_non_validee`).

**Retour à la ligne de base atteint** : la NC « règle PLU non validée » passe de **~12 696 à ~12**
(seule Saint-Pierre Uep, CES en m²/ha). L'excès de +~8 471 sur les 16 963 « zone non résolue »
constaté en PLU-CALIBRAGE-6 est résorbé.

**NC résiduelle « règle non validée »** : ~12 parcelles, Saint-Pierre Uep uniquement (CES m²/ha,
hors des deux formes).

---

## 5. Ce qui bloque encore avant `residuel-serve`

1. **Process frais obligatoire (lru_cache)** — inchangé : `_calibrage_overlay` et `_zonage_doc` sont
   en `lru_cache` à vie du process ; l'édition YAML de PLU-CALIBRAGE-6+7 impose que le prochain
   `compute-residuel --ile --new-run` tourne en **process neuf**.

2. **Résiduel « règle non validée » ramené à ~12 parcelles** (Saint-Pierre Uep, CES « 20 m²/ha »).
   Trois options pour Vic, à trancher (mineur, 12 parcelles) : (a) acter la NC (honnête) ; (b) modéliser
   la densité surfacique m²/ha comme un plafond d'emprise (une 3ᵉ forme — hors mandat ici) ; (c) laisser
   `propose`. Recommandation : (a)/(c) — 12 parcelles ne justifient pas une forme de schéma.

3. **Re-caler les bandes de score après le run** (rappel SCORING-5 §3) : les ~8 471 parcelles
   redevenues calculables porteront une SDP réelle → les bandes A/B/C/D sont à re-caler post-calibrage,
   sur témoins re-scorés.

4. **Chaîne inchangée** (SCORING-5-RETOUR §2) : `compute-residuel --ile --new-run "<label>"` (process
   frais) → comparer au run 2 → `residuel-serve <seq>` (geste Vic séparé). Rien de tout cela n'est fait
   ici.

## 6. Hors mandat (respecté)

Les 55 `propose` non-numériques · la mixité · une éventuelle 3ᵉ forme (m²/ha) · `residuel-serve` ·
tout merge · le scoring : non touchés.
