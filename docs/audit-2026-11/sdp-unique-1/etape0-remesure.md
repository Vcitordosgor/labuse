# SDP-UNIQUE-1 — Étape 0 : alignement Mac/prod + re-mesure

## Geste (base locale seulement, réversible)

Avant : le Mac servait le run résiduel **legacy 1** (`residuel_runs.is_served`, label `servi`,
aucune date, `assiette_source` NULL sur 431 663/431 663). Les DONNÉES du run 17 q_v20 étaient
déjà présentes dans `parcel_residuel_runs` (433 229 lignes, 168 106 NULL = **38,80 %**, chiffre
identique à la prod) ; seul le pointeur `is_served` et la métadonnée `residuel_runs` manquaient.

Bascule appliquée (`sql/etape0_bascule_run17.sql`) : enregistrer la métadonnée du run 17 + flip
`is_served` 1 → 17. Restauration prête (`sql/etape0_restauration.sql`). Backup de l'état avant :
`sql/residuel_runs_AVANT.csv`.

Après : la vue `parcel_residuel` sert le run 17 q_v20 (38,80 % `assiette_source` NULL), **comme la prod**.

## Les 38,8 % d'assiette vide du run 17 — quelles parcelles, est-ce attendu

168 106 / 433 229 lignes ont `assiette_source` NULL **et** `hauteur_source` NULL. Ce sont
exactement les parcelles pour lesquelles le moteur n'a **pas** calculé d'assiette (enveloppe
bâtissable) parce qu'il n'y a rien à construire. Ventilation par `cause` :

| famille de cause | nb | SDP écrite |
|---|---:|---|
| `terrain_exigu` | 64 757 | 0 |
| `zone_non_constructible:*` (A, N, Nco, Npnr, APF, Acu…) | ~83 000 | 0 |
| `zone_non_resolue:*` (A/N hors YAML calibré) | ~10 800 | 0 |
| `hors_plu` (réellement inconnaissable) | 4 255 | **NULL** |
| `habitat_interdit:*`, `surface_incertaine`, `redhibitoire`, `hauteur_indispo` | reste | 0 |

Vérifié : `assiette_source=NULL ⇒ sdp_residuelle_m2 ∈ {0 (163 851), NULL (4 255 = hors_plu)}`,
`pos_sdp = 0`. Le code (`faisabilite/residuel.py:119-147`, `compute_residuel` → `_cause_indisponible`)
court-circuite AVANT le calcul d'assiette dès que la parcelle n'est pas constructible : l'assiette
n'est renseignée que sur les 265 123 parcelles qui atteignent le calcul d'enveloppe (`gabarit`
211 200 / `residuel_legacy` 53 923). **C'est donc ATTENDU** : les 38,8 % « vides » sont les parcelles
non constructibles (zones A/N, terrains exigus, hors PLU), pour lesquelles la SDP résiduelle est 0
(ou NULL quand la zone est inconnue) et où il n'y a pas d'enveloppe à mesurer.

## Re-mesure A-001 / E-001 / E-013 (12 témoins lot A + 25 parcelles au hasard)

Trois sources de SDP comparées après bascule :
- `parcel_residuel` (vue, run 17 q_v20) — lue par l'**en-tête** de la fiche (A-001/E-001) ;
- `score_labuse` run `q_v20` — lue par le **verdict LABUSE** (A-001/E-001) ;
- `parcel_p_score_v2.potentiel_sdp_m2` run `q_v20` — SDP du **scoring** (E-013).

### 12 témoins du lot A

Les trois sources **coïncident exactement** sur les 10 témoins servables (AB0785 0/0/0,
IE0241 92/92/92, HC0139 84/84/84, EY0173 461/461/461, AM0893 73/73/73, HN0074 17/17/17,
IN0347 0/0/0, AE0050 196/196/196 ; AO0753 et AB0133 non constructibles 0 ; DR0042/BI0076 hors sujet).

Rappel des contradictions rapportées par l'audit (Mac servant le run 1) :

| témoin | audit en-tête (run 1) | audit verdict (q_v20) | après étape 0 (en-tête = verdict = scoring) | verdict |
|---|---:|---:|---:|---|
| AB0785 multi-bâti | 850 | 0 | **0 = 0 = 0** | **artefact run 1** |
| IE0241 maison | 0 | 92 | **92 = 92 = 92** | **artefact run 1** |
| HC0139 copro | 0 | 84 | **84 = 84 = 84** | **artefact run 1** |
| EY0173 grande | 444 | 461 | **461 = 461 = 461** | **artefact run 1** |
| AM0893 zone AU | 69 | 73 | **73 = 73 = 73** | **artefact run 1** |

### 25 parcelles au hasard (`id % 97 = 13`)

23/25 : les trois sources coïncident. 2/25 (`zone_non_resolue:N`/`Nerl`) : `parcel_residuel`=0,
`score_labuse`=NULL, `potentiel_sdp_m2`=0 — même gap 0-vs-NULL décrit ci-dessous.

### Masse (433 229 parcelles)

| comparaison | diffèrent | % |
|---|---:|---:|
| `parcel_residuel` vs `score_labuse` (A-001/E-001) | 12 017 | **2,774 %** |
| `parcel_residuel` vs `potentiel_sdp_m2` (E-013) | **0** | **0,000 %** |

## Classement des constats

- **E-013 (« SDP du scoring périmée, 48 % ≠ résiduel ») → ARTEFACT RUN 1 (100 %).**
  Après bascule, `potentiel_sdp_m2` == `parcel_residuel` sur **les 433 229 parcelles** (0 écart).
  Les 48 % venaient uniquement de ce que le Mac servait le run 1 pendant que le scoring était q_v20.

- **A-001 / E-001 (« deux SDP contradictoires dans la même fiche ») → ARTEFACT RUN 1 pour les
  contradictions de MAGNITUDE** (850/0, 0/92, 444/461 : toutes disparues). **Résidu VRAI, mineur :**
  un gap **0-vs-NULL** sur 12 017 parcelles (2,774 %), toutes non constructibles ou en zone non
  résolue (`zone_non_resolue:A/N` 10 394, `surface_incertaine` 1 586, `hauteur_indispo` 34) :
  `parcel_residuel` écrit **0**, `score_labuse` écrit **NULL**. Pas une contradiction de valeur —
  les deux disent « rien à construire ». Ce résidu persiste aussi en prod (deux écritures séparées
  du même run) : c'est lui que la correction E-013/source-unique et le test de cohérence ferment.

**Conclusion :** l'essentiel de A-001/E-001/E-013 était un **artefact du socle Mac** (run 1 servi).
Ce qui reste vrai et à corriger : garantir **structurellement** que l'en-tête, le verdict et le
scoring lisent la **même** source de SDP (sinon un futur run pourra re-désynchroniser), et fermer
le gap 0-vs-NULL. C'est l'objet des corrections ci-après et du test de cohérence de la recette.
