# V8-VERIF — Rapport (résultats bruts A + C)

> Lecture seule. Aucun fichier de production modifié, aucun recalcul, aucune purge, aucun rollback.
> Branche dédiée `verif/v8-calibre`. **Points A et C rendus ; B NON abordé (gated derrière feu vert A).**
> Boussole : les écarts sont rapportés tels quels, non lissés.

---

## POINT D'ARRÊT A — provenance des 85 537 reprises (BLOQUANT)

### A.1/A.2 — horodatage + version de code, par commune (run `q_v8_calibre`)
Journalisation disponible par ligne : `dryrun_parcel_evaluations.created_at` (horodatage d'écriture)
+ `.rules_version` (hash de config de règles) ; `dryrun_cascade_results.created_at`. **Pas de SHA de
CODE git par ligne.**

**`rules_version` = `b5b513abae46` — IDENTIQUE sur les 431 663 lignes / 24 communes** (reprises
comprises : Saint-Paul, La Possession, L'Étang-Salé, Saint-Pierre).

**Horodatages `created_at` par commune (ordre chronologique) :**
- Saint-Paul : 29/07 **19:09:38 → 19:50:37**
- *(écart de 1 h 17 min 39 s)*
- La Possession 21:08 → L'Étang-Salé 21:21 → Saint-Pierre 21:30→22:22 → Le Tampon 22:22 → … →
  Cilaos 30/07 **00:44 → 00:47**.
- **Toutes les transitions inter-communes = quelques secondes à ~1 min (continues), SAUF l'écart
  unique de 1 h 17 min entre Saint-Paul (fin 19:50) et La Possession (début 21:08).**

**Écart constaté, rapporté tel quel (non expliqué)** : `parcel_residuel` (lu par la couche
`residuel_socle` de la cascade) porte un `computed_at` postérieur (22:08) à la cascade de Saint-Paul
(19:09). Cela signifie que la migration de `parcel_residuel` a (ré)écrit après que Saint-Paul a été
cascadé. `migrate_residuel` étant déterministe (copie de `parcel_residuel_rerun WHERE dispo_rerun`,
253 328 lignes constantes), le CONTENU est le même à chaque migration — mais le fait est signalé.

### A.3 — comparaison reprises vs communes post-refonte
- `rules_version` : **IDENTIQUE** (b5b513abae46) entre reprises et communes calculées après refonte
  (Le Tampon, Saint-Denis, Cilaos).
- Header du run de score `q_v8_calibre` : `model_sha256 = 00a58008143d5260…` = **le champion figé
  INCHANGÉ** (identique à q_v6_m8/q_v7_defisc) ; `computed_at` 30/07 00:48 (après la fin de cascade
  00:47), durée 240 s → le scoring a tourné UNE fois, à la fin, avec l'artifact gelé.

### A.4 — le code producteur N'EST PAS journalisé ligne à ligne (dit explicitement)
`rules_version` est un hash de la **CONFIG de règles** (YAML), **PAS un SHA de code git**. Le refonte
a modifié le **CODE** (cache pré-subdivisé de `prime` dans `context.py`, commit dbca5ab **29/07
19:44**), sans toucher les règles YAML → `rules_version` reste identique et **ne prouve donc PAS
l'identité du code par ligne**. Je ne l'infère pas.

**Éléments circonstanciels (rapportés, non concluants seuls) :**
- Le script de bascule **refondu** (cascade native, commit f657e63) est daté **29/07 17:06**, soit
  AVANT la première écriture de cascade (Saint-Paul 19:09). La refonte de la re-passe existait donc
  avant toute ligne.
- Le seul changement de CODE de cascade PENDANT le run est le cache `prime` (dbca5ab, 19:44). J'ai
  mesuré ce changement dans un mandat précédent : coverage **bit-identique** (écart 0,0). Saint-Paul
  (19:09–19:50) chevauche ce commit ; un process en cours ne recharge pas son code → Saint-Paul a
  été produit par la version « à la volée », les communes tardives par la version « cache » —
  **résultat prouvé identique**, mais ce sont deux états de code.

**VERDICT A : NI « IDENTIQUE » NI « DIVERGENT » prouvés par la journalisation** — le code n'est pas
tracé par ligne (seul un hash de config l'est, et il est identique). La preuve définitive exige le
**CONTRÔLE DE SUBSTITUTION**, que je PROPOSE et n'exécute pas (interdit : aucun recalcul sans
validation) :

> Recalcul À BLANC de 50 parcelles reprises (échantillon Saint-Paul, la seule reprise pré-écart)
> dans un label isolé, comparaison des champs DÉTERMINISTES (`matrice_statut`, `q_score`, `a_score`,
> et le multiset `(layer, result, weight_applied)` par parcelle) avec les valeurs stockées de
> `q_v8_calibre`. Champs non déterministes connus (ordre des lignes `risques`/`zonage`, cf. note
> non-déterminisme) exclus de la comparaison bit-à-bit. IDENTIQUE ⇒ les reprises = ce que le code
> courant produit ⇒ équivalence d'ÉTAT prouvée (Principe 6). DIVERGENT ⇒ arrêt.

**→ S'ARRÊTE ICI. Attente feu vert Vic pour le contrôle de substitution. B NON abordé.**

---

## POINT C — état git (parallèle de A)

`origin/main` HEAD = `4bc610f` (merge de `mesure/repli-non-optimiste-phaseA`, jusqu'à `9aae96a`).

**SUR origin/main (mergé) :**
- Correctif « tête de liste » : `constructibilite.py` ✓, `statuts.py` (DECLASSE_ZONE_FERMEE ×3) ✓.
- `compute_bilan_servi` (charge foncière) : `bilan.py` ✓.

**ABSENT de origin/main (RISQUE — garde n°4 / Principe 7) :**
- **`scripts/bascule_v8_calibre.py` — ABSENT.** Le script qui a PRODUIT le run q_v8 n'est pas sur main.
- **`context.py` sur main N'A PAS le cache `spatial_layers_sub`** (0 occurrence) — c'est la version
  « prime à la volée », PAS celle (cache) qui a produit q_v8. Le code de cascade qui a produit q_v8
  diffère de celui de main (résultats prouvés identiques, mais code différent).
- **18 commits locaux absents de origin/main**, dont TOUS les commits critiques de la bascule :
  `164a6c5` (scripts bascule), `4d95402` (fix KeyError), `eb1ce17` (fix varchar), `f657e63` (script
  refondu), `dbca5ab` (perf cache), `46a2b02`+`edb57bb` (gardes), `ad872ce`+`2585626` (rollback/golden),
  + les notes et nettoyages. Liste complète en annexe.

**Branches non mergées dans origin/main** (extrait) : `mesure/repli-non-optimiste-phaseA` (au-delà de
9aae96a), `mesure/cout-par-taille-phaseA`, `mesure/couverture-prix-phase-a`,
`mesure/prix-sortie-consommateurs-A`, `verif/v8-calibre`, + plusieurs `origin/*` anciennes.

**Constat C (Principe 7)** : le run servi candidat `q_v8_calibre` a été produit par du code
(script de bascule + cache cascade) qui **n'est pas sur `origin/main`**. La garde n°4 (« code
d'application sur main ») n'est pas satisfaite pour la chaîne de bascule. Aucun merge effectué
(interdit respecté) — c'est un constat, pas une action.

---

*Aucune modification servie. `q_v7_defisc` (run servi actuel) intact : 120/1031/3587/72980/353945.
Scripts de vérification : requêtes SQL consignées dans `scripts/verif_v8_provenance.sql`.*

---
# EXTENSION — A', A'', C' (30/07)

## A' — parcel_residuel (incident traité)
- **A'.1** : `parcel_residuel` a **UNE seule valeur de `computed_at` = 29/07 22:08:46** sur les
  253 328 lignes → la table entière a été (ré)écrite en un seul `migrate`, en cours de cascade.
- **A'.2** : cascadées **AVANT 22:08** (ont lu le residuel ensuite écrasé) = **Saint-Paul,
  La Possession, L'Étang-Salé** (+ les 12 000 premières de Saint-Pierre, cf. A''). **APRÈS** = les
  21 autres. Les reprises = exactement les communes pré-22:08.
- **A'.3 (par le code)** : la CASCADE `residuel_socle` lit `parcel_residuel` **EN DIRECT au calcul**
  (`etage0_ext.py:156` → `context.residuel_sdp` : `SELECT … FROM parcel_residuel WHERE parcel_id=…`).
  Le SCORING P lit `p_model_static` (copie **FIGÉE** construite par `build_static` au début du run
  final, `sql.py:261-263,290`). Donc : les reprises ont lu le residuel pré-22:08 pendant leur
  cascade ; le scoring a lu la copie figée post-22:08 pour tout le monde.
- **A'.4 (identité de contenu, pas déterminisme)** : checksum md5 du `parcel_residuel` ACTUEL
  (22:08) = **`15f769ae…`** = checksum du recompute déterministe depuis la source
  `parcel_residuel_rerun WHERE dispo_rerun` (**IDENTIQUE**). Le contenu 22:08 est donc exactement
  l'image de la source, prouvé par checksum. **La version pré-22:08 est écrasée (un seul
  computed_at) → non checksummable directement** ; son identité au contenu 22:08 est prouvée
  INDIRECTEMENT par A'' (le residuel_socle des reprises == recompute avec le residuel 22:08).
  (`parcel_residuel_rerun` n'a pas de colonne d'horodatage — artefact de mesure statique.)

## A'' — Contrôle de substitution — VERDICT : **IDENTIQUE**
- **Point de coupure identifié** : dans Saint-Pierre, **gap de 26 min 08 s** entre la ligne 12000
  (~21:43, dernière reprise) et la ligne 12001 (**parcel_id 104372**, 22:09:19). **12 000 avant /
  30 425 après.** C'est le seul endroit où deux exécutions se touchent (le `parcel_residuel` a été
  réécrit à 22:08 pendant ce gap).
- **Échantillon** : 80 parcelles — 15 Saint-Paul, 10 La Possession, 10 L'Étang-Salé, 45 Saint-Pierre
  (20 juste avant la coupure + 20 juste après + 5 ailleurs). Recompute à blanc, label isolé.
- **Commit du recompute : `c867eec`** (HEAD verif/v8-calibre : cache prime + tous les fix).
- **Précondition prouvée (par le code) avant d'ignorer l'ordre** : le seul aspect non déterministe
  est l'**ORDRE physique des lignes** risques/zonage. `compute_matrice` (`dryrun.py:50-56`) agrège
  par `bool_or(HARD_EXCLUDE)` + `sum(weight)` + `bool_or(evenement)` — **ordre-indépendants**. Le
  tier servi (`pipeline.py:239`) = `status IN (exclue,faux_positif)` (result) + P + déclassement
  faisabilité — pas le detail/ordre. Donc l'ordre n'alimente **ni matrice, ni q/a, ni tier, ni
  chiffre servi**. Comparaison faite sur le **multiset complet** (layer, result, weight, **detail**)
  + matrice_statut/q/a ; seul l'ordre physique est ignoré. **Rien n'est exclu à tort.**
- **Résultat : 80 comparées, 0 DIVERGENTE.** Multiset (detail inclus) ET matrice/q/a identiques,
  reprises comme fraîches, de part et d'autre de la coupure.
- **CONCLUSION A (résolue)** : les 85 537 reprises sont **équivalentes en ÉTAT** (Principe 6, pas
  inféré de l'effet) à ce que produit le code courant. L'« ancien script défectueux » (qui n'écrivait
  aucune cascade) est écarté ; les deux états de code intra-run (à-la-volée / cache) sont prouvés
  résultat-identiques ; le residuel pré-22:08 a produit le même residuel_socle que le 22:08.
  **Verdict : IDENTIQUE. La base v8 n'est plus suspecte sur ce point.**

## C' — préparer le merge (NE PAS merger)
`origin/main` (4bc610f) est **incohérent pour le chemin servi** tant que la branche n'est pas mergée :
- `pipeline.py` sur main = version **buguée** (`df["label"]`, KeyError) — `parcel_constructibilite`
  existe (11 782 lignes) → un scoring sur main **planterait**. Fix = `4d95402`.
- `models.py` sur main : `tier varchar(24)` → `declasse_non_constructible` (26 car.) **déborde**.
  Fix = `eb1ce17`.
- golden sur main = **réaligné** (realign_m26 ×12) mais revert `ad872ce` absent → golden échoue
  contre le run servi q_v7.

**Les 19 commits (origin/main..HEAD), classés :**

| hash | change (1 ligne) | chiffre servi | chaîne q_v8 |
|---|---|---|---|
| `4d95402` | fix KeyError merge déclassement (pipeline.py) + test | **OUI** (corrige break latent main) | OUI |
| `eb1ce17` | tier/statut varchar 24→32 (models.py) | **OUI** (corrige débordement main) | OUI |
| `dbca5ab` | cache prime ×6 + matrice nested-loop (context/models/dryrun) | non (résultat bit-identique prouvé) | OUI |
| `ad872ce` | golden — retour arrière 12 ancres | non (réf test) — **requis cohérence golden↔q_v7** | non |
| `9cf351c` | commentaires q_v6_m8 → Q_A_RUN_LABEL | non | non |
| `164a6c5` | scripts bascule+rollback initiaux + doc | non | OUI |
| `f657e63` | bascule refondu (cascade native + auto-vérif) | non | OUI |
| `46a2b02` | gardes bascule (disque + journal) | non | OUI |
| `edb57bb` | garde disque exacte FSM | non | OUI |
| `2585626` | fix rollback (snapshot par snapshot_id) | non | non (outil undo) |
| `2dea488` | en-têtes DÉPENSÉ scripts one-shot | non | non |
| `90eab34` `fc64071` `4f2fe89` `e1ac1db` `3b9022b` `6e78d4e` `a5f835f` `c867eec` | docs/notes/rapports de mandat | non | non |

**Ordre de merge recommandé** : la branche est une continuation LINÉAIRE de `9aae96a` (que main
contient via 4bc610f). `merge-tree origin/main HEAD` **exit 0 — zéro conflit**, et l'intersection
des fichiers modifiés des deux côtés depuis la base est **VIDE**. → **un seul `git merge --no-ff
verif/v8-calibre`** suffit, sans conflit anticipé. Si Vic veut un sous-ensemble « servi d'abord » :
`4d95402` + `eb1ce17` + `ad872ce` sont le trio qui **restaure la cohérence du chemin servi sur main**
(sans eux, main plante au scoring et le golden ne passe pas) — à ne pas dissocier du déclassement
déjà mergé. **CC ne merge pas ; Vic merge en --no-ff.** (Principe 7 : la purge de q_v6_m8 et le run
v8 ne sont acquis que quand ces correctifs sont sur main.)

---
*A' et A'' résolus (VERDICT IDENTIQUE). B reste FERMÉ jusqu'à ton arbitrage. Aucun merge, aucune
relance, aucune purge. q_v7_defisc servi intact.*

---
# POINT B — gardes de complétude (exécuté sur origin/main 7b067f7)

## B.1 — tiers servis q_v8_calibre vs cibles (écart par ligne, brut)
| Tier | Cible | Réel | Écart |
|---|---:|---:|---:|
| Brûlantes | 120 | 120 | **0** |
| Chaudes | 1 042 | 1 043 | **+1** |
| Réserve foncière | 3 208 | 3 209 | **+1** |
| À creuser | 63 949 | 63 964 | **+15** |
| Écartées | 353 945 | 354 355 | **+410** |
| Déclassée « zone fermée » | 3 221 | 2 804 | **−417** |
| Déclassée « inconstructible » | 6 178 | 6 168 | **−10** |
| **TOTAL** | **431 663** | **431 663** | **0** |
Total exact. Écarts sur 6 lignes/7 — le plus grand : `declasse_zone_fermee` −417, `ecartee` +410.
Rapporté brut, non corrigé, non expliqué.

## B.2 — golden : **107/116 PASS, 9 FAIL, 0 incohérence runtime**
Les 9 FAIL sont TOUS sur `db.residuel` (capacité), AUCUN sur un tier (`tier_v2` passent — le revert
`ad872ce` a restauré les attentes de tier à l'état q_v7). Ancres en échec (brut, non ajusté) :
- 97402000AK1725 (taux_emprise_pct 49→61)
- 97408000AC1870 (sdp 3553→1870)
- 97416000CR1351 (residuel : golden présent → DB **absent**)
- 97418000AT2379 (sdp 108→146)
- 97420000AO0654 (sdp 176→117)
- 97422000AD1237 (residuel : golden présent → DB **absent** ; = golden brûlante 2AUd)
- 97423000AB1341 (sdp 199→133)
- 97423000AB1908 (sdp 183→122)
- 97424000AI0355 (taux 27→28 ; sdp 395→209)
Constat brut : `parcel_residuel` en base = version CALIBRÉE v8 (migrée par la bascule, non
rollbackée) ; le snapshot golden porte les valeurs d'AVANT calibration → 9 écarts de capacité.
Rien ajusté.

## B.3 — Saint-Benoît (21 671 parcelles)
- **Capacité renseignée** (ligne `parcel_residuel`) : **12 000**
- **Muettes** (aucune ligne `parcel_residuel`) : **9 671**
(interprétation : capacité renseignée = présence d'un résiduel calculé ; muette = absence.)

## B.4 — O12 : 35 candidats
- **35 présents** après bascule (0 sorti, 0 entré vs capture pré-bascule `/tmp/o12_avant.txt`).
- **`computed_at` = 28/07** pour les 35 → la table `division_or_candidates` **n'a PAS été recomputée
  par la bascule** ; les 35 sont inchangés.
- **EXPOSE = True** — c'est une CONSTANTE de code (`division_or.py:55`, validée Vic 28/07), globale
  (pas une colonne par ligne) → les 35 sont exposés.
- 35 idus : 97403000AR1521, 97409000AR2367, 97410000AV0207/BK0219/BM1144, 97411000CH0320/CH0631,
  97412000AH0413/AM0461/AM0946/BE0229/BW0123/CS0625, 97413000CM0268/CQ0412/CR0068/CR0093/CX0585,
  97414000ES0629, 97415000AX1059/BV0182/CH1198/CP0511/DS0617/HO0423, 97416000DM0665/HX0339/ID0021,
  97418000AO1527/AV2092, 97420000BH1036, 97422000CL0575/CY0118, 97423000AH1514, 97424000AE0089.

---
*B exécuté sur origin/main 7b067f7. Rapporté brut, rien corrigé, rien mergé. q_v7_defisc servi intact.*

---
# B-PRIME — qualification des écarts (lecture seule, sur origin/main 7b067f7)

## B'.1 — les 427 (mécanisme prouvé par le code)
- Les 427 étiquetées A/B dans `parcel_constructibilite` mais tier q_v8 ≠ déclassé sont **TOUTES
  passées en `ecartee`** (417 A « zone fermée » + 10 B « inconstructible »). **ZÉRO en
  chaude/réserve/à-creuser.**
- **Mécanisme (code)** : `assign_tiers` (statuts.py:118-120) affecte le tier déclassé PUIS
  `tier[ecartee_etage0] = TIER_ECARTEE` en **dernier** → écartée écrase déclassé. Et la bascule
  fixe `LABUSE_ETAGE0_RUN=q_v8_calibre` (bascule:189 → pipeline:236) : l'étage 0 est lu sur la
  cascade CALIBRÉE de q_v8, où **M6 2b hard-exclut les zones interdit-avec-hauteur** (UE/Uem/US/
  UCtom + AU* transition). Vérifié : **427/427 sont hard-exclues (status exclue/faux_positif) à
  l'étage 0 de q_v8.** La cible (jetable) lisait l'étage 0 de q_v7 (pré-calibration, sans ces
  exclusions) → d'où l'écart. C'est cohérent : une parcelle hard-exclue par la cascade calibrée
  est écartée (exclusion forte), pas seulement déclassée.
- **B'.1.1 (les +17 en tiers normaux)** : ce ne sont PAS des déclassées perdues (0 déclassée en
  tier normal, prouvé). Ce sont des parcelles constructibles re-classées vs la cible. **Je ne peux
  PAS les nommer par IDU** : la cible était un run jetable (supprimé), non persisté par IDU, et ses
  comptes diffèrent même légèrement des cibles du mandat (chaude 1042 vs 1043 mesuré). Je le dis
  plutôt que d'inventer une liste.
- **B'.1.2** : les 417 (A) sont en zones économiques habitat-interdit (UE 105, UCtom 37, US 33,
  Uem 33, Ue 31, UCto 20…) + AU* transition ; les 10 (B) inconstructibles. Liste complète des 427
  par IDU : `docs/mandats/V8_BPRIME_427_ecartees.tsv`.
- **B'.1.3** : les 427 en `ecartee` sont **hors de toute liste servie** (écartée). **Leur motif
  reste consultable** sur la fiche : `flash/data.py::_constructibilite` lit `parcel_constructibilite`
  et pose `out["constructibilite"]={label,motif}` **sans condition de tier** → motif affiché même
  écartée.

## B'.2 — les 3 ancres + les 6 autres FAIL
- **97422000AD1237** (Le Tampon 2AUd, `calibree=True`) : golden résiduel 453 → DB **absent**.
  **Justifié OUI** : Art. 2.2.3 p.84 ferme 2AUd → non constructible → résiduel supprimé. **Tier q_v8
  = `declasse_zone_fermee` → n'est PLUS servie brûlante.** (correction visée du défaut d'origine.)
- **97418000AT2379** (Sainte-Marie U, `calibree=False`) : 108 → 146. Aucune règle PLU changée (zone
  générique 9 m) → recompute résiduel. **Justifié : indéterminé.** Toujours brûlante, constructible.
- **97424000AI0355** (Cilaos « 86 » → AUst, `calibree=False`) : 395 → 209. Zone AUst (Art. AUst
  p.53-56) mais non calibrée. **Justifié : indéterminé.**
- 6 autres FAIL, cohérence avec le calibrage (une ligne) : AK1725 (Bras-Panon U) sdp 0→0, taux
  49→61 ✓ ; AC1870 (La Possession UBc **calibré**) 3553→1870 ✓ ; CR1351 (Saint-Pierre AU)
  3903→absent (devenu non constructible) ✓ ; AO0654 (Sainte-Suzanne UC **calibré**) 176→117 ✓ ;
  AB1341/AB1908 (Trois-Bassins 1AUb **calibré**) 199→133 / 183→122 ✓.

## B'.3 — le « plafond » à 12 000 : PAS une troncature
- Par commune (23, **Saint-Philippe absente = 0 résiduel, RNU**) : comptes variés (Saint-Paul 31957,
  Saint-Pierre 27489…) ; **Saint-Benoît = 12 000 exact, seule ronde.**
- **Débunké** : parcel_residuel_rerun Saint-Benoît = 12 238 total, **12 000 disponibles** (238
  devenues non-constructibles au recompute) ; l'ancienne parcel_residuel (29/06) = 12 238. Donc
  **12 000 = 12 238 − 238, rond par COÏNCIDENCE.** Aucun `12000`/`LIMIT`/cap dans le code
  (migration + résiduel ; seul `chunk=2000` de commit, sans effet sur le total).
- **Verdict B'.3.4** : les 9 671 muettes = **6 928 en A/N** (absence RÉELLE, non-constructible
  légitime) + **2 743 en U/AU** (dette « muettes en capacité » — zones urbaines sans résiduel, à
  investiguer). **Ni cap, ni troncature.**

