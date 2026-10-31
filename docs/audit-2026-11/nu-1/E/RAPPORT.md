# AUDIT-NU-1 — Lot E : Moteurs et calculs

**Branche** `audit/nu-1-e` · worktree `~/Desktop/labuse-nu-e` · API 9090 (PDF-capable, venv) · front 6290 · base **locale Mac** (`labuse`, 434 582 parcelles, 282 tables) · **LECTURE SEULE**.

## Chiffres en tête

- **Scénarios joués : ≈ 60** — 13 parcelles témoins × 7 moteurs (à froid puis à chaud), via navigateur (Playwright), API `:9090`, PDF (`pdftotext`) et Copilote live, + 9 recalculs de masse (25 parcelles U résiduel, 4 485 ventes maison, 11 657 ventes terrain, 416 biens Radar, 291 k emprises bâties, 434 k surfaces, 393 copros, 209 k SDP, 24 communes).
- **Bloquants : 10** — NU-E-001/002/003 (résiduel), 021/022 (estimation), 038/039 (radar), 046/047 (copilote), 055 (implantation).
- **Majeurs : 27**
- **Mineurs : 15**
- **Dette : 11**
- Total : **63 trouvailles** (NU-E-001 → NU-E-063).

Vérifications positives (pour ne pas crier au loup) : taxe d'aménagement 2026 conforme à service-public.gouv.fr (0 écart) ; flag `copro` du scoring sain (0 écart sur 3 430) ; chemin PRIX du Copilote correctement hedgé (refuse d'inventer) ; écran == PDF == endpoint pour l'estimation ; console navigateur et journaux API à 0 erreur sur toute la session.

## Méthode & garde-fou

Audit en lecture seule. Mes requêtes de recalcul indépendantes tournent **toutes** sous
`PGOPTIONS='-c default_transaction_read_only=on'` (vérifié : `CREATE TABLE` → `ERROR: cannot execute … in a read-only transaction` ; `SELECT` passe). Aucun accès prod, aucune CLI mutante (ingestion/scoring/résiduel/radar/purge). L'API tourne en mode normal contre la base **locale** : elle écrit ses propres caches de lecture (`fiche_cache`, `comparateur_raw_cache`…) comme en fonctionnement nominal — aucune table métier/source n'est modifiée par moi. Recalcul = requêtes SQL directes sur les tables sources + comparaison au servi (API/écran/PDF).

Fuseau : le moteur force `timezone=Indian/Reunion` sur chaque connexion (`db.py:91`) ; tout `CURRENT_DATE`/`now()` SQL est en heure Réunion. Mes recalculs en tiennent compte.

## Parcelles témoins

| Profil | IDU | Commune |
|---|---|---|
| Nue zone U | `97411000IC0114` | Saint-Denis |
| Bâtie maison | `97416000CT1164` | Saint-Pierre |
| Copropriété | `97404000AV0167` | Saint-Paul |
| Zone A | `97412000AH0007` | Saint-Joseph |
| Zone N | `97424000AN0072` | Cilaos |
| Zone AU | `97401000AD1314` | Les Avirons |
| Très petite (<150 m²) | `97422000CS0850` | Sainte-Marie |
| Très grande (>1 ha) | `97415000CT2637` | Saint-Louis |
| PPR rouge (interdiction) | `97415000BR0025` | Saint-Louis |
| Sans PLU calibré / RNU | `97417000AT1496` | Saint-Philippe |
| Vente DVF récente | `97422000BN2939` | Sainte-Marie |
| Disparue du cadastre | `97416000CW2642` | Saint-Pierre |
| Cilaos U (outil à zone) | `97424000AN0134` | Cilaos |

Tirage aléatoire complémentaire : 30 parcelles/commune pour les recalculs de masse (fuite, écart, rattachement), échantillon décrit par moteur.

Chaque moteur a été relu dans le code, recalculé sur les parcelles témoins + un échantillon de masse par requête SQL read-only, et confronté à l'écran/au PDF/au Copilote. Les recalculs cités sont les miens.

## Trouvailles

### A — Résiduel & SDP

**NU-E-001 [BLOQUANT] Deux résiduels contradictoires dans la MÊME fiche.** `api/app.py:6466` (`potentiel_transformation` lit la vue `parcel_residuel`) vs `api/app.py:6992` (`analyse_labuse` lit la table `score_labuse`). Vérifié par moi sur le payload live : nue-U `97411000IC0114` → `analyse_labuse.sdp_residuelle_m2 = 68` **et** `potentiel_transformation.sdp_residuelle_m2 = 64` ; maison `97416000CT1164` → **81 vs 70**. Deux chiffres de SDP résiduelle pour la même parcelle, servis côte à côte. Cause : deux sources de vérité (run courant vs vue figée). **Amélioration :** faire pointer `potentiel_transformation` et la carte sur la même source que `analyse_labuse`, ou servir un seul résiduel. Un seul fait = une seule valeur.

