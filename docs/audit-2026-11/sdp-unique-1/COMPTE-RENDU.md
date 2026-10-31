# SDP-UNIQUE-1 — compte-rendu

**Mandat.** Deux notions de SDP, deux noms, partout : « SDP restante, bâti conservé » et « SDP sur
terrain libéré ». Une source unique par notion, jamais « SDP » tout court. Branche `fix/sdp-unique-1`,
worktree `~/Desktop/labuse-sdp`, ports 9120/6320. **Aucun merge, aucun accès prod.** Base locale
`labuse` (Mac), run servi q_v20.

**Fil rouge du résultat.** Le gros de l'alarme de l'audit AUDIT-NU-1 (SDP contradictoire) était un
**artefact du socle Mac** : le Mac servait le run résiduel **legacy 1** pendant que le scoring était en
q_v20. Une fois le Mac aligné sur la prod (étape 0), l'en-tête, le verdict et le scoring **coïncident**.
Le code implémentait déjà, pour l'essentiel, les deux notions et la source unique (vocabulaire
`perimetres.ts`, `ST_Union` du bâti depuis ORACLE-FIX-1, scoring qui LIT la vue résiduelle). Restaient
de **vrais trous ciblés**, corrigés ici, et un **test de cohérence** qui verrouille la notion unique.

---

## Étape 0 — aligner le Mac sur la prod (base locale seulement)

Geste minimal et réversible (`sql/etape0_bascule_run17.sql`, backup `sql/residuel_runs_AVANT.csv`,
restauration `sql/etape0_restauration.sql`) : le Mac servait le run 1 (label `servi`, `assiette_source`
NULL sur 431 663/431 663) ; les **données** du run 17 q_v20 étaient déjà dans `parcel_residuel_runs`
(433 229 lignes, **168 106 NULL = 38,80 %**, identique à la prod), seule la métadonnée `residuel_runs`
et le pointeur `is_served` manquaient. Bascule : enregistrer le run 17 + flip `is_served` 1 → 17.
Après : la vue `parcel_residuel` sert le run 17, **comme la prod** (38,80 % NULL).

**Les 38,8 % d'assiette vide du run 17 — attendu.** Les 168 106 lignes `assiette_source` NULL sont
exactement les parcelles **non constructibles** : `terrain_exigu` (64 757), `zone_non_constructible:*`
(A/N/…, ~83 000), `zone_non_resolue:*` (~10 800), `hors_plu` (4 255), `habitat_interdit`, `redhibitoire`,
`surface_incertaine`, `hauteur_indispo`. Le moteur (`residuel.py:119-147`) court-circuite **avant** de
calculer une assiette dès qu'il n'y a rien à construire : SDP = 0 (ou NULL pour `hors_plu`). L'assiette
n'est renseignée que sur les 265 123 parcelles qui atteignent le calcul d'enveloppe (gabarit 211 200 /
legacy 53 923). Ce n'est pas un trou de calcul, c'est la réponse « parcelle non constructible ».

**Re-mesure A-001 / E-001 / E-013 (12 témoins lot A + 25 au hasard + masse 433 229).** Détail dans
`etape0-remesure.md`. Après bascule, les trois sources de SDP résiduelle coïncident :

| comparaison | avant (audit, Mac run 1) | après étape 0 | classement |
|---|---|---|---|
| **E-013** `potentiel_sdp_m2` (scoring) vs résiduel | 48 % divergent | **0 / 433 229 (0,000 %)** | **artefact run 1 (100 %)** |
| **A-001/E-001** en-tête vs verdict, contradictions de magnitude | 850↔0, 0↔92, 444↔461… | **disparues** (remesure témoins) | **artefact run 1** |
| **A-001/E-001** résidu | — | **12 017 (2,774 %)** gap 0-vs-NULL sur parcelles non constructibles (`zone_non_resolue`, `surface_incertaine`…) : résiduel écrit 0, score_labuse écrit NULL — **les deux disent « rien »** | **vrai, mineur** ; fermé par la réconciliation d'affichage + le test |

