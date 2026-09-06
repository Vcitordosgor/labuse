# CORRECTIONS-ARITHMETIQUE — CIRCUIT-4 (lot 6)

Les SEULES corrections que le mandat autorise en autonomie : unité fausse, division inversée,
arrondi qui change un résultat, signe, seuil comparé strictement au lieu de largement (ou
l'inverse) quand la référence est CLAIRE. Chaque correction : avant/après sur les témoins + test.
Tout le reste (lecture de texte) est resté en place et attend Vic (`REGLES-ECARTS.md`).

## Corrections appliquées

| # | où | avant | après | référence claire | avant/après sur témoin | test |
|---|---|---|---|---|---|---|
| A1 (= écart E1) | `src/labuse/api/app.py` (drapeau « stationnement allégé » TCSP) | `proche = d <= 800` (LARGE) | `proche = d < 800` (STRICT) | L151-36 (loi 2025-1129, vigueur 28/11/2025, extrait cité à la fiche `distance_arret_m`) : « situées à **moins de** huit cents mètres » | d = 799 → sous_800m ✓ (inchangé) · **d = 800 → sous_800m passait à TORT, ne passe plus** · d = 801 → non (inchangé). Distances entières (round SQL) : seul le cas d = 800 exact change. | `tests/regles/test_distance_knn.py::test_drapeau_800_strict` (posé en xfail STRICT au lot 4, **levé** par cette correction) |

## Ce qui n'a PAS été corrigé (et pourquoi)

- **Commentaires du YAML taxe (articles H/I inversés)** — étiquette de référence, pas un calcul :
  les VALEURS sont exactes (892/251/10/3 000/2 928, vérifiées service-public + CGI) ; l'inversion
  documentaire va à `REGLES-ECARTS.md` (E5), décision Vic (correction douce sans effet chiffré).
- **« SDP » = enveloppe sans les déductions R111-22** (E2) — c'est une LECTURE du texte (quel
  libellé, quel coefficient de passage) : jamais corrigé en autonomie.
- Les 56 exemples témoins du lot 4 (recalculs indépendants : taxe ligne à ligne, enveloppe SDP,
  médianes, trim, parts de zonage, point mort, bascules de tiers…) sont TOUS tombés justes du
  premier coup face au moteur — aucune autre erreur d'arithmétique pure détectée.
