# PROD-VERIF-1 — Recomptage en production des constats AUDIT-NU-1

**Mandat.** L'audit AUDIT-NU-1 a tourné sur la base du **Mac**. Cinq constats dépendent de l'état
des données. Ils sont ici recomptés sur la **prod** (VPS `vps-5563949c`, base `labuse`) et comparés
au Mac, pour trancher chaque fois entre « vrai en prod » et « artefact Mac ».

**Méthode / garde-fous.** Lecture seule stricte. Toutes les requêtes psql tournent sous
`PGOPTIONS='-c default_transaction_read_only=on'` (prod via `sudo -u postgres psql`, Mac en local).
Seule exception **explicitement mandatée** : la session de test « méthode 1028b » du point 4 (une
`INSERT` + une `DELETE` dans `sessions_auth`, hors read-only, **purgée en fin de point** — preuve
ci-dessous). Aucun `sudo` hors `sudo -u postgres psql`, aucun redémarrage, aucune autre écriture.
Date : 2026-10-31.

---

## Synthèse

| # | Point | Mac | Prod | Verdict |
|---|-------|-----|------|---------|
| 1 | Run résiduel servi | run 1 « servi », **100 % `assiette_source` NULL**, pas de date | run 17 `q_v20`, **38,8 % NULL**, calc. 21/10 | **Artefact Mac** (Mac sert un run legacy) |
| 2 | Radar — 60 retirés le 28/10 | passe #274 **absente**, 0 retiré le 28/10 | passe #274 **présente** (60 supp.), mais **0 retiré subsistant** → actifs | **Vrai en prod mais déjà remédié** |
| 3 | `parcel_cadastre_remplacement` | **n'existe pas** | **existe, 3007 lignes** | **Artefact Mac** (table absente en local) |
| 4 | Loyers OLL servis | tables OK (133/193) ; IRIS **0/344 code** | idem ; `/parcels/…` → `disponible:false` | **Vrai en prod** (OLL mort des deux côtés) |
| 5 | Caches DVF médianes | `dvf_secteur_medianes` 17/08 ; `dvf_prix_sortie_neuf` 21/10 | **identiques** | **Identique** (aucun écart) |

---

## Point 1 — Run résiduel servi (`residuel_runs` / `parcel_residuel_runs`)

**Question.** Quel `run_seq` est `is_served`, sa date de calcul, et `count(*) WHERE assiette_source IS NULL`
sur ce run. Comparer au run servi sur le Mac.

### Prod
```
run_seq | label |      computed_at_min       |      computed_at_max       | is_served
   17   | q_v20 | 2026-10-21 01:42:38.93+04  | 2026-10-21 07:00:05.35+04  |    t

run 17 : total 433 229 | assiette_source NULL = 168 106  (38,80 %)
```

### Mac
```
run_seq | label |  computed_at_max  | is_served
   1    | servi |      (NULL)       |    t

run 1 (servi) : total 431 663 | assiette_source NULL = 431 663  (100,00 %)
```

### Lecture
Le Mac **sert le run 1 legacy** (`label='servi'`, **aucune date de calcul**, `assiette_source` NULL
sur la **totalité** des 431 663 lignes). La table de métadonnées `residuel_runs` du Mac ne connaît
d'ailleurs que les runs 1 et 2 (« servi »/« neuf »).

Détail révélateur : la table `parcel_residuel_runs` du **Mac contient pourtant les runs 15, 16 et 17**
avec un `assiette_source` correctement calculé — le run 17 y compte **168 106 NULL / 433 229, soit
exactement le chiffre de la prod**. Mais ce run 17 n'est pas celui que le Mac *sert* ; le pointeur
`is_served` reste collé au run 1 all-NULL.

La prod, elle, sert le run 17 `q_v20` (calculé le 21/10/2026, 01h42→07h00) où **seulement 38,8 %**
des parcelles ont `assiette_source` NULL.

### Verdict : **ARTEFACT MAC.**
Le constat NU-1 « `assiette_source` NULL partout » vient de ce que le Mac sert un run résiduel
périmé (run 1). En prod, le run servi est q_v20 et le taux de NULL est de 38,8 %, pas 100 %.

---

## Point 2 — Radar (`pige_biens`, `pige_annonces`, `pige_passes`)

**Question.** `pige_biens` par statut ; nombre de biens avec `retiree_le` entre le 28/10 23 h et 23 h 18
(ils doivent être `active`) ; `pige_annonces` par portail.

### `pige_biens` par statut
| statut | Mac | Prod |
|--------|----:|-----:|
| active | 112 | **284** |
| retiree | 299 | **103** |
| en_vente_longue | 5 | **39** |
| **total** | **416** | **426** |

