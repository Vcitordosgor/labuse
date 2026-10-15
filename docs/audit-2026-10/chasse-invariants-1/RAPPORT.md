# RAPPORT — CHASSE-INVARIANTS-1

> L'essaim : des règles vraies sur TOUTE l'île. Audit LECTURE SEULE (aucun correctif, aucune
> écriture base, rien sur le VPS). Base servie : q_v18 / run_seq 15, 434 582 parcelles.
> Worktree `labuse-chasse-invariants`, branche `audit/chasse-invariants-1`, API locale 8790.
> 12 sous-agents (1 par domaine), chef d'orchestre Opus. 14→15/10/2026.

## Verdict (5 lignes)
1. **~2,2 millions de lignes-parcelles passées au crible** (l'île entière balayée par chaque règle), **97 invariants** vérifiés par requête SQL et/ou second calcul indépendant.
2. **15 violations actives** : **6 FAUX-CLIENT** (E-01…E-06), **7 INCOHERENT** (E-07…E-13), **2 ROBUSTESSE** (E-14, E-15) ; + 5 anomalies de source déjà neutralisées par le lecteur (N-01…N-05).
3. **82/97 invariants au vert** ; **3 domaines à chasse VIDE prouvée** (7 permis/DPE/BODACC, 9 dates/run, 10 Copilote : 0 hallucination) — un bon résultat, prouvé par le volume passé.
4. **Pire écart** : `taux_emprise_pct` jusqu'à **19 569 %** servi dans l'export Comparatif (E-01) — **trouvé DEUX FOIS indépendamment** (domaine 1 géométrie + domaine 12 recalcul depuis les textes), même parcelle, même ligne de code.
5. **Domaines muets** (non couverts, raison) : appartenance géométrique parcelle⊂commune (aucune couche communale ingérée), chemin LLM live du Copilote (clé absente), faisabilité API pleine échelle (rate-limit 60/min), fraîcheur AMONT réelle des sources (sondes réseau hors cron).

## Les familles de racine (ce qui compte pour le correctif)
- **« Intermédiaire impossible non borné »** → E-01 (= E-15 cousin) : la fiche plafonne, l'export Comparatif non. Un `min(100,…)` à l'écriture du run OU au moins dans `comparatif.py` ferme E-01.
- **« Non-union des polygones de même kind »** dans la cascade → E-03 + E-11 : la fiche union, la cascade non. Unioner les `INTERDICTION` avant le test de seuil ferme les deux.
- **« Âge dirigeant servi sans clamp »** → E-05 + E-06 : un seul garde-fou de bornes [18;110] sur l'aîné couvre fiche §Identité, filtre 70+ et veille succession.
- **« Table dérivée statique jamais revalidée »** → E-02 (parcel_zone_plu) et, famille voisine, E-09 (run figé avant peuplement de colonne) : des dérivées qui dérivent en silence.
- **« Deux définitions du parc dans la même carte »** → E-12 : `surface_ha` compte les disparues, `n_parcelles` non. Ajouter `filtre_vivant_sql` à la surface.

---

## Par domaine

### 1 — Géométrie et surfaces · 🔴 1 FAUX-CLIENT + 3 INCOHERENT
434 582 parcelles, 9 invariants. Géométries toutes valides/SRID/non nulles (0), disparues hors
calcul servi (0), surface jamais ≤0 (0), surface incertaine tracée (0 non-tracée). **E-01** ratios
non bornés (taux jusqu'à 19 569 %, 61 599 parcelles). **E-07** centroïde `ST_Centroid` hors parcelle
(9 792). **E-08** bâti > dessin dans la table amont (20 243, n'atteint pas la fiche). **E-09**
`surface_terrain_m2` NULL sur tout le run (fonction « surface du calcul » muette). Muet : parcelle⊂commune
(pas de couche communale → vérifié par INSEE seulement).

### 2 — Zonage et règles PLU · 🔴 1 INCOHERENT → FAUX-CLIENT (1 380)
434 582 parcelles, 7 invariants. RNU Saint-Philippe tenu (0 U/AU), non-validées jamais servies (0),
gabarit borné (0), fam↔lib (0), parts ≤100 % (0). **E-02** : `parcel_zone_plu` statique, jamais
reconstruite → 2 901 parcelles zonables orphelines, dont 1 380 servant une SDP positive sans zone à
la carte (fiche↔carte se contredisent). Classé non-bug : 4 127 A/N-dominant à SDP>0 (assiette déjà
clippée U/AU, décision Vic 24/09). Muet : volet A/N île-entière (échantillon 400, 0 fuite).

### 3 — Capacité et scoring · 🟠 0 FAUX-CLIENT, 1 INCOHERENT de conception
433 229 parcelles, 10 invariants. Couverture score 100 %, bande⇔score (5 miroirs à 0), 0 muet,
borne physique SDP (×3,14 max), moteur `sdp = emprise×niveaux` (120/120), score reproductible &
déterministe (500/500), barème monotone. **E-10** : 607 parcelles bande A ET `cascade_exclue`
(route/DPF/forêt) — bénin tant que l'overlay d'exclusion est peint, mais le tri bande A les ignore.
Muet : monotonie « à règles strictement égales » (non testable en SQL, prouvée par construction).

### 4 — Risques et servitudes · 🔴 1 FAUX-CLIENT + 1 INCOHERENT
107 406 parcelles touchant du PPR rouge, 5 invariants. Servitudes toutes sourcées (0), PPR-partiel
légitime (0), hors-rouge ≤ contenance (0). **E-03** : la cascade n'union pas les polygones INTERDICTION
→ 224 parcelles ≥50 % rouge (union) sans exclusion, dont 30 servies constructibles (pire : score B /
8 297 m² SDP sur 65 % rouge). **E-11** : sur ces 30, la fiche dit « rédhibitoire » et le score sert
constructible. Muet : union géométrique sur 64 299 mono-polygone (timeout, sans objet) ; CatNat/OCSGE
par géométrie non recoupés.

### 5 — Marché, prix et estimations · 🔴 1 FAUX-CLIENT + 1 ROBUSTESSE
282 287 lignes `score_e` + 29 566 DVF, 8 invariants. **Identité `marge=charge−prix` à l'euro près sur
150 179 lignes, 0 écart.** Mention « estimé » partout (0), €/m² et médianes plausibles (0), run partout
(0). **E-04** : fenêtre DVF sur `CURRENT_DATE` au lieu de `max(date_mutation)` → −1 068 ventes (−8,9 %)
jetées silencieusement (L7 non propagée aux lecteurs génériques). **E-15** : marges en dizaines de M€
sur très grandes parcelles (justes mais vides de sens). Muet : prix obsimmo/Radar, médianes neuf live.

### 6 — Propriétaires et sociétés · 🔴 2 FAUX-CLIENT (racine unique)
82 701 liens PM + 158 515 SIRENE + 27 146 dirigeants, 9 invariants. SIREN Luhn (0), cessée≠active (0,
déjà gardé), lien idu↔PM unique & sourcé (0 servi). **E-05** : âges de dirigeant aberrants servis en
fiche §Identité — **117 ans prouvé live** sur `/parcels/97411000BL0284`, + 0/4/13/114 (aîné pris sans
clamp de bornes). **E-06** : âge 114 entre dans « Successions à venir ». Muet : exactitude amont des
dates INPI (1909/1911 — défaut source ou ingestion non tranché).

### 7 — Permis, DPE, BODACC · 🟢 chasse VIDE prouvée
50 809 permis + 4 822 PC caducs + 1 123 DPE + 16 170 BODACC, 13 invariants, **0 violation active**.
pc_caducs rebuild 06/10 impeccable (CHASSE-FIX-3 tenu), DPE 100 % rattachés BAN + étiquettes A–G,
clôture 2117 filtrée, 7 754 inversions de dates toujours notées. 3 anomalies de source (N-01/02/03)
déjà neutralisées par le lecteur. Muet : lecteurs géométriques carte, véracité externe SDES/ADEME.

### 8 — Communes et agrégats · 🟠 1 INCOHERENT
433 229 parcelles, 24 communes, 11 invariants. 24 communes partout (0 NULL), somme = île, additivité
/stats, filtre = cardinal SQL, écart /communes vs /stats = exactement 879 slivers <2 m². **E-12** :
`foncier.surface_ha` somme les parcelles disparues alors que `n_parcelles` les exclut → +153 ha
fantômes Saint-Paul, +120 Saint-André, 22/24 communes. Muet : parts aléa/PPR en % (déjà couvertes par
`checks_commune.py`), indicateurs externes (population/SRU/prix).

### 9 — Dates et fraîcheur · 🟢 chasse VIDE prouvée
433 229 parcelles + 99 sources, 7 invariants, **0 FAUX-CLIENT ni INCOHERENT**. Run **cohérent partout**
(manifeste = residuel = mvt = score = cascade), aucune date de source dans le futur, aucun millésime
2027+, tables dérivées à la version de règle du code. 2 observations mineures : N-04 (1 DVF 2026
outlier), N-05 (caches locaux non-warmés, auto-réparants). Muet : fraîcheur AMONT réelle (sondes hors
cron), `source_millesime` = label producteur (non recalculable sauf gardes existantes RPLS/PM/BODACC).

### 10 — Copilote · 🟢 0 hallucination
30 questions à réponse connue sur 12 parcelles (5 communes, zones U/A/N, bandes 0/B/C/D/NC) + test
adversarial + 9 tests unitaires du verrou rejoués verts. **0 chiffre inventé, 0 source inventée, refus
propres.** 13/13 réponses déterministes identiques à la DB. Clé LLM absente en local → chemin modèle
dégradé HONNÊTE (jamais de chiffre), chemin déterministe lit le robinet de la fiche (parité). Muet :
chemin modèle live + recherche web sourcée (à auditer le jour où la clé est posée) ; le verrou aval est
déterministe, indépendant du prompt (ceinture-bretelles).

### 11 — API et robustesse · 🟠 2 ROBUSTESSE
59 requêtes limites sur les vraies routes, 7 invariants. idu/commune/liste/filtre/recherche malformés :
**0 × 500, 0 affichage sale, 0 négatif impossible** (404/422 propres, SQLi filtré). **E-14** : tuile MVT
avec x/y hors `[0,2^z)` → **HTTP 500** sur les DEUX routes (`z` validé, `x`/`y` jamais bornés avant
`ST_TileEnvelope`). Muet : POST authentifiés (évaluate/projets — non sondés pour rester lecture seule),
concurrence/pool.

### 12 — Double-calcul indépendant · 🔴 1 FAUX-CLIENT + 2 bords d'arrondi
Taxe (10 cas + 500 parcelles × 3 profils = 1 510), faisabilité (300 chaîne + 73 480 base), bilan (10
jeux) — recalculés depuis le CGI, les règlements PLU et le modèle Excel **sans ouvrir le code de calcul
de LABUSE**. **Taxe au centime (0), bilan 10/10 (0), chaîne faisabilité 0 écart réel.** **E-01**
reconfirmé indépendamment (F3 : 61 599 taux > 100 %). **E-13** : `sous_densite=true` avec taux affiché
40 % (bord d'arrondi, le flag a raison sur le fond). V3 (6 « divergences » SDP) et 3 « divergences »
bilan : artefacts d'arrondi / erreur de la calculette — **LABUSE a raison**, consignés par honnêteté.

---

## Les gardes de nuit
Toute règle vérifiée est portée dans `scripts/coherence/chasse_invariants.py`, rejouable par
`PYTHONPATH=src .venv/bin/python -m scripts.coherence.chasse_invariants` (lecture seule,
`statement_timeout` posé). Aujourd'hui le banc MORD (les 15 écarts sont ouverts) ; après correctifs il
doit passer au vert et rejoindre le banc de nuit — sans doublonner `chasse_donnees.py` (cessée/active,
fraîcheur BODACC/RPLS), `checks_commune.py` (aléa/PPR %), `aggregats.py` (compteurs de filtre).

## Gestes pour Vic (hors périmètre de cet audit lecture seule)
1. **E-01** (le plus visible) : plafonner `taux_emprise_pct`/`pct_potentiel` à l'écriture du run **ou**
   au moins dans `exports/blocs/comparatif.py:97` (la fiche est déjà protégée).
2. **E-03/E-11** : unioner les polygones `INTERDICTION` de même kind avant le seuil de 50 % dans la
   cascade (`cascade/layers/phase1.py`).
3. **E-05/E-06** : clamp [18;110] sur l'âge de dirigeant à la source (`_pm_dirigeant`, `v_pm_propension_vendre`).
4. **E-02** : revalider/reconstruire `parcel_zone_plu` quand `parcels`/`spatial_layers` ont bougé.
5. **E-12** : ajouter `filtre_vivant_sql` à `surface_ha` (`api/app.py:2161`).
6. **E-14** : borner `0 ≤ x,y < 2^z` avant `ST_TileEnvelope` (un seul correctif, deux routes).
7. **E-09** : re-jouer le run pour peupler `surface_terrain_m2` (code d'écriture présent).
8. Mineurs : E-13 (même arrondi aux deux colonnes), E-15 (garde-fou de surface sur le bilan score_e),
   E-07/E-08 (`ST_PointOnSurface` à l'ingestion, clip de la table bâti amont).