**NU-E-002 [BLOQUANT] Le run résiduel servi est périmé et irreproductible — 22/25 parcelles fausses.** La vue `parcel_residuel` = `residuel_runs.is_served` = run_seq 1 (calculé 29/07–19/08, `assiette_source` NULL sur 431 663/431 663 lignes, donc antérieur au moteur d'assiette gabarit). Recalcul frais du moteur vs servi sur 25 parcelles U aléatoires : **22/25 divergent, médiane 20,5 %** ; extrêmes : servi 5 m² / frais 272 m² (×54), 82→253 m², et deux parcelles servies « 0 » alors que 95 et 242 m² constructibles. Le client filtre et achète sur des chiffres de plus de deux mois jamais rafraîchis après le changement d'assiette. **Amélioration :** rejouer un run avec l'assiette actuelle et le promouvoir `is_served` ; alarme sur l'âge du run servi.

**NU-E-003 [BLOQUANT] Les deux chemins d'assiette (gabarit `clippee=True` vs legacy `clippee=False`) donnent des capacités incompatibles.** `faisabilite/db.py:500` vs `:585`. `97415000CT2637` → résiduel 8 827 (gabarit) / 12 418 (legacy) / 12 220 (run servi) : trois valeurs. `97424000AN0134` pire : gabarit → **non constructible (`ppr_rouge`)**, legacy → **constructible 18 m²**. Le verdict dépend d'un flag d'appel, pas de la parcelle. **Amélioration :** un seul chemin d'assiette pour tout ce qui est servi (fiche, run, score).

**NU-E-004 [MAJEUR] « Bâti existant 76 %, démolition à prévoir » sur une parcelle où « Le bien » affiche 0 m² bâti.** `faisabilite/residuel.py:199-201` : `_emprise_revelee` (CoSIA, `parcel_bati_revele`) écrase l'emprise BD TOPO. `97411000IC0114` : BD TOPO = 0 bâtiment (`le_bien.emprise_batie_m2=0`) mais CoSIA = 82,65 m² → `analyse_labuse` dit « bâti sur 76 % — démolition à prévoir ». Le client lit « 0 m² bâti » et « démolition » sur la même fiche. **Amélioration :** afficher la source quand l'emprise retranchée vient de CoSIA, au lieu d'un « 76 % bâti » muet et contradictoire.

**NU-E-005 [MAJEUR] Double-compte du bâti existant (SUM sans ST_Union).** `faisabilite/residuel.py:194` via `bati.stats_batch:119` somme les intersections de bâtiments sans les unir (contrairement à `emprise_bati_bdtopo_m2` qui unionne). `97424000AN0134` : SUM = 268,5 m² (6 polygones se recouvrant) vs union 89,5 m² sur 467 m² → `pct_potentiel` stocké **258 %**, taux 233 %. Le résiduel soustrait un bâti gonflé ~3×. **Amélioration :** utiliser l'emprise unionnée partout, comme pour « Le bien ».

**NU-E-006 [MAJEUR] Parcelle annulée en entier par un booléen « bande littorale ».** `faisabilite/engine.py:802-804` + `db.py:42-43` : `bande_littorale` (simple `ST_Intersects(trait_de_cote)`) impose `facteur=0` → verdict `redhibitoire`, SDP 0. Témoin PPR `97415000BR0025` : le PPR INTERDICTION ne couvre que **234/566 m² (41 %)** et le gabarit le classe « pas d'exclusion auto » (zone d'implantation 256 m²), mais le booléen littoral l'écrase → SDP 0. **Amélioration :** moduler par la part de surface réellement grevée (comme le PPR), pas en tout-ou-rien.

**NU-E-007 [MAJEUR] SDP résiduelle reposant sur une hauteur-placeholder non signalée.** `faisabilite/residuel.py:72,207` : sans LiDAR/BD TOPO, bâti existant supposé R+1 (`niveaux=1,0`, `hauteur_source='sans'`). Dans le run SERVI, `hauteur_source` est **NULL sur 431 663/431 663 lignes** et le flag `estimation_sdp` n'y est pas porté. Le client ne distingue pas un résiduel mesuré d'un résiduel « au R+1 supposé » — exactement le « verdict déduit là où la doctrine demande une mesure » que Vic proscrit. **Amélioration :** servir et afficher `hauteur_source`/`estimation_sdp` depuis le run servi.

**NU-E-008 [MINEUR] SDP max rabotée de 55 % par une hypothèse invisible dans le nombre de tête.** `faisabilite/engine.py:64,666` : `coef_occupation=0.45` (vérifié 49/109=0,45) ampute l'emprise constructible, en plus du rendement 0,80. Le « SDP max » servi n'est donc pas réglementaire mais ×0,45 ; documenté dans `hypotheses[]` mais pas sur le chiffre de tête. **Amélioration :** nommer le champ « SDP constructible estimée (occupation 45 %) ».

**NU-E-009 [DETTE] Exceptions avalées sur les tiroirs annexes du résiduel.** `bati.py:198,310,327,345 ; residuel.py:53-57` : `except: rollback` sur CoSIA/RNB/BAN/OCSGE rend un échec de lecture indiscernable d'un vrai « 0 ». **Amélioration :** distinguer « table absente » de « requête en erreur » (log).

### B — Scoring & bandes

