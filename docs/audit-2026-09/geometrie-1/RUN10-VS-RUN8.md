# RUN 10 (assiette gabarit) vs RUN 8 (servi) — comparaison en lecture seule

Branche `audit/run10` (worktree `~/Desktop/labuse-run10`, base `origin/main` `bef20136`).
**Aucune écriture pendant l'analyse — que des `SELECT`.** Toutes les requêtes ci-dessous
sont rejouables telles quelles sur `postgresql://openclaw@localhost:5432/labuse`.

## Les deux runs

| | run 8 (servi) | run 10 (candidat) |
|---|---|---|
| label | `post-plu8-clip-2shard` | `q_v15 assiette gabarit` |
| `code_commit` | `c7f581b2` | `babcc084` |
| lignes | 431 663 | 431 663 |
| calculé le | 24/09 12:28 → 15:24 | 25/09 01:44 → 06:30 |
| assiette | inset uniforme (legacy), `assiette_source` non écrit | **zone d'implantation du gabarit** (reculs par côté, PPR rouge découpé) |
| servi | **oui** | non |

**Complétude run 10 vérifiée par le timestamp, pas le compteur** (piège du rollback
silencieux d'un chunk) : 0 ligne « trou » (cause vide **et** sdp NULL **et** assiette_source
NULL **et** capacite_estimee NULL), timestamps continus de 01h à 06h30 sans creux, les 431 663
présentes. Les deux runs couvrent l'île entière, mêmes `parcel_id`.

---

## (1) Calculées / avec cause — les deux runs

« Calculée » = la géométrie a produit un résultat (cause vide, `assiette_source` renseigné) ;
« avec cause » = exclue avant le calcul de surface (zone N/A, terrain exigu, PPR rédhibitoire…).

| | run 8 | run 10 | Δ |
|---|--:|--:|--:|
| **calculées** (cause vide) | 262 246 | 262 263 | **+17** |
| **avec cause** | 169 417 | 169 400 | **−17** |
| SDP résiduelle > 0 | 150 180 | 147 838 | **−2 342** |
| SDP résiduelle = 0 | 277 239 | 279 581 | +2 342 |
| SDP NULL (`hors_plu`) | 4 244 | 4 244 | 0 |
| **capacité estimée = true** | **19 770** | **19 770** | **0 (même ensemble exact)** |
| SDP résiduelle totale | 79 716 952 m² | 79 051 217 m² | **−665 735 m² (−0,84 %)** |

Provenance de l'assiette (colonne `assiette_source`, écrite seulement par le nouveau code) :
sur les 262 263 calculées de run 10, **207 467 via le gabarit (79 %)** et **54 796 via le
legacy (21 %)** — les 5 causes non servies par le gabarit gardent le chemin legacy, conforme
à GEOMETRIE-1. Run 8 n'écrit pas cette colonne.

> **Invariant fort** : les **19 770** parcelles `capacite_estimee = true` (la vraie
> sous-densité, le signal qui compte pour le scoring) sont **exactement les mêmes** aux deux
> runs (0 perdue, 0 gagnée). Seule la magnitude de la SDP bouge, pas l'ensemble des
> opportunités.

```sql
-- calculées / avec cause / totaux, par run
SELECT run_seq,
  count(*) FILTER (WHERE cause IS NULL OR cause='')            AS calculees,
  count(*) FILTER (WHERE cause IS NOT NULL AND cause<>'')      AS avec_cause,
  count(*) FILTER (WHERE sdp_residuelle_m2>0)                  AS sdp_pos,
  count(*) FILTER (WHERE capacite_estimee)                     AS cap_estimee,
  sum(sdp_residuelle_m2)                                       AS sdp_totale
FROM parcel_residuel_runs WHERE run_seq IN (8,10) GROUP BY run_seq;
```

---

## (2) Delta par cause