Les 12 témoins : 10 servables coïncident (AB0785 0/0/0, IE0241 92/92/92, HC0139 84, EY0173 461,
AM0893 73, HN0074 17, IN0347 0, AE0050 196 ; AO0753/AB0133 non constructibles 0 ; DR0042/BI0076 hors
sujet). Captures faithful AVANT/APRÈS AB0785 & IE0241 dans `captures/` (voir `AVANT-APRES.md`).

---

## Corrections (sur ce qui reste vrai après l'étape 0)

| Constat | État avant correction (code HEAD) | Correction | Preuve |
|---|---|---|---|
| **E-003** un seul chemin d'assiette servi | Déjà vrai : le run servi porte **une** valeur par parcelle (gabarit, legacy en repli) ; fiche/score/Comparer servi lisent cette valeur. L'audit construisait la divergence en appelant `clippee=True` vs `False` sur la même parcelle. | **Verrouillé** : Comparer lit désormais la SDP résiduelle de la fiche **servie** (`qv2.potentiel_transformation`), plus un recalcul live divergent. | recette (comparer == en-tête) |
| **E-005** bâti unionné, plus de somme | Déjà vrai : `bati.stats_batch` (bati.py:119) et `emprise_bati_bdtopo_m2` font `ST_Union` **avant** `ST_Area` (ORACLE-FIX-1, 2026-10-04, antérieur au run 17). Aucune somme sans union ne subsiste dans le chemin bâti/résiduel/scoring. | Commentaire périmé corrigé (bati.py disait encore « SUM sans union »). | recompute 200 parcelles = run (0 écart) |
| **E-004 / E-052 / A-010** une seule emprise bâtie, CoSIA distinct | Déjà vrai : `le_bien` sert **une** emprise (BD TOPO unionnée) ; CoSIA servi À PART (« Bâti détecté (CoSIA) — non cartographié BD TOPO », « Part imperméabilisée % », « Couverture du sol · CoSIA 20 cm ») ; `surface libre` = contenance − BD TOPO, montrée à côté de « Part imperméabilisée ». Le MAX(BD TOPO, CoSIA) du scoring est interne, jamais servi comme emprise client. | — (vérifié, rien à changer) | payloads le_bien AB0785/IE0241 |
| **E-007** hauteur supposée R+1 signalée | **Trou** : le run stocke `hauteur_source` ('lidar'/'bdtopo'/'sans') mais la fiche ne la servait pas. | L'en-tête sert `hauteur_bati_source` + `hauteur_bati_supposee` (vrai seulement si `hauteur_source='sans'` ET un bâti est déduit, `taux_emprise>0`) + une ligne ambre « Hauteur du bâti supposée R+1 — SDP restante à confirmer ». | AV1247 → supposée=True+note ; IE0241 (lidar) → False |
| **E-013** SDP du scoring = même source que la fiche | Déjà vrai : `scoring/p_v2/potentiel.py:110` **LIT** `parcel_residuel` (la vue servie), ne recalcule pas. | — (vérifié : 0 écart sur 433 229) | masse E-013 |
| **C-001 / D-042** deux libellés partout, jamais « SDP » nu | Comparer, `comparatif.py`, page de garde Dossier, tuile fiche + infobulle : **déjà** « bâti conservé » / « terrain libéré » (`perimetres.ts`). **Trous** : (a) Assemblage affichait « SDP » nu ; (b) « Estimer un bien » (9ᵉ doc) hors du harnais `docs_coherence`. | (a) Assemblage qualifié `· terrain libéré` (`PERIM_POTENTIEL_COURT`), ligne par bien + tuile cumulée ; (b) `/analyse-annonce` ajouté à `docs_coherence.documents()`. | vitest ; `test_docs_coherence_couvre_estimer` |
| **A-001 résidu** (découvert à la recette) | **Trou réel** : 6 659 parcelles (1,5 %) où `parcel_residuel.sdp > 0` mais le scoring les ÉCARTE (`hors_classement` : forêt publique / DPF inacquérable). Le verdict servait « aucune SDP », l'en-tête, Comparer et le PDF Estimer montraient encore la valeur (ex. AE0050 196 vs ∅). | L'en-tête, Comparer et le PDF Estimer **défèrent** désormais à l'écartement du scoring (lecture gardée de `score_labuse.cause`) : « aucune SDP exploitable » d'une seule voix. | recette AE0050 ∅/∅/∅/∅/∅ |

