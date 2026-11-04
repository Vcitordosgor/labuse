# CHASSE-1 — LOT A — Incohérences données & calculs

**Mandat** : chasse aux incohérences que les témoins habituels ne voient pas — tirage au
hasard, cas limites, comptes & totaux, temps/fuseaux, prod contre local. Lecture seule partout.

- **Branche** : `audit/chasse-1-a` · worktree `~/Desktop/labuse-chasse-a` · ports 9590/6790
- **Base** : Mac locale `labuse`, run servi **q_v20** (`/readyz` → `served_run q_v20`), 434 582 parcelles (433 229 vivantes, 1 353 `cadastre_disparue`)
- **HEAD** : `423106cdc` (DEPLOY-GROUPE-1)
- **Date** : 2026-11-05, ~01h40 Réunion (UTC+4)
- **Prod** : **NON testée** — la fenêtre 01h–05h Réunion interdit l'accès prod (voir §Prod-vs-local). À reprendre après 05h.
- **Méthode** : API locale bootée sur 9590 (q_v20, auth désactivée) + SQL brut sur `labuse` + lecture de code. Harnais de comparaison inter-surfaces conservé (`harness-cross-surface.py`), échantillon reproductible (`echantillon-362.txt`).

---

## Résumé — trouvailles par gravité