## B'.4 — O12 contre v8 : les 35 seraient INCHANGÉS
- La détection division_or (division_or.py:181-282) lit **géométrie** (surface 1000-6000, bâti,
  résiduel free_m2, cercle inscrit, compacité, façade, solidité) + `_emprise_max_sql` = seuil
  `emprise_sol_pct` du **YAML calibré** (`load_rules`, l.670-684). Elle NE lit NI `parcel_residuel`,
  NI le run/tier, NI la constructibilité résolue. Géométrie statique + YAML inchangé depuis le
  27-28/07 (avant le calcul du 28/07) → **un recompute contre q_v8 rend les mêmes 35** (la bascule
  n'a touché aucun input de la détection). (Non relancé : interdit « recomputer une table servie »,
  pas de mécanisme de label isolé dans division_or ; conclusion étayée par le code.)
- **B'.4.3 — à revoir visuellement par Vic** : 3 candidats dont la parcelle est désormais
  NON CONSTRUCTIBLE en v8 (candidat géométrique O12, mais foncier fermé/inconstructible) :
  **97410000BK0219** (declasse_non_constructible), **97414000ES0629** (declasse_non_constructible),
  **97416000HX0339** (declasse_zone_fermee). Secondairement, 11 des 35 sont désormais `ecartee`
  (hard-exclues cascade : risque/foncier public/interdit) — à regarder aussi.

