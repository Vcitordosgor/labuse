# AUDIT M89 — Les 3 424 parcelles sans rang (Phase 1, mesure)

**Branche `audit/m89-rang-total`. Aucune correction. Mesuré le 15/08/2026 (run servi q_v9_m81). STOP.**

## Verdict en une phrase
Les 3 424 parcelles sans rang sont **EXACTEMENT les 3 424 copropriétés** (`copro = true`) : corrélation
**parfaite**, exclusion **délibérée** (« univers HORS copro, jamais dans le ranking », doctrine M3.6),
**stable** sur les 6 runs. Ce n'est **pas** un effet de bord — c'est un choix de scoring assumé. La
seule dette : le dénominateur servi (dossier banquier « rang X / 428 239 ») est **NU**, sans dire le
périmètre. Le chiffre est juste, sa présentation est incomplète.

## 1 — Qui sont ces 3 424 ?
Toutes DANS la table de score (0 parcelle hors table), mais avec `rang = NULL`. Matrice `copro × rang` :

| copro | rang | n |
|---|---|---|
| **false** | classé | **428 239** |
| **true** | **NULL** | **3 424** |

→ **Corrélation à 100 %** : toute copropriété est sans rang, toute non-copropriété est classée. Aucune
autre cause. Par tier (une copro garde un tier, elle est juste hors ranking) : ecartee 3 074, declasse_
bati_sature 160, a_creuser 125, declasse_non_constructible 39, declasse_bati_revele 17, reserve_fonciere
8, declasse_zone_fermee 1. Par commune (urbaines, cohérent avec l'habitat collectif) : Saint-Denis 1 157,
Saint-Paul 536, Saint-Pierre 380, Le Tampon 233, Saint-Leu 196, La Possession 190, Saint-Louis 100…

## 2 — L'hypothèse copropriétés tient-elle ?
**Oui, exactement.** 3 424 sans rang = 3 424 copro = 100 % ; le compte tombe juste, aucune part
résiduelle. `copro` est une colonne de `parcel_p_score_v2` (owner_type Score V §4.3, code propriétaire
7 = « Copropriétaires », score_v_constants.py:208 ; score_v.py:229-241).

## 3 — Où le rang « se perd »
Nulle part par accident : il n'est **jamais attribué** aux copro, **par construction**.
- `src/labuse/scoring/p_v2/__init__.py:11` : « univers produit par défaut **HORS copro** (badge + toggle,
  jamais dans le ranking) ».
- `src/labuse/scoring/p_v2/statuts.py:77` : « rang (hors copro, **NaN pour copro**/écartée) » ;
  ligne 110-114 : « chaude (copro exclue par construction : rang NaN) … `& ~df["copro"]` ».
Le rang est un `ROW_NUMBER` calculé sur l'univers hors-copro ; les copro reçoivent `NaN` → `NULL` en base.

## 4 — Délibéré ou accidentel ?
**DÉLIBÉRÉ.** Les copropriétés sont hors univers de classement par doctrine (protocole as-of M3.6, même
univers d'évaluation « hors copro » que l'arène — `arene.py:190-192`). Une copropriété n'est pas une
opportunité foncière au sens du produit (propriété morcelée, pas d'assiette mobilisable) → elle porte un
tier informatif mais pas de rang concurrentiel. **Rien à corriger, rien à rejouer.**

## 5 — L'écart est-il stable ?
**Parfaitement.** Sur 6 runs (q_v8_calibre, …_pre_m28, …_pre_m39, …_pre_pond, …_pre_regle, q_v9_m81) :
**3 424 sans rang = 3 424 copro** à chaque fois. Écart constant, jamais variable → pas un symptôme.

## La dette réelle (présentation, pas données)
`rang_total` (verdict_servi.py:55) est DOCUMENTÉ dans le code (« nombre de parcelles CLASSÉES (hors
copropriétés) »). Mais **à l'écran/au papier, le périmètre disparaît** : le dossier banquier
(briques_pdf.py:399-401) affiche `rang {rang} / {rang_total}` = « rang 57 643 / **428 239** » **nu**,
sans « hors copropriétés ». Un lecteur ne peut pas relier 428 239 aux 431 663 du bandeau. C'est
exactement le « 428 239 nu » que le mandat juge malhonnête.

## Décision demandée à Vic (STOP)
L'exclusion étant **délibérée et stable**, la Phase 2 est la voie « exclusion délibérée » :
1. **Nommer le périmètre là où le chiffre est servi** (dossier banquier + tout écran de volume) :
   « rang 57 643 / 428 239 classées — copropriétés hors univers de classement ». Point de lecture unique.
2. **La fiche d'une copropriété doit DIRE pourquoi** elle n'a pas de rang (pas un vide) — vérifier le
   comportement actuel (verdict_servi porte déjà `copro`/badge ; à confirmer côté fiche).
3. **Aucun rejeu, aucune correction de données** — le classement est correct.
