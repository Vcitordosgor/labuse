# OUTIL-PERMIS-FIX-1 — compte-rendu

> Réponse point par point à la **liste fermée** du contre-audit du relecteur (`~/Desktop/audit-outils/02-PERMIS-ASTRA.md`).
> Branche `fix/outil-permis-1` (partie de `fix/mini-corrections-2`). Base locale `labuse` (lecture + reconstruction des couches dérivées en local), API de recette sur **:7500**, front sur **:10300**. Les ports 8000/5173 et la base partagée des autres sessions n'ont pas été perturbés (aucune requête lourde laissée tourner, aucune écriture sur `sitadel_permits`).
> Captures : `~/Desktop/outil-permis-fix-1/`.

## En deux lignes

Les trois bloquants sont levés : le filtre « Autres » **égale** son compteur sur les quatre périmètres (plus aucune soustraction) ; sur les 30 dormants témoins, **1 seul** reste dormant après mesure du bâti (29 étaient annulés, commencés ou bâtis) ; le voisinage 200 m **retrouve les 13 permis de BZ 1065** et les 10 recomptes du relecteur, et suit désormais les permis par trigger. Une **seule fonction serveur** (`src/labuse/permis_classe.py`) classe un permis pour le compteur, le filtre, la liste, la carte et le mode parcelle.

---

## Le socle du correctif — une seule définition des états