---
*B-PRIME lecture seule, rien corrigé, rien mergé, rien recomputé sur table servie. q_v7_defisc servi
intact. Artefact : V8_BPRIME_427_ecartees.tsv.*

---
# MANDAT O12-GARDE — garde de constructibilité (code posé, table servie INTOUCHÉE)

## Garde ajoutée (code) — division_or.py
Filtre AMONT dans `_DETECT` : un candidat dont la parcelle SUPPORT est (a) hard-exclue à l'étage 0
du RUN SERVI (`:served` = `Q_A_RUN_LABEL` → **suit automatiquement toute bascule future**), OU
(b) marquée non constructible (`parcel_constructibilite` declasse_*), n'est PAS candidat.
Robuste : la garde (b) retombe sur `true` si `parcel_constructibilite` absente. Code posé sur la
branche ; la table servie `division_or_candidates` **n'est PAS recomputée** (point d'arrêt).

## Recompte à blanc (mesure, sans écriture sur la table servie)
Sur les 35 candidats : **14 tombent, 21 survivent** (mêmes 14 sous q_v7 servi actuel et sous q_v8) :
| verdict | n | idus |
|---|---|---|
| DROP — non constructible (declasse_*) | 3 | 97410000BK0219, 97414000ES0629, 97416000HX0339 |
| DROP — écartement définitif (PPR rouge / foncier public) | 8 | CH0320, AM0461, CM0268, CR0068, CH1198, CP0511, DS0617, CL0575 |
| **ARBITRAGE — « déjà bâti » (faux_positif_probable)** | 3 | 97415000BV0182, 97418000AV2092, 97420000BH1036 |

