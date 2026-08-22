# M130-6 — PDF projet : cause de la variante multi-zones, parenthèse étage 0, script QA

Branche `feat/m130-pdf-projet`. Ne pas merger.
`git branch` = `feat/m130-pdf-projet` · `git log -1` (départ) = `1d806dd1` ·
`lsof -ti:8000 | xargs kill -9` = serveur dev tué (rendu régénéré en direct).

PDF régénérés **par le script `qa/m130/generer_pdf_qa.py`** (§D) :
`M130-6-projet-{P1..P4}.pdf`.

---

## A — Variante multi-zones choisie sur la CAUSE

Trois variantes, sélectionnées sur la **cause d'absence de SDP** :

1. **SDP chiffrée > 0** → « SDP calculée sur la partie constructible ; les autres
   parts restent à instruire. »
2. **Supprimée par la famille** (A / N / zone fermée : `zone_non_constructible…`)
   → « la SDP n'est pas chiffrée ; une partie constructible peut exister et reste
   à instruire. »
3. **Calculée et NULLE** (cause ∈ {terrain_exigu, capacite_nulle, redhibitoire,
   habitat_interdit}) → « le résiduel calculé est nul sur la part {zone
   dominante} ; les autres parts restent à instruire. »

`97415000CW1056` — **3 lignes rendues après correctif** (cohérentes entre elles) :

> · SDP résiduelle : aucune (résiduel nul après reculs et emprises)
> · Hauteur PLU : égout 15 m · faîtage 19 m (Sourcé — PLU calibré · Zone U3a,
>   Art. 10.2, p.110-112 · via renvoi : AU3a → règles de U3a (renvoi du règlement,
>   Règles de U3 de même indice. Source: p.154))
> · Zone PLU AU3a — à urbaniser (Sourcé — GPU/PLU, millésime 17/12/2025)
> · Parcelle multi-zones : AU3a (à urbaniser) ~ 67 % · Nto (naturelle) ~ 33 % —
>   **le résiduel calculé est nul sur la part AU3a** ; les autres parts restent à
>   instruire.

La ligne multi-zones ne dit plus « la SDP n'est pas chiffrée » — elle est
alignée sur la cause affichée deux lignes plus haut (résiduel nul).

**Bascules cas 2 → cas 3 par projet** : **P1 = 1 · P2 = 5 · P3 = 0**.

---

## B — Parenthèse étage 0 : la couche réellement interrogée

**Définition littérale de `_ETAGE0_SQL`** (`api/app.py:728`) :
`(d.status IN ('exclue', 'faux_positif_probable'))` — table
**`dryrun_parcel_evaluations`** (alias `d`), colonne **`status`**, valeurs
retenues **`'exclue'`** et **`'faux_positif_probable'`**, run de référence
**`q_v10_m129`** (`d.run_label`, constante `RUN`).

Preuve du défaut : `97422000AD1237` porte la cause SDP « zone fermée à
l'urbanisation » (zone 2AUd) mais son `status` réel est **`a_creuser`** — un
tier, **pas** l'étage 0. L'ancienne parenthèse « zones fermées à l'urbanisation »
nommait donc une chose absente de `_ETAGE0_SQL`, en empruntant les mots d'une
cause de SDP.

**Nouvelle parenthèse, mot pour mot** (aucune énumération illustrative, aucun mot
des causes de SDP) :

> classées à l'étage 0 du moteur (**écartées avant évaluation — statut « exclue »
> ou « faux positif probable » du run de scoring**)

Contrôle : la phrase étage 0 ne contient plus « résidus cadastraux », « emprises
non exploitables » ni « zones fermées à l'urbanisation » (0 occurrence).

---

## C — Dénominateur : part étage 0 du total

Ligne d'état P3, mot pour mot :

> Liste plafonnée : 60 parcelles figées sur ~ 10 725 retenues par le cadrage
> **dont ~ 10 725 classées à l'étage 0** (à ce jour). …

| P3 | valeur |
|---|---|
| total (population `_run_cadrage`) | **10 725** |
| part étage 0 **du total** | **10 725** (100 % — le cadrage `tiers:[ecartee]` ne retient que l'étage 0) |
| part étage 0 **des figées** | **60 / 60** |

Comptage à coût nul (un `count(*) FILTER (WHERE _ETAGE0_SQL)` sur la même requête
que le total). P1 / P2 : `dont ~ 0 classées à l'étage 0` (leur population exclut
déjà l'étage 0 par la base `AND NOT _ETAGE0_SQL`).

---

## D — Script QA reproductible

`qa/m130/generer_pdf_qa.py`, versionné. Sur une base où les projets n'existent
pas encore : (re)crée les 4 projets (idempotent, nettoyage par nom), fige P1/P2/P3
avec une **date de figeage déterministe (2026-08-22)**, laisse P4 sans figeage,
écrit les 4 PDF dans `qa/m130/`, **persiste** (aucun rollback), affiche les `pid`.

Exécuté ici sur une base vierge de ces projets → pids **65, 66, 67, 68**
(compte_id 18), 4 PDF générés. Reproductible chez Vic ; les projets deviennent
visibles dans `GET /projets` pour le compte rattaché.

*Note :* contrairement au constat du mandat, les `qa/m130/*.pdf` **ne sont pas
gitignorés** (`git check-ignore` = non ignoré, `git ls-files` les liste) — ils
survivent au `git pull`. Ce qui manquait chez Vic, ce sont les **projets** (P1–P4
n'existaient que dans ma base) : le script les recrée.

---

## E — Finitions

- **E.1** `97415000AY1622` (U4c 62 % / U4b 38 %, tout constructible) →
  « SDP calculée sur la partie constructible ; les autres parts **relèvent d'un
  autre règlement de zone, à instruire.** » ✅
- **E.2** `97420000AO0528` : « UC ~ 95 % · **A (agricole) ~ 5 %** … » — la part à
  exactement 5 % **passe** (seuil = *strictement inférieur à 5 % → complément* ;
  `pct >= 5` affiché). ✅
- **E.3** `97415000CW1056` : « … Source: p.154**)** » — le point final parasite du
  libellé « via renvoi » est retiré (`_src_propre` étendu : `.)` → `)`). ✅

ruff : 0 erreur nouvelle (I001 restantes = imports pré-existants décalés ;
script QA : `All checks passed`).
