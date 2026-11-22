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
