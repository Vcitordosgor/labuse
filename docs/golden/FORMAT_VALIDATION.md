# Golden — champ `validation` (Phase 0 J3)

Le format golden gagne un champ **`validation`** par parcelle, renseigné à la revue Vic sur PREUVES
(dossier `reports/j3-revue/DOSSIER-REVUE-J3.pdf`), pas sur expertise :

| valeur | signification | usage |
|---|---|---|
| `factuelle` | négative (écartée/exclue) dont l'exclusion est **prouvée** (source tracée + verdict recalculé isolé = servi + mesure PostGIS directe concordante) | **seule** base du **gate boussole** de l'arène |
| `coherence` | positive / cas limite servant d'**ancre de non-régression** (le verdict servi doit rester stable) | contrôle de non-régression, PAS le gate boussole |
| (absent / `barrée`) | non validée ou écartée par Vic | ignorée du golden |

## Règle (mandat)
- **Le gate boussole de l'arène ne s'appuie QUE sur des négatives `validation = factuelle`.** Une
  parcelle golden écartée/exclue passée `brulante`/`chaude` chez un challenger n'est éliminatoire que
  si elle est `factuelle`.
- **Les positives (`coherence`) entrent en ancres de non-régression** : leur verdict servi doit rester
  stable, mais elles ne rejettent pas un challenger via le gate boussole.

## Câblage (étape 2, APRÈS validation ligne à ligne)
1. Intégrer les additions VALIDÉES au format `qa/golden_check.py` (les 32 d'origine inchangés), en
   posant `validation` selon la revue.
2. `scoring/arene._golden_boussole` : filtrer les attendues sur `validation == 'factuelle'`
   (défaut rétro-compatible `factuelle` pour les entrées sans champ, à confirmer).
3. Golden élargi **N/N** sur `q_v6_m8`, puis branchement en préambule obligatoire de l'arène.

**Rien n'est gelé ni câblé avant la validation.** Ce document fixe la convention ; l'implémentation
suit la revue.
