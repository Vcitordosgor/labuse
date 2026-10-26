# ETUDE-V6-6 — recette complète (4 types, lotissement, parking amont, cohérence, PDF)

Branche `feat/etude-v6`, **pas de merge**. 4 lots = 4 commits, mêmes gardes.

## Lotissement (items 1-3) — Lot 1 `eafe868e9`

1. **Règles lues du PLU de la zone de l'assiette** (jamais Saint-Leu Ud en dur) : CES, pleine terre et
   stationnement/lot viennent de `regles` (barème « logement individuel ») ; chacune sourcée ou « non
   servie ». **Étang-Salé UA** (70 % · UA 2.4 / 30 % · UA 2.6 / 2 pl. · UA 2.7.3) **vs Saint-Leu UD**
   (40 % · UD 9 / 40 % · UD 13 / 2 pl. · UD 12) — règles **différentes, chacune sur sa zone**.
2. **0 lot n'est jamais muet** : raison chiffrée (« après la voirie 382 m², reste 773 m² sur 1 155 m² nets —
   insuffisant ») + remède (réduire le lot / accès direct / assiette plus grande). Étang-Salé (bande de 17 m)
   → 0 lot **avec raison claire**. Saint-Leu AC264 → **14 lots** (= l'architecte).
3. **Hypothèses du lotissement** = taille de lot visée + largeur de voirie (jamais T1–T4) ; elles entrent
   dans le study_id.

## Parking en amont + jauge (items 4-5) — Lot 2 `9ed2ec99b`

4. **Étape 3, sous les logements** : « Stationnement : Aérien · Sous-sol 1 niveau · Sous-sol 2 niveaux »
   (aérien par défaut). Le choix part avec le programme ; le toggle du résultat et « Testez en sous-sol » restent.
5. **Jauge EN LOGEMENTS** (plus jamais « SDP ») : `N ≈ zone × niveaux × coef ÷ (surf_moy + places/logt × 25 ×
   niveaux × coef)` en aérien ; en sous-sol le parking ne consomme pas le sol. Affichage « ≈ N logements
   estimés · avant calcul », barre demande/estimation. **30 T1 Étang-Salé : estimé 34 vs calcul 40 = 15 %** (< 20 %).

## Cohérence + UI + étape 1 (items 6-8) — Lot 3 `bfb514152`

6. **Une seule vérité** : tenus/demandés d'une source unique (grand chiffre = « Votre programme ») ; facteur
   limitant unique (champ serveur) ; mixité lue de la même variante écran = PDF.
7. **Sélection vert OPAQUE** (fond plein, texte sombre) : étapes, cartes de type, choix de stationnement, chips.
8. **Étape 1** : Retour/Continuer alignés à droite sans barre vide ; « Zone PLU : Urbanisme PLU/GPU (API
   Carto). » retiré ; « (Lot D) » retiré.

## PDF (items 9-11) — Lot 4 `7cd6b7ec8`

9. **Le PDF décrit l'étude du client** : `scenario_retenu` retient « votre programme » (ce que l'écran affiche).
   Témoin **30 T1 → 30 logements, R+1, 30 places** ; synthèse « Votre projet — <type en toutes lettres> : N
   logements demandés… » puis « Maximum du terrain : K » en second. Plus de « scénario A », « retenu », « collectif ».
10. **N° de document EF-<8>** dérivé du study_id, identique écran/cartouche, indépendant de la date ; deux
    études = deux numéros (ex. étudiant `EF-55e38d77`, senior `EF-16d4a898`, social `EF-8de8ba1c`).
11. **Garde PDF=écran** étendue : n° doc, type projet, logements du programme, mixité, verrou `nombres_hors_payload` = 0.

## Gardes (toutes vertes)

| Garde | Résultat |
|---|---|
| `tsc -b` | 0 |
| `vitest` | **298 / 298** |
| pytest implantation + etude_v6 | **178 passed** ; 2 `test_route_*` échecs **pré-existants** (env `labuse_test` vide) |
| `chasse_docs` | **20 OK · 0 ECART · 0 SKIP** |
| `chasse_donnees` | **23 OK · 0 ECART · 2 SKIP** |
| verrou `nombres_hors_payload` | **0** (6 PDF collectif + 2 lotissement) |

## Recette — captures (`captures/`)

- **PDF (8)** : étudiant 30 T1 (aérien + sous-sol), senior 32 T2 (aérien + sous-sol), social 30 T1 + 10 T2
  (aérien + sous-sol), lotissement Étang-Salé (0 lot), lotissement Saint-Leu AC264 (14 lots). N° EF-<8>
  uniques, verrou vide.
- **Écran (5)** : étape 3 parking + jauge logements, résultat étudiant 30 T1 (cohérence 30/30 · max 40),
  lotissement Étang-Salé (0 lot + raison + règles UA), lotissement Saint-Leu AC264 (14 lots + règles UD +
  hypothèses lot/voirie), étape 2 type vert opaque. + PNG des couvertures PDF pour la mise côte à côte.

## Réserves honnêtes

- Lotissement Étang-Salé : l'assiette (bande ≈ 17 m de profondeur) ne loge pas une voirie centrale + lots —
  d'où 0 lot avec raison claire (pas un bug : un terrain trop étroit). Saint-Leu AC264 = 14 lots conforme.
- Jauge sous-sol volontairement optimiste (le parking ne consomme pas le sol) ; le calcul, borné par les
  niveaux (V6-5), affine et la bannière de divergence prévient.

Services arrêtés (8830/6060/8860 libres). **Aucun merge.**
