# OUTILS-P1-1 — Lot 3d, recette des captures lot3c

Étape 0 : `pwd`=labuse-outils, branche `fix/outils-p1-1`. L'arbre n'était pas « propre » — à cause de
l'extraction (captures committées supprimées + `PREUVE PREUVE/` et `PREUVE PREUVE.zip` ajoutés). Les
fichiers suivis ont été restaurés ; les dossiers `PREUVE PREUVE` (untracked) laissés tels quels. Pas de
merge, rien d'autre que cette liste. Tests au premier plan.

Captures cropées sur l'élément : `lot3d-<NN>-<outil>-<quoi>.png`.

## Les 6 points

| # | Point | État |
|---|-------|------|
| 1 | Assemblage : « 2 630 m² · dont 1 689 m² en zone constructible · 31 % hors zone » (1 689/2 630 = 64 %, pas 69 %) | **Fait.** Capture `lot3d-01-assemblage-horszone.png`. |
| 2 | Courrier : « MOUTOUSSAMY EMILE — au siège social déclaré » a l'air d'une personne physique | **Fait + rapport + garde.** |
| 3 | Scan : la tuile « 745 / 3 366 / 77 » déborde de sa case | **Fait.** Capture `lot3d-03-scan-tuile.png`. |
| 4 | Permis : la définition du dormant n'évoque pas « parcelle non bâtie » que le code exige | **Fait.** Capture `lot3d-04-permis-dormant-def.png`. |
| 5 | Assemblage (rapport seul) : l'assemblage (676 m²) donne moins qu'une de ses parcelles (734 m²) | **Rapport.** |
| 6 | Taxe : « close et couverte de plus de 1,80 m » → « sous une hauteur de plafond de plus de 1,80 m » ; capturer le « i » OUVERT | **Fait.** Captures `lot3d-06-taxe-i-open.png` (i ouvert) + `lot3d-06b-taxe-surface-wording.png` (libellé). |

---

### Point 1 — Assemblage : les 3 chiffres sortaient de 3 bases différentes

Ce que mesurait « 31 % » : c'était `100 × (1 − inset_uau / inset_total)` — la part **hors zone de la
géométrie INSETÉE** (après recul, union de toutes les zones ∩ U/AU). Or « 1 689 m² » était
`surface_union_DESSINÉE × part_constructible`, et « 2 630 m² » la **somme des contenances cadastrales**.
Trois bases ≠ → `1 689 / 2 630 = 64 %`, incohérent avec `1 − 31 % = 69 %`.

**Fix** (`assemblage.py`, `aggregate_assiette`) : les deux chiffres affichés décomposent désormais le
**MÊME total** (la surface cumulée) via la part constructible — `surface_constructible = surface_cumulée
× part_c` et `% hors zone = 100 × (1 − part_c)` → ils s'additionnent à 100 %. La surface constructible
géométrique interne (pour la SDP) est inchangée. Témoin, pair `97418000AO0368+AO0950` (= le cas montré) :
**« 2 630 m² · dont 1 820 m² en zone constructible · 31 % hors zone »** → 1 820/2 630 = 69,2 %, + 31 % ≈ 100 %.

### Point 2 — Courrier : MOUTOUSSAMY EMILE est une SARL, pas une personne physique

Forme juridique de « MOUTOUSSAMY EMILE » (SIREN 429764574) : **SARL** — catégorie juridique INSEE **5499**,
`nom_complet = « SARL MOUTOUSSAMY EMILE »`. C'est bien une **personne morale** (société qui porte le nom
d'une personne) ; le pli nominatif au siège est **correct**, aucune anomalie.

Règle demandée (entrepreneur individuel / personne physique = particulier → pli NON nominatif, jamais son
nom ni son adresse déclarée). **Combien de propriétaires sont dans ce cas : 0.** Mesuré sur
`parcelle_personne_morale ⋈ owner_enrichment` : **aucun** propriétaire de catégorie juridique **1000**
(entrepreneur individuel) ; 0 EI dans tout `owner_enrichment`. Le fichier DGFiP « personnes morales »
exclut par construction les personnes physiques. 3 039 propriétaires PM ne sont pas enrichis (pas de
SIRENE) mais restent des PM par construction du fichier.

