# OUTIL-COMMUNES-FIX-5 — réponse à la relecture 3 (`relecture-communes-3.md`)

Trois points. Base locale `labuse` ; SEULE la table `dvf_secteur_medianes` est écrite (reconstruction
AUTORISÉE par Vic), plus sa sauvegarde datée. Aucune autre table de `labuse` touchée. Tout chiffre sort
d'un script committé (`scripts/communes_fix5_*.py`) ou de psql, sortie brute dans
`docs/audit-2026-11/outil-communes-fix-5/`.

---

## 1. Preuve terrain refaite avec LA FONCTION SERVIE (plus de borne fantôme)

`communes_fix4_terrain_preuve.py` appliquait un `BETWEEN 50 AND 4000 €/m²` que `ligne2_terrain_zone`
(la fonction servie au tableau) **n'applique pas** → ses « après » divergeaient de l'écran.

Nouveau script `scripts/communes_fix5_terrain_preuve.py` : colonne **« servi »** = appel DIRECT à
`ligne2_terrain_zone(db, commune)` (arrondi + seuil d'effectif de la fonction) ; colonne **« avant »** =
la MÊME requête mot pour mot, avec la qualification d'avant FIX-4, sans aucune borne. Sortie brute :
`FIX5-1-terrain-preuve.txt`. Contrôle intégré :

```
Saint-Denis U : servi 287·594  attendu 287·594  OK
Saint-Paul  U : servi 271·872  attendu 271·872  OK
Le Tampon   U : servi 202·653  attendu 202·653  OK
```

Les chiffres « servi » ÉGALENT l'écran et le rapport externe (effectifs à l'unité). Exemple de delta
réel (avant → servi) : Saint-Denis U **285·604 → 287·594**, Saint-Paul U **271·879 → 271·872**,
Le Tampon U **202·657 → 202·653** — le retrait des actes local/multi-communes, sans borne ajoutée.

---

## 2. Libellé : 13 communes « sans procédure » ne disent plus « à jour »

`api/fiche_commune.py` : `procedure='aucune'` n'est plus mappé sur « à jour ». Le statut servi est
désormais **« aucune procédure connue au 31/12/2024 »** (date de la source — le squelette national
Sudocuh — calculée de `etat_au`). Vérifié sur les 13 communes concernées (`test_plu_13_sans_procedure_libelle_date`) :
Avirons, Bras-Panon, Entre-Deux, Petite-Île, Le Port, La Possession, Saint-Benoît, Saint-Joseph,
Saint-Pierre, Sainte-Rose, Salazie, Le Tampon, Cilaos — toutes « aucune procédure connue au 31/12/2024 »,
aucune « à jour ».

Aucune commune ne dit « à jour » sur une inférence d'absence > 12 mois. Les seules « à jour » restantes
sont les PLU **approuvés** (clôturés) — Sainte-Marie et Sainte-Suzanne — adossés à un ACTE d'approbation
daté (fait positif, re-constaté le 24/11/2026), pas à un squelette : état validé par relecture-3 (§ point 3).
Les communes « en révision » (Saint-Denis, Saint-Paul, La Plaine-des-Palmistes…) gardent leur réserve.

Front : la carte Urbanisme affiche ce libellé tel quel (pas de préfixe « PLU » parasite pour la forme
phrase), au-dessus de la ligne « État au … » existante.

---

## 3. Reconstruction du cache `dvf_secteur_medianes` dans `labuse`

### a. Sauvegarde + empreinte AVANT
`CREATE TABLE dvf_secteur_medianes_bak__20261124 AS SELECT * FROM dvf_secteur_medianes;`

```
EMPREINTE_AVANT : lignes = 2359 · checksum = 64732330743
```
(checksum = Σ hashtext des colonnes métier `secteur|type_bien|n_ventes|mediane_valeur|mediane_prix_m2|fenetre`, hors `computed_at` volatile.)

### b. Reconstruction (builder corrigé, hors 13 h 30–14 h)
`labuse.ingestion.dvf_marche.compute_medianes_secteur` (terrain via `ACTE_TERRAIN_NU_CTE`) lancé à
**16 h 51 (Indian/Reunion)**. Résultat : `{'lignes': 2354, 'secteurs': 848, 'ventes': 40267}`.
EMPREINTE_APRÈS : lignes = 2354 · checksum = -25299229330.