**NU-E-010 [MAJEUR] La copropriété reçoit un palier de tête — doctrine « hors palier » violée.** `scoring p_v2/statuts.py:252-280` : `assign_paliers` est f(p) pure et ne masque jamais `copro` (le masque existait dans l'ancien `assign_tiers:118`, perdu). Recalcul : **393 copros portent `priorite` (70) ou `a_suivre` (323)** alors que la doctrine et le docstring disent « hors copropriété ». **Amélioration :** masquer `copro` vers `sans_signal` avant écriture, comme le font déjà `rang`/`percentile`.

**NU-E-011 [MAJEUR] Une copro « Écartée » est servie « 1/20 de vente sous 1 an, nettement au-dessus de la moyenne ».** `api/app.py:4479/4500`, `api/score_v2.py:87`, front `ScoreV2Block.tsx:113`. Vérifié par moi sur `97404000AV0167` : `tier=ecartee`, `copro=true`, `percentile/rang=null` (correct) **mais** `fraction="1/20"`, `mult_base=3,24`, `verbal.mot="nettement au-dessus de la moyenne"`, `reglette_pct=36,5`. `mult_base=p/taux_base` compare la copro à une base dont elle est exclue. **Amélioration :** si copro/écartée, servir `fraction=None` et `verbal` sans `mot`. « Écartée » et « 1 chance sur 20 » ne peuvent coexister.

**NU-E-012 [MAJEUR] `valeur_creee_eur` = chiffre d'affaires brut sans aucun coût, jusqu'à 878 M€.** `scoring p_v2/potentiel.py:112` : `sdp_residuelle × €/m² bâti`, zéro déduction foncier/construction/promotion/taxe. Recalcul : médiane 447 655 €, p99 14,7 M€, **max 878 615 230 €**, 3 123 parcelles > 10 M€. Atténuation : la colonne n'est lue par aucun écran/PDF aujourd'hui. **Amélioration :** ne jamais câbler cette colonne en l'état ; si affichée, déduire les coûts et la nommer « potentiel de CA, fourchette », jamais un € ferme.

**NU-E-013 [MAJEUR] SDP du scoring périmée : 48 % des `potentiel_sdp_m2` ≠ résiduel courant.** `potentiel.py:110` : recalcul `potentiel_sdp_m2 IS DISTINCT FROM round(sdp_residuelle_m2)` = **209 614 / 433 229 (48 %)**, dont 3 054 stockés > 0 alors que le résiduel courant est NULL. Deux sources de vérité pour la SDP (fiche live vs scoring figé). **Amélioration :** recalculer le potentiel à la bascule ou servir la même SDP partout.

**NU-E-014 [MAJEUR] `prix_secteur_eur_m2` est communal (pas sectoriel) et basé sur un millésime 2025 incomplet.** `potentiel.py:97,104` : `GROUP BY left(idu,5)` = 24 valeurs pour 24 communes alors que le « secteur » du modèle = `left(idu,10)` ; assise ~174 ventes/commune en 2025 (~40 % complet). Nom trompeur + granularité commune. **Amélioration :** renommer `prix_commune_*` et exiger un N minimum (sinon NULL).

**NU-E-015 [MAJEUR] Étage 0 (prime d'écartement) lu sur un run cascade potentiellement ≠ du run scoré.** `pipeline.py:381` : `etage0_run = runs.current()` ≠ run en cours de scoring ; un cascade périmé peut écarter/ne pas écarter à tort. **Amélioration :** vérifier à la bascule que run cascade == run scoré, sinon alerter.

**NU-E-016 [MINEUR] `event_age_mois` calculé sur l'horloge OS, pas l'heure Réunion.** `pipeline.py:391` (`Timestamp.today()`) vs `today_reunion()` ailleurs — même classe de bug que le fuseau RADAR-COUVERTURE-1. Impact nul sur les paliers servis, réel si l'ancien système est réactivé. **Amélioration :** `today_reunion()`.

**NU-E-017 [MINEUR] `plancher_c` : SDP NULL→0 confond « inconnu » et « nul ».** `statuts.py:69` (`fillna(0)`) ; pilote encore le drapeau réserve foncière. **Amélioration :** distinguer NULL de 0 au niveau capacité.

**NU-E-018 [MINEUR] Exception avalée silencieusement sur la provenance.** `pipeline.py:560-564` : `snapshot_source_millesimes` échoue → `[]` sans `warnings.warn` (contrairement aux blocs voisins). **Amélioration :** avertir comme les blocs voisins.

**NU-E-019 [DETTE] Seuils ICD et poids codés en dur, contraires à « jamais en dur » ; assert qui crashe l'import.** `scoring/icd.py:61-62` + `assert POIDS_TOTAL==100`. **Amélioration :** passer en YAML, remplacer l'assert par une erreur gracieuse.

**NU-E-020 [DETTE] Deux systèmes de tiers dans un fichier + `SCORING_SPEC.md` intégralement périmé.** `statuts.py` contient `assign_tiers` (brûlante/chaude, **mort**) et `assign_paliers` (servi) ; la spec décrit le run `q_v7_defisc` (0 ligne) et des tiers qui n'existent plus. **Amélioration :** retirer le code mort et réécrire la spec. *Note de vérification : le flag `copro` servi est SAIN (3 430 == `copro_rnic OR copro_dvf`, 0 écart) — le faux positif « toutes parcelles » de CHASSE-4 ne s'applique pas au flag ; les paliers sont bornés proprement (pas de chevauchement).*

### C — Estimation (« Estimer un bien »)

**NU-E-021 [BLOQUANT] Valeur bâtie = emprise au sol × €/m² HABITABLE (deux unités incompatibles).** `pige/api.py:1644-1645,1547` (surface = `_emprise_bati_m2`) × médiane habitable `marche_service.py:323`. Vérifié live (écran==PDF) sur `97416000CT1164` : **784 000 €** = 239 m² (emprise BD TOPO) × 3 280 €/m², fourchette 564 000–1 003 000 €. Or les comparables sont des maisons de ~90 m² habitable (24–139) → valeur réelle **≈ 295 000 €**. L'emprise au sol vaut en moyenne **5,3×** la surface habitable (recalc sur 4 485 ventes maison). La valeur affichée est gonflée d'un facteur ~2 à 5 sur toute maison. **Amélioration :** multiplier par une surface habitable (SDP ou `surface_reelle_bati` estimée), ou ne servir que le €/m² sans total.

**NU-E-022 [BLOQUANT] Nature lue de la PARCELLE, pas de la mutation → ~49 % des terrains valorisés en mini-maison.** `pige/api.py:1469-1484` : `_nature_parcelle` lit `taux_emprise_pct` (couverture actuelle), pas la nature du bien vendu. Témoin vente récente `97422000BN2939` : affiché **59 000 €** (classé maison, 26 m² × 2 285) ; or la parcelle s'est **vendue 140 000 €** (terrain 682 m², 0 bâti) → **−58 %**. Recalc : sur 11 657 ventes de terrain nu récentes, **5 685 (49 %)** seraient valorisées en bâti. **Amélioration :** croiser avec la présence réelle d'un local bâti / la nature DVF ; sous un bâti significatif, traiter en terrain.

**NU-E-023 [MAJEUR] La parcelle sujet apparaît dans ses propres comparables (pas d'auto-exclusion).** `marche_service.py:402-418` (terrain) & 314-331 (bâti) : aucun `WHERE id_parcelle <> :idu`. `97408000AP1584` liste sa propre vente 12/2025 (distance 0 m) parmi les 8 comparables → fuite dans la médiane. **Amélioration :** exclure la mutation/parcelle sujet de l'agrégat et du tableau.

**NU-E-024 [MAJEUR] ±% codé en dur par segment, vendu comme « fiabilité » bien par bien.** `pige/api.py:1522-1535` (`_ECART_SEGMENT`), `estimation_prix.py:28` : « fiabilité Limitée, ±28 % » identique pour toute maison, indépendamment de n, q1/q3, dispersion. `estimation_prix.py` porte un **second** chiffre divergent (±30 %). **Amélioration :** dériver l'intervalle de la dispersion mesurée de l'échantillon servi et unifier les deux chemins.

**NU-E-025 [MAJEUR] Aucun filtre VEFA/neuf, viager, dépendances, multi-lot avant la médiane.** `marche_service.py:314-336`, `filtre_ventes:37-95` : seul garde-fou bornes 1000–12000 €/m² + z-MAD. `nature_mutation ILIKE 'vente%'` capte VEFA (prix TTC DOM) et viager (prix minoré) ; mutations multi-parcelles agrégées faussent le €/m². **Amélioration :** exclure VEFA/viager de la nature, diviser au grain mutation réel.

**NU-E-026 [MAJEUR] Branche copro inatteignable quand la parcelle est classée « nue ».** `pige/api.py:1593-1618` : le `return` « nue » (1599) précède la branche copro (1618) ; témoin copro `97404000AV0167` (taux_emprise=0) sort en `terrain_nu`. En plus `copro=fiche["score_v2"]["copro"]` dépend d'un champ parfois absent. **Amélioration :** tester copro avant la nature.

**NU-E-027 [MINEUR] Nature « inconnue » : médiane servie mais `valeur_indicative=None`, sans avertissement.** `pige/api.py:1636-1660` ; `97412000AH0007` (zone A, taux NULL) sort `median=1761` sans total ni réserve → l'utilisateur multiplie lui-même. **Amélioration :** afficher « nature non déterminée, pas d'estimation ».

**NU-E-028 [MINEUR] Repli commune entière silencieux.** `marche_service.py:359-361` : sous n≥8, la médiane devient celle de la commune ; seul indice, le badge « Limitée ». **Amélioration :** phrase « médiane commune entière (secteur insuffisant) ».

**NU-E-029 [DETTE] Trois chemins de médiane bâti coexistent sans test de cohérence.** `dvf_mediane.py:34`, `marche_service.py:300` (`comparateur_bien`), `mon_secteur.py:92` (`sector_price`). **Amélioration :** converger vers un lecteur unique.

### D — Marché DVF

**NU-E-030 [MAJEUR] VEFA (neuf) blanchi en « prix du marché/secteur » de l'ancien.** `faisabilite/bilan.py:232`, `marche_service.py:259/328` : filtre `nature_mutation ILIKE '%vente%'` matche « Vente en l'état futur d'achèvement » (349 ventes VEFA à Saint-Denis, médiane 4 878 ; 1 386 sur l'île à 4 759) alors que le baromètre commune (`api/moteurs.py:762`) utilise `= 'Vente'` strict. Swing commune +2,5 % à +8,6 %, bien plus au rayon serré 500 m. **Amélioration :** `= 'Vente'` (ou exclure VEFA/VTB) sur les chemins de valorisation ; le neuf a déjà `neuf_vefa_commune`.

**NU-E-031 [MAJEUR] Comparateur terrain : dénominateur = somme des lignes répétées → €/m² faux (jusqu'à ×146).** `marche_service.py:407-417` : `sum(dm.surface_terrain)` sur toutes les lignes, sans le `max() PARTITION BY parcelle` que tous les autres chemins terrain appliquent. 1 076/16 357 mutations (6,6 %) ont un dénominateur gonflé ; **624 passent le filtre et s'affichent au client avec un €/m² erroné**. **Amélioration :** dédupliquer par `(id_mutation,id_parcelle)` avec `max(surface_terrain)` avant la somme.

**NU-E-032 [MAJEUR] `dvf_secteur_medianes` = cache figé jamais invalidé, servi comme « prix du secteur ».** `ingestion/dvf_marche.py:101`, `mon_secteur.py:33` : `computed_at = 2026-08-17` ; le champ `fenetre` stocké ne correspond même plus à la constante du code (table bâtie par une version antérieure). Aucune garde ne lie le cache au millésime DVF. **Amélioration :** rebuild dans le même déploiement que l'ingestion DVF, ou servir/vérifier `computed_at`.

**NU-E-033 [MINEUR] `mediane_bati()` ancre sa fenêtre 36 mois sur `now()`, pas sur la dernière vente.** `dvf_mediane.py:66` : DVF s'arrête 2025-12-31, « aujourd'hui » 2026-10-31 → borne haute ~10 mois dans le vide, borne basse jette fin 2022 — le bug même que `dvf_fenetre.py` clôt, non appliqué ici. **Amélioration :** utiliser `fenetre_dvf_sql` (ancre `max(date_mutation)`).

**NU-E-034 [MINEUR] Le « marché bâti de la commune » du Radar = une seule parcelle.** `pige/signaux.py:127-147` : `_dvf_bati` prend le `sector_price` d'UN point (centroïde) pour l'écart demandé/acté servi. **Amélioration :** utiliser `prix_ancien_communes` (vraie médiane commune, VEFA exclue, ≥100 ventes).

**NU-E-035 [MINEUR] VTB (« Vente terrain à bâtir ») portant du bâti fuit dans le comparateur bâti.** `marche_service.py:328`, `bilan.py:232` : 31 mutations VTB avec surf_bati≥20 entrent dans l'échantillon bâti. **Amélioration :** même correctif que VEFA (`= 'Vente'`).

**NU-E-036 [DETTE] Deux planchers €/m² et deux filtres de nature coexistent sans test de cohérence.** Baromètre [100;12000] `='Vente'` vs valorisation [1000;12000] `ILIKE '%vente%'`. L'écart de filtre nature n'est pas documenté et produit NU-E-030/035. **Amélioration :** factoriser le prédicat de nature dans une constante unique testée.

**NU-E-037 [DETTE] Docstring `neuf_vefa_commune` dit « 3 ans », code = 5 ans.** `ingestion/dvf_marche.py:188` vs 158. **Amélioration :** corriger la docstring.

### E — Radar / pige

*(La « vie » des annonces vit dans `pige/` ; `radar.py` à la racine est une autre feature — voir Hors lot. Base locale : 416 biens, 428 annonces, un seul portail = Leboncoin.)*

**NU-E-038 [BLOQUANT] 299/416 biens (72 %) sont `retiree` par la chaîne de confirmation FAUSSE pré-fix, jamais nettoyés.** `pige_passes` enregistre n_supprimees 107/1/134/55/11 = 308 retraits sur 312 pages (97–100 % de retrait par passe), à la signature exacte des fausses suppressions que RADAR-FIX-3 a corrigées — mais la SQL de restauration (`radar-fix-3/restauration.sql`) n'a jamais été appliquée ici (0 bien restauré, 0 `vendue_le`). Le « délai médian de retrait » (`marche.py:54`) est calculé sur 299 retraits fantômes. Un client voit 72 % de l'inventaire faussement « retiré ». **Amélioration :** jouer la restauration, puis une passe de confirmation propre.

**NU-E-039 [BLOQUANT] Rattachement réel = 0/416 → tout l'aval est mort.** `pige/html_ingest.py:323-331` : `_rattacher` renvoie `non_rattachee` pour chaque annonce (« rattachement automatique retiré — RADAR-2 ») ; seul un clic humain rattache, et il y en a **0**. Conséquence : `idu IS NULL` partout → `matcher_dvf` (cycle.py:76) ne peut JAMAIS produire une `vendue` (0 vendue confirmée), `qualifier_retiree_sans_vente` ne se déclenche jamais, `rattachees_pct = 0,0`. Toute la promesse « annonce→DVF qui affine l'estimateur » ne produit rien. **Amélioration :** recâbler `rattachement_html.rattacher` en ingestion pour le niveau `source` (≥2 critères), ou pousser agressivement les 47 pistes dans la file de réinstruction.

**NU-E-040 [MAJEUR] Dédoublonnage SAUTÉ pour toute annonce « à qualifier » → vrais doublons servis.** `pige/html_ingest.py:381` : la fusion est gardée `if not degrade and not motifs`. Preuve : biens **#284 et #332**, terrain, Plaine-des-Palmistes, surface 420, prix 88 000 €, même motif cosmétique → identiques selon `_est_meme_bien` (surf+prix exacts) mais stockés comme deux annonces. **Amélioration :** fusion exacte (surf+prix) AVANT la garde motif ; planifier le job `fusionner_doublons_existants` (existe, jamais programmé).

**NU-E-041 [MAJEUR] Le dédoublonnage inter-portail n'a jamais tourné en réel.** `html_next.py:170-295` : 428/428 annonces sont Leboncoin (0 list_id Bien'ici). Le seul mécanisme qui attraperait un même bien sur LBC + Bien'ici est inexercé. **Amélioration :** ne pas revendiquer un dédoublonnage inter-source fonctionnel tant qu'il n'a pas de données.

**NU-E-042 [MAJEUR] Le réglage de rayon 60 m/150 m ne rattache rien (le rattachement est débranché).** `pige/rattachement_html.py:69,196-233` : la cascade 60 m (adresse) / 150 m (ville) + ≥2 critères est saine mais `rattacher` n'est pas appelé en ingestion (NU-E-039) ; 320/416 biens sont en position « ville » (150 m, ambigu), 24 seulement en « adresse ». **Amélioration :** recâbler le site d'appel, sinon le réglage fin est sans effet.

**NU-E-043 [MINEUR] 79 annonces / 77 biens sans date de publication → « repéré le » retombe en silence sur la date de dépôt.** `html_ingest.py:397-399` : `first_publication_date` NULL → pas de 1970 (le piège tz est absent, bon point), mais `en_vente_longue` (>90 j) ne peut jamais se déclencher et un bien ancien peut être masqué par une date de dépôt récente. **Amélioration :** afficher « repéré le (relevé) » distinct de « en ligne depuis ».

**NU-E-044 [MINEUR] Deux idiomes de fuseau côte à côte dans le cycle.** `pige/cycle.py:31,61` : `marquer_a_reverifier` compare `now() - interval` alors que les voisins font `(now() AT TIME ZONE 'Indian/Reunion')::date` sur une session déjà en Réunion (`db.py:91`). Inoffensif aujourd'hui (Réunion +4 fixe) mais incohérent. **Amélioration :** choisir une convention.

**NU-E-045 [DETTE] La file `a_confirmer` (83 biens) rejouera des retraits sur l'inventaire fantôme.** `api.py:238-243` : une passe sur des liens majoritairement morts peut dépasser le garde-fou 30 % et bloquer des passes légitimes. **Amélioration :** restaurer (NU-E-038) avant de confirmer. *Note : le code distingue correctement « prix demandé (Radar) » vs « acté (DVF) » (`marche.py:95,156,200`) — pas de confusion de ce côté.*

### F — Copilote (affirmations vs donnée)

**NU-E-046 [BLOQUANT] Faux verdict de copropriété inventé par le LLM.** `copilote_v2/answering.py:439` (`_formuler`) + `outils.py:339` (`fiche_parcelle` sans champ copro) + `resume_fiche.py:236` (`_CHAMPS` sans copro). Sur `97404000AV0167`, le Copilote affirme « **Non, cette parcelle n'est pas en copropriété** » alors que `parcel_p_score_v2.copro = TRUE`. L'outil choisi ne porte aucun champ copro, et `_formuler` laisse le LLM trancher. **Amélioration :** outil/champ déterministe `copro` ; tant qu'un fait n'a pas d'outil, refuser (« je n'ai pas cette donnée »).

**NU-E-047 [BLOQUANT] Le verrou anti-invention est aveugle aux affirmations non chiffrées.** `answering.py:299-311` (`_anti_invention`) ne vérifie que les *nombres* présents dans le résultat d'outil ; un verdict qualitatif (copro oui/non, constructibilité) n'est jamais confronté à la donnée. Toute la surface d'hallucination qualitative est non gardée. **Amélioration :** restreindre `_formuler` à reformuler des champs *présents* dans `res.data` ; refuser si l'outil ne porte pas la grandeur demandée.

**NU-E-048 [MAJEUR] Source falsifiée : un verdict PLU/constructibilité est estampillé « Cadastre Etalab ».** `outils.py:361-362` + `answering.py:228` : `fiche_parcelle` tague tout son payload `source="cadastre Etalab"` et `_formuler` recopie cette source. Sur zone A `97412000AH0007` : « écartée de la constructibilité selon le PLU… **(cadastre Etalab)** » — la constructibilité ne vient pas du cadastre. **Amélioration :** ne servir un verdict PLU que via `destination_zone`/`regles_plu_zone` (source PLU).

**NU-E-049 [MAJEUR] Doctrine « scoring seulement où demandé » contournée.** `outils.py:357-360` : `fiche_parcelle` embarque systématiquement `verdict = tier` dans le payload LLM ; une question factuelle reçoit un verdict de potentiel non demandé et mal sourcé. **Amélioration :** retirer `verdict` du payload `fiche_parcelle` ; router la constructibilité vers l'outil dédié.

**NU-E-050 [MINEUR] Exception avalée → réponse générique indiscernable.** `copilote_v2.py:128-133` : toute exception devient « Je n'ai pas su traiter cette demande » (`erreur:true`) ; combiné à l'absence de refus déterministe, un fait manquant devient une hallucination plutôt qu'une erreur honnête. **Amélioration :** refus typés par outil, filet réservé aux vrais incidents.

**NU-E-051 [DETTE] % PPR repris sans borne de plausibilité.** `outils.py:799` (`part_pct`) — sur `97415000BR0025` « zone rouge sur 41 % » est plausible et bien gardé par `_anti_invention`, mais aucun garde-fou si la couche renvoie une valeur aberrante. *Note : le chemin PRIX est bien hedgé — le Copilote refuse d'inventer un nombre et ouvre la Calculette (pas de sur-vente).* **Amélioration :** borne de plausibilité + test.

### G — Cross-moteurs & cohérence (observé directement)

**NU-E-052 [MAJEUR] L'emprise bâtie servie au client est incohérente d'un panneau à l'autre de la fiche.** « Le bien » affiche **165 m²** (`parcel_residuel_bati`, étiqueté « BD TOPO IGN ») ; le scoring (`score_v2.motif` « bâtie saturée — ratio 45 % ») et l'estimation/PDF affichent **239 m²** (`p_model_bati`/CoSIA, étiqueté « BD TOPO (239 m²) »). Même source nommée « BD TOPO », deux valeurs, deux récits opposés (« 378 m² libre » vs « bâtie saturée, déclassée »). Systémique : sur 289 976 parcelles ayant du bâti dans les deux tables, écart moyen **49 %**, et **193 420 (67 %) divergent de plus de 20 %** ; **25 742 parcelles (8,8 %) sont « saturées » selon le modèle (≥40 %) mais pas selon le résiduel (<40 %)**. **Amélioration :** une seule emprise bâtie servie, avec une source unique et honnête ; réconcilier le récit « libre » et le récit « saturé ».

**NU-E-053 [MINEUR] La « surface » de tête et la valeur foncière utilisent la surface GÉOMÉTRIQUE tout en l'étiquetant « cadastre ».** La fiche sert `surface_m2 = surface_dessin_m2` (aire du dessin) avec `surface_source="cadastre"`, alors que la contenance cadastrale (surface légale de l'acte) est dans `contenance_m2`. Témoin maison : 526 m² servi / 543 m² cadastral ; le PDF « lecture foncière » fait « 526 × 231 €/m² ». Recalc base : écart médian 1,6 %, p90 7,7 %, **76 185 parcelles (17,5 %) > 5 %**. **Amélioration :** servir et valoriser la contenance cadastrale (surface juridique) ou étiqueter clairement « surface dessinée ».