`src/labuse/permis_classe.py` : **ordre de priorité ÉCRIT** (le premier qui s'applique gagne), **horloge unique** = `dmax` (`max(date)` de `sitadel_permits` = fin du flux Sitadel, 31/08/2026) :

1. **Achevé** — `daact` présente **OU** code état `6`.
2. **Dormant** — PC, code état ∉ {4 annulé, 5 commencé, 6 achevé}, sans `daact`, `date < dmax − 36 mois`, parcelle **mesurable** et **sans bâti** (`parcel_bati_emprise.bati_m2 < 10 m²`).
3. **Récent** — `date ≥ dmax − 24 mois`.
4. **Autre** — le reste.

`etat_case_sql()` sert le **compteur** (GROUP BY) *et* le **filtre** (`etat_pred_sql` = `(CASE…) = 'etat'`) → compteur = lignes du filtre **par construction**. Lu par : `/modules/permis` (compteur/liste/carte), `/modules/parcelle-permis` (mode parcelle), `/modules/promesses` (liste dormante), `registre/moteurs/commune.permis_point_mort` (fiche commune).

---

## Point 1 — Unifier les états (compteur = filtre = liste = carte, partout)

**Avant (relecteur).** Le chip « Autres » comptait `Tous − Récent(3 mois) − Dormant − Achevé` ; cliquer « Autres » (fenêtre 24 mois) rendait **4 880 permis de moins** sur l'île. Deux « récent » (3 mois vs 24 mois) sous le même mot ; un achevé < 24 mois changeait d'état entre île (récent) et parcelle (code 6).

**Après.** Une requête **partition** (`/modules/permis?count_only&etats=true`) compte les quatre états en une passe (GROUP BY du CASE). Plus aucune soustraction ; « Récent » = **24 mois partout** ; achevé = `daact ∨ code 6` partout. Preuve : **compteur = nombre de lignes du filtre**, par état, sur les quatre périmètres, et Σ états = Tous.

| Périmètre | Récents | Dormants | Achevés | Autres | **Σ = Tous** | compteur == filtre |
|---|--:|--:|--:|--:|--:|:--:|
| La Réunion | 5 238 | 895 | 21 006 | 23 669 | **50 808** | ✅ (4/4 états) |
| Saint-Denis | 421 | 84 | 1 454 | 1 965 | **3 924** | ✅ |
| Saint-Paul | 600 | 129 | 2 044 | 3 645 | **6 418** | ✅ |
| Cilaos | 50 | 8 | 111 | 236 | **405** | ✅ |

Rappel du relecteur sur l'île : « Autres » affiché 13 698 vs filtre 8 818 (**écart 4 880**) → **écart 0** désormais.

**Requêtes rejouables** (API :7500) :
```bash
# partition (les 4 états comptés, + total/géocodés/sans_date)
curl -s "http://127.0.0.1:7500/modules/permis?count_only=true&etats=true"           # île
curl -s "http://127.0.0.1:7500/modules/permis?count_only=true&etats=true&commune=Cilaos"
# filtre d'un état : son total == le compteur de la partition
for e in recent dormant acheve autre; do
  curl -s "http://127.0.0.1:7500/modules/permis?etat=$e&months=240&limit=1" | python3 -c "import sys,json;print('$e', json.load(sys.stdin)['total'])"
done
```
```sql
-- recompte SQL direct (lecture seule) : partition île = 50 808 (= total daté)
WITH dm AS (SELECT max(date) dmax FROM sitadel_permits)
SELECT (CASE
  WHEN raw->>'daact' IS NOT NULL OR raw->>'etat'='6' THEN 'acheve'
  WHEN type='PC' AND (raw->>'etat' IS NULL OR raw->>'etat' NOT IN ('4','5','6')) AND raw->>'daact' IS NULL
       AND date < (SELECT dmax FROM dm) - interval '36 months'
       AND EXISTS (SELECT 1 FROM jsonb_array_elements_text(idu_codes) c(idu) JOIN parcel_bati_emprise b ON b.idu=c.idu)
       AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements_text(idu_codes) c(idu) JOIN parcel_bati_emprise b ON b.idu=c.idu WHERE b.bati_m2>=10)
    THEN 'dormant'
  WHEN date >= (SELECT dmax FROM dm) - interval '24 months' THEN 'recent'
  ELSE 'autre' END) etat, count(*) FROM sitadel_permits WHERE date IS NOT NULL GROUP BY 1;
```
Capture : `01-entree-ile-partition.png`, `01b-panneau-partition.png`.

---

## Point 2 — Corriger la qualification Dormant (bâti mesuré, annulés/commencés exclus)

**Décision de Vic appliquée.** Dormant = **PC autorisé, non annulé, > 3 ans, sans achèvement déclaré, sans bâtiment détecté** (emprise de bâti **mesurée** < 10 m², `parcel_bati_emprise` = intersection parcelle × empreintes BD TOPO `spatial_layers.kind='batiment'`) — **plus** « absence d'exclusion dans le run » (`dryrun_cascade_results`), **plus** l'horloge `now()`. Les annulés (code 4) et les travaux commencés (code 5) **sortent**.

**Libellé.** « PC autorisés depuis plus de 3 ans, sans achèvement déclaré (DAACT), **aucun bâtiment détecté sur leurs parcelles** » — jamais « terrain resté nu » ni « caducité ».

**Île : 15 773 → 895 dormants.** (La chute vient des annulés + commencés + parcelles bâties retirés ; mesuré en 26,7 s puis servi en < 1 s via la couche précalculée.)

**Les 30 dossiers témoins (même tirage SHA-256 `"PERMIS-20261122:"+id`, ordre ascendant) — avant / après :**

La mesure de bâti `parcel_bati_emprise` **coïncide exactement** avec le contre-audit : 97441516A0419 → 253 m², 97441122A0103 → 133 m², 97442320A0048 → 188 m² (annulé). Décompte Sitadel identique : **19** travaux commencés, **6** autorisés, **5** annulés ; **28** avec bâti ≥ 10 m², **2** sans.

| # | permis | date | statut Sitadel | bâti mesuré (m²) | avant | après |
|---|--------|------|----------------|---:|-------|-------|
| 1 | 97441516A0419 | 2016-11-15 | travaux commencés | 253 | dormant | autre (commencé) |
| 2 | 97441614A0222 | 2014-12-01 | travaux commencés | 17084 | dormant | autre (commencé) |
| 3 | 97440419A0067 | 2019-12-30 | travaux commencés | 4380 | dormant | autre (commencé) |
| 4 | 97441819A0249 | 2020-05-25 | travaux commencés | 77 | dormant | autre (commencé) |
| 5 | 97440913A0177 | 2013-10-10 | travaux commencés | 152 | dormant | autre (commencé) |
| 6 | 97441615A0169 | 2015-06-12 | autorisé | 125 | dormant | autre (**bâti 125 m²**) |
| 7 | 97440621A0121 | 2021-10-20 | travaux commencés | 500 | dormant | autre (commencé) |
| 8 | 97441615A0550 | 2016-01-29 | annulé | 12 | dormant | autre (annulé) |
| 9 | 97440922A0246 | 2023-03-10 | autorisé | 18 | dormant | autre (**bâti 18 m²**) |
| 10 | **97440816A0043** | 2017-01-05 | **autorisé** | **0** | dormant | **dormant (aucun bâti)** |
| 11 | 97440921A0260 | 2022-04-12 | travaux commencés | 10 | dormant | autre (commencé) |
| 12 | 97442320A0048 | 2020-10-13 | annulé | 188 | dormant | autre (annulé) |
| 13 | 97441414A0104 | 2014-06-05 | travaux commencés | 77 | dormant | autre (commencé) |
| 14 | 97440822A0163 | 2022-09-27 | travaux commencés | 0 | dormant | autre (commencé) |
| 15 | 97442018A0057 | 2018-06-27 | travaux commencés | 236 | dormant | autre (commencé) |
| 16 | 97440116A0058 | 2016-08-24 | travaux commencés | 165 | dormant | autre (commencé) |
| 17 | 9744121230162 | 2013-04-23 | annulé | 69 | dormant | autre (annulé) |
| 18 | 97441815A0038 | 2015-05-22 | travaux commencés | 118 | dormant | autre (commencé) |
| 19 | 97441414A0241 | 2015-03-06 | autorisé | 16346 | dormant | autre (**bâti 16346 m²**) |
| 20 | 97441417A0012 | 2017-05-09 | travaux commencés | 532 | dormant | autre (commencé) |
| 21 | 97441419A0141 | 2019-09-17 | travaux commencés | 135 | dormant | autre (commencé) |
| 22 | 97441520A0131 | 2020-10-15 | annulé | 197 | dormant | autre (annulé) |
| 23 | 97441122A0103 | 2022-07-19 | autorisé | 133 | dormant | autre (**bâti 133 m²**) |
| 24 | 97441521A0176 | 2021-11-05 | travaux commencés | 110 | dormant | autre (commencé) |
| 25 | 97441521A0350 | 2021-08-19 | travaux commencés | 71 | dormant | autre (commencé) |
| 26 | 97441119A0409 | 2020-05-12 | travaux commencés | 71 | dormant | autre (commencé) |
| 27 | 97442021A0019 | 2021-03-25 | travaux commencés | 180 | dormant | autre (commencé) |
| 28 | 97442115A0042 | 2015-08-19 | travaux commencés | 699 | dormant | autre (commencé) |
| 29 | 97441512A0662 | 2013-03-08 | annulé | 169 | dormant | autre (annulé) |
| 30 | 97441415A0166 | 2015-08-28 | autorisé | 202 | dormant | autre (**bâti 202 m²**) |

**Sur l'échantillon demandé : 1/30 reste dormant** (97440816A0043, autorisé, 0 m² de bâti). L'affirmation « terrain resté nu », contredite 28/30 avant, n'est plus faite que sur un terrain réellement mesuré sans bâti.

**Où le chiffre est aussi utilisé — tous lisent la même fonction** (`permis_point_mort` / prédicat `permis_classe`) :
- outil Permis, compteur d'entrée Dormant (`/modules/promesses?count_only`) ;
- **fiche commune**, bloc « Construire ici » → « Permis dormants » (`api/fiche_commune.permis_bloc`) ;
- la **liste** Dormant (`/modules/promesses`) ;
- la **partition** et le **mode parcelle** (section Point 3).

Dormants après correction : **île 895**, Saint-Denis 84, Saint-Paul 129, Cilaos 8.

**Reconstruction PROD de la couche de bâti mesuré (à exécuter une fois, PUIS à chaque run M-VIA — NON exécutée en prod ici) :**
```bash
python - <<'PY'
from labuse.db import session_scope
from labuse.faisabilite.viabilisation_build import ensure_parcel_bati_emprise
with session_scope() as s:
    print(ensure_parcel_bati_emprise(s))   # {'parcel_bati_emprise': …, 'baties': …}
PY
# intégré : build_viabilisation() appelle désormais ensure_parcel_bati_emprise() (une M-VIA suffit).
```

---

## Point 3 — Voisinage 200 m synchronisé, dessin aligné, dormants servis

**Pourquoi le retard.** `via_permits_geo` était un **snapshot** `DROP TABLE … ; CREATE TABLE AS …` refait **uniquement** au run M-VIA (`viabilisation_build`). Entre deux runs, elle prenait du retard : dernière autorisation **31/07** au lieu de 31/08, et **3 004 permis** déjà datés + géolocalisés absents (BZ 1065 : 11 au lieu de 13).

**Correctif.** `via_permits_geo` devient une couche **maintenue par TRIGGER** (`via_permits_geo_sync` sur `sitadel_permits`, INSERT/UPDATE/DELETE) : elle **suit d'elle-même** chaque mise à jour des permis, sans dépendre du run M-VIA. Trigger **défensif** (no-op si la table a été droppée par du code hérité ; DELETE+INSERT sans dépendre de la PK) pour ne jamais casser une autre session. Reconstruction locale : **47 070 → 50 074** lignes (+3 004), dernière autorisation **31/08/2026**.

**Les 10 parcelles du relecteur — recompte 200 m depuis la limite de parcelle (EPSG 2975) :**

| Parcelle | Attendu (relecteur) | Recompte après correction |
|---|--:|--:|
| 97411000BZ1065 (Saint-Denis) | 13 | **13** ✅ |
| 97415000CV1498 (Saint-Paul) | 14 | **14** ✅ |
| 97424000AB0001 (Cilaos) | 0 | **0** ✅ |
| 97411000AD0001 (1 bis rue Doret) | 18 | **18** ✅ |
| 97422000AD0887 (Le Tampon) | 14 | **14** ✅ |
| 97414000DK0208 (Saint-Louis) | 33 | **33** ✅ |
| 97416000HT0538 (Saint-Pierre) | 31 | **31** ✅ |
| 97408000AC2215 (La Possession) | 13 | **13** ✅ |
| 97422000BW2635 (Le Tampon) | 3 | **3** ✅ |
| 97408000BI0351 (La Possession) | 12 | **12** ✅ |

Trigger vérifié (test transactionnel, ROLLBACK, base partagée intacte) : un UPDATE de `raw.etat` ou de `geom` se propage, un DELETE retire la ligne.

**Dessin = distance réellement mesurée.** `/modules/parcelle-permis` sert `buffer_200m` = `ST_Buffer(parcelle, 200)` (4326). Le front dessine **cette bande** autour de la *limite* de la parcelle au lieu d'un cercle autour du centroïde — un point à 146,6 m correctement compté n'est plus visuellement hors-cercle.

**Le mode parcelle affiche les dormants.** Chaque permis du voisinage reçoit son `etat_cycle` serveur (même fonction qu'à l'île) ; le segment **Permis dormants** existe désormais en mode parcelle. BZ 1065 : Récents 0 · Dormants 0 · Achevés 6 · Autres 7 · **Tous 13**.

**L'écran dit les pertes de couverture :** « **734 sans point sur la carte (non géolocalisés)** · **1 sans date (hors fenêtre temporelle)** » (sous le total).

**Autres lectures de la couche — ce que le retard a faussé :**
- `/modules/parcelle-permis` et **fiche parcelle « permis à proximité »** (`PermitsProximityBlock`) : sous-comptaient le voisinage (BZ 1065 : −2) ;
- **`parcel_viabilisation`** (`viabilisation_build`) : `c100 / c200 / c100_recent / c100_acheve` sont des `count(via_permits_geo)` → avec 3 004 permis manquants, le **signal de viabilisation était sous-estimé**, donc le **CLASSEMENT** des parcelles (`parcel_p_score_v2`, stock « brûlantes/chaudes », comparateur des communes) **sous-notait** les parcelles dont un permis récent voisin n'était pas encore dans la couche. La couche est désormais fraîche ; le classement se réaligne **au prochain `build_viabilisation`** (qui relit la couche à jour).

**Commande de reconstruction PROD (NON exécutée) :**
```bash
# couche de voisinage : table + trigger + réconciliation pleine (idempotent)
python - <<'PY'
from labuse.db import session_scope
from labuse.faisabilite.viabilisation_build import ensure_via_permits_geo
with session_scope() as s:
    print(ensure_via_permits_geo(s, resync=True))   # {'via_permits_geo': …}
PY
# puis rafraîchir le CLASSEMENT (le score de viabilisation relit la couche à jour) :
#   python -m labuse build-parcel-viabilisation
```
Captures : `02-parcelle-bz1065-buffer.png`, `02b-panneau-bz1065.png`.

---

## Point 4 — Donnée Sitadel (réconcilier le millésime, distinguer logements/lots)

**Pourquoi 97440925G0371 a une autre date.** C'est une **DP** (famille *logements* uniquement — pas un conflit inter-fichiers). Le refresh mensuel (`permits_sdes.refresh_since`) posait une borne `max(date) − 3 mois` et filtrait le serveur sur `DATE_REELLE_AUTORISATION ≥ since`. Une **correction SDES** qui déplace ce dossier de **12/12/2025 → 16/02/2026** (deux dates antérieures à la fenêtre de 3 mois) n'était **jamais re-fetchée** → la date périmée restait en base. L'API Dido ne filtre **que** sur la date d'autorisation (pas de date de *modification*).

**Correctif à l'ingestion.** `refresh_since` renvoie désormais **None** : le refresh re-charge le **millésime complet** et ré-upserte (idempotent, `ON CONFLICT`) → toute correction est réconciliée. Le volume (dép. 974, ~50 k lignes) rend ce plein mensuel acceptable. (Prouvé par `tests/test_outil_permis_fix1.py::test_lot4_refresh_correction_safe` ; la ré-ingestion live n'est **pas** lancée ici — réseau + base partagée. Commande : `python -m labuse.ingestion.permits_sdes --refresh`.)

