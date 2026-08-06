# M33 — BILAN (Mode B : réhabilitation du bâti existant, 24/24 communes)

**Branche `m33-mode-b-rehabilitation`** · base `main` 2097ad68 (post-M36) · commits `[M33-P0/P1/P2]`
+ vérification. **Aucun tier touché, aucune écriture sur le run servi ou le cache scoring,
rien de persisté par le paramètre client.** Golden **117/117** de bout en bout.

## Population retenue (arbitrage Vic 06/08, post-P0)

**Les 2 tiers déclassés bâti = 33 958 parcelles** (saturé 29 907 + révélé 4 051 — la bande
adjudication CoSIA 20-40 m² des « 8 031 » M32 n'est PAS déclassée, correction actée).
Zone PLU **informative** (jamais un critère ABSENT — une réhabilitation n'exige pas de droit
à construire). Hors population (servies, écartées, autres déclassées) : `disponible=False`
motivé, AUCUN panneau — jamais un mode B sur une parcelle classée.

## Comptes P0 (mesurés, requêtes au rapport `M33_P0_CONSTAT.md`)

| | Saturé | Révélé |
|---|---:|---:|
| Total | 29 907 | 4 051 |
| Emprise ≥ 20 m² (par construction) | 100 % | 100 % |
| Prix de sortie bâti local (secteur n≥3 → repli commune) | 100 % | 100 % |
| Niveaux RÉELS BD TOPO (Sourcé) | 28 332 (94,7 %) | 1 232 (30,4 %) |
| Zone PLU connue (informative) | 29 218 | 4 000 |

ABSENT réel dans la population servie : **0** (mesuré) — la branche ABSENT du moteur reste
en place (défensive, verrouillée par test).

## Mesure Q6 — close (arbitrage : v1 = zéro reclassement)

Le SIGNE du bilan au paramètre par défaut ne dépend QUE du prix local (positif ⟺ prix >
travaux/0,79 ≈ 1 899 €/m² à 1 500) — c'est un test de MARCHÉ, pas de parcelle (travaux et CA
tous deux ∝ SHAB). Comptes complets au rapport P0 (ex. : 180 325 écartées « positives » à
1 500 = la carte des marchés > ~1 899 €/m², PAS des opportunités).
**Conclusion consignée (Vic)** : tout futur mode B CLASSANT exigera une dimension
parcellaire discriminante — prix d'acquisition observé, état du bâti. Rien en v1.

## Formule (documentée, briques mode A)

```
SHAB réhabilitable = emprise bâtie × niveaux existants ÷ 1,15
  emprise  : p_model_bati = max(BD TOPO éd. 2026-06-15, CoSIA PVA 2025)   [Sourcé]
  niveaux  : POINT UNIQUE residuel._niveaux_existants — étages/hauteur BD TOPO [Sourcé]
             sinon placeholder 1 niveau (prudent, minore)                  [Estimé]
  1,15     : coefficient plancher→habitable, convention mode A

prix d'achat max réhab = SHAB × prix_sortie × coef_CA − SHAB × travaux
  prix_sortie : médiane DVF maison/appartement, préséance SECTEUR (n≥3) → COMMUNE
                (repli étiqueté — 338 parcelles concernées, mesuré P0)     [Sourcé DVF]
  coef_CA     : 1 − marge 9 % − frais 12 % = 0,79 (Hypotheses, mode A)     [Estimé conv.]
  travaux     : PARAMÈTRE CLIENT — défaut 1 500 €/m², bornes 500-4 000
                (clampées serveur), jamais persisté                        [ESTIMÉ]
```

**Héritage d'étiquette STRICT** : le résultat est TOUJOURS **Estimé** (le paramètre travaux
l'est par nature — aucune source Réunion fiable, cadrage acté). Assumé au libellé :
« jamais un prix Sourcé : l'hypothèse travaux est toujours estimée ».

**Valeurs par défaut et justification** : 1 500 €/m² = milieu de la fourchette qualitative
1 200–2 000 (cartographie P0, aucune source quantitative) ; bornes 500–4 000 = amplitude
état léger → réhabilitation lourde. La sensibilité du parc au choix est chiffrée au rapport
P0 (seuils de marché 1 519 / 1 899 / 2 532 €/m²).

## Surfaces livrées

- **Fiche web** : tiroir « Mode B — Réhabilitation » en BAS de pile — le verdict/tier M34
  reste premier à l'écran (captures 1-3). Étiquettes PAR LIGNE : emprise Sourcé (source
  affichée), **niveaux Sourcé/Estimé visibles par parcelle** (exigence 2), prix Sourcé DVF
  avec niveau de préséance, travaux ESTIMÉ ajustable (recalcul `/parcels/{idu}/mode-b`,
  état d'UI). **Bilan négatif DIT** (message ambre, défaut vs saisi — exigence 1), jamais
  masqué, jamais servi comme actionnable.
- **Exports md/html/one-pager** : section/ligne mode B avec toutes ses étiquettes — jamais
  un chiffre orphelin ; rien hors population (cohérence P2.3).
- **Assistant IA** : `mode_b` dans les FAITS uniquement sur la population (None sinon —
  l'IA ne peut pas l'inventer) ; prompt : cité UNIQUEMENT comme ESTIMÉ avec l'hypothèse
  travaux ; synthèse déterministe alignée.

## Vérifications

1. **Golden 117/117** (API bootée code M33, 0 incohérence base↔API).
2. **Re-mesure M34/M35 : 0 divergence dans les deux sens** (1 071 fiches), ancres intactes.
3. **Non-persistance PROUVÉE** (capture 6) : recalcul à 3 000 €/m² → −49 107 € ; re-lecture
   immédiate au défaut → 180 851 € / 1 500 €/m² (rien en base ; le moteur n'a AUCUN write).
4. Suite pytest : **1 307 verts** (+7 verrous mode B) — 5 échecs pré-existants env
   (residuel ×4, au_ouverture), consignés depuis M34.
5. **Captures** `qa/m33/screens/` : 1 saturée AW2362 (panneau complet, niveaux **Sourcés**,
   ~180 851 €) · 2 révélée CX2643 (niveaux **Estimés** — le partage visible) · 3 BI0229
   (**bilan négatif au défaut** — marché 1 685 €/m², message honnête) · 4 nue AP1610
   (**AUCUN panneau** — témoin) · 5 export one-pager étiqueté · 6 preuves non-persistance +
   hors-population (JSON réels).

## Reliquats consignés

- Locatif/défisc = vague 2 pré-client (cadrage acté) — rien préparé « au cas où ».
- La capture « ABSENT servi » n'existe pas EN RÉEL (0 cas dans la population, mesuré) —
  la branche est verrouillée par test (`test_absent_explicite_emprise`) et montrée en JSON.
- Si un jour mode B classant : dimension parcellaire discriminante requise (conclusion Q6).