**NU-E-054 [DETTE] Génération PDF lente (>2 s).** La génération de l'« Analyse d'annonce » PDF a pris **16–18 s** (`/analyse-annonce/{idu}.pdf`, WeasyPrint + recalcul). Au-delà du seuil 2 s ; risque de time-out derrière le proxy. **Amélioration :** mettre en cache le calcul (déjà fait pour l'écran) et profiler WeasyPrint. *Vérifs positives : console navigateur 0 erreur/0 avertissement au chargement de la fiche ; journaux API 0 ERROR/Exception sur toute la session ; écran == PDF == endpoint pour l'estimation ; taxe d'aménagement 2026 (892/1011 €/m² hors-IdF/IdF, piscine 251, stationnement 2928/5857) **conforme** à service-public.gouv.fr A15416 — aucun écart.*

### H — Implantation & étude de faisabilité

**NU-E-055 [BLOQUANT] Commune sans PLU (RNU) → zone « UA » inventée, programme chiffré sans aucune règle vérifiée.** `implantation/moteur.py:184` : `zone = _resoudre_zone(...) or "UA"`. Témoin Saint-Philippe `97417000AT1496` (RNU) : l'outil sert **12 logements R+5, 1 245 m² SDP, emprise 232,5 m², « exploitable en pré-faisabilité »** alors qu'Emprise/Hauteur/Reculs/Stationnement/Perméabilité sont tous « Non effectué » (recalc confirmé). En RNU la constructibilité relève de L111-3 (limitation aux parties urbanisées), non modélisée. Le défaut « UA » est traité comme une vraie zone U → l'assiette n'est pas clippée et le moteur monte jusqu'à R+6. **Amélioration :** si `_resoudre_zone` est None, refuser (« commune en RNU, hors périmètre ») ; ne jamais servir un nombre de logements quand zéro règle n'est validée.

**NU-E-056 [MAJEUR] Seuil stationnement TCSP périmé : 500 m codé en dur, la loi est à 800 m (loi 2025-1129 du 26/11/2025).** `moteur.py:403,406` · `service.py:604,613,696` + citations `410-418,705-728`. Le plafond L151-35/36 est appliqué et cité « à moins de 500 m d'un transport collectif » ; depuis le 27/11/2025 le rayon est **800 m** (vérifié : [Cerema](https://outil2amenagement.cerema.fr/actualites/la-loi-du-26-novembre-2025-facilite-les-densites-minimales-et-allege-les-obligations), [Légifrance art. 20](https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000052857983)). Tout terrain entre 500 et 800 m d'un TCSP se voit refuser à tort le plafond réduit → l'outil impose trop de places et **sous-estime la capacité en logements**. **Amélioration :** porter le seuil à 800 m (en config, il a déjà bougé) et réviser les citations.

**NU-E-057 [MAJEUR] Parcelle > 1 ha : l'étude time out (503) au lieu de rendre un résultat.** Grille `moteur.py:207-220` (3 formes × 5 niveaux × 15 fractions × contrôles géo × LiDAR non borné). Témoin `97415000CT2637` → `etude_trop_lourde` « relancez » (confirmé API + recalc direct qui ne termine pas ; log API : `POST /modules/etude 503`). Or le grand terrain est le cas à fort enjeu d'achat. **Amélioration :** réduire/paralléliser la grille pour les grandes assiettes, ou servir un résultat dégradé borné — un promoteur ne peut pas « relancer » un terrain à 2 M€.

**NU-E-058 [MAJEUR] CES et pleine terre comparés à la contenance CADASTRALE, emprise mesurée sur le DESSIN (bases hétérogènes).** `controles.py:242,334` : Emprise OK si `emprise_dessin ≤ CES × contenance_cadastrale` ; `contenance_totale_m2` = cadastre × pct_constructible (`terrain.py:227`) alors que l'emprise est mesurée en EPSG:2975 sur la géométrie (CT1164 : 526,5 dessin vs 543 cadastre, ≈ 3 %). Le ratio réel peut dépasser le CES de l'écart cadastre↔dessin sans que le contrôle le voie. **Amélioration :** comparer emprise et plafond sur la même surface de référence ; documenter le choix.

**NU-E-059 [MAJEUR] Hauteur = niveaux × 3 m forfaitaires, jamais la hauteur réelle (acrotère/faîtage ignorés).** `controles.py:251`, `moteur.py:94` : « R+5 ≈ 18 m ≤ plafond » calculé en `niveaux × 3,0` sans toiture/acrotère/combles ni rez surélevé, alors que le PLU mesure à l'égout/faîtage depuis le TN (R.111-26). Un R+5 réel dépasse souvent 18 m à l'égout → des scénarios déclarés conformes peuvent violer le plafond. **Amélioration :** ajouter acrotère/retombée, distinguer égout vs faîtage, marquer « hauteur estimée » avec marge.

**NU-E-060 [MINEUR] Verdict déduit du nombre de contrôles verts, « Non effectué » ne pèse pas.** `controles.py:470-521` : « Exploitable sous hypothèses » dès 0 Échoué + 0 À-confirmer-bloquant + voie, même si Emprise/Hauteur sont « Non effectué » (zone non calibrée). **Amélioration :** exiger Emprise + Hauteur « Réussi » avant un verdict meilleur que « À compléter ».

**NU-E-061 [MINEUR] Ratio L151-35 piloté par la seule distance, pas par la catégorie de logement (loi 2025-1129).** `moteur.py:408`, `service.py:603` : `0,5 si <500 m sinon 1,0`, alors que la loi différencie locatif aidé (1 pl.) vs intermédiaire/RPA (0,5 pl.) indépendamment de la distance. **Amélioration :** table ratio par catégorie × distance 800 m.

**NU-E-062 [DETTE] ZeroDivisionError latent en mode sous-sol.** `capacite.py:394` : `emprise_sous_sol_m2 / places_sous_sol` en f-string (garde partiel). **Amélioration :** diviser une seule fois, `or 1`.

**NU-E-063 [DETTE] Exceptions avalées masquant plan/accès/LiDAR.** `terrain.py:85,159`, `service.py:1051,1060,1066,1120` (`except Exception: pass`, `planche_svg=""`) : un échec de contexte produit un plan schématique ou une pente absente sans que le client le sache. **Amélioration :** journaliser ET afficher un drapeau « contexte indisponible ».

*Hypothèses implicites de ce moteur (non montrées comme déterminantes) : hauteur d'étage 3,0 m utilisée comme mesure réglementaire ; tailles logement T1 30/T2 56/T3 70/T4 80 m² et répartition T2×3/T3×2/T4×1 ; niveaux max R+6 purement techniques ; profondeur barre 13 m, coef plancher→habitable 0,80 ; TCSP = `tcsp_station` seul (bus exclu), distance à vol d'oiseau et non par cheminement.*

## Hors lot

- `radar.py` (racine) = sondes de fraîcheur `data_sources`, feature distincte de la vie des annonces — non instruit.
- Validation statistique du modèle P (RR@k, walk-forward, ECE), `mutation.py` (4ᵉ score orphelin, poids PLACEHOLDER), Score V (vendabilité non servie) — hors « scoring servi ».
- Loyers (`ligne9_loyer`), DPE, permis Sitadel, `dvf_prix_sortie_neuf` (agrégat île) — lus, non recalculés.
- Miroirs TS front (`fourchette.ts`, `format.ts`), rendu au pixel des badges — non ré-audités.
- Bannière carte « pas à jour — reconstruction des tuiles en attente » (capture `accueil-carte-pas-a-jour.png`) = pipeline tuiles, hors moteurs.
- Chaîne web du Copilote (`recherche_web`), quota/429, mémoire de session — hors périmètre « affirmations vs donnée ».

## Les 5 trouvailles les plus graves & ce que je changerais d'abord

Le fil rouge du lot : **le produit affiche, avec aplomb et une jolie fiabilité, des chiffres qu'il n'a pas mesurés** — une valeur bâtie multipliée par la mauvaise surface, un résiduel figé il y a deux mois, un Radar vide présenté comme un marché, un Copilote qui tranche là où il ne sait pas. Pour un client à 349 €/mois qui engage un achat, c'est l'inverse de ce qu'on vend.

1. **NU-E-021 — L'estimation d'une maison est gonflée ×2 à ×5.** Elle multiplie l'**emprise au sol** (239 m²) par un €/m² calculé sur des surfaces **habitables** (~90 m²). Témoin vérifié à l'écran et au PDF : 784 000 € pour une maison qui vaut ~295 000 €. C'est le chiffre sur lequel un acheteur signe.
2. **NU-E-022 — Un terrain sur deux est estimé comme une mini-maison.** La nature est lue sur l'état *actuel* de la parcelle, pas sur le bien vendu : témoin vendu 140 000 € affiché 59 000 € (−58 %), 49 % des terrains concernés.
3. **NU-E-038/039 — Le Radar est inerte et faussement « vidé ».** 0/416 annonces rattachées (tout l'aval DVF mort) et 72 % de l'inventaire marqué « retiré » par l'ancienne chaîne de fausses suppressions jamais nettoyée.
4. **NU-E-001/002/003 — Le résiduel/constructible est incohérent et périmé.** Deux valeurs de SDP résiduelle dans la même fiche (68 vs 64), un run servi vieux de deux mois (22/25 parcelles fausses, écarts jusqu'à ×54), et trois capacités selon le chemin d'assiette.
5. **NU-E-046/047 — Le Copilote invente des verdicts.** Il affirme « cette parcelle n'est pas en copropriété » sur une copro avérée, parce que le verrou anti-invention ne contrôle que les nombres, jamais les affirmations qualitatives.

**Ce que je changerais en premier, dans l'ordre :**

1. **Réparer l'unité de l'estimation (NU-E-021/022) avant tout.** Multiplier par une surface habitable (ou ne servir que le €/m² sans total), et lire la nature sur la mutation, pas sur la parcelle. C'est une faute de produit, pas une finition : la valeur affichée est fausse pour l'écrasante majorité des biens bâtis et pour la moitié des terrains. Tant que ce n'est pas corrigé, l'argumentaire « précision » doit disparaître.
2. **Unifier les sources de vérité.** Une seule emprise bâtie servie (NU-E-052), un seul résiduel (NU-E-001), un seul chemin d'assiette (NU-E-003), un seul prédicat de nature DVF (NU-E-030/036). Aujourd'hui chaque fait existe en 2–3 exemplaires qui se contredisent sur la même fiche.
3. **Rafraîchir et recâbler ce qui est figé/débranché.** Promouvoir un run résiduel récent (NU-E-002), restaurer puis reconfirmer le Radar et rebrancher le rattachement (NU-E-038/039), relier le cache DVF au millésime (NU-E-032).
4. **Refuser au lieu d'inventer.** Copilote : outil déterministe pour copro/constructibilité, refus explicite sinon (NU-E-046/047). Implantation : refuser en RNU plutôt qu'inventer « UA » (NU-E-055).
5. **Mettre à jour le droit et rendre les hypothèses visibles.** Stationnement à 800 m (loi 2025-1129, NU-E-056), hauteur réelle vs forfait 3 m (NU-E-059), et afficher sur le chiffre de tête les coefficients cachés (occupation 45 %, R+1 supposé, surface géométrique étiquetée « cadastre »).

*Conduite d'audit : lecture seule respectée — mes recalculs sous `default_transaction_read_only=on`, aucune écriture métier, aucun accès prod, aucune CLI mutante. L'API a servi ses caches de lecture normalement contre la base locale.*