Sur les **233 valeurs de cause**, toutes les zones (`zone_non_constructible:*`,
`habitat_interdit:*`, `zone_non_resolue:*`, `hors_plu`, `capacite_nulle`…) sont **identiques
au parcel près**. **Trois causes seulement bougent**, et elles se compensent :

| cause | run 8 | run 10 | Δ |
|---|--:|--:|--:|
| (vide = calculée) | 262 246 | 262 263 | **+17** |
| **`terrain_exigu`** | 61 152 | **61 107** | **−45** |
| **`redhibitoire`** | 6 013 | 6 041 | **+28** |
| toutes les autres | — | — | **0** |

Le Δ net minuscule cache une **rotation réelle** (requête NULL-safe, `IS DISTINCT FROM`) :

**`terrain_exigu`** — stables 59 760 ·
- **sortent : 1 392** → dont **1 329 deviennent calculées** (SDP calculée), 63 → `redhibitoire` ;
- **entrent : 1 347** → dont **1 312 étaient calculées** en run 8.
- Lecture : les reculs *par côté* préservent les angles que l'inset uniforme rabotait
  (1 329 petits lots redeviennent constructibles), mais le recul de voie (3–4 m contre 2 m
  d'inset) vide 1 312 autres lots. Solde −45.

**`redhibitoire`** — **les 63 nouvelles viennent TOUTES de `terrain_exigu`** (0 depuis une
calculée) ; 35 anciennes redeviennent autre chose. Solde +28. Lecture : sous l'assiette
gabarit (reculs + PPR rouge découpé) une poignée de terrains déjà exigus basculent en « plus
rien du tout ».

```sql
WITH j AS (SELECT a.cause c8,b.cause c10 FROM parcel_residuel_runs a
  JOIN parcel_residuel_runs b USING(parcel_id) WHERE a.run_seq=8 AND b.run_seq=10)
SELECT count(*) FILTER (WHERE c8='terrain_exigu' AND c10 IS DISTINCT FROM 'terrain_exigu') te_sortent,
       count(*) FILTER (WHERE c8 IS DISTINCT FROM 'terrain_exigu' AND c10='terrain_exigu')  te_entrent,
       count(*) FILTER (WHERE c8='terrain_exigu' AND c10='redhibitoire')                    te_vers_red,
       count(*) FILTER (WHERE c8 IS DISTINCT FROM 'redhibitoire' AND c10='redhibitoire')     red_entrent
FROM j;
```

---

## (3) Parcelles qui basculent SDP > 0 ↔ 0

| sens | nombre |
|---|--:|
| **SDP > 0 (run 8) → 0 (run 10)** — pertes sèches | **3 524** |
| **0 (run 8) → SDP > 0 (run 10)** — gains secs | **1 182** |
| SDP > 0 aux deux | 146 656 |
| SDP 0/NULL aux deux | 280 301 |

**Réponse directe à la question posée** (« reculs latéraux sur terrain étroit ? PPR ? ») :

- **Les pertes sont écrasées sur les petits lots** — 1 709 font < 400 m² (moy. 249 m²),
  1 358 entre 400 et 800 m² (moy. 546 m²), 379 entre 800 et 2 000, **65 entre 2 000 et 5 000,
  13 seulement > 5 000**. C'est le mécanisme attendu : **le recul de voie par côté (3–4 m)
  élimine ce qu'un inset uniforme à 2 m laissait passer** sur un terrain étroit. Cause en
  run 10 : 2 611 « calculée SDP=0 » (l'assiette gabarit se ferme) + 913 `terrain_exigu`.
- **Les gains sont l'inverse et corrigent un défaut de run 8** : les plus gros sont de
  **grandes parcelles 1AU (à urbaniser) que run 8 classait à tort `terrain_exigu`** (SDP 0).
  Sur les 1 182 gains, 741 étaient `terrain_exigu` en run 8, 441 calculées SDP 0.

**10 exemples — pertes (SDP > 0 → 0), triées par SDP run 8 perdue :**

| idu | commune | surface | SDP run 8 | SDP run 10 | cause run 10 | zone | assiette |
|---|---|--:|--:|--:|---|---|---|
| 97422000DE0262 | Le Tampon | 16 587 | 3 185 | 0 | terrain_exigu | 1AUb | (exclue) |
| 97422000AW0153 | Le Tampon | 10 053 | 1 844 | 0 | terrain_exigu | Nco | (exclue) |
| 97416000EN1426 | Saint-Pierre | 3 989 | 1 330 | 0 | terrain_exigu | N | (exclue) |
| 97424000AN0028 | Cilaos | 6 533 | 1 305 | 0 | (calculée) | Ub | gabarit |
| 97422000AW0679 | Le Tampon | 2 460 | 1 210 | 0 | terrain_exigu | 1AUb | (exclue) |
| 97409000BD0516 | Saint-André | 1 888 | 1 016 | 0 | (calculée) | UB | gabarit |
| 97418000AS1378 | Sainte-Marie | 1 417 | 836 | 0 | terrain_exigu | — | (exclue) |
| 97409000AL0623 | Saint-André | 1 150 | 639 | 0 | (calculée) | — | gabarit |
| 97421000BO0220 | Salazie | 1 822 | 632 | 0 | terrain_exigu | — | (exclue) |
| 97409000AL0620 | Saint-André | 1 121 | 622 | 0 | terrain_exigu | — | (exclue) |

Les « grosses » pertes (16 587 m², 10 053 m²) sont **multizones à dominante non-constructible**
(1AUb à cheval, Nco, N) : la portion U/AU réellement bâtissable est un liseré qui se ferme
sous les reculs — cohérent, pas une parcelle pleine remise à zéro à tort.

**10 exemples — gains (0 → SDP > 0), triés par SDP run 10 gagnée :**

| idu | commune | surface | cause run 8 | SDP run 10 | zone | assiette |
|---|---|--:|---|--:|---|---|
| 97422000BT0920 | Le Tampon | 51 557 | terrain_exigu | 67 375 | 1AUb | gabarit |
| 97422000BH0397 | Le Tampon | 51 408 | terrain_exigu | 39 628 | 1AUb | gabarit |
| 97422000BH0251 | Le Tampon | 29 026 | terrain_exigu | 35 620 | 1AUb | gabarit |
| 97414000CX0244 | Saint-Louis | 19 272 | terrain_exigu | 28 810 | 1AUa | gabarit |
| 97422000AX1329 | Le Tampon | 18 960 | terrain_exigu | 25 596 | 1AUe | gabarit |
| 97422000BV2447 | Le Tampon | 14 186 | terrain_exigu | 25 415 | — | gabarit |
| 97422000EM0237 | Le Tampon | 9 009 | terrain_exigu | 24 020 | — | gabarit |
| 97414000DE1530 | Saint-Louis | 11 017 | terrain_exigu | 17 350 | — | gabarit |
| 97422000EM0073 | Le Tampon | 6 327 | terrain_exigu | 15 713 | — | gabarit |
| 97422000EM0328 | Le Tampon | 5 732 | terrain_exigu | 14 149 | — | gabarit |

Ces gains sont sans appel : des parcelles **1AU de plusieurs hectares** (zones *à urbaniser*)
que run 8 déclarait « terrain exigu » (SDP 0). **Run 10 corrige un vrai défaut de run 8.**

---

## (4) Distribution des écarts de SDP

**Sur toute l'île (431 663)** : **87,6 % ont une SDP strictement identique** (378 281),
la cause est identique à 99,4 % (428 924).

**Sur les 146 656 parcelles comparables (SDP > 0 aux deux runs)** :

| tranche d'écart | parcelles | part |
|---|--:|--:|
| identiques (0 %) | 97 980 | 66,8 % |
| ± 10 % (hors exact) | 23 368 | 15,9 % |
| ]10 % ; 50 %] | 20 853 | 14,2 % |
| > 50 % | 4 455 | 3,0 % |
| **bougent de plus de ±10 %** | **25 308** | **17,3 %** |

