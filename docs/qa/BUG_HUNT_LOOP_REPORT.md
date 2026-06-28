# LABUSE — Boucle QA/fix « bug hunt » jusqu'à 0 P0/P1/P2

> Boucle structurée CLIENT → DEVOPS → FIX → RETEST, **lecture seule** sauf 1 correction config
> petite/testée. `/enrichment` aborté en QA (0 écriture). Rédigé le 2026-06-28 sur base `ec7949a`.
> **Convergence en 1 itération.** DB métier vérifiée inchangée (`431663 / 9103 / enrichment 27`).

## Verdict final : ✅ GO démo/vente

Sur la matrice testée (24 communes × routes × calques × responsive × états × erreurs), **0 bug P0,
0 P1, 0 P2 reproductible** après correction. **487 tests verts**, QA multi-commune verte, DB intacte.
Reste un backlog **P3** non bloquant (cf. §6).

---

## 1. Itérations

**1 seule itération** : la passe CLIENT a trouvé **1** bug reproductible (P2), corrigé (config-only)
et **retesté vert**. Aucun nouveau P0/P1/P2 au retest → **STOP**.

## 2. CLIENT — couverture & bugs trouvés

**Couverture (toute verte sauf BUG-L1) :**
- **24 communes** : sélection, badge, stats (KPI = DB), **anti-stale 24/24** (idu préfixé INSEE),
  Radar sidebar + calque, fiche, console — bascules < 5 s. (sweep `client_qa_24`)
- **Routes** : 29 GET sûrs → **tous 200** ; erreurs **404/422 toutes correctes** (idu/commune
  inconnue, niveau/limit invalides…). (sweep `client_qa_routes` — « ANOMALIES : AUCUNE »)
- **Calques** : bâti (mutabilité, 51129 ratios), permis (1985), Radar (153) — OK.
- **Fiche / accordéon / export / shortlist / pipeline (lecture)** — OK.
- **Responsive** 390 / 768 / 1440 : **0 overflow**, **0 pageerror** ; sélecteur atteignable (onglet
  « Liste » sur écrans compacts).
- **États vides** : Saint-Philippe (0 éval) → Radar vide + carte vide propres, **pas de crash**
  (BUG-MC1 déjà corrigé), badge « Non évaluée » correct.

**Bug reproductible trouvé :**

| ID | Sév | Rôle | Commune | Reproduction | Attendu | Observé |
|---|---|---|---|---|---|---|
| **BUG-L1** | **P2** | config | Saint-Leu | sélectionner Saint-Leu | badge cohérent | badge **« Non évaluée »** alors que **976 opportunités** affichées (+ radar plein) |

## 3. DEVOPS — triage & décisions

- **BUG-L1 (P2, config)** → **À CORRIGER**. Cause : `config/communes_gold_standard.yaml` classait
  Saint-Leu `partiel_non_evalue` (comme Saint-Philippe, réellement non évalué) avec `eval_pct: 0`,
  **stale** : Saint-Leu a depuis été **évalué** (22959/22959 parcelles, 976 opp). Correctif :
  `etat → partiel_evalue`, `eval_pct → 100`. **Sûr** : c'est de l'INFORMATION (cf. `communes.py`),
  PAS une donnée métier / verdict / scoring ; `reliable` reste **False** (non-gold → garde-fou
  commercial intact). 1 ligne, testable.
- **Faux positif auto-flag** : le sweep n'avait pas levé BUG-L1 (comparaison de casse « Non évaluée »
  vs DOM « NON ÉVALUÉE ») — **détecté à la relecture humaine** du tableau. Corrigé manuellement.
- **Hors périmètre / refusé** : aucune correction risquée. Pas de dérivation `etat` depuis la DB
  (changerait `communes.py` lecture-seule en accès DB — refusé).

## 4. FIX (config) & tests

- `config/communes_gold_standard.yaml` — Saint-Leu `partiel_non_evalue → partiel_evalue`, `eval_pct
  0 → 100`. **Aucun code frontend/backend modifié** (l'UI affichait déjà fidèlement le badge).
- `tests/test_communes_gold_standard.py` — nouveau test `test_saint_leu_classee_evaluee_pas_non_evaluee`
  (badge cohérent, `reliable=False` préservé, Saint-Philippe inchangé).

## 5. RETEST (CLIENT) — vert

- **Saint-Leu badge = « Partielle »** (était « Non évaluée »), opp=976 cohérent ; fiche ouvrable.
- Saint-Philippe = « Non évaluée » (inchangé, 0 opp) ; Cilaos = « Partielle » ; Saint-Paul = « Gold ».
- **0 erreur console.** Multi-commune toujours OK.
- `screenshot : retest_saint_leu.png`.

## 6. Bugs restants (backlog P3 — non bloquants, acceptés)

| # | Sujet | Pourquoi P3 |
|---|---|---|
| 3 | Auth OFF en `env=local` | hygiène **déploiement** (fail-closed en prod), pas un bug runtime démo |
| 5 | `/map/bati` ~11 s | lazy / non bloquant |
| 9 | `app.py` monolithe | dette technique, pas un bug |
| 12 | Liste `/mutation` froide ~4,7 s | mémorisée ensuite ; décision perf produit |
| 14 | Sidebar « à surveiller » = prioritaire/forte | nécessite pool élargi (perf) |
| — | Sélecteur derrière l'onglet « Liste » (mobile/tablette) | by-design responsif ; fonctionne |

Aucun ne bloque démo, usage, ni sécurité.

## 7. Tests / QA / DB

- **pytest : 487 passés** (+1 coherence test BUG-L1). `node --check app.js` OK.
- QA : 24 communes vertes, routes 200 + erreurs 404/422, calques, responsive, états vides, retest.
- **DB métier inchangée** : `parcels=431 663`, `opportunités=9 103`, `parcel_enrichment=27` (intact —
  `/enrichment` aborté en QA). Aucune écriture, aucune migration, aucun re-cascade.

## 8. Screenshots

- `retest_saint_leu.png` — Saint-Leu après fix (badge « Partielle », 976 opp cohérents).
- `check_768_selector.png` — sélecteur 24 communes atteignable à 768 px.

## 9. Conclusion

> **LABUSE est prêt pour la démo / vente.** La matrice testée est **verte** : 0 P0, 0 P1, 0 P2
> reproductible. Le seul bug trouvé (badge Saint-Leu) est corrigé et retesté. Multi-commune,
> Radar Mutation, carte, fiches, exports, responsive, erreurs : tout fonctionne, 0 erreur console,
> DB intacte. Backlog P3 documenté, non bloquant. **GO.**