## Motifs des 11 écartés (point 4)
- **5 PPR zone rouge inconstructible** (CH0320, CM0268, CR0068, DS0617, CL0575) → drop clair.
- **4 propriété publique non-acquérable** (AM0461, CM0268 aussi, CH1198, CP0511) → drop clair.
- **3 « déjà bâtie probable » 31-40 %** (BV0182, AV2092, BH1036) → `faux_positif_probable`.
  **DÉFENDABLES** : O12 vise précisément le bâti-dans-un-coin avec résiduel détachable ; le
  hard-exclude « déjà bâti » de la cascade entre en TENSION avec la raison d'être d'O12. **Ta
  décision** : la garde (status IN exclue/faux_positif) les drop ; faut-il la restreindre à
  `status='exclue'` (définitif) pour GARDER ces 3, motif servi ? Non tranché par moi.

## Revue visuelle (point 5)
Manifeste des 14 candidats dont l'état a changé depuis la revue du 28/07 :
`docs/mandats/O12_GARDE_REVUE_MANIFEST.txt` (idu, commune, motif, verdict garde). À revoir
visuellement avant exposition.

## Point d'arrêt
Garde CODÉE, table servie `division_or_candidates` INTOUCHÉE, aucune bascule. En attente :
arbitrage sur les 3 « déjà bâti » + revue visuelle → puis recompute O12 + bascule q_v8.

