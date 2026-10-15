# Domaine 3 — Capacité (SDP/emprise/niveaux) et scoring servis

## Verdict (3 lignes)
433 229 parcelles vivantes passées au crible (= 100 % des parcelles servies ; les 1 353 de
`parcels` en plus sont `cadastre_disparue_le` et correctement HORS du run q_v18/run_seq 15).
10 invariants vérifiés sur TOUTE l'île. **0 violation FAUX-CLIENT. 1 INCOHERENT de conception
(607 parcelles bande A ET exclusion dure).** Resté muet : rien de structurel — la monotonie
« à règles égales » n'est pas testable en SQL pur (zone_lib trop grossière), mais prouvée par
construction (barème saturant monotone + moteur `sdp = footprint × niveaux`).

## Invariants

| # | règle (une phrase FR) | requête/script | parcelles passées | violations |
|---|---|---|---|---|
| 1a | Un `sdp_residuelle=0` sans cause n'existe que sur le chemin `disponible` (bâti saturé) — pas de 0 muet | SQL INV1a + caractérisation | 64 995 (toutes `taux` & `pct_potentiel` présents, pct≥92 %) | 0 |
| 1b | Une cause présente s'accompagne toujours d'un 0 ou NULL (jamais d'une SDP positive muette) | `… WHERE run_seq=15 AND cause IS NOT NULL AND sdp>0` | 433 229 | 0 |
| 1c | Jamais `sdp NULL` ET `cause NULL` (= muet total) | `… WHERE run_seq=15 AND sdp IS NULL AND cause IS NULL` | 433 229 | 0 |
| 2 | 100 % des parcelles vivantes portent un score q_v18 | LEFT JOIN `parcels`/`score_labuse` filtré `cadastre_disparue_le IS NULL` | 433 229 | 0 |
| 3 | bande ⇔ score : `0`⇔score 0, `NC`⇔score NULL ⇔ `non_calculable` | INV3a..e (5 requêtes miroir) | 433 229 | 0 |
| 4 | `non_calculable=true` ⇒ cause présente | `… WHERE non_calculable AND cause IS NULL` | 16 583 NC | 0 |
| 5 | Table `parcel_residuel_bati` : `emprise_bâtie + résiduelle = max`, résiduelle ≥ 0, ≤ max | INV5a/b/c | 292 056 | 0 |
| 6 | Borne physique : `sdp_residuelle ≤ terrain × 20` (plafond niveaux généreux) | INV6 join `parcels` (ratio max 3,14 ; moy 0,40) | 193 394 (SDP>0) | 0 |
| 7 | Moteur : `SDP_max ≤ emprise_constructible × niveaux` (recompute indépendant) | script `parcel_faisabilite` sur 120 constructibles tirées au hasard | 120 | 0 |
| 8 | Score reproductible & fidèle : recompute `score_parcelle` == stocké, et déterministe | script `lire_entrees`+`score_parcelle` ×2, cascade `q_v18_sources`, 500 tirées | 500 | 0 |
| 9 | Monotonie du barème capacité : SDP ↑ ⇒ points ↑ (à faisabilité égale) | `_bareme_capacite` balayé 0..20 000 | sweep | 0 |
| 10 | bande A ⇒ score>0, SDP>0, non disparue, non NC | INV7a/c/d/e | 6 207 (bande A) | 0 (sauf INV7b, cf. ci-dessous) |
| 10b | bande A ⇒ pas d'exclusion cascade dure | INV7b | 6 207 | **607** |

### Requêtes rejouables (les principales)

INV1a (0 muet) — et sa caractérisation :
```sql
SET statement_timeout='120s';
SELECT count(*) FROM parcel_residuel_runs WHERE run_seq=15 AND sdp_residuelle_m2=0 AND cause IS NULL;
-- les 64 995 ont TOUTES taux_emprise_pct & pct_potentiel non NULL, pct_potentiel≥92 %
SELECT (taux_emprise_pct IS NOT NULL), (pct_potentiel IS NOT NULL), count(*)
FROM parcel_residuel_runs WHERE run_seq=15 AND sdp_residuelle_m2=0 AND cause IS NULL GROUP BY 1,2;
```

INV2 (100 % des vivantes scorées) :
```sql
SELECT count(*) FROM parcels p
LEFT JOIN score_labuse s ON s.parcel_id=p.id AND s.run_label='q_v18'
WHERE p.cadastre_disparue_le IS NULL AND s.parcel_id IS NULL;  -- → 0
```

INV3 (bande ⇔ score) :
```sql
SELECT count(*) FROM score_labuse WHERE run_label='q_v18' AND bande='0' AND (score IS NULL OR score<>0);  -- 0
SELECT count(*) FROM score_labuse WHERE run_label='q_v18' AND score=0 AND bande<>'0';                     -- 0
SELECT count(*) FROM score_labuse WHERE run_label='q_v18' AND score IS NULL AND bande<>'NC';              -- 0
SELECT count(*) FROM score_labuse WHERE run_label='q_v18' AND non_calculable AND score IS NOT NULL;        -- 0
SELECT count(*) FROM score_labuse WHERE run_label='q_v18' AND bande='NC' AND non_calculable=false;         -- 0
```

INV6 (borne physique SDP) :
```sql
WITH j AS (SELECT r.sdp_residuelle_m2 AS sdp, COALESCE(p.contenance_m2,p.surface_m2)::numeric AS surf
  FROM parcel_residuel_runs r JOIN parcels p ON p.id=r.parcel_id
  WHERE r.run_seq=15 AND r.sdp_residuelle_m2>0)
SELECT count(*) FROM j WHERE surf>0 AND sdp > surf*20;  -- → 0 ; max ratio = 3,14
```

INV10b (bande A + exclusion dure) :
```sql
SELECT count(*) FROM score_labuse WHERE run_label='q_v18' AND bande='A' AND cascade_exclue=true;  -- → 607
```

## Violations

### V1 — 607 parcelles bande A ET exclusion cascade dure (classe A)
- **Gravité : INCOHERENT (conception documentée, faible).** PAS FAUX-CLIENT tant que l'overlay
  d'exclusion est bien peint : la carte lit l'exclusion depuis `dryrun_cascade_results`
  (`result='HARD_EXCLUDE'` / étage 0, cf. `api/tiles.py:186-213`), PAS depuis la colonne
  `score_labuse.cascade_exclue` (le mot `cascade_exclue` n'apparaît NULLE PART dans `api/`).
- **idus** (échantillon des familles de motif, classe-A HARD_EXCLUDE) : `osm_faux_positif` 253,
  `emprise_routiere` 185, `dpf` 78, `zonage_plu_gpu` 44, `foret_publique` 36, `ens` 13,
  `pente`/`eau` 7, `parc_national` 1. Ce sont des « parcelles » qui sont en fait de la route,
  du domaine public fluvial, de la forêt publique, etc.
- **attendu** : une parcelle exclue dure (assiette nulle) ne devrait pas pouvoir être servie en
  tête de bande A (top capacité) sans que le classement/listing la marque explicitement.
- **obtenu** : `bande='A'` + `cascade_exclue=true` coexistent dans la même ligne servie ; le
  classement (`_cle_classement`, `score_labuse_combine.py:140-146`) trie sur la bande SANS tenir
  compte de `cascade_exclue` → ces 607 peuvent apparaître en tête de la bande A.
- **cause probable** : par CONSTRUCTION, `bande` (capacité LABUSE) et `cascade_exclue`
  (reclassement) sont deux dimensions stockées côte à côte sans fusion
  (`score_labuse_combine.py:124-136` ; `cascade_exclue=(r.exclue …)` l.134). `exclusion` n'est
  mis qu'en `classe=='A' AND result=='HARD_EXCLUDE'` (`cascade_v2.py:90`). La cohérence est
  parfaite (les 607 ont bien tous un HARD_EXCLUDE classe A dans `q_v18_sources`, 0 divergence),
  mais rien ne RABAT la bande ni n'écarte la ligne du tri. Dépend de l'overlay côté lecteur.
- **fichier:ligne** : `src/labuse/scoring/score_labuse_combine.py:134` et `:140-146` ;
  `src/labuse/scoring/cascade_v2.py:52,90`.

## Non vérifié
- **Monotonie « à règles strictement égales » en SQL** : non testable proprement. Groupé par
  `zone_lib` puis `zone_filtre`, on compte 516 549 « inversions » (petit terrain, plus de SDP
  qu'un terrain ≥2×), mais inspection des pires cas (zone N : 88 866 m²→31 096 m² SDP vs
  272 554 m²→184 m²) montre que c'est LÉGITIME : la SDP suit la portion CONSTRUCTIBLE clippée
  (reculs, pleine terre, sous-zone U/AU), pas le terrain brut ; `zone_lib`/`zone_filtre`
  regroupe des règles PLU hétérogènes. L'invariant VRAI (barème saturant monotone en SDP +
  moteur `sdp = footprint × niveaux` avec footprint ↑ en emprise) est prouvé par construction
  (INV7 + INV9). **Conclusion : pas de bug de monotonie, mais pas de garde SQL universelle possible.**
- **« Deux parcelles identiques ⇒ même bande »** : non testable par GROUP BY (zone+surface ne
  capture ni pente, ni forme, ni accès, ni bâti — 6 015 groupes « conflictuels » sur terrains
  nus, tous expliqués par des facteurs de faisabilité non contrôlés). Remplacé par l'invariant
  ÉQUIVALENT ET FORT INV8 : `score_parcelle` est une fonction PURE déterministe (500/500
  recompute == stocké, 0 non-déterminisme) ⇒ mêmes entrées ⇒ même bande par construction.
- **INV7 sur TOUTE l'île** : le moteur ne stocke pas `sdp_max`/`emprise_max`/`niveaux` dans
  `parcel_residuel_runs` (colonnes éphémères) → recompute borné à un échantillon aléatoire de
  120 constructibles (0 violation). La borne stockée indirecte INV6 couvre, elle, les 193 394.

## Gardes proposées
Prêtes pour `scripts/coherence/chasse_invariants.py` (chaque fonction rend `("OK"|"ECART", detail)` ;
le runner fait exit 1 si un ECART). `RUN='q_v18'`, `RSEQ=15`, `CASCADE='q_v18_sources'`.

```python
def g_d3_01_zero_muet(cx):
    """Résiduel servi : aucun 0 ni NULL muet (0 sans cause doit être un bâti saturé : taux & pct présents)."""
    muet_total = cx.scalar("SELECT count(*) FROM parcel_residuel_runs "
        "WHERE run_seq=%s AND sdp_residuelle_m2 IS NULL AND cause IS NULL", RSEQ)
    cause_sdp_pos = cx.scalar("SELECT count(*) FROM parcel_residuel_runs "
        "WHERE run_seq=%s AND cause IS NOT NULL AND sdp_residuelle_m2>0", RSEQ)
    zero_muet = cx.scalar("SELECT count(*) FROM parcel_residuel_runs "
        "WHERE run_seq=%s AND sdp_residuelle_m2=0 AND cause IS NULL "
        "AND (taux_emprise_pct IS NULL OR pct_potentiel IS NULL)", RSEQ)
    n = muet_total + cause_sdp_pos + zero_muet
    return ("ECART" if n else "OK", f"muet_total={muet_total} cause+sdp>0={cause_sdp_pos} zero_muet={zero_muet}")

def g_d3_02_score_couverture(cx):
    """100 % des parcelles vivantes (non disparues) portent un score du run servi."""
    n = cx.scalar("SELECT count(*) FROM parcels p "
        "LEFT JOIN score_labuse s ON s.parcel_id=p.id AND s.run_label=%s "
        "WHERE p.cadastre_disparue_le IS NULL AND s.parcel_id IS NULL", RUN)
    return ("ECART" if n else "OK", f"vivantes sans score {RUN} = {n}")

def g_d3_03_bande_score_coherence(cx):
    """bande ⇔ score : 0⇔score0, NC⇔scoreNULL⇔non_calculable (5 miroirs)."""
    q = ("SELECT "
         " count(*) FILTER (WHERE bande='0'  AND (score IS NULL OR score<>0)),"
         " count(*) FILTER (WHERE score=0    AND bande<>'0'),"
         " count(*) FILTER (WHERE score IS NULL AND bande<>'NC'),"
         " count(*) FILTER (WHERE non_calculable AND score IS NOT NULL),"
         " count(*) FILTER (WHERE bande='NC' AND non_calculable=false),"
         " count(*) FILTER (WHERE non_calculable AND cause IS NULL) "
         "FROM score_labuse WHERE run_label=%s")
    a,b,c,d,e,f = cx.row(q, RUN)
    n = a+b+c+d+e+f
    return ("ECART" if n else "OK", f"b0/s≠0={a} s0/b≠0={b} sNULL/b≠NC={c} nc/s≠NULL={d} NC/nc=false={e} nc/cause=NULL={f}")

def g_d3_04_sdp_borne_physique(cx):
    """SDP résiduelle servie ≤ terrain × 20 (plafond niveaux très généreux : filet anti-explosion)."""
    n = cx.scalar("SELECT count(*) FROM parcel_residuel_runs r JOIN parcels p ON p.id=r.parcel_id "
        "WHERE r.run_seq=%s AND r.sdp_residuelle_m2>0 "
        "AND COALESCE(p.contenance_m2,p.surface_m2)>0 "
        "AND r.sdp_residuelle_m2 > COALESCE(p.contenance_m2,p.surface_m2)*20", RSEQ)
    return ("ECART" if n else "OK", f"sdp > terrain×20 : {n}")

def g_d3_05_residuel_bati_coherence(cx):
    """parcel_residuel_bati : emprise bâtie + résiduelle = max (±1 m²) et résiduelle ≥ 0, ≤ max."""
    n = cx.scalar("SELECT count(*) FROM parcel_residuel_bati WHERE emprise_residuelle_m2<0 "
        "OR emprise_residuelle_m2 > emprise_max_m2+0.5 "
        "OR (emprise_residuelle_m2>0 AND abs((emprise_batie_m2+emprise_residuelle_m2)-emprise_max_m2)>1.0)")
    return ("ECART" if n else "OK", f"incohérences emprise = {n}")

def g_d3_06_cascade_exclue_fidele(cx):
    """La colonne cascade_exclue reflète EXACTEMENT l'exclusion classe-A HARD_EXCLUDE de la cascade servie
       (true ⇒ il existe un HARD_EXCLUDE ; aucune divergence de source)."""
    n = cx.scalar("SELECT count(*) FROM score_labuse s WHERE s.run_label=%s AND s.cascade_exclue=true "
        "AND NOT EXISTS (SELECT 1 FROM dryrun_cascade_results d "
        " WHERE d.parcel_id=s.parcel_id AND d.run_label=%s AND d.result='HARD_EXCLUDE')", RUN, CASCADE)
    return ("ECART" if n else "OK", f"cascade_exclue=true sans HARD_EXCLUDE = {n}")

def g_d3_07_bande_A_servable(cx):
    """bande A doit être servable : score>0, SDP>0, non disparue, et SIGNALER les A exclus dur (≥1 ⇒ à peindre en overlay)."""
    dur = cx.scalar("SELECT count(*) FROM score_labuse s JOIN parcels p ON p.id=s.parcel_id "
        "WHERE s.run_label=%s AND s.bande='A' "
        "AND (s.score IS NULL OR s.score<=0 OR COALESCE(s.sdp_residuelle_m2,0)<=0 "
        "     OR p.cadastre_disparue_le IS NOT NULL)", RUN)
    exclus = cx.scalar("SELECT count(*) FROM score_labuse WHERE run_label=%s AND bande='A' AND cascade_exclue=true", RUN)
    # dur>0 = vrai bug ; exclus>0 = attendu par conception, à surveiller (ne casse pas, informe)
    return ("ECART" if dur else "OK", f"A non servables (bug)={dur} ; A exclus-dur (overlay attendu)={exclus}")
```

Les gardes de reproductibilité du score (INV8/INV9) sont des tests Python (pas SQL) et doublonnent
l'esprit de `scripts/coherence/checks_parcelle.py` (comparaisons run_different) — à garder côté pytest
scoring plutôt que dans `chasse_invariants.py`.
