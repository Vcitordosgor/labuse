# RAPPORT-2 — CHASSE-INVARIANTS-2

> Mille règles, **générées, pas écrites à la main**. On ne passe pas à 1 000 en écrivant 900 règles de
> plus : on les génère depuis ce que l'app sait d'elle-même (schéma, registre, routes, règlements PLU),
> puis on les fait tourner sur toute l'île. Audit **LECTURE SEULE** — aucun correctif, aucune écriture
> base, rien sur le VPS. Base servie **q_v18 / run_seq 15 / cascade q_v18_sources**, **434 582 parcelles**
> (433 229 vivantes), 24 communes, corrections de FIX-1 mergées. Worktree `labuse-chasse-inv2`, branche
> `audit/chasse-invariants-2`, API locale 8793. Opus chef d'orchestre, un sous-agent par famille.
> 15/10/2026. **Avant le run final.**

## Verdict (5 lignes)
1. **1 485 règles générées · 1 035 retenues** (vague 2) **+ 97 reprises de la vague 1 = 1 132 règles
   utiles**, chacune traçable à sa famille et à sa source ; **450 candidates écartées AVANT de tourner**
   (chacune avec sa raison — discipline « une règle qui n'a pas de sens est retirée avant, jamais après »).
2. **Lignes passées : plusieurs millions de lignes-parcelles** — la quasi-totalité des règles SQL balaient
   l'île entière (434 582 parcelles) ; + 4 837 faisabilités calculées à blanc, ~5 400 cas métamorphiques,
   ~250 requêtes API aux bornes, 248 chiffres + 158 robinets + 581 arêtes du registre vérifiés.
3. **4 violations confirmées, TOUTES par F1 (schéma), 3 d'une MÊME racine** : les hauteurs LiDAR
   (`batiment_hauteur_lidar.faitage_m`/`egout_m`) servies **sans borne** — `egout_m < 0` ×1 218,
   `faitage_m < 0` ×44, `faitage_m = 53 401 m` ×2 — à la fiche ET à l'outil Gabarit (FAUX-CLIENT) ; + 1
   DPE à l'année 1761 (anomalie source ADEME, ROBUSTESSE). Détail dans `ECARTS-2.md`.
4. **6 des 7 axes de la vague 2 sont des CHASSES VIDES PROUVÉES par le volume** : F2 (même valeur partout,
   0 incohérence inter-surfaces), F2b (registre structurellement intègre, 253 chiffres/robinets), F3
   (les 3 moteurs monotones par construction, 0 contre-exemple), F4 (calibrage PLU sain, **aucune zone
   `propose` ne sert**), F5 (API robuste — **E-14 corrigé, 0 × 500**), F6 (**parcelle⊂commune : 0
   misattribution** sur 433 229 ; faisabilité intègre à l'échelle). Seul F1 (schéma) mord.
5. **Zones muettes de la vague 1 : fermées** — l'appartenance géométrique parcelle⊂commune (le muet-titre)
   est désormais couverte (geojson officielle en couche de session, 0 trou) ; la faisabilité pleine échelle
   tourne en appel direct du moteur (bypass du rate-limit) ; le reste du muet est soit couvert, soit écarté
   avec sa raison. **3 écarts de la BASE restent rouges** (E-09, E-03/E-11, E-13) : ce sont les correctifs
   « calcul » de FIX-1 qui ne passeront au vert **qu'après le run final q_v19** (code mergé, donnée servie
   encore q_v18) — attendus, documentés, non nouveaux.

## Le banc de nuit (rejouable, < 30 min)
Toutes les règles retenues entrent dans `scripts/coherence/invariants2/banc2.py`, rejouables par **une
commande** :
```bash
PYTHONPATH=src .venv/bin/python -m scripts.coherence.invariants2.banc2 --tout --api http://127.0.0.1:8793
```
- **`--tout` (hebdo ou chaque nuit) : ~18 min** — base vague-1 (97/39 gardes) + les 7 axes. **Compatible
  nuit** (< 30 min) ; peut tourner chaque nuit.
- **`--nuit` (smoke rapide, ~4 min)** : saute les deux familles à boucle API cadencée (F2 valeur
  inter-surfaces 546 s, F5 API 289 s) ; garde base + F1 + F2b + F3 + F4 + F6 (tout le SQL île entière).
- `--famille F1,F4` pour un sous-ensemble ; `--no-base` pour sauter les 97 repris.
- Lecture seule stricte : connexion `read_only`, `statement_timeout` 120 s, aucun INSERT/UPDATE/DDL.
Le banc MORD aujourd'hui (7 ECART : 3 base q_v19-pending + 4 F1) ; après le garde-fou hauteurs LiDAR et
le run q_v19, il doit passer au vert et rejoindre la garde de nuit.

---

## Par famille

### F1 — Le schéma · 🔴 4 FAUX-CLIENT/ROBUSTESSE (1 racine)
303 générées / **238 retenues** / 65 écartées. Dictionnaire métier nom→règle appliqué à **31 tables
servies** (feeders fiche/carte/liste + fiche commune) : non-négativité, bornes (année∈[1800,2026],
proportion≤100, probabilité∈[0,1], pente≤90°, hauteur bâti≤300 m), dates ni futures ni <1900, énum légale
fermée (DPE A–G, bande), nullité attendue. 234 vertes sur l'île entière. **4 écarts** (cf. ECARTS-2) : la
racine unique est les hauteurs LiDAR `methode='dalle'` servies sans borne (fiche + Gabarit) ; + 1 DPE 1761
(source ADEME). 65 écartées à bon escient : taux d'imposition non plafonnés à 100, pct de base >100
légitimes (clampés au rendu, vague-1 E-01), colonnes signées (delta/NDVI/longitude), techniques.

### F2 — Le registre, valeur inter-surfaces · 🟢 chasse vide
59 retenues / 234 écartées. Généralisation de la chasse aux données : **la même valeur partout**. 4 axes —
liste `/parcels` vs source DB île entière (17), liste vs fiche (14, 2 chemins de code), `/filtre` vs liste
(7), export vs fiche (2), + 19 de la 1re passe. **0 incohérence.** Écartées : chiffres mono-surface (204),
surfaces non-GET-JSON (PDF/Copilote/tuiles), définitions différentes (gabarit vs résiduel, mutation vs
parcelle). **Zone muette assumée** : 18 chiffres commune derrière `commune_contexte_cache` VIDE dans ce
worktree (documentée, pas un trou).

### F2b — Le registre, intégrité par chiffre · 🟢 chasse vide
253 retenues / 4 écartées. Granularité **par chiffre** (cadre du mandat : « pour chaque chiffre du registre
et chaque robinet qui le sert »). Un invariant d'intégrité par chiffre (248 : unité/niveau/portée/libellé/
version bien formés + chaque réservoir listé porte son arête) + socle robinet/arêtes (5). Registre
**structurellement intègre** (0 anomalie). 4 écartées car non universelles (moteur nul légitime 107/248,
reservoirs vides 76/248, chiffres[] vides 2/158) dont `parent_existe` — `parent` mélange ids de robinet et
étiquettes de surface → règle insensée retirée avant 53 faux-mordants.