---
# O12-GARDE — ARBITRÉE (Vic 30/07) : garde à `status='exclue'` seul

Garde restreinte : `faux_positif_probable` RETIRÉ du critère de drop (probabilité ≠ fait ; le
bâti-avec-résiduel EST la prémisse O12 — cohérent avec l'arbitrage bâti du 29/07). Code : `_DETECT`
→ `de.status = 'exclue'` (+ `parcel_constructibilite` declasse_*).

**Recompte à blanc CONFIRMÉ : 24 candidats survivent, 11 tombent (définitifs).**
- **GARDÉS (arbitrage, +3)** : 97415000BV0182 (Saint-Paul, résiduel 520, bâti 40 %),
  97418000AV2092 (Sainte-Marie, 535, 32 %), 97420000BH1036 (Sainte-Suzanne, 883, 30 %) — « déjà
  bâti » (faux_positif_probable), désormais GARDÉS.
- **11 DROPS définitifs confirmés** : 3 non-constructibles (BK0219, ES0629, HX0339) + 8 PPR rouge /
  foncier public (CH0320, AM0461, CM0268, CR0068, CH1198, CP0511, DS0617, CL0575).

**Revue visuelle** : `O12_GARDE_REVUE_MANIFEST.txt` — les 3 « déjà bâti » EN TÊTE (rang 1), à
trancher en premier par Vic, ortho à l'appui. Table servie `division_or_candidates` **INTOUCHÉE**,
aucune exposition, aucune bascule.

---
# REVUE VISUELLE O12 — dossier des 24 cartes (garde appliquée à blanc)

**Correction de chemin (constat)** : `qa/division_or/gen_revue.py` n'existe NI en working tree, NI
dans git (toutes branches / historique), NI sur le disque. Le générateur réel est la commande
**`labuse division-or-review`** → `src/labuse/api/division_review.py::build_review_dossier`
(fond IGN ortho WMTS, PDF). C'est lui qui a produit les cartes de revue du 28/07.

**Généré** sur les **24 candidats retenus après garde** (35 − 11 drops), **BV0182 / AV2092 / BH1036
forcés en cartes 01 / 02 / 03**. Chaque carte : ortho IGN + contour parcelle + emprise bâti + lot
résiduel proposé + voirie (accès). Table servie `division_or_candidates` **INTOUCHÉE** (les 24 sont
sélectionnés à blanc, pas réécrits).

**Sorties** (`qa/division_or/revue_v8/`, JPEG q85 @140 dpi pour l'hygiène git ; PDF = les 24 d'un bloc) :
- **carte 01 — `qa/division_or/revue_v8/carte_01.jpg`** — 97415000BV0182 (Saint-Paul, résiduel 520 m², bâti 40 %, façade voirie du lot 22,3 m)
- **carte 02 — `qa/division_or/revue_v8/carte_02.jpg`** — 97418000AV2092 (Sainte-Marie, 535 m², 32 %)
- **carte 03 — `qa/division_or/revue_v8/carte_03.jpg`** — 97420000BH1036 (Sainte-Suzanne, 883 m², 30 %)
- dossier complet : `qa/division_or/revue_v8/dossier_revue_v8.pdf` (24 cartes)

Observation (non-verdict) : la carte 01 porte une façade voirie du lot de 22,3 m (> 0) → accès a
priori propre, pas enclavé ; **ta revue visuelle tranche.** Rien exposé, rien basculé.

---
# O12-REVUE-VIC — retours (lecture seule, table servie INTOUCHÉE)

## BLOQUANT carte 15 — AUh Saint-Denis (97411000CH0631) : NON RÉSOLU par les données
Le YAML calibre AUh avec ses articles DIMENSIONNELS : hauteur (Art. AUh.10, p.103), emprise 30 %
(Art. AUh.9, p.103), reculs (AUh.6/7), pleine terre (AUh.13, p.105). **Mais la calibration n'a PAS
extrait l'Article AUh.1/AUh.2** (occupations autorisées / caractère de zone) — là où se lit
l'ouverture ou la subordination à une modification/OAP. **Je n'ai pas le règlement source**
(« Modification simplifiée n°8, févr. 2024 », 154 p.) pour citer le verbatim exigé.
- **Signal (inférence réglementaire, PAS verbatim)** : AUh possède des articles de CONSTRUCTION
  complets (9/10/13) et ses propres chapitres (`zones_au_renvoi: {}`) ; `zones_au_st: []` (aucune
  zone de transition à Saint-Denis) ; les calibrateurs ont noté « conditionnelles à l'ouverture
  future » pour **AUx** mais RIEN pour AUh. Par convention PLU, une AU dotée de règles de
  construction complètes est ouverte (une 2AU fermée n'aurait pas d'Art. 9/10 chiffrés). **Cela
  suggère AUh ouverte — sans le prouver.**
- **Verdict : INDÉTERMINÉ sans le règlement.** Il faut Art. AUh.1/AUh.2 (ou « caractère de la
  zone AU ») du PLU Saint-Denis. **O12 reste non exposé** jusqu'à ce verdict (consigne respectée).
- **Balayage des 24** : **un SEUL candidat est en zone AU — carte 15 (AUh)**. Les 23 autres sont
  en U. Donc si AUh est fermée, seule la carte 15 sort. La garde « AU fermée = 2AU » est PRÊTE à
  poser, mais **butte sur une dette** : les YAML calibrent les DIMENSIONS des AU, pas leur STATUT
  d'ouverture → la garde ne peut pas distinguer AU ouverte/fermée sans que ce statut soit gravé.

## FAUX POSITIF carte 1 — 97415000BV0182 : SORT
Confirmé par les données : compacité 0,472 (la PLUS BASSE du pool), emprise lot restant 48 %,
144 m² de démolition. Sortira au recompute (avec la garde). Noté.

## Seuil de compacité — mesuré sur les 35
Les 3 « déjà bâti » sont les 3 compacités les plus basses : **0,472 (BV0182), 0,485 (BH1036),
0,505 (AV2092)** ; valeur suivante **0,563** (AM0946). **Gap net : ZÉRO candidat dans la zone grise
0,55-0,5629.** Un seuil de compacité minimale à **0,55 sépare proprement** les 3 du reste. Meaningful
uniquement sur la famille `libre`/`demolition` (terrain réel) — la famille `decoupe` est ≥ 0,608
(compacité auto-validée, cf. dette #6). **Mesuré, cohérent, mais 35 = petit échantillon → à
confirmer sur un pool plus large avant de graver** (comme demandé).

## Emprise du lot restant — par le code + par candidat
`_emprise_max_sql` (division_or.py:670) lit le `emprise_sol_pct` **CALIBRÉ** du YAML par zone (CASE),
sinon **repli générique 0,60** (`EMPRISE_RESTANTE_MAX`). Donc calibré pour les zones au YAML, repli
sinon. Cartes signalées (emprise restante vs emprise max appliquée) :
- **Carte 2** — AV2092 (UB Sainte-Marie) : 56 % vs **70 % CALIBRÉ** (Art. calibré) → conforme réel ✓
- **Carte 3** — BH1036 (UB Sainte-Suzanne) : 56 % vs **60 % GÉNÉRIQUE** (UB Sainte-Suzanne NON
  calibrée) → vérifié contre le repli, **PAS contre le réel** → **recontrôle requis** (défaut repli
  générique) : besoin de l'emprise max réelle de UB Sainte-Suzanne (article).
- **Carte 1** — BV0182 (U6c) : 48 % vs 60 % générique — mais faux positif, sort.
- **Carte 23** — ID0021 (Ug Saint-Pierre) : 43 % vs **50 % CALIBRÉ** → conforme réel ✓
(Les 24 sont tous ≤ leur max appliqué ; le risque est confiné aux zones en repli générique — 12/24,
dont BH1036 est la seule proche du seuil.)

## Douteux — aucun hard-exclu par la cascade (à contrôler visuellement/manuellement)
- **Carte 7 (97416000DM0665, Saint-Pierre)** : `owner_type='pm'` (personne morale), **PAS flaggé
  foncier public** (hors groupes DGFiP publics) ; contexte piste d'athlétisme à l'ortho → contrôle
  MANUEL de la dénomination du propriétaire requis (dénomination non disponible en base).
- **Carte 16 (97412000CS0625, Saint-Joseph)** : cascade = « Aléa mvt terrain FAIBLE » seul, **aucune
  exclusion PPR ni ravine** → la ravine SE vue à l'ortho n'est pas captée (soit hors buffer, soit
  data ravine incomplète) → contrôle distance lot↔axe ravine.
- **Carte 8 (97424000AE0089, Cilaos)** : « Aléa mvt terrain FAIBLE » seul, pas de PPR → à confirmer
  (Cilaos = cirque, risque mvt terrain sous-estimé possible).

## Dettes consignées (V8_DETTES_CONSIGNEES.md #5, #6)
5 · Aucun critère de PENTE (6/24 sur versant raide) → mesurer sur MNT IGN.
6 · Indicateurs auto-validés sur la famille `decoupe` (compacité→π/4, solidité→1) → ne présenter
compacité/solidité comme qualité que sur `libre`/`demolition`.

## État
18 recevables (dont 6 avec réserve de pente) — NON exposés avant : (1) verdict AUh carte 15,
(2) recontrôle emprise carte 3 (BH1036). Table servie INTOUCHÉE, rien basculé.

---
# O12-REVUE-VIC suites (arbitrages 30/07)

## DETTE #7 (prioritaire) — ouverture des AU non gravée : MESURÉE (run servi q_v7_defisc)
- 187 zones AU distinctes servies : **106 ouverture documentée, 81 NON**.
- **6 636 parcelles servies en AU à ouverture NON documentée** (3 829 génériques + 2 807 calibrées
  dimensions seules), dont **420 en tête de liste : 12 brûlantes, 172 chaudes, 236 réserve**.
- Même classe de risque que la 2AUd brûlante du 29/07, à l'échelle. Consigné dette #7 → à intégrer
  au mandat calibration (extraire Art. 1/2 des AU). Chiffres bruts, aucune correction.

## Carte 3 (Sainte-Suzanne UB) — TRANCHÉ : repli légitime, étiqueter Estimé
UB EXISTE au YAML Sainte-Suzanne, `emprise_sol_pct: null`, `emprise_src: "Art. U7, p.14 : « Sans
objet »"`. **L'article existe et ne plafonne PAS l'emprise** (« Sans objet ») → le repli générique
60 % est LÉGITIME → BH1036 conforme (56 % < 60 %), **carte 3 passe, à étiqueter « Estimé »**. Ce
n'est PAS une lacune de calibration (le YAML a correctement gravé « Sans objet » = null + source).

## Seuil compacité #4 — NON gravé ; mesure au pool large à faire
COMPACITE_MIN actuel = 0,25. Le gap 0,505 → 0,563 est observé sur les 35 seulement. Principe 4 :
un seuil dérivé d'une distribution se périme → à mesurer sur le pool large des **5 916 résiduels
bruts** (funnel 5916→294→…→35), pas sur 35. Mesure en cours (recompute géométrique à blanc, sans
écriture sur la table servie).

## Dette #8 — l'ortho voit ce que la cascade rate (cartes 16, 8) : consignée.

## #4 compacité — le gap 0,55 est un ARTEFACT de petit échantillon (mesuré au pool large)
Pool de **1 422 résiduels viables** (recompute géométrique à blanc, 24 communes, sans plancher
compacité ; 40× les 35 — le « 5 916 » du funnel est le brut AVANT filtres de viabilité, mon pool
applique free_m2≥500/rad≥9). **La compacité est un CONTINUUM lisse** :
`[0,45-0,50)=81 · [0,50-0,55)=98 · [0,55-0,60)=86 · [0,60-0,65)=87` — aucune rupture.
**105 candidats tombent dans l'ancien « gap » [0,505 ; 0,563)** (contre 0 sur les 35).
**Verdict : le gap 0,55 était une illusion de petit échantillon (Principe 4).** À l'échelle,
aucune coupure naturelle → un seuil de compacité serait une coupe ARBITRAIRE dans un continuum, pas
un séparateur. NE PAS graver 0,55. Si un plancher de compacité est voulu, il doit se justifier sur
le critère de forme acceptable (revue visuelle), pas sur un « gap ».

---
# MANDAT AU-OUVERTURE (dette #7 devenue bloquante) — lecture seule

## Étape 1 — cadrage : combien de règlements
- **51 zones AU non documentées portent les 420 têtes de liste, sur 18 communes.**
- **12 brûlantes → 6 zones / 4 communes seulement** : Saint-Benoît AUb19 (**7**), AUa5 (1) ;
  La Possession AUBm (1), AUAv (1) ; Saint-Denis AUm (1) ; Bras-Panon AU (1). **→ 4 règlements**
  résolvent les brûlantes.
- Table complète (zone × commune × tier × classe) : mesure ci-dessous, triée brûlantes d'abord.

## Étape 2 — deux positions d'attente (mesurées, non tranchées)
Les 420 se scindent : **107 « dimensions seules »** (règles de construction extraites → vraisembl.
OUVERTES) + **313 génériques** (statut PUR inconnu = cœur du risque).

| | Option a — laisser servi + mention « ouverture non vérifiée » (Absent) | Option b — déclasser temporairement |
|---|---|---|
| parcelles changeant de tier | **0** | **420** (12 brûl, 172 ch, 236 rés) |
| risque résiduel faux POSITIF | **420 servies non vérifiées** (12 brûlantes = risque max) | **0** |
| coût | risque concentré sur 313 génériques | jusqu'à **420 faux NÉGATIFS** (107 dimensions-seules probabl. ouvertes, gelées à tort) |

Observation (non-décision) : un HYBRIDE existe — déclasser les 313 génériques (inconnu pur),
laisser les 107 dimensions-seules servies-avec-mention. À toi de trancher a / b / hybride.

## Étape 3 — addendum calibration RÉDIGÉ (non exécuté)
`docs/mandats/ADDENDUM_CALIBRATION_AU_OUVERTURE.md` : extraire Art. 1/2 des AU (champ `ouverture`
+ `ouverture_src`), priorité aux 4 communes à brûlantes, garde-fou `a_verifier` si illisible.

*Rien exposé, rien basculé, rien déclassé. q_v7_defisc servi intact.*

---
# AU-OUVERTURE — arbitrage HYBRIDE (mesures avant application, RIEN appliqué)

## Mesure 1 — split des 12 brûlantes non documentées : CONFIRMÉ
- **11 génériques → à DÉCLASSER** : Saint-Benoît AUb19 (×6 : CD0905/0907/0939/0943/0897/0934/0893
  — en fait 7), AUa5 (AS1425) ; La Possession AUAv (BN3751), AUBm (AP1496) ; Bras-Panon AU (AD1052).
- **1 dimensions-seules → SERVIE + mention** : Saint-Denis AUm, `97411000KA0296`.
(Les 20 autres brûlantes en AU sont en zones DOCUMENTÉES — hors périmètre ; dont la 2AUd golden,
gérée par le tête-de-liste en q_v8.)

## Mesure 2 — la brûlante AUm Saint-Denis
`97411000KA0296`, **rang 7 / percentile 100** (7ᵉ parcelle servie de l'île). AUm = « dimensions
seules » : YAML a extrait Art. AUm.9 (emprise 50 %, p.98), AUm.10 (hauteur he 7/hf 10, p.98),
AUm.6/7 (reculs), AUm.13 (pleine terre) — **tous dimensionnels, aucun Art. AUm.1/2** (ouverture).
Vérifiable à la main : une brûlante de rang 7 sur une AU au statut non lu, servie AVEC mention.

## Mesure 3 — PROPOSITION de libellé (NON appliqué, attend ton feu vert)
Nouveau tier/label **`declasse_au_statut_inconnu`** (26 car., varchar 32 OK), DISTINCT de
`declasse_zone_fermee` (règlement ferme) et `declasse_non_constructible` (physique) : ici le statut
est INCONNU, la zone n'est pas fermée.
- **Motif fiche (déclassées, 313 génériques)** : « Zone à urbaniser — ouverture à l'urbanisation
  NON VÉRIFIÉE, statut inconnu. Le règlement de cette zone n'a pas été lu. Déclassement TEMPORAIRE
  jusqu'à vérification de l'article d'ouverture. » (Absent.)
- **Mention fiche (servies, 107 dimensions-seules)** — texte imposé Vic : « Zone à urbaniser —
  ouverture non vérifiée. Le règlement fixe des règles de construction pour cette zone, mais son
  ouverture à l'urbanisation n'a pas été confirmée. Vérifiez auprès de la commune avant tout
  engagement. » (Absent, jamais Estimé.)

### Plan d'intégration (esquisse, non exécutée)
1. Table `parcel_au_statut(idu, classe 'générique'|'dimensions_seules', zone_lib, computed_at)` —
   bâtie comme `parcel_constructibilite` (le classifieur = resolve_zone + zone AU + ouverture non
   documentée). Lit le run servi Q_A_RUN_LABEL, suit toute bascule.
2. `constructibilite.py` : constante `DECLASSE_AU_STATUT_INCONNU`.
3. `statuts.py::assign_tiers` : classe='générique' → tier `declasse_au_statut_inconnu` (prime sur
   tiers normaux, sous `ecartee`) ; classe='dimensions_seules' → RESTE servi (mention seule).
4. `flash/data.py::_constructibilite` : les DEUX textes ci-dessus selon la classe, étiquette Absent.
Effet mesuré (option hybride) : **313 déclassées** (11 brûlantes, 126 chaudes, 176 réserve) ;
**107 servies + mention** (1 brûlante AUm, 46 chaudes, 60 réserve). Temporaire par construction :
dès l'article lu, la parcelle remonte ou tombe définitivement.

## Ordre de lecture des règlements (Vic ce matin)
1. **Saint-Benoît** (AUb19 = 7 brûlantes / 12). 2. **Saint-Denis** (AUm brûlante + AUh carte 15 —
un seul règlement résout les deux). 3. **La Possession** (AUAv, AUBm). 4. **Bras-Panon** (AU).

*Rien appliqué, rien exposé, rien basculé, table servie intouchée. q_v7_defisc sert toujours.
Attend : feu vert sur le libellé `declasse_au_statut_inconnu` + verbatims des règlements.*