**Garde défensive ajoutée** (`courrier_adressage.py`) : `resoudre_destinataire` lit `nature_juridique` ;
si = `1000` (EI), l'adressage bascule en **« À l'occupant »** (non nominatif). 0 cas aujourd'hui → aucune
sortie ne change ; la règle tient si un EI apparaissait un jour.

### Point 3 — Scan : la tuile composite tient dans sa case

La tuile « nus / bâtis / bâti non renseigné » affiche **trois** nombres (`745 / 3 366 / 77` pour la SIDR) ;
en `whitespace-nowrap text-[16px]` (comme les tuiles à un seul nombre) elle débordait. **Fix**
(`ModulePanel.tsx` M02) : cette tuile-là passe en `text-[12.5px] break-words` (les autres restent à 16 px
nowrap). Mesuré sur la SIDR (SIREN 310863592, 4 188 parcelles) : `scrollWidth == clientWidth` → **aucun
débordement**, la valeur tient dans la case quel que soit le propriétaire.

### Point 4 — Permis : la définition du dormant dit maintenant « terrain resté nu »

Le code exige bien une **parcelle non bâtie** (`permis_point_mort` : PC > 36 mois, sans DAACT, **parcelle
non bâtie au run** — `fiche_commune.py:354`, `modules.py:559`). La définition l'ignorait. **Fix**
(`ModulePanel.tsx`) : **« autorisés depuis plus de 3 ans, sans achèvement déclaré (DAACT), terrain resté
nu »**. (Le test `test_retours16_permis.py` reste vert : il vérifie la sous-chaîne « sans achèvement
déclaré (DAACT) », préservée.)

### Point 5 — Assemblage (676) < une de ses parcelles (734) : pourquoi, et pourquoi ce n'est pas un bug

Les deux chiffres viennent de **deux moteurs sur deux assiettes** :
- **« reconstruction 734 m² » (AO0368 seule)** = `sdp_max_seule_m2`, la SDP brute de la MEILLEURE parcelle
  **calculée seule**, sur sa propre assiette et son propre recul.
- **« Après démolition 676 m² » (assemblage)** = `sdp_terrain_libere_m2`, la SDP brute de l'**UNION** des
  géométries, ré-insetée sur le contour fusionné puis **bornée à la part en zone constructible** (U/AU)
  — règle NU-G-007, déjà dite à l'écran (« dont 1 820 m² en zone constructible · 31 % hors zone »).

Ici l'union est à **31 % hors zone** : la seconde parcelle (AO0950) est en partie hors U/AU et n'apporte
quasiment pas de surface bâtissable. Comme la SDP de l'union est bornée à l'intersection constructible et
que le recul est **recalculé sur le contour combiné**, la capacité de l'union retombe **juste sous** celle
de la meilleure parcelle seule (676 < 734). Ce n'est pas une régression : c'est la borne « part
constructible » qui s'applique, et l'écran le dit (part hors zone + « ⚠ parcelles non contiguës » sur le
cas 97401000). Reproduit en direct sur deux pairs : `97418000` → 676 < 734 ; `97401000` → 378 < 389.

### Point 6 — Taxe : « sous une hauteur de plafond de plus de 1,80 m » + « i » ouvert

**Fix** (`TaxeAmenagement.tsx`) : « Surface close et couverte **de plus de 1,80 m** » →
« Surface close et couverte, **sous une hauteur de plafond de plus de 1,80 m** — garages et annexes
INCLUS. ». Captures : `lot3d-06b-taxe-surface-wording.png` (le libellé) et `lot3d-06-taxe-i-open.png`
(le « i » Méthode et sources OUVERT : valeur forfaitaire hors IDF 892 €/m², CGI art. 1635 quater A,
source service-public.gouv.fr — le « i » ne répète pas la définition de surface, qui vit en clair sous le
champ).

---

## Tests (au premier plan)

`npx tsc -b` 0 · `npx vitest run` **326** · `pytest -m "not db and not local and not reel and not network"`
**3273 passed, 49 skipped** · `scripts/ci/coherence_run.sh` **7 passed** · `scan_secrets.sh` rien trouvé.

Fichiers touchés : `assemblage.py` (pt 1), `courrier_adressage.py` (pt 2), `ModulePanel.tsx` (pt 3, 4),
`TaxeAmenagement.tsx` (pt 6). Point 5 = rapport, aucun code.