**Libellés.** Fiche permis : « Nombre de lots » → **« Logements créés »** (le champ est `NB_LGT_TOT_CREES`). La date de fraîcheur affichée est **« dernière autorisation intégrée le JJ/MM/AAAA »** (max `date` en base, pas aujourd'hui), à l'entrée, en mode parcelle et au pied de liste.

**Comptés et dits.** La **ligne sans date** (1) et les **permis sans point** (734 non géolocalisés) sont affichés. Les enregistrements **écartés à l'ingestion sans référence cadastrale** restent comptés au rapport d'ingestion (`stats["sans_cadastre"]`, journalisé) ; dates invalides/futures de même (`dates_invalides`, `dates_futures`).

---

## Point 5 — Carte et performance

- **Même permis = même couleur quel que soit le filtre.** Chaque permis porte son `etat_cycle` **servi** (liste + carte). En « Tous », un achevé ancien reste gris, un dormant corail — plus de reclassement par date au front. Palette confirmée par le relecteur : Récent **bleu**, Dormant **corail**, Achevé **gris**, Autre **orange**.
- **« Tous » sur l'île ne déclenche plus la liste lourde des dormants.** La liste `/modules/promesses` (lourde) n'est chargée **que** sur le segment Dormant ; en « Tous », les dormants sont déjà dans la carte `/modules/permis` (chaque point porte son `etat_cycle`). Le second chemin relevé par le relecteur (`enabled: pointMort || tous`) est supprimé.
- **Ordre stable.** `/modules/permis` : `ORDER BY date DESC, permit_id ASC` (liste et carte) ; `/modules/parcelle-permis` : `dist_m ASC, permit_id ASC` ; `/modules/promesses` : `date ASC, permit_id ASC`.
- **« annulé · annulé ».** La bulle carte (`MapView`) concaténait `statut` (déjà « annulé ») + un flag « annulé ». Désormais **une seule fois** : `statut` donne le mot, `annule` ne donne que la couleur. Vérifié sur **97441612A0486** (capture `03-fiche-annule-sans-doublon.png`).

---

## Point 6 — Harmoniser les libellés (événement, périmètre, période, date de référence)

| Écran | Avant | Après |
|---|---|---|
| Tuile outil (`registry`) | « Qui construit quoi, et où… » (laisse croire le chantier observé) | « Les autorisations d'urbanisme (Sitadel) : récentes, dormantes, achevées — par commune et parcelle. » |
| Segment « Récents » | « autorisés, 90 derniers jours de la donnée » | « autorisés depuis 24 mois (fin des données) » |
| Segment « Dormants » | « …terrain resté nu » | « PC autorisés depuis plus de 3 ans, sans achèvement déclaré (DAACT), aucun bâtiment détecté sur leurs parcelles » |
| Mention Sitadel (« i ») | « …pas les demandes en cours d'instruction » | « …autorisations **accordées (y compris annulées ensuite)**, pas les refus ni les demandes en cours d'instruction » |
| Date de fraîcheur | « Sitadel au JJ/MM » | « dernière autorisation intégrée le JJ/MM » |
| Fiche commune (`ContextePanel`) | « Permis déposés (12 mois) » | « Permis **autorisés** (12 mois, annulés compris) » (événement = autorisation, `date`, ancré fin des données) |
| Fiche permis | « Nombre de lots » | « Logements créés » |
| Dossier / PDF (`nearby_permits`) | acceptait un permis **sans date** dans la fenêtre « 24 mois » | `s.date IS NOT NULL` requis (un permis sans date n'entre plus dans la fenêtre) |

Le bloc « dépôts » (`DepotsBlock`) dit déjà son événement (dépôt), son périmètre (parcelle + section) et sa période (36 mois) — inchangé. Témoin commun **BZ 1065** conservé pour distinguer les écarts justifiés (rayons/périodes différents) des erreurs de données.

---

## Tests & preuves

- **`tests/test_outil_permis_fix1.py`** (non-db, lot pre-push) — ordre de priorité du CASE, dormant (annulés/commencés exclus, bâti mesuré, inactif sans la couche), filtre = compteur, refresh correction-safe. **5/5 ✅**
- **`tests/regles/test_point_mort.py`** (réécrit) — dormant mesuré : seul le PC autorisé sans DAACT sur parcelle non bâtie compte (annulé/commencé/achevé/bâti exclus). ✅
- **`tests/test_retours17_permis.py`** — invariant de partition (Σ = total), compteur = liste. ✅
- **`tests/test_retours16_permis.py`** — compteur « Tous » = partition servie, libellés. ✅
- **Front** : `tsc -b` ✅ ; `vitest run` **345/345** ✅ (dont `PermisDouble.test.tsx` adapté à la partition unique).
- **Recette manuelle** (:7500 / :10300) : captures `01`–`04` dans `~/Desktop/outil-permis-fix-1/`.

> Note hook : un test **hors périmètre permis** (`test_dashboard2_cloture::test_courrier_a_deposer_le_meme`) peut rester rouge dans le lot « sans base » tant que `courrier_demandes` de la base de test **partagée** `labuse_test` dépasse 300 lignes (pollution accumulée par des runs répétés). C'est un défaut d'isolement **préexistant** (test DB mal marqué `db`), sans lien avec ce lot ; la base de test partagée n'a pas été nettoyée (consigne « laisse-les tranquilles »).

## Fichiers touchés

Back : `src/labuse/permis_classe.py` (nouveau), `api/modules.py`, `registre/moteurs/commune.py`, `api/fiche_commune.py`, `faisabilite/viabilisation_build.py`, `ingestion/permits.py`, `ingestion/permits_sdes.py`.
Front : `components/outils/ModulePanel.tsx`, `components/outils/registry.ts`, `components/map/MapView.tsx`, `components/contexte/ContextePanel.tsx`, `lib/api.ts`.
Couches locales (re)construites : `via_permits_geo` (+ trigger), `parcel_bati_emprise`.

---
---

# OUTIL-PERMIS-FIX-2 — réponse à la relecture indépendante (`~/Desktop/relecture-permis-1.md`)

> La relecture confirme les trois bloquants levés et trouve **trois défauts** (A bloquant, B, C) + **trois mineurs** (D, E, F). Correction de chacun, **exécution** cette fois des correctifs codés (ré-ingestion + reconstruction viabilisation **en base locale**), preuves rejouées sur les données ainsi rechargées.
>
> Effet de bord assumé du rechargement : le millésime Sitadel passe de **31/08 à 30/09/2026** (+316 permis, 127 dates corrigées) — tous les chiffres ci-dessous sont donc ceux de la **donnée vive rechargée**, pas ceux du mandat 1.

## Défaut A (bloquant) — classement/fiche = outil, et péremption SIGNALÉE

**Cause** : `via_permits_geo` est devenue vivante (trigger) mais `parcel_viabilisation` restait un instantané du 05/09 ; les deux divergeaient entre deux runs (BZ 1065 : outil 13, fiche/score 11 ; **43,75 %** des parcelles divergentes).

**Correctif exécuté (base locale)** : `build_viabilisation` relancé sur les 24 communes (434 582 parcelles, 2 124 s). `parcel_viabilisation.c100/c200` recalculés contre la couche vive.

**Preuve — outil = fiche (c200), 10 parcelles de la relecture** (API `/parcelle-permis` vs `parcel_viabilisation` stocké) :

| Parcelle | outil (c200) | fiche (c200) |
|---|--:|--:|
| 97411000BZ1065 | 13 | 13 ✅ |
| 97415000CV1498 | 14 | 14 ✅ |
| 97424000AB0001 | 0 | 0 ✅ |
| 97411000AD0001 | 18 | 18 ✅ |
| 97422000AD0887 | 14 | 14 ✅ |
| 97414000DK0208 | 33 | 33 ✅ |
| 97416000HT0538 | 32 | 32 ✅ |
| 97408000AC2215 | 13 | 13 ✅ |
| 97422000BW2635 | 3 | 3 ✅ |
| 97408000BI0351 | 12 | 12 ✅ |

Et **globalement** : `parcel_viabilisation.c200` = recompte frais depuis `via_permits_geo` pour **toutes** les parcelles (`c200_divergents = 0`, contre 43,75 % avant). BZ 1065 outil 13 = fiche 13 = score (band `confirmee`).

**Signal de péremption (structurel, pour que ça ne revienne pas)** : nouveau repère `parcel_viabilisation_meta` (état de la couche au dernier run) + fonction `viabilisation_fraicheur(db)`. Si `via_permits_geo` bouge après le run, `perimee=True`, signalé **dans la fiche** (bloc Viabilisation → `perimee` + note) **et dans `/readyz`** (champ `viabilisation` + action « relancer build-parcel-viabilisation »). Après le run : `perimee=False` (via_count 50 414, via_max_d 2026-09-30, en phase).

**Ce que la reconstruction change dans les entrées du classement** (avant = instantané 05/09, après = recompte frais) :
- **20 145** parcelles changent de **note** (`score`), dont **4 804** changent de **classe** (`band`).
- Sens : surtout vers le **haut** (le snapshot SOUS-comptait le voisinage) — **18 900** parcelles +6 à +15 pts, **918** de plus de +15 pts ; en baisse : 256 de −6 à −15, 67 de plus de −15.

**Séquence PROD exacte (NON exécutée en prod)** — la couche de voisinage puis la viabilisation ; la commande `viabilisation` fait déjà les deux (elle appelle `ensure_via_permits_geo(resync=True)` + `ensure_parcel_bati_emprise` avant de recalculer) :
```bash
# (optionnel, pour isoler l'étape couche) table + trigger + réconciliation pleine, idempotent :
python - <<'PY'
from labuse.db import session_scope
from labuse.faisabilite.viabilisation_build import ensure_via_permits_geo
with session_scope() as s: print(ensure_via_permits_geo(s, resync=True))
PY
# reconstruction du classement (recompte c100/c200/score/band + pose le repère de fraîcheur) :
python -m labuse viabilisation
# contrôle : /readyz → viabilisation.perimee=False ; la fiche ne signale plus « périmé ».
```
En prod, cette séquence déplacera ~20 000 notes de viabilisation (ordre de grandeur mesuré en local), majoritairement vers le haut, et réconciliera c200 fiche/score avec l'outil.

## Défaut B — donnée Sitadel rechargée (exécuté)

Rechargement plein `python -m labuse.ingestion.permits_sdes --refresh --no-geocode` (refresh correction-safe). Résultats :
- **97440925G0371 : 2025-12-12 → 2026-02-16** ✅ (date officielle SDES logements), `nb_lgt` servi « Logements créés » = 2.
- **127 permis** ont vu leur **date** corrigée par le rechargement (dont le témoin) ; **721** ont vu un champ clé corrigé (date/état/logements/DAACT) ; **316 nouveaux** permis ; **506** enregistrements écartés sans cadastre, **7** dépôts invalides (comptés et dits au rapport d'ingestion).
- Nouveau millésime : **dernière autorisation intégrée = 30/09/2026** (était 31/08).

Requête de preuve : `SELECT date::date FROM sitadel_permits WHERE permit_id='97440925G0371';` → `2026-02-16`.

## Défaut C — dormant = TOUTES parcelles retrouvées et mesurées (exécuté)

`permis_classe._dormant_sql` : avant, un `EXISTS` « au moins une parcelle mesurée » + `NOT EXISTS` « une parcelle bâtie » → une parcelle **absente** de `parcels` (donc non mesurée) était **ignorée** (47/895 dormants, bâti possiblement invisible). Après : `jsonb_array_length ≥ 1` **ET** `NOT EXISTS` une parcelle **non mesurée** (`LEFT JOIN … WHERE be.idu IS NULL`) **ou** bâtie (≥ 10 m²) → le permis n'est dormant **que si toutes ses parcelles sont retrouvées et mesurées sans bâti**.

- Sur les données de la relecture : **895 → 848** (−47, exactement les dormants à parcelle absente).
- Sur la donnée **vive rechargée** : **nouveau total dormant = 854** (île ; Saint-Denis 78, Saint-Paul 126, Cilaos 7). Le même prédicat sert la partition, le filtre, la liste `/promesses`, le mode parcelle et la fiche commune (vérifié : `/promesses?count_only` = 854 = partition).

## Mineurs

- **D** — `AnalyserAnnonce.tsx` : « Permis déposés, 12 mois » → **« Permis autorisés, 12 mois »** (`permis_12m` compte par date d'autorisation, même indicateur que la fiche commune).
- **E** — affinage `months` : le compteur de l'état **actif** suit déjà la liste (`nShown=total`) et changer d'état réapplique la profondeur complète (`choisirSeg`→240). On le **DIT** désormais (note sous le segment quand la fenêtre est affinée) ; `monthsDefaut` corrigé (240, plus un résidu « 3 »).
- **F** — `perimCounts.tous` lit le **`c200` exact** de l'API (plus la longueur du payload ≤ 500) ; marqueur millésime `tables.py` « 2026-07 » figé → libellé non figé (« via_permits_geo suivie par trigger, millésime = dernière autorisation intégrée »).

## Preuves du mandat 1, rejouées sur la donnée rechargée

- **Partition = filtre, 4 périmètres** : île `5201 / 854 / 21322 / 23747 = 51 124` ; Saint-Denis `418/78/1467/1976=3 939` ; Saint-Paul `593/126/2076/3653=6 448` ; Cilaos `48/7/112/238=405`. Compteur == filtre pour les 4 états, 4/4 périmètres.
- **10 parcelles** : c200 outil = recompte indépendant = fiche (tableau Défaut A).
- **30 témoins** (même tirage) : **1 dormant** (97440816A0043, parcelle AY0502 mesurée bâti 0 m²), 28 autre, **1 achevé** (un témoin a reçu une DAACT au rechargement — correction de donnée, correctement reclassé achevé).

## Fichiers touchés (mandat 2)

Back : `permis_classe.py` (Défaut C), `api/modules.py` (promesses — Défaut C), `faisabilite/viabilisation_build.py` (repère + `viabilisation_fraicheur` — Défaut A), `api/app.py` (fiche viabilisation + readyz — Défaut A), `registre/tables.py` (Défaut F).
Front : `components/outils/ModulePanel.tsx` (Défauts E, F), `components/outils/AnalyserAnnonce.tsx` (Défaut D).
Tests : `test_outil_permis_fix1.py` (C/A/D/F), `regles/test_point_mort.py` (cas parcelle absente — C).
Couches (re)construites en base locale : `sitadel_permits` rechargée, `via_permits_geo` (trigger, 50 414), `parcel_bati_emprise`, `parcel_viabilisation` (24 communes) + `parcel_viabilisation_meta`.

---

## Relecture 2 (`~/Desktop/relecture-permis-2.md`) — G1, G2, G3

La seconde relecture valide A, B, C et la liste fermée entière. Trois restes :

### G2 (à corriger) — garde-fou de fraîcheur du BÂTI (`parcel_bati_emprise`)

Même famille que le Défaut A, non traitée pour le bâti : la couche qui fonde « aucun bâtiment détecté » était un instantané sans repère. Ajouté, par symétrie avec la viabilisation :
- `parcel_bati_emprise_meta` (singleton) : à chaque `ensure_parcel_bati_emprise`, on enregistre l'état de la **source** bâti (`spatial_layers kind='batiment'` : nombre + dernière `created_at`) et la **date de mesure** (`built_at`).
- `bati_emprise_fraicheur(db)` : `perimee=True` si la BD TOPO a bougé depuis la mesure → un dormant « aucun bâtiment détecté » ne repose plus en silence sur une mesure plus vieille que sa source.
- **Date connue, affichée dans le « i » des dormants** : la partition `/modules/permis?etats` sert `bati_fraicheur` ; le segment Dormant ajoute « · bâti mesuré le JJ/MM/AAAA » (et « ⚠ mesure périmée (BD TOPO plus récente) » si `perimee`).
- **Signalée dans `/readyz`** : champ `bati_emprise` + action « relancer la mesure de bâti » si périmée.
- État local : `built_at` 23/11/2026, source 817 506 bâtiments (BD TOPO, dernière création 29/06/2026), **`perimee=False`**.

### G3 (mineur) — libellé de source de la fiche commune

`fiche_commune.permis_bloc` disait encore « *permis au point mort (36 mois sans DAACT, **run servi**)* » — l'ANCIENNE logique (proxy « absence d'exclusion au run »). Corrigé : « *permis dormants (PC > 3 ans sans DAACT, **aucun bâtiment détecté sur leurs parcelles**)* » — ce qui est réellement mesuré. Le chiffre (78/126/7) était déjà juste ; c'est son explication qui est corrigée.

### G1 (mineur, NOTÉ — non corrigé, par consigne) — LIMITE CONNUE

Le signal de péremption de la viabilisation (`viabilisation_fraicheur`) compare **le nombre** de permis et **la date max** de `via_permits_geo`. Une **mise à jour d'attribut en place** entre deux runs (un permis qui reçoit une DAACT → devient achevé, ou dont la géom bouge) ne change **ni le compte ni la date max** → `perimee` reste `False` alors que `c100_recent`/`c100_acheve` du score peuvent avoir dérivé. Le signal **attrape le cas courant** (nouveaux permis mensuels : compte + date max bougent) mais **rate les reclassements silencieux**. Correction possible (non faite ici, par consigne) : comparer aussi une empreinte d'état/géom de la couche, ou dater sa dernière écriture (le trigger pourrait tamponner un `updated_at`). **Limite connue, non bloquante** : la couche est reconstruite à chaque run M-VIA, et le cas courant est couvert.

### Mineur E (rappel) — divulgation, pas réconciliation

L'affinage `months` : le chip de l'état **actif** affiche la partition pleine profondeur pendant que la liste affinée montre moins. C'est désormais **dit** (note sous le segment) ; ce n'est pas une mise en accord des deux nombres (acceptable pour un mineur, assumé).

### Fichiers touchés (relecture 2)

Back : `faisabilite/viabilisation_build.py` (G2 — meta bâti + `bati_emprise_fraicheur`), `api/modules.py` (G2 — `bati_fraicheur` dans la partition), `api/app.py` (G2 — `/readyz.bati_emprise`), `api/fiche_commune.py` (G3).
Front : `lib/api.ts` + `components/outils/ModulePanel.tsx` (G2 — date de mesure dans le « i » des dormants).
Tests : `test_outil_permis_fix1.py` (G2, G3). Couche : `parcel_bati_emprise_meta` (repère posé).

---
---

# OUTIL-PERMIS-FIX-3 — relecteur externe (recontrôle de 2fc4636f9)

Il valide les états, les 854 dormants, les dix voisinages, les couleurs, le chargement de « Tous ». Trois restes, dont **le premier est une régression que j'avais introduite**.

## Point 1 (BLOQUANT) — Dossier : rayon 500 m rétabli (régression du mandat 1)

**Cause** : au mandat 1, en excluant les dates nulles de la requête `dynamique` du Dossier (`ingestion/permits.py`, `nearby_permits`), j'ai **supprimé la condition `ST_DWithin`** (le `:r` restait passé mais inutilisé). Le Dossier écrivait « dans un rayon de 500 m » et recevait le **total de l'île** (≈ 5 140 permis / 8 543 logements) pour n'importe quelle parcelle.

**Correctif** : rayon `ST_DWithin(ST_Transform(p.centroid,2975), ST_Transform(s.geom,2975), :r)` **rétabli**, l'exclusion des dates nulles **conservée**.

**Attendus — recompte (rayon 500 m, 24 mois)** : `97411000BZ1065 = 1 permis / 4 logements` ; `97424000AB0001 = 0` ; `97415000CV1498 = 5 permis / 6 logements`. ✅ (identiques en SQL).

**Dossier PDF par la VRAIE route** (`GET /dossier/97411000BZ1065.pdf`, HTTP 200) — la ligne servie :
```
Permis à proximité            1 permis (< 500 m, 24 mois)            sourcé
```
(avant le correctif : ~5 140 permis.)

**Pourquoi ni mes tests ni le hook ne l'ont vu** :
1. `tests/test_permits.py` est marqué **`pytest.mark.db`** → le **hook pre-push (`-m "not db"`) ne le lance jamais**.
2. Même joué, il **ne couvrait pas** le compte de dynamique avec le rayon : `test_permit_hors_rayon_absent` teste la **liste** (qui garde SON `ST_DWithin`), et `test_nature_et_dynamique` ne sème que des permis **proches** sur une base de test minuscule → retirer le filtre de distance ne changeait aucun compte. Le bug n'était visible que sur la vraie base (50 k permis étalés sur l'île).

**Tests ajoutés** : `test_permits.test_dynamique_respecte_le_rayon` (db — sème un proche 10 logts + un lointain 999 logts, exige que le compte ne voie QUE le proche) **et** `test_outil_permis_fix1.test_fix3_point1_rayon_dossier_present` (**non-db, DANS le hook** — échoue si `ST_DWithin` disparaît du compte de dynamique : c'est la garde qui aurait attrapé ma régression).

**Diff ciblé — rien d'autre changé dans les documents** : `git diff 99e9635b4..HEAD -- src/labuse/exports/ src/labuse/api/{documents,dossier,pre_dossier,bilan}.py` = **vide**. Le seul chemin de mes commits vers le Dossier est `ingestion/permits.py` (le rayon).

## Point 2 (BLOQUANT) — Dormants : l'affinage ne peut que RESTREINDRE les 854

**Cause** : la liste `/modules/promesses` gardait un prédicat RECOPIÉ, avec son `:m` injecté sans plancher. « Affiner → 24 m+ » remplaçait les 36 mois de la définition par 24 → **1 118 dormants** ; `97441123A0147` (Autre) passait Dormant.

**Correctif** :
- `/modules/promesses` lit DÉSORMAIS la **définition unique** `permis_classe._dormant_sql` (plus de prédicat recopié) ;
- le seuil d'âge est **clampé à ≥ 36 mois** (`max(months, DORMANT_MOIS)`) côté liste **et** compteur (`permis_point_mort`) : un affinage ne peut qu'**OTER** des dormants, jamais en ajouter ;
- le front n'offre plus « 24 » (`MONTHS_PM = [36, 48, 60, 72]`).

**Preuve — dormant par valeur d'affinage, 4 périmètres** (non-croissant, ≤ 854, et 24 m = 36 m = base) :

| Réglage | La Réunion | Saint-Denis | Saint-Paul | Cilaos |
|---|--:|--:|--:|--:|
| 24 m (clampé→36) | 854 | 78 | 126 | 7 |
| 36 m | 854 | 78 | 126 | 7 |
| 48 m | 622 | 64 | 86 | 6 |
| 60 m | 455 | 50 | 68 | 3 |
| 72 m | 352 | 44 | 58 | 3 |

`97441123A0147` : **absent** de la liste dormante à months=24 (reste « Autre »).

## Point 3 (à corriger) — couche des délais recalculée, vivante, cohérente

**Cause** : `m10_permit_delais` était figée au **14/07/2026**. La fiche mélangeait le **dépôt + délai** de m10 (vieux) et l'**autorisation** de Sitadel rechargé → `97440925G0371` : dépôt 01/01/2025, autorisation 16/02/2026, « 11 mois » (calculé sur d'autres dates). **108 dates** différaient entre m10 et Sitadel.

**Correctif** :
- **Recalcul sur la donnée rechargée, SANS re-pull réseau** : m10 est reconstruite DEPUIS `sitadel_permits` (dépôt `date_depot`, autorisation `date`, achèvement `raw.daact`) — la donnée SERVIE, pas un millésime Dido potentiellement différent. **0 date ne diffère plus** (était 108).
- **Suit les mises à jour comme le voisinage** : trigger `trg_m10_permit_delais_sync` sur `sitadel_permits` (INSERT/UPDATE/DELETE) + `ensure_delais_vivants` appelée par la ré-ingestion. Vérifié transactionnel (UPDATE → délai recalculé, ROLLBACK → restauré).
- **Une seule version** : la fiche prend dépôt ET autorisation depuis `sitadel_permits`, et n'affiche le **délai que s'il est COHÉRENT** avec ces deux dates (`delai_coherent = valide ET m10.date_autorisation = sitadel.date ET m10.date_depot = sitadel.date_depot`).
- Résultat fiche `97440925G0371` : **dépôt 16/02/2026, autorisation 16/02/2026, délai 0 mois** (cohérent).

**La couche sert ailleurs** : OUI — l'outil **Communes** (comparateur / vélocité) lit `m10_permit_delais` (`registre/moteurs/commune.py:35`, `velocite_delai_median_mois` = médiane du délai dépôt→autorisation sur `valide AND famille='logements'`). Le recalcul rafraîchit donc aussi ce délai médian servi aux Communes.

## Preuves des mandats précédents, rejouées (donnée vive)

- Partition = filtre, 4 périmètres : île `5201/854/21322/23747 = 51 124` ; Saint-Denis `418/78/1467/1976=3 939` ; Saint-Paul `593/126/2076/3653=6 448` ; Cilaos `48/7/112/238=405`. 4/4 OK ; `/promesses` = colonne Dormant.
- 10 parcelles : c200 outil `13/14/0/18/14/33/32/13/3/12` (inchangé).
- 30 témoins : 1 dormant (97440816A0043).

## Fichiers touchés (mandat 3)

Back : `ingestion/permits.py` (P1 — rayon), `api/modules.py` (P2 — /promesses lit la fonction unique + clamp ; P3 — fiche cohérente), `registre/moteurs/commune.py` (P2 — clamp point_mort), `ingestion/permit_delais_m10.py` (P3 — trigger + resync), `ingestion/permits_sdes.py` (P3 — ré-ingestion rafraîchit m10).
Front : `components/outils/ModulePanel.tsx` (P2 — MONTHS_PM).
Tests : `test_permits.py` (db — rayon), `test_outil_permis_fix1.py` (non-db — P1/P2/P3). Couche : `m10_permit_delais` reconstruite + trigger.

---
---

# OUTIL-PERMIS-FIX-4 — réserve de la relecture 3 : la colonne « Instruction (mois) » tombée à 0

Mon recalcul de `m10_permit_delais` (mandat 3, OUTIL-PERMIS-FIX-3) l'a reconstruite depuis `sitadel_permits.date_depot` (= `DR_DEPOT`). Résultat : la colonne « Instruction (mois) » de l'outil Communes serait passée à **0** pour les 24 communes.

## Point 1 — Constat (lecture seule)

| | Saint-Denis | Saint-Pierre | Saint-Paul | Le Tampon | Saint-Louis | Saint-André |
|---|--:|--:|--:|--:|--:|--:|
| **main (avant ma branche)** — validé relecteur | 9 | 8 | 9 | 9 | 9 | 9 |
| **ma branche (mandat 3)** — DR_DEPOT | **0** | 0 | 0 | 0 | 0 | 0 |
| **ma branche (ce correctif)** — AN_DEPOT | **9** | **8** | **9** | **9** | **9** | **9** |

Oui, elle avait changé (8-9 → 0). Le correctif la **restaure** (médiane logements, source unique `m10_permit_delais` lue par `registre/moteurs/commune.indicateurs_communes`).

## Point 2 — Cause

- **L'ancienne couche (14/07)** datait le dépôt avec **`AN_DEPOT`** (ANNÉE de dépôt, convention `AAAA-01-01` — d'où `date_depot = 2025-01-01` pour 97440925G0371, dont `AN_DEPOT = 2025`).
- **La mienne (mandat 3)** lisait `sitadel_permits.date_depot`, alimenté par **`DR_DEPOT`**. Or `DR_DEPOT` est **corrompu** : dans l'échantillon SDES il vaut **exactement la date d'autorisation** ; sur l'île, il est **postérieur à l'autorisation dans 62,6 %** des cas (31 810/50 843) ; sur les permis autorisés en 2023, **5 sur 2 692** seulement l'ont avant l'autorisation. Ce n'est pas une date de dépôt.
- **Le bon champ** : `AN_DEPOT` (l'année de dépôt, fiable). Vérifié : la médiane recalculée dessus = **9/8/9/9/9/9**, exactement les valeurs validées par le relecteur.

## Point 3 — Correction

- **Source du dépôt = `AN_DEPOT`** : l'ingestion stocke `raw.an_depot` ; la couche des délais en dérive `date_depot = AAAA-01-01`, `delai_mois = autorisation − (AAAA-01-01)`, `valide = autorisation ≥ dépôt`. Médiane commune **8-9 restaurée**.
- **Reste MAINTENUE PAR TRIGGER** (dérivée de `sitadel_permits`, via `raw.an_depot`) : vérifié transactionnel (changer `an_depot` → délai recalculé, ROLLBACK → restauré).
- **Délai absent, jamais 0 (fiche)** : une date de dépôt n'est **fiable pour une fiche** que si c'est une **date précise** (DR_DEPOT strictement antérieur à l'autorisation ET non un 1er janvier = proxy d'année). **377** permis seulement y satisfont ; pour eux la fiche montre dépôt + délai (ex. 9744012520063 : dépôt 29/12/2025, délai 4 mois). Pour tous les autres → **ni dépôt ni délai** (jamais un « 0 mois » issu d'un `DR_DEPOT` = autorisation). La médiane communale, elle, est un AGRÉGAT qui tolère l'année de dépôt (proxy) — distinction documentée.

## Point 4 — 97440925G0371

« Dépôt et autorisation le même jour, délai 0 » était **le même défaut** (son `DR_DEPOT` = 2026-02-16 = l'autorisation ; son vrai dépôt est `AN_DEPOT = 2025`, soit ~13 mois). La date de dépôt n'étant pas fiable (précise), **la fiche ne montre NI dépôt NI délai** (vérifié : `date_depot: null`, `delai_instruction: null`).

## La couche sert-elle ailleurs ?

Oui : `m10_permit_delais` alimente l'indicateur **« Dynamisme / délai d'instruction » de l'outil Communes** (comparateur, `commune.indicateurs_communes` → `velocite`, médiane sur `valide AND famille='logements'`) **et** l'outil **Vélocité** autonome (`/modules/velocite`). Le recalcul rafraîchit les deux.

## Preuves des mandats précédents (stables après ré-ingestion)

dmax 30/09/2026 inchangé (51 125 lignes). Partition île `5201/854/21322/23747 = 51 124` (compteur = filtre) ; dormant 854 ; 10 parcelles c200 `13/14/0/…` inchangées ; 97440925G0371 date d'autorisation 16/02/2026.

## Fichiers touchés (mandat 4)

`ingestion/permits_sdes.py` (stocke `raw.an_depot`), `ingestion/permit_delais_m10.py` (dépôt = AN_DEPOT, trigger + `build_delais`), `api/modules.py` (fiche : délai seulement si dépôt précis fiable ; le rayon du Dossier n'est pas touché ici). Tests : `test_outil_permis_fix1.py` (+2), `test_permits.py` (+1, db). Couche : `m10_permit_delais` reconstruite depuis AN_DEPOT, `raw.an_depot` peuplé.
