# CHIRURGICAL-FIX-1 — LOT J (3ᵉ passage du relecteur indépendant, 4 parcelles)

**Branche** `fix/chirurgical-j` (depuis `fix/chirurgical-i`, qui contient le LOT I).
**Modèle** Opus 4.8. **Dépôt** `~/Desktop/labuse-chasse-ecrans`. Les 4 parcelles : **BW2635**
`97422000BW2635` (Uav, Le Tampon), **AM0838** `97404000AM0838` (UE, habitat interdit),
**AD0887** `97422000AD0887` (Ud, Le Tampon), **IS0448** `97411000IS0448`. Un commit par
point/groupe. Gardes dans `tests/test_chirurgical_fix_j.py`. Documents livrés dans
`~/Desktop/chasse-1/_lot-final-3/`. Règle de régénération : **vider `fiche_cache`** des parcelles
(le cache L2 servait l'ancien texte).

---

## 1 — Bilan Excel

### 1a — plus de référence circulaire (AM0838 sans produit)
`bilan/excel.py`. Quand une parcelle n'a AUCUN produit (AM0838, habitat interdit), la ligne
« Total produits » se sommait **elle-même** (`=SUM(B34:B33)` avec la ligne de total en 34) → au
recalcul, Excel signale une **référence circulaire**. `_somme_produits(col)` renvoie **0** quand la
plage de produits est vide (`prod_last < prod_first`), sinon la vraie somme.

### 1b — plus de `#DIV/0!` quand la surface vendable est nulle
Les ratios « €/m² de surface vendable » sont gardés `=IF(SUV=0,"",…)` : surface vendable nulle →
cellule vide, jamais `#DIV/0!`.

### 1c — validation Excel « ≥ 0 » sur TOUTES les cellules de saisie + refus serveur
`bilan/excel.py` : une `DataValidation(decimal, ≥ 0)` (openpyxl) couvre **toutes** les cellules de
saisie (programme, produits, coûts) — un coût négatif (−250 000 € → 128 % de marge sur AD0887) est
refusé à la main dans le tableur, avec un message. Côté serveur, le **modèle des ratios maison**
(`api/bilan.py` `RatioIn.valeur`) refuse aussi un coût négatif (`_valider_non_negatif`), comme les
autres postes.

### 1d — test PERMANENT : recalcul par un moteur INDÉPENDANT
`tests/test_chirurgical_fix_j.py::test_1d_recalcul_moteur_independant_zero_erreur`. Chaque classeur
généré est **recalculé par `formulas`** (moteur Excel indépendant, pip), sur les **4 parcelles**
(dont AM0838 non constructible), **coûts vides PUIS saisis** : **0 erreur, 0 cycle** (ni `#DIV/0!`,
ni `#REF!`, ni `#CYCLE`).

### 1e — surface terrain réelle + net promoteur à la TVA de la vente
`bilan/excel.py`, `api/bilan.py`. La surface du terrain pré-remplie est la **contenance cadastrale
réelle** de la parcelle (route `.xlsx` alignée sur le PDF : `sources_parcelle(...).terrain`), jamais
une valeur de banc (1703 AD0887, 2003 BW2635). Le **« net promoteur TTC »** applique la TVA de la
**ligne de vente** (`×(CA_TTC/CA_HT)`), pas un taux figé : sur un produit à TVA 0, net TTC = net HT
(4318 €/m²), pas ×1,085.

---

## 2 — Une parcelle, une adresse
`api/pre_dossier.py`. Le CERFA (PCMI4) choisissait son adresse avec un `ORDER BY` propre (sans
départage par numéro de voie) → il tombait parfois sur une AUTRE adresse que la fiche (AM0838 : « 14
Rue de la Boulangerie » au CERFA vs « 4 Impasse Henri Madore » partout ailleurs). Il reprend
désormais l'**ordre canonique `_BAN_ORDER`** (celui de `_ban_adresse`/la fiche) → la **même ligne
BAN** partout. Source unique.

---

## 3 — Formulations

### 3a — stationnement Le Tampon : renvoi à l'article, pas un nombre partiel
`plu_reglement.py`, `api/traducteur.py`. Le barème de stationnement à plusieurs paliers (type de
logement, taille de l'opération) n'est pas servi en entier : la ligne RENVOIE à l'article (**« barème
selon le type de logement et la taille de l'opération — voir l'article Ua 12.2 / Ud 12.2 »**), plus
un nombre partiel. La **capacité** lit toujours le ratio de base (`places_par_logement()` inchangé).

### 3b — zone rouge : le reste soumis au règlement du plan de prévention
`api/risques_arbitrage.py` + `cascade/layers/phase1.py`. On ne dit plus « … ne s'appliquent qu'en
zone bleue » (qui laissait croire que le rouge est sans règle) : **« la partie en zone rouge est
exclue de l'implantation ; le reste est soumis au règlement du plan de prévention »**.

### 3c — sol : une seule phrase combinée
`plu_reglement.py`, `api/traducteur.py`. Les deux obligations de sol tiennent en UNE phrase : **« X %
de surface perméable, dont au moins Y % en pleine terre »** (plus deux lignes séparées). AD0887 (Ud)
40 %/30 %, BW2635 (Uav) 30 %/20 %.

### 3d — IS0448 : la VRAIE raison de l'absence de marge
`exports/miroir.py` (`_absence_une_raison`). La hauteur du bâti **est** mesurée (4,1 m à l'égout, le
Dossier l'affiche) : l'absence de marge de surélévation n'est donc pas « hauteur du bâti non
mesurée » (faux) mais **« hauteur de la zone non comparable à la hauteur mesurée du bâti »** (règle
et mesure sur des références différentes / non résolue). Détecté via `hauteur_egout_mesuree_m`.

### 3e — comparables : classés par RESSEMBLANCE + note dans le Dossier
`exports/blocs/annonce.py`, `exports/miroir.py`. Les 8 comparables sont classés par **ressemblance**
(le poids d'Estimer, `estimer3.py:555` tri par `_poids`), pas par distance (une vente à 321 m plus
ressemblante passe devant une à 297 m). Le titre et la note le disent (Estimer **et** Dossier), et la
note qui les distingue de l'échantillon du **prix médian** (calculé sur tout le secteur) apparaît
désormais aussi dans le **Dossier**.

### 3f — plans de prévention : couvre la parcelle ≠ existe dans la commune
`api/app.py` (`_ppr_documents_couvrant`, `_aleas_block`), `exports/miroir.py` (`_r_aleas`),
`exports/robinet_fiche.py`. On distingue le plan qui **COUVRE** la parcelle (son zonage l'intersecte,
`ST_Intersects`) de ceux qui **EXISTENT** seulement dans la commune. AM0838 : seul le **PPR 2016**
couvre (« couvre la parcelle ») ; le **PPRL 2017** est cité à part (« Autres plans dans la commune
(ne couvrent pas la parcelle) »).

### 3g — PLU : une seule date « version servie »
`exports/miroir.py` (`_r_statut_plu`). UNE SEULE date porte « version servie » (l'approbation de la
version servie) ; les autres dates (évolution engagée, approbation enregistrée au GPU) sont des
**repères**, plus une seconde « version servie » (ambiguïté levée).

---

## 4 — Numéro de document : toute la matière rendue
`exports/builder.py` (`_signature_contenu`, `_NUMERO_PLACEHOLDER`), `bilan/pdf.py`. La clé de contenu
ne hachait que les `valeurs` (LOT I) : deux documents au contenu **affiché** différent mais aux mêmes
valeurs (adresse rendue hors `valeurs`, contexte Apporteur, programme du Bilan à CA identique)
recevaient le MÊME numéro. Désormais le numéro porte la **signature du corps réellement rendu** (corps
HTML, visuels volatils retirés pour l'idempotence) : rendu en deux passes (jeton → signature →
substitution). **Deux documents au contenu affiché différent ⇒ numéros différents** ; une génération à
l'identique garde le même numéro. Preuve : un Bilan de programme 1703 m² et un de 2003 m² (même CA)
ont des numéros différents (collision LOT I levée).

---

## Complément — doublons de ventes (`dvf_mutations_parcelle`)

**Mesuré sur la base réelle** : la table republie/duplique la même ligne de vente. **19 588 / 55 640
couples (mutation, parcelle) sont dupliqués** (35 %) ; pire couple **3 048 lignes** (97415000CT2791 /
2024-1188637) ; CH0360 / 2022-1640493 = 327 lignes pour **33 lignes de contenu distinct** (≈ 10 copies
par lot, même millésime). La correction d'Estimer (LOT I, `DISTINCT ON (id_mutation, id_parcelle)`)
soignait UN lecteur ; voici l'audit de **tous** les lecteurs.

### 1 — Audit des lecteurs (dédoublonnage + effet mesuré)

**Sûrs (déjà dédoublonnés `DISTINCT ON (mutation, parcelle)` / `GROUP BY mutation` / `max()`/`LIMIT 1`
/ `EXISTS` / `COUNT(DISTINCT …)`)** — résultat INCHANGÉ par les doublons :
`pige/estimer3.py` (pool comparables), `marche_dvf_commune.py` (médiane terrain), `marche_service.py`
(comparateur terrain + bâti), `pige/banc_estimer.py`, `api/moteurs.py` (série terrain),
`ingestion/dvf_marche.py` (vue dernière vente), `api/scoreur.py` (liste des ventes de la fiche),
`api/site_voisinage.py`, `pige/signaux.py`, `scoring/score_v.py`, `scoring/p_model/sql.py:129`
(`p_model_mut_all`, DISTINCT), `courrier_compose.py` (`count(DISTINCT id_mutation)`),
`api/events.py` (lignes brutes mais dédoublonnées par la clé de notification),
`pige/cycle.py` (LIMIT 1 / NOT EXISTS), `signal_instantane.py` (max/COUNT DISTINCT), `ingestion/anc.py`,
`ingestion/vefa_neuf.py`, `cascade/context.py` (EXISTS).

**Faussés par les doublons — CORRIGÉS** (le premier audit statique les avait crus sûrs ; la mesure sur
base les a démasqués) :

| lecteur | ce qu'il calcule | effet MESURÉ des doublons | correction |
|---|---|---|---|
| `faisabilite/bilan.py` `_surface_terrain_sujet` | `sum(surface_reelle_bati)` → surface bâtie du sujet → **pondération de ressemblance Estimer** | **1431 / 16929 parcelles** faussées, **jusqu'à ×209** (CH0360 : 11 802 → 2 364 m²) | somme sur lignes DÉDOUBLONNÉES (`SELECT DISTINCT id_mutation, type_local, surface_reelle_bati, …`) |
| `scoring/p_model/sql.py` `p_model_mut_l2.s_bati` | `sum(surface_reelle_bati)` → `pm2_bati = valeur / bâti` (**feature de prix du p-model/score**) | **934 couples** faussés, **jusqu'à ×57** (prix/m² déflaté d'autant) | CTE `ded` (`DISTINCT`) avant la somme |
| `faisabilite/marche_commune.py` `_median_terrain_commune` | `sum(surface_terrain)` par mutation → **médiane €/m² du terrain nu** | **19 / 24 communes** voyaient leur médiane bouger (Le Tampon 251 → 267, Saint-Paul 433 → 465 ; max Δ 27,5 €/m²) | une surface par couple (`max(surface_terrain) OVER (PARTITION BY mutation, parcelle)` + `DISTINCT`) avant la somme |

`max()`/`valeur_fonciere` (constants par mutation) ne sont jamais touchés par les copies — seuls les
`sum()` l'étaient.

### 2 — Test anti double-comptage
`tests/test_dvf_doublons_couple.py` (marqueur `db`) — INJECTE 40 copies d'un couple existant **dans une
transaction annulée** (aucune écriture persistée) et vérifie que le résultat du lecteur **ne bouge
pas**. Avant correction il bougeait → c'est le test qui échoue si un prix recompte le même couple.
Preuve mesurée : médiane terrain Le Tampon = **267 (n=113) avant ET après +40 doublons** (invariant) ;
surface sujet invariante. Les copies sont injectées en **UN seul `INSERT … SELECT … CROSS JOIN
generate_series`** (lecture des lignes d'origine UNE fois) — une boucle d'`INSERT … SELECT` relirait
l'ensemble qui grossit et croîtrait de façon EXPONENTIELLE. Garde statique (hook) en plus dans
`test_chirurgical_fix_j.py::test_dvf_lecteurs_prix_dedoublonnent_par_couple`.

### 3 — Clé unique à la construction (à faire au rebuild — NON exécuté)
Les correctifs ci-dessus soignent les LECTEURS ; la SOURCE garde ses doublons. Au prochain rebuild de
la table (ingestion `ingestion/dvf_detail.py`), viser **une ligne par couple (mutation, parcelle)** :

```sql
-- 1) Reconstruire la table dédoublonnée + agrégée au grain (mutation, parcelle).
--    Un couple = une vente d'une parcelle ; surface_reelle_bati = somme des LOTS DISTINCTS (pas des
--    copies) ; valeur_fonciere / date / nature sont constantes par couple (on prend l'unique valeur).
CREATE TABLE dvf_mutations_parcelle_v2 AS
WITH ded AS (   -- dédoublonne les copies (republication / duplication) : contenu distinct
  SELECT DISTINCT id_mutation, id_parcelle, date_mutation, nature_mutation, valeur_fonciere,
         code_commune, type_local, surface_reelle_bati, surface_terrain, nature_culture,
         longitude, latitude
  FROM dvf_mutations_parcelle
)
SELECT id_mutation, id_parcelle,
       min(date_mutation)              AS date_mutation,
       min(nature_mutation)            AS nature_mutation,
       max(valeur_fonciere)            AS valeur_fonciere,   -- constante par mutation
       max(code_commune)               AS code_commune,
       string_agg(DISTINCT type_local, ' / ') AS type_local, -- lots agrégés
       sum(surface_reelle_bati)        AS surface_reelle_bati, -- somme des LOTS distincts
       max(surface_terrain)            AS surface_terrain,    -- terrain du couple
       max(nature_culture)             AS nature_culture,
       max(longitude) AS longitude, max(latitude) AS latitude
FROM ded
GROUP BY id_mutation, id_parcelle;

-- 2) Clé unique à la CONSTRUCTION : un couple ne peut plus réapparaître.
ALTER TABLE dvf_mutations_parcelle_v2
  ADD CONSTRAINT dvf_mut_parc_uc UNIQUE (id_mutation, id_parcelle);

-- 3) Bascule atomique + réindexation (reprendre les index existants : (id_parcelle), (code_commune), …).
BEGIN;
  ALTER TABLE dvf_mutations_parcelle      RENAME TO dvf_mutations_parcelle_old;
  ALTER TABLE dvf_mutations_parcelle_v2   RENAME TO dvf_mutations_parcelle;
  CREATE INDEX ON dvf_mutations_parcelle (id_parcelle);
  CREATE INDEX ON dvf_mutations_parcelle (code_commune);
COMMIT;
-- DROP TABLE dvf_mutations_parcelle_old;  -- après recette

-- 4) Côté ingestion (dvf_detail.py) : insérer avec ON CONFLICT (id_mutation, id_parcelle) DO UPDATE
--    (ou pré-agréger le lot DVF avant insertion) pour que la contrainte tienne à chaque run.
```

Une fois ce grain en place, les `DISTINCT`/`GROUP BY` des lecteurs deviennent redondants (mais restent
corrects) ; les correctifs de LECTURE ci-dessus protègent **jusque-là**.

---

## Recette
`tests/test_chirurgical_fix_j.py` (1a..1e, pt2, pt3a..g, pt4, garde statique dvf) +
`tests/test_dvf_doublons_couple.py` (invariance aux doublons, marqueur `db`) + tests LOT I alignés
(test_chirurgical_fix_i 3b/3c/3d/pt2, test_bilan_routes coût majeur requis, test_annonce_pdf titre
comparables). Hook pré-push (famille unitaire + front + cohérence) **vert sans `--no-verify`**,
branche poussée, **pas de merge**.