### F3 — Relations métamorphiques · 🟢 chasse vide
74 générées / **72 retenues** / 2 écartées. Calcul à blanc, en-process (jamais l'API ni d'écriture), 3
moteurs : faisabilité (96 ZoneRules réelles), bilan financier, taxe. ~5 400 cas. Couples entrée↑⇒sortie
dans le bon sens : surface⇒capacité/SDP/emprise/niveaux≥ ; hauteur⇒niveaux/SDP≥ ; recul⇒emprise≤ ;
contrainte rouge (PPR/littoral/SAR/pente)⇒SDP/logements≤ ; prix⇒marge≤ ; taxe monotone en surface/taux,
abattements≤. **0 contre-exemple** — monotonie par construction, perturbations qui MORDENT réellement
(contre-vérifié) donc les OK ne sont pas des no-ops. 2 écartées (hauteur↛emprise ; prix revente↛taux marge).

### F4 — Le PLU · 🟢 chasse vide
349 générées / **218 retenues** / 131 écartées. Par zone calibrée (23 communes hors RNU St-Philippe, 348
zones, ~2 023 feuilles valide) : valeur servie dans les bornes du règlement (154), citation non vide + page
dans `meta.pages_total` (46), renvoi vers une zone déclarée (15), **aucune feuille SDP `propose` ne porte de
valeur** (garde moteur), couverture GPU (3). **0 écart.** Preuve faux-client (YAML + donnée) : aucune
parcelle SDP servie > 0 ne dérive d'une zone `propose` ; 737 couples (insee, zone_lib) servis résolvent tous
à une ZoneRules (0 trou muet). 2 règles resserrées avant de tourner (extrait PDF épars ; SDP=0 saturé).