### Biens `retiree_le` ∈ [28/10 23:00 ; 23:18[ (heure Réunion, +04)
- **Prod : 0.** **Mac : 0.**
- En prod, **tous** les `retiree_le` datent du **26/09/2026** (01h–02h Réunion, 103 biens) ; aucun
  retrait nulle part ailleurs. En particulier **aucun retrait le 28/10**.
- Sur le Mac, les retraits se répartissent sur 26/09 (103), 10/10 (133), 23/10 (52) et 27/10 (11) —
  également **aucun le 28/10**.

**Mais** la passe de confirmation du 28/10 existe — **en prod seulement** :
```
PROD  pige_passes #274 | confirmation | 2026-10-28 00:00 (Réunion) | source=auto | n_supprimees=60
MAC   pige_passes #274 : AUCUNE LIGNE (la passe n'existe pas sur le Mac)
```
La passe #274 a bien **enregistré 60 suppressions** le 28/10 en prod (c'est l'événement visé par le
constat NU-1 et par la fiche mémoire RADAR-CONFIRMATION-FIX, « 60/60 »). Or **aucun de ces 60 biens
n'est aujourd'hui retiré** (0 `retiree_le` le 28/10, 0 dans la fenêtre 23:00–23:18) : ils sont de
nouveau **actifs**. La restauration/neutralisation a donc été appliquée en prod. Trace cohérente :
sur `date_derniere_confirmation`, **63 `active` + 31 `en_vente_longue` re-confirmés le 29/10**, et
la passe de confirmation suivante #334 (29/10) affiche `n_supprimees=0`.

### `pige_annonces` par portail
| portail | Mac | Prod |
|---------|----:|-----:|
| leboncoin | 428 | 344 |
| bienici | — (absent) | **100** |

### Verdict : **VRAI EN PROD, MAIS DÉJÀ REMÉDIÉ — et l'audit regardait le mauvais socle.**
- L'événement « 60 faux retraits le 28/10 » est **réel en prod** (passe #274), mais les 60 biens
  sont aujourd'hui **actifs** comme ils doivent l'être : **0 bien n'a de `retiree_le` dans la fenêtre**
  → la correction tient.