Ventilé par sens (au-delà de ±10 %) : **gains 3 040 · pertes 22 268**. La médiane de
variation est **0,00 %**, la moyenne **−3,03 %** : la moitié des parcelles ne bouge pas, la
queue penche vers la baisse (reculs de voie plus stricts). Le solde agrégé reste faible :
**−0,84 % de SDP totale**.

> Note : c'est **l'inverse du test Saint-Denis (run 9)** où les gains dominaient (28,8 % vs
> 4,8 %). Saint-Denis (urbain dense, petits U) profitait surtout de la préservation des angles ;
> à l'échelle de l'île, ce sont les reculs de voie sur les lots pavillonnaires qui dominent.
> Les deux effets sont réels et attendus — ils ne s'annulent qu'en moyenne.

```sql
WITH j AS (SELECT a.sdp_residuelle_m2 s8,b.sdp_residuelle_m2 s10
  FROM parcel_residuel_runs a JOIN parcel_residuel_runs b USING(parcel_id)
  WHERE a.run_seq=8 AND b.run_seq=10 AND a.sdp_residuelle_m2>0 AND b.sdp_residuelle_m2>0)
SELECT count(*) FILTER (WHERE s10=s8) ident,
       count(*) FILTER (WHERE abs((s10-s8)::numeric/s8*100)<=10 AND s10<>s8) d10,
       count(*) FILTER (WHERE abs((s10-s8)::numeric/s8*100)>10 AND abs((s10-s8)::numeric/s8*100)<=50) d50,
       count(*) FILTER (WHERE abs((s10-s8)::numeric/s8*100)>50) sup50 FROM j;
```

