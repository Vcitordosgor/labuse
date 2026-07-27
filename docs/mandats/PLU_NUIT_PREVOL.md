# PLU-SÉRIE-NUIT — PHASE 0 : PRÉ-VOL DES 17 COMMUNES

> Session A, 27/07/2026 22:12-22:35. AUCUN accès base applicative, AUCUNE API LABUSE —
> réseau GPU/data.geopf.fr uniquement. Scripts : `/tmp/plu_nuit/prevol*.py` ; règlements
> extraits en cache local `/tmp/plu_nuit/reglements/<insee>_reglement.pdf` (17/17).

## Méthode

1. **Concordance GPU** : idurba EN_VIGUEUR vs manifeste — **17/17 CONCORDANTES** (re-vérifiées
   live, pas seulement reprises de l'audit du matin).
2. **Règlements** : 17 archives téléchargées séquentiellement (suppression après extraction du
   seul règlement écrit), md5 calculés, pages comptées, offset PDF↔imprimé détecté par vote
   sur les numéros de pied de page (4 non détectés → à établir manuellement en phase 1,
   signalé, non bloquant).
3. **Libellés** : 3 passes de rattachement — exact → graphie (espaces/casse) → **famille**
   (suffixes numériques `Ns24→Ns`, suffixes `oapN`, **préfixes d'ouverture `1AUa→AUa`**,
   chapitre « AU indicée » type Tampon). Codes à lettre unique (A, N) : rattachés d'office à
   leurs chapitres (artefact du filtre de longueur, vérifié).
4. **Croisement `o12_zones_activite.yaml`** (lecture seule depuis le clone O12) :
   pré-identification des zones habitat-interdit.
5. **Alertes** : COS, texte pauvre/OCR, offset indétectable, libellés non rattachables >20 %.

## RÉSULTAT : 17/17 PRÊTES — aucune commune écartée d'entrée

Aucune divergence de millésime, aucune dépublication nouvelle, aucun règlement illisible
(taux de pages avec texte : 0,79 à 0,98). Les motifs de saut restent armés pour la phase 1
(chaîne de renvois non résolue, contradictions, etc.).

| Commune | insee | Parcelles* | Zones | Libellés | Pages | Offset | md5 règlement | Signaux pour la phase 1 |
|---|---|---|---|---|---|---|---|---|
| Saint-Louis | 97414 | 29 241 | 245 | 52 | 139 | +2 | `bae5ab70e6a8…` | **DUR** — ⚠ COS dans un doc 2025 (post-ALUR : consigner, ne pas appliquer) ; chapitre « AU indicée » type Tampon ; familles 1AU/2AU nombreuses ; O12 : 1AUe, 2AUe, UE |
| Saint-Joseph | 97412 | 28 959 | 343 | 58 | 185 | +1 | `f7f3e0470cd4…` | **DUR** — zones par bassins numérotés (U3/U5/U6, 1/2/3AU…) type Saint-Paul ; « AU indicée » ; 30 familles AU à résoudre ; O12 : néant (à vérifier en lecture) |
| Saint-Benoît | 97410 | 21 671 | 306 | 71 | 162 | **ND** | `900a6c13641a…` | **DUR** — 53 STECAL numérotés (Ns20-46, Nta47-54) rattachés aux familles Ns/Nta (règles par tableaux probables) ; offset à établir ; zéro renvoi ; O12 : AUe3, AUp1, Ue, Up |
| Sainte-Marie | 97418 | 16 746 | 268 | 32 | 66 | **ND** | `14a9319d8120…` | MOYEN — 66 p. seulement ; offset à établir ; O12 riche : UEa/UEc/UEm/UEp/UR (aéroport)/UT/UTp |
| La Possession | 97408 | 13 338 | 246 | 30 | 164 | 0 | `8b3bd9de4c9a…` | FACILE — 30/30 libellés exacts ; O12 : UE, UEm, AUEm |
| Petite-Île | 97405 | 13 137 | 335 | 34 | 169 | 0 | `19407563d462…` | FACILE — 34/34 exacts, zéro renvoi ; O12 riche : UE/UEa/AUE/UT/AUT/UZ/1AUz |
| Sainte-Suzanne | 97420 | 12 527 | 191 | 24 | 48 | 0 | `c7cf9f25fad6…` | MOYEN — 48 p. (dense ?) ; 17 renvois ; O12 : UE, 1AUe |
| Le Port | 97407 | 10 195 | 110 | 27 | **319** | **ND** | `5df6eb00bd50…` | MOYEN — règlement le plus épais (319 p.) ; offset à établir ; O12 : Ue/Uem/1AUe/1AUem/2AUem |
| L'Étang-Salé | 97404 | 9 070 | 78 | 24 | 106 | **ND** | `e6f47a869dbe…` | FACILE — 24/24 exacts, zéro renvoi ; offset à établir ; O12 : UE, AUe |
| Les Avirons | 97401 | 8 611 | 163 | 27 | 59 | 0 | `73a0f8f65869…` | FACILE — 27/27 exacts ; O12 : Ue, AUec, AUes |
| Salazie | 97421 | 7 035 | 325 | 15 | 64 | +2 | `4c18dc58075b…` | FACILE — 15 libellés seulement ; cirque (A/N dominants attendus) |
| Cilaos | 97424 | 6 560 | 149 | 15 | 90 | +1 | `124d7e80e9c1…` | MOYEN — ⚠ COS (doc 2024, consigner) ; **titres à lettres DOUBLÉES à l'extraction** (« AARRTTIICCLLEE ») → normalisation requise ; NtoPOS→famille Nto |
| La Plaine-des-Palmistes | 97406 | 6 450 | 274 | 21 | 217 | 0 | `533ce4c9aa4b…` | FACILE-MOYEN — ⚠ COS (doc 2023, consigner) ; 217 p. ; O12 : Ue, AUe |
| Entre-Deux | 97403 | 6 312 | 182 | 15 | 62 | 0 | `673137a9ac9b…` | FACILE — O12 : AUe |
| Sainte-Rose | 97419 | 6 287 | 125 | 22 | 87 | +2 | `401cb6fad4b1…` | MOYEN — chapitre AU GÉNÉRIQUE (indices a/b/c/d absents du texte : différenciation à trancher en lecture, sinon non-calibrage motivé) ; O12 : Ue |
| Bras-Panon | 97402 | 6 041 | 130 | 29 | 110 | +2 | `7032a0cc8d10…` | MOYEN — 25 renvois (record) ; familles AU sans préfixe dans le texte ; O12 : Ue, 1AUec, 2AUec, AUst ; doc le plus récent de l'île (28/04/2026) |
| Les Trois-Bassins | 97423 | 5 314 | 165 | 30 | 119 | 0 | `c3d7e7fd26ba…` | MOYEN — ⚠ COS (doc 2022, consigner) ; 24 renvois ; O12 : Ue, 1AUe |

\* **Parcelles = TOTAL cadastre par commune** (source : `docs/AUDIT_MULTICOMMUNE_24.md`,
colonne « Attendu »). Le POOL SERVI exact par commune exige la base (interdite cette nuit) —
le total cadastre est le proxy de dimensionnement ; les pools servis seront mesurés en
phase 4. Total des 17 : **207 494 parcelles**.

**COS post-ALUR consigné (invariant 5) dans 4 documents** : Saint-Louis (2025), Cilaos (2024),
La Plaine-des-Palmistes (2023), Les Trois-Bassins (2022) — à citer au rapport de chaque
commune, ne JAMAIS l'appliquer.

**Hors périmètre (rappel mandat)** : Saint-André et Saint-Leu (dépubliés GPU, dossiers d'appel
prêts), Saint-Philippe (RNU).

## RÉPARTITION EN 2 LOTS — équilibrée par pool ET par difficulté

La session A porte EN PLUS la **consolidation Saint-Paul** (tâche n°1, ajout Vic : 3 valeurs
sans source, 48 citations sans page, a_verifier à fort pool en commençant par Usdu — c'est le
plus gros pool de l'île, 51 129 parcelles). Le lot A est donc plus léger d'un « DUR » et d'une
commune ; la charge estimée s'équilibre.

### LOT A (cette session, clone `labuse-plu`, branche `feat/plu-nuit-a`) — ordre d'exécution :

| # | Tâche | Parcelles | Difficulté |
|---|---|---|---|
| 0 | **Consolidation Saint-Paul** (`[PLU-NUIT] Saint-Paul — consolidation`, source PDF md5 `0aee7298…`) | 51 129 | conso (≈1-1,5 h) |
| 1 | Saint-Joseph | 28 959 | DUR |
| 2 | Sainte-Marie | 16 746 | MOYEN |
| 3 | La Possession | 13 338 | FACILE |
| 4 | Sainte-Suzanne | 12 527 | MOYEN |
| 5 | L'Étang-Salé | 9 070 | FACILE |
| 6 | Salazie | 7 035 | FACILE |
| 7 | Entre-Deux | 6 312 | FACILE |
| 8 | Sainte-Rose | 6 287 | MOYEN |
| | **Total communes lot A** | **100 274** | 1 DUR · 3 MOYEN · 4 FACILE |

### LOT B (session B, clone `labuse-plu-b`, branche `feat/plu-nuit-b`) — ordre d'exécution :

| # | Commune | Parcelles | Difficulté |
|---|---|---|---|
| 1 | Saint-Louis | 29 241 | DUR |
| 2 | Saint-Benoît | 21 671 | DUR |
| 3 | Petite-Île | 13 137 | FACILE |
| 4 | Le Port | 10 195 | MOYEN (319 p.) |
| 5 | Les Avirons | 8 611 | FACILE |
| 6 | Cilaos | 6 560 | MOYEN (lettres doublées) |
| 7 | La Plaine-des-Palmistes | 6 450 | FACILE-MOYEN |
| 8 | Bras-Panon | 6 041 | MOYEN |
| 9 | Les Trois-Bassins | 5 314 | MOYEN |
| | **Total lot B** | **107 220** | 2 DUR · 4 MOYEN · 3 FACILE |

Équilibre : A = 100 274 parcelles + consolidation du pool n°1 de l'île ; B = 107 220
parcelles et une commune de plus. Les deux lots ouvrent par leur plus gros pool (si la nuit
tourne court, les communes qui pèsent sont faites).

**Note pour la session B** : les règlements des 17 sont déjà en cache
(`/tmp/plu_nuit/reglements/`), md5 au tableau — inutile de re-télécharger ; re-vérifier le md5
avant gravure. Le mandat complet est commité dans `docs/mandats/MANDAT_PLU_SERIE_NUIT.md`.