- Cet événement est **totalement absent du Mac** (pas de passe #274, aucun retrait le 28/10). Le
  Mac, lui, porte des centaines de retraits d'autres nuits jamais restaurés (retiree=299 vs 103) et
  **ignore Bien'ici** (0 annonce vs 100 en prod). NU-1 ayant tourné sur le Mac n'a donc **pas pu**
  observer les 60 retraits du 28/10 depuis `retiree_le` : la vérité de cet incident est en prod.

---

## Point 3 — Table `parcel_cadastre_remplacement`

**Question.** Existe-t-elle, combien de lignes.

```
PROD : to_regclass = parcel_cadastre_remplacement   → EXISTE, count(*) = 3007
MAC  : to_regclass = (NULL)                          → N'EXISTE PAS  (ERROR: relation does not exist)
```

### Verdict : **ARTEFACT MAC.**
La table de remplacement cadastral existe en prod avec **3007 lignes** ; elle est **absente du Mac**.
Le constat NU-1 (fiche parcelle disparue → 500, « table non gardée » type `cadastre_disparue`)
reflète l'absence de la table **sur le socle Mac**. En prod, le chemin « parcelle remplacée » dispose
de ses 3007 correspondances.

---

## Point 4 — Loyers OLL (`oll_loyers` / `oll_zonage`) et `GET /parcels/97411000IE0241`

**Question.** La table des loyers existe-t-elle, combien de lignes, et `GET /parcels/97411000IE0241`
sur la prod sert-il un loyer.

### Tables (identiques des deux côtés)
| table | Mac | Prod |
|-------|----:|-----:|
| oll_loyers | 133 | 133 |
| oll_zonage | 193 | 193 |

### `GET /parcels/97411000IE0241` en prod (session de test 1028b)
Session créée pour le compte **id 31** (`gb-test-ae@labuse.local`, admin, plan illimité, actif) :
token généré localement, **hash SHA-256 inséré** dans `sessions_auth` (expire +1 h), cookie
`labuse_session=u.<token>` servi via un `curlrc` 600 ; appel `http://127.0.0.1:8000`.

- **HTTP 200**, 83 856 octets. Le bloc `loyers_oll` **est servi** mais :
```json
"loyers_oll": {
  "disponible": false,
  "source": "Loyers OLL — ADIL / AGORAH (réseau des observatoires)",
  "millesime": "OLL 2024 — Île de La Réunion (L9740, agrément 28/08/2024)"
}
```
→ **Aucun loyer n'est servi** pour cette parcelle (champ présent, `disponible:false`).

**Purge (preuve)** : `DELETE FROM sessions_auth WHERE utilisateur_id=31` → `restantes_uid31 = 0` ;
`curlrc`, réponse JSON et token local supprimés (`shred`). Une seule session avait été créée.

### Pourquoi `disponible:false` — et c'est systémique
`fiche_blocs3.loyers_oll` appelle `oll_parcelle(idu)`, qui résout la zone OLL par l'IRIS
intersecté : `JOIN spatial_layers sl ON sl.kind='iris_insee' … JOIN oll_zonage z ON …
z.iris = right(coalesce(sl.attrs->>'code_iris', sl.name), 4)`.

Diagnostic sur la parcelle (prod) : la couche IRIS qui l'intersecte a
`attrs->>'code_iris' = NULL` et `name = "Mairie de la Bretagne-Centre"` → `right(name,4) = "ntre"`,
qui ne matche aucun des codes IRIS à 4 chiffres (`0101`, `0102`, …) de `oll_zonage`. La jointure
renvoie **0 ligne** → `oll_parcelle` = None → `disponible:false`.

Ce n'est pas propre à cette parcelle — c'est **systémique et identique sur les deux bases** :
```
spatial_layers kind='iris_insee' : 344 lignes
   avec un code_iris exploitable          : 0 / 344   (PROD et MAC)
   dont name finissant par 4 chiffres      : 0 / 344   (PROD et MAC)
   couches matchant un oll_zonage.iris      : 0         (PROD)
```
La couche de référence « iris_insee » ne porte **aucun code IRIS** (ses `name` sont des libellés de
mairie) : `oll_parcelle` ne résout **aucune** parcelle. Les 133 lignes `oll_loyers` sont chargées
mais jamais atteignables à la parcelle.

### Verdict : **VRAI EN PROD.**
Les tables OLL existent (133 / 193 lignes, identiques Mac/prod), mais le bloc `loyers_oll` servi est
`disponible:false` pour la parcelle demandée — et **pour toute parcelle**, car la clé de jointure
(code IRIS de `spatial_layers kind='iris_insee'`) est absente (0/344) sur les deux bases. Le constat
NU-1 « OLL mort » est **confirmé en prod**, ce n'est pas un artefact Mac : c'est un défaut de câblage
de la couche IRIS commun aux deux socles.

---

## Point 5 — Caches DVF médianes (`computed_at`)

**Question.** `computed_at` de `dvf_secteur_medianes` et de toute autre table de médianes servie.

Seule une table porte « median » dans son nom : **`dvf_secteur_medianes`**. La table de prix de
sortie neuf **`dvf_prix_sortie_neuf`** (médianes VEFA/neuf) porte aussi un `computed_at` et est jointe.

| table | Mac | Prod |
|-------|-----|------|
| `dvf_secteur_medianes` (2359 lignes) | `computed_at = 2026-08-17 13:17:17+04` | `2026-08-17 13:17:17+04` |
| `dvf_prix_sortie_neuf` (12 lignes) | `computed_at = 2026-10-21 11:45:04+04` | `2026-10-21 11:45:04+04` |

Les deux caches ont un **unique `computed_at`** (min = max), **rigoureusement identique** entre Mac
et prod — à la microseconde.

### Verdict : **IDENTIQUE — aucun écart.**
Les caches de médianes DVF servis en prod sont les mêmes qu'en local (secteur : 17/08/2026 ; prix de
sortie neuf : 21/10/2026). Rien à recompter : ni divergence, ni artefact.

---

## Conclusion

| Constat NU-1 | Statut après recomptage prod |
|--------------|------------------------------|
| `assiette_source` NULL partout | **Artefact Mac** — Mac sert le run legacy 1 ; prod sert q_v20 (38,8 % NULL) |
| 60 biens Radar faussement retirés le 28/10 | **Vrai en prod** (passe #274) **mais déjà restauré** (0 subsistant, biens actifs) ; absent du Mac |
| Fiche disparue → 500 (table de remplacement absente) | **Artefact Mac** — `parcel_cadastre_remplacement` existe en prod (3007 lignes) |
| OLL mort | **Vrai en prod** — couche IRIS sans code (0/344), `oll_parcelle` ne résout aucune parcelle |
| Caches médianes DVF | **Identique** — mêmes `computed_at` Mac/prod |

Deux constats sur cinq étaient des **artefacts du socle Mac** (run résiduel périmé, table absente),
un était **réel mais déjà corrigé en prod** (Radar 28/10), un est un **défaut réel et persistant des
deux côtés** (OLL), et le dernier est un **non-sujet** (caches identiques). Fil rouge : le Mac n'est
pas une image fidèle de la prod — il sert des pointeurs périmés (run 1), lui manque des tables (remplacement
cadastral) et une source (Bien'ici), et porte des retraits Radar jamais restaurés. Les décisions qui
dépendent de l'état des données doivent se vérifier en prod.

*Fin PROD-VERIF-1.*
