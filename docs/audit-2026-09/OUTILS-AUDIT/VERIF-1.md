# OUTILS-VERIF-1 — Trois questions en lecture seule

Branche `audit/outils-verif-1` (depuis `main`). Lecture seule : aucune écriture code/base. Vérifs recoupées avec la base servie (`q_v11_m137`, psql local).

---

## Q1 — Solaire : le « 65° » — **KO 🟡 (libellé seul faux, productible juste)**

1. PVGIS reçoit `angle` (inclinaison) et `aspect` (azimut) DEPUIS LA CONFIG, pas `optimalangles` :
   `solaire.py:120-121` → `"angle": p["angle_deg"], "aspect": p["aspect_deg"]`, avec `config/solaire.yaml:9` `angle_deg: 15` et `:10` `aspect_deg: 180` (180 = plein nord, hémisphère sud). `optimalangles` n'est **jamais** appelé.
2. Deux « 65° » DISTINCTS qui coïncident sur cette parcelle :
   - « Orientation du bâti : 65° » = `f.azimut` = `parcel_solar.azimut_bati_deg` (azimut du bâti, ST_OrientedEnvelope), affiché `ProspectionSolaire.tsx:341`. C'est une vraie valeur mesurée par parcelle (929 parcelles ont az≈65° en base) — c'est un AZIMUT, pas une inclinaison.
   - « inclinés à 65° » du pied = **littéral en dur** `ProspectionSolaire.tsx:395` (« panneaux exposés plein nord et inclinés à 65° »). Rien ne le calcule ; il ne suit pas la config.
3. Le productible de `parcel_solar` a été calculé à **15°**, pas 65° : `angle_deg` vaut 15 depuis son introduction (commit `a6edc0ac`, 2026-08-23, même jour que le relevé porté sur la donnée) — jamais 65 dans l'historique. `prod_spec_kwh_kwc` servi = 950→1598 kWh/kWc/an, cohérent avec ~15° (un calcul à 65° l'effondrerait). Donc le chiffre est bon (15° ≈ optimum ~20° à 21°S) ; **seul le libellé du pied ment** — il annonce 65° et le présente comme « l'orientation qui capte le mieux ». **KO 🟡.** Correctif d'une phrase : remplacer le littéral 65° par la valeur config (15°).

---

## Q2 — Faisabilité, tri « par adéquation » — **KO (tri serveur inversé + troncature cachée)**

1. `POST /modules/programme` (`modules.py:1721`) calcule `marge_capacite = sdp_dispo/sdp_min` (≥1) puis trie **DÉCROISSANT** : `modules.py:1858` `items.sort(key=lambda x: -x["marge_capacite"])` (les plus SURDIMENSIONNÉES d'abord), puis tronque à `cap=200` (`modules.py:1863-1866`, `_moteurs_cap("programme_max",200)`).
2. Filtres = SDP résiduelle ≥ sdp_min (`modules.py:1748`), surface ≥ 0,4×sdp_min (`:1754`), tier ∈ brûlante/chaude/réserve/à-creuser (`:1755`), marge ≥ 1 (`:1830` `if sdp_dispo < sdp_min: continue`). **Aucun** filtre n'exclut les ×1–×24 : elles sont dans `items` et **comptées** dans `n = len(items)` (19 342, `modules.py:1889`). Mais elles ont une petite marge → en **bas** du tri décroissant → **hors des 200 servis** (`items[off:off+cap]`). Le compte (tout) et la liste servie (200 plus grosses) ne portent donc PAS sur le même sous-ensemble.
3. Le front (`M22Programme.tsx:91-99`) re-trie « adéquation » (×1–×3 en tête, puis marge croissante) **mais seulement sur les lignes déjà chargées** (commentaire :92) — c.-à-d. les 200 plus grosses marges. Les parcelles ajustées ×1–×3 n'ont jamais été envoyées : d'où « première ligne ×24,77 » (la plus petite marge PARMI le top-200) et « 200ᵉ ×488 » (la plus grosse). **KO** : les parcelles proches de ×1 existent en base et sont comptées, mais pas servies en tête — cause DOUBLE : tri serveur décroissant (opposé au libellé) + troncature top-200 qui décime les petites marges avant le tri « adéquation » du front. Correctif d'une phrase : trier serveur par |marge−1| croissant (ou paginer avant troncature).

---

## Q3 — Densifier, origine de « Surélévation » — **KO (valeur servie périmée, hors chaîne du moteur actuel)**

1. `GET /renouvellement/liste` lit la valeur affichée **directement dans la table batch** : `app.py:4998` `r.surelevation_possible, r.niveaux_surelevation` (SELECT sur `parcel_renouvellement`). Aucune jointure vivante. La fiche parcelle fait pareil : `_renouvellement_block` `app.py:3937` lit les mêmes deux colonnes de la même table (même scope run). Fiche et tableau sont donc cohérents ENTRE EUX.
2. Les deux colonnes sont bien LUES (liste + fiche) — donc pas code mort côté lecture. **Mais le batch les ÉCRIT en dur `false / NULL`** : `renouvellement.py:219-220` (`false AS surelevable, NULL::int AS niveaux_sur`) → INSERT `renouvellement.py:264/268` vers `surelevation_possible/niveaux_surelevation`. Le signal vivant (`faisabilite/potentiel.surelevation`) n'est pas rebranché (dette EXPORTS-1 assumée en commentaire :216).
3. **KO.** La chaîne moteur→écran est ROMPUE. Preuve base : `parcel_renouvellement` (run servi `q_v11_m137`) a `computed_at = 2026-09-04 17:36` et porte **42 639/67 260** lignes `surelevation_possible=true`, `niveaux_surelevation` non-null (max +10 niv.). Or le `false/NULL` en dur a été introduit le **2026-09-05** (commit `65767cb5`, exports-1 lot 3, mergé main `207f44b2`). La table servie précède ce code d'un jour : l'écran affiche des `+N niv.` RÉELS mais PÉRIMÉS, que le code actuel ne peut plus produire ; au prochain `build()` les 67 260 basculeront à « — ».
   → 🟠 n°3 d'OUTILS-AUDIT-1 : **maintenu comme dette**, mais son libellé (« colonne morte, ne dira jamais rien ») est **faux aujourd'hui** — la colonne n'est pas muette, elle sert des valeurs anciennes crédibles vouées à disparaître au prochain rebuild. Requalifier « colonne morte » → « valeur périmée hors chaîne, silencieusement fatale au rebuild ».