Fichiers touchés (7, chirurgical, +98/−12) : `api/app.py` (en-tête : `hauteur_source`/flag E-007 +
réconciliation écartement scoring ; Comparer lit la fiche servie), `bati.py` (commentaire),
`pige/api.py` (PDF Estimer défère), `frontend/{Fiche.tsx, moteurs.tsx, lib/types.ts}`,
`scripts/docs_coherence.py`.

---

## Nouveau run ? — NON, les valeurs du run ne bougent pas

Les corrections ne touchent **pas** la math de `compute_residuel` : elles exposent des colonnes déjà
écrites (`hauteur_source`) et réconcilient l'**affichage** (déférer à `score_labuse.cause`). Chiffrage
(recompute live `clippee=True` vs run 17 servi) : **0 écart sur 200 parcelles** (+ 36 témoins/aléatoires),
magnitude > 1 m² = 0. Le run servi est déjà cohérent avec le moteur HEAD. **Aucun nouveau run, aucun
déploiement de données à décider.** (Si une correction FUTURE touchait le calcul, le même chiffrage
dirait combien de parcelles bougent, et le run neuf serait produit en local, non servi en prod.)

---

## Recette

- **Test de cohérence** `scripts/sdp_coherence.py` (+ `tests/test_sdp_unique_coherence.py`) : compare,
  sur les 12 témoins, la SDP résiduelle « bâti conservé » de **l'en-tête, du verdict, de Comparer, du
  PDF Dossier et du PDF Estimer** ; échoue au moindre écart (une valeur positive qui diffère, ou une
  source qui dit « rien » quand une autre affiche un positif). **Résultat : vert** — 11 témoins servables
  cohérents (`recette-sdp-coherence.txt`), DR0042 (disparue, 500 — artefact Mac connu, table
  `parcel_cadastre_remplacement` présente en prod per PROD-VERIF-1) traitée proprement.
- `tests/test_sdp_unique_coherence.py` : garde unitaire D-042 (hook) + invariant `reel` DB (en-tête
  réconciliée == verdict ; donnée brute résiduel == `potentiel_sdp_m2`). **2 passed.**
- **Captures AVANT/APRÈS** AB0785 & IE0241 : synthèse versionnée `AVANT-APRES.md` (JSON bruts sur
  disque dans `captures/`, non versionnés — politique MENAGE-1) : 850↔0 → 0=0 ; 0↔92 → 92=92.
- **Hook vert** (composants joués à la main, base locale) : secrets `rien trouvé` · front `tsc -b` 0,
  `vitest` **305/305**, `vite build` OK · python unitaires **2758 passed** (0 échec ; les 2 régressions
  introduites par le 1ᵉʳ jet — `score_labuse` absente des fixtures — corrigées par lecture gardée).

---

## Garde-fous respectés

Aucun merge, aucun accès prod, aucune CLI mutante. Seules écritures base locales : la bascule du
pointeur servi (étape 0, réversible, backup + restauration fournis) et les caches de lecture
idempotents de l'API (`fiche_cache`, `comparateur_raw_cache`, vidés comme au déploiement). Recomputes
de contrôle sous `default_transaction_read_only=on`. État final : run 17 q_v20 servi.
