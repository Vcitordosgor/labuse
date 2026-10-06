# PPR-PARTIEL-1 — une parcelle partiellement rouge n'est pas une parcelle perdue

**Audit lecture seule — Phase 1 (mesure du gisement avant tout code).**
Branche `audit/ppr-partiel-1`, worktree `~/Desktop/labuse-pprpartiel`, base `origin/main` (HEAD `7fc0307d`). Run servi analysé : **q_v16 / `parcel_residuel_runs.run_seq = 13`** (2026-10-05). Aucune écriture, aucun run, aucune bascule — toutes les mesures sont des requêtes `psql` rejouables sur la base `labuse`.

> **En une phrase.** La règle met à 0 **toute** parcelle qui *touche* une zone rouge PPR (pas « majoritairement en rouge »), en déduisant de l'implantation **l'enveloppe réglementaire entière** (`pm1`, rouge **+** bleu) et non le seul rouge réel. Résultat mesuré : **3 888 parcelles en zone U/AU gardent plus de 500 m² hors zone rouge (588 ha au total) et sont pourtant servies à 0** — dont des parcelles urbaines de plusieurs milliers de m² rayées par un coin rouge de quelques dizaines de m². Le gisement est réel et important ; il mérite le chantier, en deux temps (signalement d'abord, recalcul ensuite, avec un garde-fou accès/tenant).

---

## 1. Où la mise à zéro se décide, et quelle est la règle

### La chaîne exacte (fichier:ligne)

Le 0 d'une parcelle partiellement rouge se construit en trois maillons :

1. **Le déclencheur — « touche du rouge »** (pas « majoritairement rouge »).
   `src/labuse/gabarit/builder.py:334-339` lit la cascade :
   ```python
   ppr = ... "WHERE parcel_id=:pid AND layer_name='risques' ORDER BY (result='HARD_EXCLUDE') DESC LIMIT 1"
   ppr_rouge = bool(ppr and ppr["result"]=="HARD_EXCLUDE" and "PPR zone rouge" in (ppr["detail"] or ""))
   ```
   La cascade `risques` pose `HARD_EXCLUDE` dès qu'une parcelle **intersecte** un polygone PPR `INTERDICTION` — *n'importe quelle* intersection, fût-elle d'un m². (En base : les 151 545 lignes `HARD_EXCLUDE` de `risques` portent toutes le même `detail` « Exclue : PPR zone rouge (inconstructible). »)

2. **La déduction — l'enveloppe entière, pas le rouge réel.**
   `src/labuse/gabarit/builder.py:401-410`, le bloc SUP qui soustrait de la zone d'implantation :
   ```sql
   AND (sl.subtype <> 'pm1'                       -- normalement on IGNORE l'enveloppe pm1…
        OR EXISTS (SELECT 1 FROM spatial_layers r
                   WHERE r.kind='ppr' AND r.subtype='INTERDICTION'
                     AND ST_Intersects(r.geom_2975, p.geom_2975)))  -- …SAUF si la parcelle touche du rouge
   ```
   La SUP `pm1` = « Enveloppe des zonages réglementaires » du PPR **couvre le rouge ET le bleu indistinctement** (311 lignes sur l'île). Normalement elle est retirée du calcul (correctif ORACLE-FIX-1 : une parcelle en zone bleue ne doit pas être vidée). **Mais dès que la parcelle touche un coin rouge, on re-soustrait l'enveloppe entière** — souvent ≈ la parcelle entière. Le commentaire du code l'assume (`builder.py:395-400`) : *« on préfère 0 à une incohérence gabarit↔verdict … CHANTIER POST-DÉPLOIEMENT : les parcelles partiellement en rouge devraient à terme être calculées sur leur portion hors rouge »*.
   À noter : l'exclusion du **rouge réel seul** est, elle, déjà calculée géométriquement juste au-dessus (`builder.py:348-365`, `ST_Intersection` avec `subtype='INTERDICTION'`). C'est la *sur*-déduction `pm1` qui écrase tout.

3. **L'écrasement → `terrain_exigu` → SDP 0.**
   `src/labuse/faisabilite/db.py:471` : `emprise = max(0.0, emprise_brute - greve_tot)` (l'implantation déjà vidée par l'enveloppe).
   `src/labuse/faisabilite/db.py:505-507` : `if emprise < SEUIL_EXIGU_M2: if ppr_rouge: vide_raison = "ppr_rouge"`.
   `SEUIL_EXIGU_M2 = 5.0` (`src/labuse/faisabilite/engine.py:20`).
   `engine.py:491-504` transforme l'assiette < 5 m² en `cause="terrain_exigu"`, capacité (0,0).
   `src/labuse/faisabilite/residuel.py:136` écrit la SDP 0 pour cette cause.
   Côté client, le motif affiché (`engine.py:313`) est **« terrain trop étroit une fois retirée la zone rouge du PPR »** — un libellé factuellement **faux** pour le gisement, puisqu'il reste en moyenne 474 m² (et jusqu'à 56 000 m²) hors rouge.

### La règle, en une phrase
> **« Touche une zone rouge »** (`ST_Intersects` avec un polygone PPR `INTERDICTION`), pas « majoritairement en zone rouge » : toute intersection, même minime, fait déduire l'enveloppe réglementaire PPR entière (rouge + bleu) de l'implantation → emprise < 5 m² → `terrain_exigu` → SDP 0.

### Interaction avec `terrain_exigu`
La parcelle est exclue **par le PPR**, pas par sa taille réelle : le seuil exigu (5 m²) n'est que la **dernière porte** qui écrit le 0 une fois l'implantation vidée par l'enveloppe. Pour le gisement, le terrain n'est pas petit du tout — c'est l'étiquette « terrain_exigu » qui masque une exclusion PPR sur-large. Pour les parcelles réellement petites (< 200 m² de reste hors rouge, cf. §2), `terrain_exigu` est en revanche **correct** : il n'y a rien à bâtir. Les deux cas vivent sous le même code — c'est la **surface hors rouge** qui les sépare.

---

## 2. Le gisement mesuré

**Population analysée** : parcelles qui touchent du rouge (flag cascade « PPR zone rouge »), servies à 0 au run 13 avec `cause='terrain_exigu'`, et dont le PLU autorise le logement (`zone_fam ∈ {U, AU}`). → **15 176 parcelles.**
(Les parcelles rouges en zone A/N sont écartées : inconstructibles au PLU de toute façon, ce n'est pas un gisement. Les parcelles rouges déjà saturées de bâti — `cause` NULL, SDP 0 — aussi.)

Pour chacune : **surface hors zone rouge = aire parcelle − aire(parcelle ∩ rouge `INTERDICTION`)** (union des rouges, `ST_Intersection`, même géométrie que le code).

### Distribution des 15 176 parcelles (surface hors rouge)

| Tranche hors rouge | Parcelles | % | Reste moyen | Lecture |
|---|---:|---:|---:|---|
| **< 200 m²** (perdu pour de bon) | 8 389 | 55 % | 36 m² | `terrain_exigu` **correct** — rien à bâtir |
| **200 – 500 m²** | 2 890 | 19 % | 346 m² | marginal, à étudier au cas par cas |
| **500 – 1 000 m²** | 2 237 | 15 % | 697 m² | **gisement** |
| **> 1 000 m²** | 1 660 | 11 % | **2 607 m²** | **gros gisement** |

### Le chiffre qui compte

> **3 888 parcelles en zone U/AU gardent plus de 500 m² hors zone rouge et sont servies à 0.**
> Soit **588 hectares** de foncier constructible-éligible actuellement invisibles. Répartition : **U = 3 761 · AU = 127**.

C'est **plus** que la borne ≤ 4 122 de QV16-VERIF-1/EXPLIQUE-RUN13, et c'est normal : cette borne-là comptait seulement les parcelles qui *ont perdu* de la SDP dans la bascule q_v15→q_v16 (un **delta**). Le chiffre ci-dessus est le **stock** réel aujourd'hui servi à 0, indépendamment de l'historique.

### 15 cas réels (tirage pseudo-aléatoire, hors rouge > 500 m²)

| IDU | Commune | Zone PLU | Surface totale | Hors rouge | % hors rouge |
|---|---|---|---:|---:|---:|
| 97420000BC0311 | Sainte-Suzanne | UA | 4 749 | 3 194 | 67 % |
| 97415000AW1694 | Saint-Paul | U4b | 3 464 | 2 529 | 73 % |
| 97423000AK0825 | Les Trois-Bassins | Ub | 1 705 | 1 280 | 75 % |
| 97416000HY1719 | Saint-Pierre | Ug | 1 661 | 1 168 | 70 % |
| 97409000AV0563 | Saint-André | UC | 1 317 | 728 | 55 % |
| 97409000AW0048 | Saint-André | UC | 1 236 | 876 | 71 % |
| 97415000BI0528 | Saint-Paul | U1b | 1 002 | 945 | 94 % |
| 97409000BE0652 | Saint-André | UB | 918 | 846 | 92 % |
| 97422000BW0343 | Le Tampon | Uav | 880 | 748 | 85 % |
| 97406000AM0553 | La Plaine-des-Palmistes | Ub | 844 | 677 | 80 % |
| 97418000AP1104 | Sainte-Marie | UD1 | 803 | 623 | 78 % |
| 97409000AX0436 | Saint-André | UC | 800 | 792 | 99 % |
| 97411000HD0225 | Saint-Denis | Um | 693 | 591 | 85 % |
| 97416000EH0915 | Saint-Pierre | Ug | 598 | 545 | 91 % |
| 97409000AN0442 | Saint-André | UB | 528 | 526 | 100 % |

**Les cas les plus caricaturaux** (vérifiés géométriquement) :
- **97409000AY0786** (Saint-André, UC, 4 877 m²) — zone rouge réelle = **145 m²** (3 % de la parcelle). Rayée à 0 « terrain trop étroit ». **4 732 m² hors rouge perdus.** (Témoin « bonne parcelle périmée » déjà cité par EXPLIQUE-RUN13.)
- **97404000AX0047** (L'Étang-Salé, UA, 2 138 m²) — rouge réel = **6 m²**. Garde 2 132 m².
- **Top stock** : `97411000IR0368` Saint-Denis **Uma 57 554 m²** → 56 241 m² hors rouge, servie à 0. `97412000BM1341` Saint-Joseph U3 36 547 → 31 719. `97411000DT0156` Saint-Denis Uh 28 261 → 26 059. `97409000AK0804` Saint-André UB 28 258 → 24 896.

Ces parcelles — grandes, urbaines, rayées par une lame rouge — sont **exactement** ce qu'un promoteur paie LABUSE pour trouver.

---

## 3. Ce que coûterait de servir la partie constructible

### Le calcul géométrique à ajouter — moins lourd qu'il n'y paraît
La géométrie du **rouge réel seul** est **déjà calculée** dans le moteur gabarit (`builder.py:348-365`, l'exclusion `ppr-rouge`). La sur-exclusion vient uniquement du maillon `pm1` (`builder.py:405-407`). Deux chemins possibles :
- **Chemin « réutilise l'existant »** : cesser de re-déduire l'enveloppe `pm1` quand la parcelle touche du rouge, et laisser l'exclusion rouge-seul déjà présente faire le travail. **Coût CPU additionnel ≈ nul** (la géométrie rouge est déjà produite à chaque run). C'est un changement de **clause SQL**, pas un nouveau calcul.
- **Chemin « calcul neuf »** (si on veut une mesure indépendante) : une intersection parcelle ∩ rouge par parcelle. Chronométré ici : **~23 ms/parcelle** sur les parcelles rouges. Appliqué aux seules 151 545 parcelles rouges ≈ **58 min** ; sur les 431 663 de l'île ≈ **2 h 45**. Inutile si on réutilise l'existant.

Dans les deux cas, **la vraie dépense n'est pas le CPU du run** mais la validation en aval.

### Ce qui doit changer en aval
- **SDP résiduelle** (`residuel.py:206`) : recalculée sur l'emprise hors rouge **après reculs** (voir pièges).
- **Score & bande** : ~3 888 parcelles quittent la bande 0 vers A/B/C/D → `score_labuse` recalculé, **bandes gravées** à revérifier (SCORING-9), témoins à re-constituer (AY0786/AX0047 cessent d'être « périmés »).
- **Cohérence cascade ↔ gabarit** : aujourd'hui la cascade dit `HARD_EXCLUDE` « inconstructible PPR rouge » pendant que le gabarit vaudrait > 0 → **incohérence** (la raison même du « 0 plutôt qu'incohérence » de Vic). Il faut traiter la cascade **et** le gabarit **ensemble** : pour une parcelle U/AU partiellement rouge, verdict « constructible sur la partie hors zone rouge » (SOFT_FLAG), pas `HARD_EXCLUDE`.
- **Fiche** : remplacer « terrain trop étroit une fois retirée la zone rouge » (`engine.py:313`, faux ici) par « constructible sur la partie hors zone rouge : X m² ».
- **Exports** (Dossier, plan Gabarit) : le plan dessine déjà le rouge découpé (`plan_svg.py`) — cohérent, mais le texte du verdict suit le changement ci-dessus.

### Les pièges — à ne pas sous-estimer
- **PPR superposés** : plusieurs polygones rouges se recouvrant → déjà géré par `ST_Union` du rouge (aire comptée une fois). OK.
- **Géométries invalides** : `ST_MakeValid` déjà appliqué partout ; QV16 note 0 invalide sur l'île. Risque faible.
- **Reculs qui s'ajoutent au rouge** : les **588 ha mesurés sont du foncier brut hors rouge, PAS de l'emprise constructible.** Sur la portion hors rouge il faut encore appliquer reculs voie/limites, ER/EBC, PEB, etc. L'emprise réellement bâtissable sera **nettement inférieure** — il ne faut surtout pas servir 588 ha comme de la SDP.
- **Reste non d'un seul tenant / sans accès** : piège majeur. Si le rouge coupe la parcelle en fragments, ou pire s'il longe la **façade sur rue** et enclave la partie saine (fréquent : les PPR inondation/ravine suivent l'eau en bord de parcelle), la portion hors rouge peut être **inexploitable** même si sa surface est grande. Non mesuré ici (coûteux) → **garde-fou obligatoire** avant tout passage au score : contiguïté (`ST_Dump`/plus grand fragment) + accès voirie de la partie saine.

### Ce qu'il ne faut **pas** faire
Annoncer « constructible » un terrain dont la partie saine est enclavée ou inexploitable. Mieux vaut un signalement honnête **« à étudier — partie hors zone rouge : X m² »** qu'un faux espoir servi dans le score. Le sens prudent reste la bonne valeur par défaut tant que l'accès n'est pas vérifié.

---

## 4. Recommandation

**Le chantier vaut le coup** : 3 888 parcelles U/AU (588 ha), dont des parcelles urbaines de 20 000 à 57 000 m² rayées par une lame rouge, c'est le cœur de la promesse produit, pas une frange négligeable. Mais il se fait **en deux temps**, pas d'un bloc.

- **Option B — signalement seul (recommandée en premier). Effort : petit, sans run, sans risque.**
  Un badge fiche/liste **« Partie hors zone rouge : X m² — à étudier »**, calculé depuis la géométrie rouge déjà disponible, sans toucher au score ni à la bande (la parcelle reste prudemment à 0). Corrige aussi le libellé faux « terrain trop étroit ». Surface immédiatement le gisement pour qu'un humain le qualifie (accès, tenant). Aucune bascule, aucune incohérence introduite.

- **Option A — recalcul complet (post-déploiement). Effort : moyen à grand.**
  Supprimer la sur-déduction `pm1` quand touche-rouge (`builder.py:405-407`) + harmoniser la cascade (SOFT_FLAG « partie hors rouge » au lieu de `HARD_EXCLUDE` en U/AU) + **garde-fou contiguïté/accès** sur la portion saine + re-run résiduel + recalcul score/bandes + re-constitution des témoins + libellés fiche/exports. Le CPU du run est quasi gratuit (géométrie rouge déjà produite) ; le coût est la **validation aval** et le garde-fou accès.

**Chemin conseillé : livrer B maintenant** (cheap, sûr, montre le gisement et son caveat d'accès), **puis A après déploiement** avec le garde-fou — jamais basculer 3 888 parcelles dans le score sans vérifier que la partie hors rouge est accessible et d'un seul tenant.

---

## Annexe — harnais (rejouable, lecture seule)

Base `labuse` (`PGUSER=openclaw PGHOST=localhost`), run `parcel_residuel_runs.run_seq=13` (q_v16). Aucune écriture.
- **Parcelles rouges** : `cascade_results WHERE layer_name='risques' AND result='HARD_EXCLUDE' AND detail LIKE '%PPR zone rouge%'` (151 545).
- **Scope gisement** : jointure `parcel_residuel_runs` (run 13, `cause='terrain_exigu'`) × `parcel_zone_plu` (`zone_fam ∈ {U,AU}`) → 15 176.
- **Surface hors rouge** : `ST_Area(parcel) − ST_Area(ST_Union(ST_Intersection(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975, p.geom_2975)), p.geom_2975)))` sur `spatial_layers kind='ppr' subtype='INTERDICTION'`.
- **Chronométrage** : 300 parcelles = 6,97 s → ~23 ms/parcelle ; distribution complète 15 176 parcelles en ~6 min.
- Code de la règle : `src/labuse/gabarit/builder.py:334-410`, `src/labuse/faisabilite/db.py:471-507`, `src/labuse/faisabilite/engine.py:20,313,491-504`, `src/labuse/faisabilite/residuel.py:136`.
- Arrêt propre, 0 transaction idle-in-transaction, ports 8717/5917 jamais ouverts (audit purement SQL + lecture de code).