---

## (5) Verdict — **SERVABLE**

**Oui, run 10 est servable, et il vaut mieux que run 8.** Les raisons :

1. **C'est le moteur unique voulu** (décision Vic du 24/09, GEOMETRIE-1) : le résiduel lit
   enfin la même assiette que le gabarit et l'outil. Le changement de géométrie est le but,
   pas un effet de bord.
2. **Il corrige un défaut réel de run 8** : de grandes parcelles 1AU (jusqu'à 5 ha) que le
   run servi classait « terrain exigu » à 0 SDP reçoivent enfin leur capacité (741 parcelles,
   dont des multi-hectares). Aucun mécanisme équivalent ne fabrique de fausse capacité en sens
   inverse : les pertes sont sur des petits lots (3 067 des 3 524 font < 800 m²) où le recul de
   voie par côté est plus juste que l'inset uniforme.
3. **Impact agrégé modéré et sain** : −0,84 % de SDP totale, 87,6 % des parcelles inchangées
   au m², cause identique à 99,4 %.
4. **Le signal qui compte pour le scoring est stable** : l'ensemble des 19 770 parcelles
   `capacite_estimee = true` est **identique** entre les deux runs.
5. **Run complet et propre** : 0 trou, timestamps continus, `hors_plu` cohérent.

**Ce qui reste à surveiller (non bloquant) :**

- **13 parcelles > 5 000 m² tombent à 0 SDP.** Le contrôle du zonage les montre multizones à
  dominante non-constructible (1AUb à cheval, N, Nco) : le liseré U/AU se ferme sous les reculs
  — plausible, mais ces 13 cas n'ont pas été tracés géométriquement un à un dans cet audit
  lecture-seule. Ils rentrent dans la famille « extrêmes d'assiette » déjà acceptée aux runs
  précédents ; à échantillonner si un doute persiste avant un run suivant.
- **La bascule fait baisser le nombre de parcelles à capacité de 2 342** (150 180 → 147 838
  SDP > 0). C'est le prix de l'exactitude des reculs ; à annoncer côté produit, pas un défaut.

**Rien ne cloche de bloquant.** Run 10 peut être servi.

Retour arrière si besoin : `residuel-serve 8`.