| # | Gravité | Titre | Surface |
|---|---------|-------|---------|
| A-1 | **MAJEUR** | Le compteur de parcelles masque les slivers sur le **dessin** et non sur la **surface servie** → 279 parcelles réelles (jusqu'à 35 m²) disparaissent du compteur/entonnoir/Stats/Découverte mais restent sur la carte, la fiche et la recherche | compteur `/filtre`, liste, Stats |
| A-2 | mineur | Les **tuiles MVT** (`/map/tiles`) n'appliquent **aucun** plancher de surface → 879 parcelles sub-2 m² (dont 600 vrais slivers) sont peintes, contrairement au contrat « slivers masqués de la carte » | carte (tuiles vectorielles) |
| A-3 | mineur | Grappe de dates **J-1** au front : 7 `toLocaleDateString('fr-FR')` sans `timeZone:'Indian/Reunion'` + calculs d'âge « il y a N j » mélangeant heure navigateur et UTC (classe SILENCE-1) | front (Veille, Radar, carte, John, Copilote, Licences) |

**Rien d'autre trouvé.** La campagne confirme surtout des **invariants sains** (voir §Contrôles passés) : le balayage inter-surfaces de 362 parcelles n'a relevé **0 divergence**.

---

## A-1 — MAJEUR — Le compteur masque les slivers sur le dessin, pas sur la surface servie

**Preuve.**
- Sur une commune (Cilaos) : la carte/tuiles peignent **6 583** parcelles, le compteur `/filtre` en annonce **6 576** (écart 7). À l'échelle de l'île : tuiles **433 229** vivantes vs compteur global **432 350** → **écart 879**.
- L'écart **879 = exactement** le nombre de parcelles vivantes dont le **dessin** `surface_m2 < 2 m²`. Décomposition SQL :

```
live surface_m2<2 (dessin)          = 879   ← tout l'écart compteur↔carte
  dont servie COALESCE(cont,dessin)≥2 =  279  ← PARCELLES RÉELLES masquées à tort
  dont servie <2 (vrais slivers)      =  600
```

- Cause racine dans le code : le masque anti-sliver teste le **dessin** `p.surface_m2`, pas la surface servie :
  - `src/labuse/api/app.py:4448` (`_q_v2_stats`, le compteur) : `AND (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf)`
  - `src/labuse/api/app.py:4126` (`_q_v2_list`, la liste) : `AND (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf)`
  - Or la surface **servie au client** est la **contenance** si présente (`src/labuse/surface.py`, CONTENANCE-1 : `SURFACE_TERRAIN_SQL = COALESCE(contenance_m2, surface_m2)`), lue telle quelle par la fiche, la recherche, la tuile (`tiles.py:225`), le GeoJSON (`app.py:3912`) et le Copilote.

- Effet client vérifié sur `97416000DM0437` (Saint-Pierre) — dessin 1,88 m², **contenance 35 m²** :

```
GET /parcels/97416000DM0437        → surface_terrain_m2 = 35 (cadastre)
GET /parcels/search?q=97416000DM0437 → surface_terrain_m2 = 35
mvt_parcels (carte)                → présente (peinte)
/filtre (compteur/Stats/liste)     → ABSENTE (surface_m2 1,88 < 2)
```

Une parcelle de 35 m², avec fiche complète et peinte sur la carte, **ne compte pas** dans « N parcelles », l'entonnoir, la page Stats ni la Découverte.

- Répartition des 279 (par commune) : Saint-Denis 48, Saint-Pierre 44, Saint-Paul 42, Le Port 25, Saint-Louis 16, Saint-Joseph/Sainte-Marie/Le Tampon 13… contenance max observée 35 m².
- Inverse symétrique mineur : **38** parcelles ont dessin ≥ 2 m² mais contenance < 2 m² → **comptées** par le compteur alors qu'elles sont des slivers au sens servi.

**Reproduction (1 ligne).**
```
curl -s "localhost:9590/parcels/97416000DM0437" | jq .surface_terrain_m2   # 35, mais absente de /filtre?commune=Saint-Pierre&source=q_v20
```
ou SQL : `SELECT count(*) FROM parcels WHERE cadastre_disparue_le IS NULL AND surface_m2<2 AND COALESCE(contenance_m2::float,surface_m2)>=2;` → **279**.

**Cause probable.** La campagne CONTENANCE-1 a créé `SURFACE_TERRAIN_SQL` et migré l'**affichage** vers la contenance, mais les masques anti-sliver de `_q_v2_stats`/`_q_v2_list` sont restés sur `surface_m2` (le dessin). Les commentaires du code (« UNE SEULE définition du nombre de parcelles partout », FIX-FILTRES F2 ; CONTENANCE-1 « plus personne ne lit `surface_m2` seul pour FILTRER une surface de terrain ») affirment l'invariant que ce masque viole.

**Gravité.** MAJEUR (défaut de correction d'un compteur de tête + contradiction d'un invariant revendiqué), **faible volume** (279 / 433 229 = 0,06 %, ≤ 48 par commune) et parcelles quasi-dégénérées → impact pratique limité. Correctif évident (remplacer `p.surface_m2` par `COALESCE(p.contenance_m2, p.surface_m2)` dans les deux masques), non appliqué (lecture seule).

---

## A-2 — mineur — Les tuiles MVT n'ont aucun plancher de surface

**Preuve.** Le commentaire `app.py:71` affirme « slivers cadastraux < 2 m² : masqués de la CARTE et de la Découverte ». Or la requête de service des tuiles ne filtre QUE la bbox et (au build) `cadastre_disparue_le IS NULL` :

```
src/labuse/api/tiles.py:684-689
  SELECT ST_AsMVTGeom(...) FROM mvt_parcels m, b WHERE m.geom_3857 && b.env
```

Aucun `MIN_DISPLAY_SURFACE_M2`. `mvt_parcels` contient donc les 879 parcelles sub-2 m² de dessin (600 vrais slivers + les 279 ci-dessus). Le GeoJSON commune (`app.py:3912`) et la liste/compteur appliquent un plancher ; les tuiles non. C'est l'autre moitié de l'écart A-1 côté carte.

**Reproduction.** `SELECT count(*) FROM mvt_parcels m JOIN parcels p ON p.idu=m.idu WHERE COALESCE(p.contenance_m2::float,p.surface_m2)<2;` → **638** vrais slivers peints.

**Cause probable.** `build-mvt` matérialise toutes les parcelles vivantes sans plancher ; `ST_AsMVTGeom` écarte les géométries dégénérées aux faibles zooms (les slivers « disparaissent » visuellement < z19), ce qui a masqué le défaut. Visible seulement au zoom max.

**Gravité.** mineur (invisible en pratique < z19 ; aucun chiffre faux). Lié à A-1 : même notion de « sliver » appliquée de façon incohérente entre trois chemins carte (tuiles = aucun filtre ; GeoJSON/liste/compteur = filtre sur dessin ; fiche/recherche = aucun filtre, sert tout).

---

## A-3 — mineur — Grappe de dates J-1 au front (classe SILENCE-1)

**Preuve.** 7 appels `toLocaleDateString('fr-FR')` **sans** `timeZone:'Indian/Reunion'` (le reste du front le fixe — 18 fichiers conformes) :

```
frontend/src/components/outils/VeillePromoteurs.tsx:202, 259   (millésime Sitadel)
frontend/src/components/panel/ResultsSection.tsx:101, 104      (date événement BODACC)
frontend/src/components/outils/RadarMarche.tsx:16              (date marché)
frontend/src/components/map/MapView.tsx:73, 1001               (date permis / période opération)
```

Plus des calculs d'âge relatif (« il y a N j / N mois ») qui diffèrent `Date.now()` (heure **navigateur**) d'un ISO parsé en **UTC** — classe SILENCE-1 côté front :

```
frontend/src/components/admin/circuit/JohnTaylor.tsx:151   const jours = Math.floor((now.getTime()-d.getTime())/86_400_000)
frontend/src/components/copilote/ConversationsSidebar.tsx:14
frontend/src/lib/status.ts:305                              (âge en mois, licences)
frontend/src/components/admin/Radar.tsx:188 · Licences.tsx:163
```

**Reproduction.** Afficher un millésime Sitadel date-seule (`'2026-10-11'`) depuis un navigateur en UTC-5 → rend « 10/10 » au lieu de « 11/10 ».

**Cause probable.** Nettoyage I-TPS incomplet : fichiers récents (Veille, John, Copilote, carte) ajoutés après la passe qui a corrigé `format.ts`/cockpit/ZIP. **Backend sain** : `tz.py` (`today_reunion`/`now_reunion`) partout ; seuls des outils offline (`scripts/`) utilisent `date.today()` naïf, hors chemins servis.

**Gravité.** mineur — ne mord que les navigateurs dont le fuseau ≠ Réunion (les utilisateurs sont à la Réunion) et près de minuit. Cosmétique sur un millésime/une date d'événement.

---

## Contrôles passés (invariants confirmés sains)

Autant de « pièges habituels » vérifiés **sans écart** — utile pour ne pas les rechasser :

1. **Balayage inter-surfaces, 362 parcelles** (288 tirées au hasard, 12/commune, md5 reproductible + 74 cas limites : géantes >1 km², minuscules 1–5 m², sans contenance, sans zonage PLU, surface incertaine). Comparé fiche ↔ recherche/liste ↔ carte (mvt) sur : surface servie, drapeau surface incertaine, zone, tier, rang, SDP résiduelle. **0 divergence, 0 erreur fiche.** (`findings.json` = `[]`.)
2. **Surface servie** : source unique `surface.py` (contenance sinon dessin, repli « mesurée sur le plan »). Tuile == fiche : seules 28 parcelles (contenance NULL → dessin) diffèrent du champ contenance, par conception.
3. **Drapeau « surface incertaine »** (facteur > 2 dessin↔contenance) : carte `mvt_parcels.surface_incertaine` == règle `surface.py` → **1 593 des deux côtés, 0 dérive.**
4. **Somme des parties = total** :
   - Logement commune : p1+p2+p3+p4+p5p = résidences principales (Cilaos 2 092) ; +secondaires +vacants = logements (2 926). ✓
   - `/filtre` : Σtiers = total = Σbandes = instruire+écartées (Cilaos 6 576). ✓
   - Σ des totaux par commune = total île global (432 350). ✓
5. **Fiche commune** : `classement.evaluees` (Cilaos 6 583) = parcelles vivantes = parcelles zonées ; `sans_zonage = 0`. ✓
6. **PDF == fiche** sur cas limite (parcelle sans contenance 76 m² : PDF « 76 m² · surface (plan) » = fiche). ✓
7. **Multi-zone / « à cheval »** : la fiche liste toutes les zones ≥ 2 % de recouvrement + drapeau `a_cheval` (cascade `zone_dominante`) ; la carte/filtre n'en gardent que la dominante (`parcel_zone_plu`) — comportement voulu, déjà traité (FRONT-CHIFFRES-2).
8. **Parcelles disparues** : les 1 353 `cadastre_disparue` sont exactement les 1 353 absentes de la carte (`mvt_parcels`). ✓
9. **24 communes**, préfixe INSEE idu ↔ libellé commune cohérent sur les 24. ✓

---

## Prod contre local — DIFFÉRÉ

Non exécuté : le mandat interdit l'accès prod entre 01h et 05h Réunion, et la session s'est
tenue dans cette fenêtre (≈ 01h00–01h45 Réunion). À reprendre après 05h Réunion :
rejouer `harness-cross-surface.py` contre l'API prod pour les 362 IDU de `echantillon-362.txt`
et diffuser les écarts (surface servie, tier, rang, zone, SDP). Hypothèse : identiques (prod
sert le même manifeste q_v20) ; à prouver.

---

## Annexes (dans ce dossier)

- `harness-cross-surface.py` — harnais de comparaison fiche/recherche/carte (rejouable : `PYTHONPATH=src ../labuse/.venv/bin/python harness-cross-surface.py` avec l'API sur 9590).
- `echantillon-362.txt` — les 362 IDU (288 aléatoires reproductibles + 74 cas limites).
