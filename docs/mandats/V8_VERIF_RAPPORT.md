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