### F5 — L'API à la limite · 🟢 chasse vide (E-14 corrigé)
165 générées / **162 retenues** / 3 écartées. Par route × classe de paramètres (18 routes GET). 3 invariants
par cas : jamais de 500, jamais de NaN/None/null affiché, réponse identique à 2 appels. ~250 requêtes aux
bornes/vides/absurdes/SQLi/unicode/surdimensionnées/combinées. **0 violation.** **E-14 (vague 1 : tuile hors
grille → 500) est GREEN** — 204 partout (FIX-1 tient). 3 écartées (`/discover` absent du build ; 2 null-checks
légitimes). Observation hors périmètre : `/recherche/suggest` expose un champ latence `ms`.

### F6 — Zones muettes de la vague 1 · 🟢 chasse vide prouvée
44 générées / **33 retenues** / 11 écartées. **(1)** Appartenance parcelle⊂commune (le muet-titre) :
limites officielles `communes974.geojson` en couche de session (littéral GeoJSON, aucune table), rattachement
par INSEE ; piège de la geojson simplifiée (44 KB) neutralisé par raisonnement sur le centroïde (violation
seulement > 200 m dans une AUTRE commune). **0 misattribution grossière sur 433 229 parcelles**, pire cas
75,4 m = sliver de bord (3 pires revérifiés). **(2)** Faisabilité pleine échelle, moteur en appel direct
(bypass rate-limit) : **4 837 parcelles calculées proprement, 0 exception, 0 incohérence**. **(3)** Volet A/N
île entière vert. 11 muets écartés avec raison (union PPR = E-03 déjà ouvert, OCSGE/CatNat double-jointure
hors budget, parts = `checks_commune.py`, E-09 déjà ouvert, Copilote/fraîcheur/POST hors portée lecture seule).

### BASE — les 97 de la vague 1 (repris tels quels) · 🟠 3 ECART q_v19-pending
36 OK · **3 ECART** · 0 SKIP (39 gardes). Les 3 — **E-09** (`surface_terrain_m2` NULL sur q_v18), **E-03/E-11**
(union PPR dans la cascade), **E-13** (sous-densité cohérente) — sont les correctifs **« calcul »** de FIX-1 :
le code est mergé mais ne s'applique qu'au recalcul du **run final q_v19** ; la donnée servie est encore q_v18.
Attendus, documentés (cf. `../chasse-invariants-1/RAPPORT-FIX.md`), **non nouveaux**.

---

## Ce qui reste muet (honnêteté)
- **18 chiffres commune** (F2) : `commune_contexte_cache` est VIDE dans ce worktree → `/communes/{c}/contexte`
  ne sert pas sru/prix/marché/foncier ici. À rejouer quand le cache est chaud.
- **Recoupes géométriques lourdes** (F6) : union PPR île entière et OCSGE/CatNat par géométrie = double-jointures
  hors budget d'un audit « une requête lourde à la fois » ; union PPR déjà couverte par E-03.
- **Chemins hors portée lecture-seule/local** : LLM live du Copilote (clé absente), fraîcheur AMONT réelle
  (sondes hors cron), POST authentifiés, concurrence/pool, prix obsimmo/Radar & médianes neuf live,
  véracité externe SDES/ADEME.

## Gestes pour Vic (hors périmètre de cet audit lecture seule)
1. **Hauteurs LiDAR (E2-01/02/03, FAUX-CLIENT)** : borner au service — `GREATEST(0, LEAST(faitage_m, 300))`
   (idem `egout_m`), ou repli sur `hauteur_bdtopo_m` quand `methode='dalle'` rend un négatif. Ferme les 3
   d'un coup, fiche (`app.py:6423-6424`) + outil Gabarit (`gabarit.py:63`).
2. **DPE 1761 (E2-04)** : signaler l'anomalie à l'amont ADEME (saisie), comme les 481 dates INPI de FIX-1.
3. **Run q_v19** : embarque déjà les correctifs calcul de FIX-1 (E-09/E-03/E-13…) → la BASE passera au vert.
