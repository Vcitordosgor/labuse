# Domaine 4 — Risques et servitudes

## Verdict (3 lignes)
Passées : **434 582 parcelles** (toute l'île) pour les invariants structurels (source, HARD_EXCLUDE→0, servitude orpheline) ; **107 406 parcelles touchant du PPR rouge** pour l'invariant central, dont **2 196 à flags rouge gradués** analysées exhaustivement depuis les verdicts stockés + **224 re-vérifiées à la géométrie d'union réelle**.
Invariants vérifiés : 5. Violations : **1 famille FAUX-CLIENT + INCOHERENT** (224 parcelles sous-comptées, dont **30 servies constructibles** et jusqu'à **score B / 8 297 m² SDP** sur un terrain 65 % rouge).
Resté muet : l'invariant d'union rouge sur les 64 299 parcelles mono-polygone n'a PAS été re-calculé géométriquement (timeout 120 s sur ST_Union des polygones INTERDICTION à ~320 k sommets) — mais il est sans objet là (un seul polygone ⇒ cascade et union coïncident). Les aléas Géorisques (double-compte amont cascade) n'ont pas été recomptés parcelle par parcelle à la géométrie.

## Invariants

| # | règle (une phrase FR) | requête/script | parcelles passées | violations |
|---|---|---|---|---|
| I1 | Une parcelle dont la zone rouge PPR (union de tous les polygones INTERDICTION) couvre ≥ 50 % de sa surface doit recevoir un verdict risques HARD_EXCLUDE (⇒ rouge déduit, SDP sur la partie hors rouge). | `req-I1` ci-dessous (verdicts stockés) + `req-I1b` (union géométrique sur les 228 candidats) | 2 196 parcelles à rouge gradué (228 candidats re-vérifiés à l'union) | **224** (dont 30 servies constructibles) |
| I2 | Deux lecteurs du même PPR rouge doivent s'accorder : si la fiche §Pièges & risques dit « zone rouge inconstructible / rédhibitoire », le score et la SDP servis ne peuvent pas être > 0. | `req-I2` + contrôle `aleas_parcelle()` vs `score_labuse`/`parcel_residuel` | les 224 de I1 (sur-ensemble des contradictions) | **30** (fiche = rédhibitoire, score/SDP > 0) |
| I3 | Aucune servitude / risque servi (ppr, sup, georisque_alea, icpe, sol_pollue, cavite, mvt, tri_zone, endiguement, znieff, zone_humide) sans `data_source_id`. | `req-I3` | 434 582 (toutes lignes `spatial_layers` de ces kinds) | **0** |
| I4 | Une parcelle en risques HARD_EXCLUDE rouge servie avec SDP > 0 doit l'être par la règle PPR-PARTIEL (rouge < 100 %, partie hors rouge servable), jamais par oubli de découpe. | `req-I4` | 105 298 (toutes les HARD_EXCLUDE rouge) | **0** (22 613 SDP>0 tous < 100 % rouge = PPR-PARTIEL légitime) |
| I5 | L'aire servie « hors zone rouge PPR » ne dépasse jamais la contenance (on ne sert pas plus que le terrain). | lecture `faisabilite/db.py:950-962` : `hors_rouge = max(0, dessin−rouge) × contenance/dessin ≤ contenance` (prouvé par construction) | gisement terrain_exigu/ppr_rouge (runtime, non stocké) | **0** (invariant tenu par construction : clamp `max(0,…)` + facteur ≤ 1) |

Requêtes rejouables (poser `SET statement_timeout='120s';` d'abord) :

**req-I1** (détection depuis les verdicts stockés — la cascade écrit un % par polygone) :
```sql
WITH red_soft AS (
  SELECT parcel_id,
    (regexp_match(detail,'PPR zone rouge sur (\d+) %'))[1]::int AS pf,
    (regexp_match(detail,'PPR rouge marginal : \d+ m² \((\d+)'))[1]::int AS pm
  FROM cascade_results WHERE layer_name='risques' AND result='SOFT_FLAG'
    AND (detail LIKE '%PPR zone rouge sur%' OR detail LIKE '%PPR rouge marginal%')),
sums AS (SELECT parcel_id, sum(COALESCE(pf,pm,0)) sum_pct, max(COALESCE(pf,pm,0)) max_pct
         FROM red_soft GROUP BY parcel_id),
he AS (SELECT DISTINCT parcel_id FROM cascade_results WHERE layer_name='risques'
       AND result='HARD_EXCLUDE' AND detail LIKE '%PPR zone rouge%')
SELECT count(*) FILTER (WHERE sum_pct>=50 AND max_pct<50
         AND parcel_id NOT IN (SELECT parcel_id FROM he)) AS undercounted
FROM sums;   -- => 228 candidats (borne haute : somme des % ignore les recouvrements)
```

**req-I1b** (re-vérification à la géométrie d'union réelle sur les 228 candidats) :
```sql
-- même CTE cand = 228 ids ; pour chacun :
SELECT ST_Area(ST_Intersection(
         ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975,p.geom_2975))), p.geom_2975))
       / NULLIF(ST_Area(p.geom_2975),0) AS union_cov
FROM parcels p JOIN spatial_layers sl
  ON sl.kind='ppr' AND sl.subtype='INTERDICTION' AND ST_Intersects(sl.geom_2975,p.geom_2975)
WHERE p.id=:cand GROUP BY p.geom_2975;   -- 224 / 228 ont union_cov >= 0.50 (confirmé)
```

**req-I3** :
```sql
SELECT kind, count(*) FROM spatial_layers
WHERE kind IN ('ppr','sup','georisque_alea','icpe','sol_pollue','cavite','mvt','tri_zone',
               'endiguement','znieff','zone_humide') AND data_source_id IS NULL
GROUP BY kind;   -- => 0 ligne
```

**req-I4** :
```sql
WITH he AS (SELECT DISTINCT parcel_id FROM cascade_results
            WHERE layer_name='risques' AND result='HARD_EXCLUDE' AND detail LIKE '%PPR zone rouge%')
SELECT count(*) FILTER (WHERE pr.sdp_residuelle_m2>0) served_sdp_gt0
FROM he LEFT JOIN parcels p ON p.id=he.parcel_id
LEFT JOIN parcel_residuel pr ON pr.parcel_id=he.parcel_id;   -- 22 613, tous < 100 % rouge = légitime
```

## Violations

### V1 — PPR rouge sous-compté : la cascade n'union pas les polygones INTERDICTION
**Gravité : FAUX-CLIENT** (et **INCOHERENT** pour les 30 servies > 0, cf. V2).
- **idu(s)** : 224 parcelles. Servies constructibles (score>0, SDP>0) : 30. Pires : `97401000AK0138` (**score B/60, 8 297 m² SDP**, union rouge **65 %**), `97401000AM0384` (C/376 m²), `97401000AD0605` (C/328 m²), `97401000AD0660` (C/677 m²), `97401000AR0383` (C/802 m²), `97401000AM1179` (D/55 m², union **92 %**). Les 194 autres sont déjà à 0 pour un AUTRE motif (zone A/N) qui masque le défaut.
- **attendu** : union(INTERDICTION) ≥ 50 % ⇒ verdict risques HARD_EXCLUDE ⇒ rouge découpé de l'emprise ⇒ SDP calculée sur la seule partie hors rouge (comportement PPR-PARTIEL-A).
- **obtenu** : chaque polygone INTERDICTION est évalué SÉPARÉMENT ; aucun n'atteint 50 % (ex. AM1179 : 43 % + 49 %) ⇒ aucun HARD_EXCLUDE ⇒ `ppr_rouge=False` dans le gabarit ⇒ le rouge n'est même PAS clippé de l'emprise ⇒ le terrain majoritairement rouge est servi comme pleinement bâtissable.
- **cause probable** : `src/labuse/cascade/context.py:340-366` (`intersections()`) et `:88-138` (prime) renvoient **une `Intersection` par ligne `spatial_layers`**, `coverage = ST_Area(ST_Intersection(p, sl))/ST_Area(p)` **sans ST_Union** des polygones de même kind. `src/labuse/cascade/layers/phase1.py:663-703` (`RisquesLayer.evaluate`) boucle `for i in ctx.intersections(... kind_ppr)` et teste `cov_pct >= excl_pct` (50 %) **sur chaque `i` isolément** (`:683`), jamais sur l'union. Quand un même PPR rouge est ingéré en plusieurs polygones adjacents (41 405 parcelles ont 2 polygones INTERDICTION, 1 701 en ont ≥ 3 — cf. `GROUP BY p.id HAVING count(*)>=2`), la part réelle est fragmentée sous le seuil. Le reste de la chaîne est correct : `builder.py:342` lit bien `ppr_rouge` depuis ce verdict, et `faisabilite/db.py:529,537,352` (fiche `aleas_parcelle`) union correctement — c'est la SEULE lecture non-unionnée, et c'est elle qui pilote le score/SDP.

### V2 — Score/SDP contredit la fiche « zone rouge inconstructible »
**Gravité : INCOHERENT.**
- **idu(s)** : les 30 parcelles servies > 0 de V1. Exemple vérifié `97401000AM1179`.
- **attendu** : les deux lecteurs du même PPR s'accordent.
- **obtenu** : `aleas_parcelle()` (fiche §Pièges & risques) affiche **« PPR … zone rouge (inconstructible) sur 92 % de la surface », redhibitoire=True** (vérifié en exécutant la fonction), tandis que `score_labuse`/`parcel_residuel` servent **score D/9, SDP 55 m²** (constructible). L'utilisateur voit un terrain « rédhibitoire » noté et chiffré comme exploitable.
- **cause probable** : même racine que V1. La fiche aléas union (`servitudes.py:258-271`, `ST_Union(ST_Intersection…)` GROUP BY subtype), la cascade non ⇒ divergence structurelle entre les deux lecteurs du PPR rouge.

## Non vérifié
- **Invariant I1 en géométrie sur les 64 299 parcelles mono-polygone INTERDICTION** : non recalculé à l'union (le `ST_Union`+`ST_Intersection` des polygones INTERDICTION, ~320 k sommets, dépasse 120 s dès ~300 parcelles ; même `ST_ClipByBox2D` préalable n'a pas suffi). Sans objet pour le défaut découvert (un seul polygone ⇒ cascade = union), mais un éventuel écart cascade↔union sur une parcelle mono-polygone (p.ex. coverage calculé en 2975 vs 4326) n'a pas été sondé.
- **Double-compte des aléas Géorisques** : la cascade stocke un `SOFT_FLAG` par polygone `georisque_alea` (observé : `mouvement_terrain` fort+moyen+faible sur une même parcelle) ; la fiche (`aleas_parcelle`, best-niveau-par-type) et l'outil le recollapsent, donc **pas de double-compte côté client** — mais je n'ai pas prouvé que TOUS les lecteurs client collapsent (seuls fiche + contraintes_parcelle vérifiés par lecture de code).
- **CatNat / OCSGE servis = géométrie intersectée** : `catnat_arretes` est rattaché par INSEE commune (pas par géométrie parcelle) et `parcel_ocsge` n'a pas été recoupé à `spatial_layers.ocs_ge` parcelle par parcelle (budget).
- **I5 (hors rouge ≤ contenance)** : prouvé par lecture du code (clamp + facteur ≤ 1), pas par exécution sur le gisement runtime (`exigu_raison` n'est pas une colonne stockée — calcul moteur à la demande).

## Gardes proposées

```python
# scripts/coherence/chasse_invariants.py  —  DOMAINE 4 : risques & servitudes

RED_EXCLUDE_PCT = 50   # config/cascade_rules.yaml: ppr_red_exclude_pct

def g_ppr_union_vs_cascade(session):
    """[ECART] si une parcelle a >= RED_EXCLUDE_PCT % de surface en PPR rouge (UNION des
    polygones INTERDICTION) sans verdict risques HARD_EXCLUDE. Détecte le sous-comptage de
    phase1.RisquesLayer qui n'union pas (context.intersections rend un coverage par polygone).
    Étape 1 (rapide, verdicts stockés) : somme des % par polygone >= 50 & max < 50 & pas de HARD_EXCLUDE.
    Étape 2 (confirmation géométrique) : union réelle >= 50 % sur les candidats seulement."""
    cand = session.execute(text("""
        WITH red_soft AS (
          SELECT parcel_id,
            (regexp_match(detail,'PPR zone rouge sur (\\d+) %'))[1]::int pf,
            (regexp_match(detail,'PPR rouge marginal : \\d+ m² \\((\\d+)'))[1]::int pm
          FROM cascade_results WHERE layer_name='risques' AND result='SOFT_FLAG'
            AND (detail LIKE '%PPR zone rouge sur%' OR detail LIKE '%PPR rouge marginal%')),
        sums AS (SELECT parcel_id, sum(COALESCE(pf,pm,0)) sp, max(COALESCE(pf,pm,0)) mp
                 FROM red_soft GROUP BY parcel_id),
        he AS (SELECT DISTINCT parcel_id FROM cascade_results WHERE layer_name='risques'
               AND result='HARD_EXCLUDE' AND detail LIKE '%PPR zone rouge%')
        SELECT parcel_id FROM sums
        WHERE sp>=:t AND mp<:t AND parcel_id NOT IN (SELECT parcel_id FROM he)
    """), {"t": RED_EXCLUDE_PCT}).scalars().all()
    confirmed = []
    for pid in cand:                       # confirmation géométrique, candidats seulement (petit)
        row = session.execute(text("""
            SELECT ST_Area(ST_Intersection(
                     ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975,p.geom_2975))),p.geom_2975))
                   / NULLIF(ST_Area(p.geom_2975),0) AS cov
            FROM parcels p JOIN spatial_layers sl ON sl.kind='ppr' AND sl.subtype='INTERDICTION'
               AND ST_Intersects(sl.geom_2975,p.geom_2975)
            WHERE p.id=:pid GROUP BY p.geom_2975"""), {"pid": pid}).scalar()
        if row is not None and float(row) >= RED_EXCLUDE_PCT/100.0:
            confirmed.append(pid)
    if confirmed:
        return "ECART", f"{len(confirmed)} parcelles >= {RED_EXCLUDE_PCT}% PPR rouge (union) sans HARD_EXCLUDE (ex. ids {confirmed[:5]})"
    return "OK", f"{len(cand)} candidats, 0 confirmé a l'union"

def g_fiche_vs_score_ppr_rouge(session):
    """[ECART] si la fiche aleas_parcelle dit 'zone rouge (inconstructible)/redhibitoire' alors
    que score_labuse.score>0 ou parcel_residuel.sdp_residuelle_m2>0 pour la meme parcelle."""
    from labuse.api.servitudes import aleas_parcelle          # lecteur fiche (union)
    bad = []
    for pid in _g_ppr_union_candidats(session):               # reutilise l'etape 1 ci-dessus
        idu = session.execute(text("SELECT idu FROM parcels WHERE id=:p"), {"p": pid}).scalar()
        redhib = any(a["redhibitoire"] and a["nature"].startswith("PPR") for a in aleas_parcelle(session, idu))
        served = session.execute(text("""
            SELECT COALESCE(max(sl.score),0) s, COALESCE(max(pr.sdp_residuelle_m2),0) sdp
            FROM parcels p LEFT JOIN score_labuse sl ON sl.idu=p.idu AND sl.run_label='q_v18'
            LEFT JOIN parcel_residuel pr ON pr.parcel_id=p.id WHERE p.id=:p"""), {"p": pid}).one()
        if redhib and (served.s > 0 or served.sdp > 0):
            bad.append(idu)
    if bad:
        return "ECART", f"{len(bad)} parcelles fiche=redhibitoire mais score/SDP>0 (ex. {bad[:5]})"
    return "OK", "fiche et score d'accord sur le PPR rouge"

def g_servitude_sans_source(session):
    """[ECART] toute ligne spatial_layers de risque/servitude sans data_source_id."""
    n = session.execute(text("""
        SELECT count(*) FROM spatial_layers
        WHERE kind IN ('ppr','sup','georisque_alea','icpe','sol_pollue','cavite','mvt',
                       'tri_zone','endiguement','znieff','zone_humide')
          AND data_source_id IS NULL""")).scalar()
    return ("ECART", f"{n} servitudes/risques sans source") if n else ("OK", "0 servitude orpheline")

# exit 1 si une garde rend ECART.
```