### c. Contrôle APRÈS (`scripts/communes_fix5_cache_after.py`, `FIX5-3-cache-apres.txt`)
- **Section IZ de Saint-Denis (terrain) = 284 €/m² · 18 ventes** (était 272 · 19 — le témoin
  2023-1315722, local sur IZ0236, a disparu). ✓
- **Cache TERRAIN == qualification unique** : 786 secteurs cache == 786 CTE, **0 divergence** → le cache
  est bâti SANS acte avec local déclaré ni à cheval sur deux communes. ✓
- **60 secteurs** dont le prix servi au Bilan mode B (n ≥ 3) bouge — exactement le nombre annoncé.
  Écart médian **10 €/m²**, max **118 €/m²** (97407000AT 346→228). Liste complète avec Δ par secteur
  dans `FIX5-3-cache-apres.txt`.
- 5 secteurs perdent toutes leurs ventes terrain (97402000AR, 97416000HK, 97407000AB, 97411000AH,
  97418000AZ) — tous n ≤ 2, donc AUCUN ne servait de prix au Bilan (seuil n ≥ 3).

### d. Suite de cohérence (après reconstruction)
`scripts/ci/coherence_run.sh` sur la base reconstruite (`FIX5-3-coherence.txt`) :
**87 passed · aucun écart (1 €/1 m²) sur les témoins.** AUCUN témoin du Bilan ne bouge : tous les
lecteurs (fiche §8, Comparatif, Bilan mode B) lisent le MÊME cache reconstruit → ils restent cohérents
entre eux. Rien à arrêter, rien à re-baseliner. (Si un témoin avait bougé, je me serais arrêté ici avec
témoin / ancien / nouveau / acte retiré, sans toucher le témoin.)

### e. Commande de RETOUR ARRIÈRE (restaurer la sauvegarde)
Testée sur une COPIE (table TEMPORAIRE, jamais persistée) : après dérive simulée, la commande restaure
l'empreinte AVANT exacte (2359 · 64732330743). Commande à exécuter pour revenir en arrière :

```sql
BEGIN;
TRUNCATE dvf_secteur_medianes;
INSERT INTO dvf_secteur_medianes
       (secteur, type_bien, n_ventes, mediane_valeur, mediane_prix_m2, fenetre, computed_at)
SELECT  secteur, type_bien, n_ventes, mediane_valeur, mediane_prix_m2, fenetre, computed_at
FROM    dvf_secteur_medianes_bak__20261124;
COMMIT;
-- contrôle : doit redonner lignes=2359, checksum=64732330743
SELECT count(*),
       sum(hashtext(secteur||'|'||type_bien||'|'||coalesce(n_ventes::text,'')||'|'||
           coalesce(mediane_valeur::text,'')||'|'||coalesce(mediane_prix_m2::text,'')||'|'||
           coalesce(fenetre,''))::bigint)
FROM dvf_secteur_medianes;
```

(La reconstruction a ajouté la colonne `millesime_dvf` — conformité NU-E-032 ; le rollback restaure les
DONNÉES servies à l'identique, cette colonne restant NULL sur les lignes restaurées — sans effet sur les
lecteurs. La PK (secteur, type_bien) et les index sont préservés : la reconstruction fait DELETE+INSERT,
jamais de DROP de la servie.)

Sauvegarde conservée : `dvf_secteur_medianes_bak__20261124` (2359 lignes).

---

## Vérifications finales
- Filet `tests/test_communes_cas_externes.py` : **13 passed** (base `labuse` reconstruite) — dont les 2
  nouveaux tests de libellé PLU.
- Front `tsc -b` : OK.
- Cohérence (12 témoins, base reconstruite) : **87 passed, aucun écart**.
- `dvf_secteur_medianes` reconstruit ; sauvegarde `dvf_secteur_medianes_bak__20261124` conservée ;
  commande de rollback testée sur copie TEMP. Aucune autre table de `labuse` écrite.
- Pas de fusion dans `main`.
