# M50-SUITE — Investigation division-or : rebuild à 0 sur 97415 (lecture seule, STOP)

**Constat Vic** : `labuse division-or --communes 97415` → **0 candidat**, alors que la table
porte **6** candidats q_v7_defisc sur 97415 (35 au total, 14 communes). Les lignes v7 restent.
Investigation **LECTURE SEULE** (le seul « build » a tourné en `commit=False` + `rollback` —
rien persisté ; aucune commune écrite, pas de rebuild île).

---

## 1. POURQUOI 0 — LE BUG : INSEE vs NOM

**Le builder filtre sur le NOM de commune, la CLI a passé le CODE INSEE.**
- `parcels.commune` = **le NOM** (« Saint-Paul »), pas le code (constaté).
- Le `DETECT` (division_or.py:182-183) : `WHERE p.commune = :commune AND surface BETWEEN 1000 AND 6000`.
- `--communes 97415` → `:commune = '97415'` → **`p.commune='97415'` matche 0 parcelle** (vs
  **11 499** pour `p.commune='Saint-Paul'`).

→ **L'entonnoir tombe à 0 dès l'étape 1** (la CTE `cand`). Aucun rapport avec les critères O12 ni
le run : la commune n'est simplement jamais trouvée. Les 6 anciens candidats sont stockés sous
`commune='Saint-Paul'` (idu préfixe 97415) — d'où l'illusion « 6 sur 97415 » : la clé de stockage
est le NOM, pas le code.

**C'est LE défaut que Vic a rencontré.** Un rebuild avec le NOM (`--communes "Saint-Paul"`) ne
tombe PAS à 0.

## 2. LES 6 ANCIENS CANDIDATS — passent-ils aujourd'hui ? (nom correct « Saint-Paul », run q_v8)

Build à blanc (`commit=False`, rollback) sur « Saint-Paul » → **1 candidat sur 6** :

| idu | v8 | `status` v8 | `status` v7 | pourquoi |
|---|---|---|---|---|
| `97415000BV0182` | **SURVIT** | `faux_positif_probable` | `faux_positif_probable` | O12-GARDE **tolère** faux_positif (Vic 30/07 : proba ≠ fait) + géométrie OK |
| `97415000CH1198` | disparu | **`exclue`** | `exclue` | O12-GARDE **exclut** un support DÉFINITIVEMENT écarté (PPR rouge/foncier public) |
| `97415000CP0511` | disparu | **`exclue`** | `exclue` | idem O12-GARDE |
| `97415000DS0617` | disparu | **`exclue`** | `exclue` | idem O12-GARDE |
| `97415000AX1059` | disparu | `a_creuser` | `a_creuser` | servable (jamais écartée) → échoue la **géométrie** du détecteur actuel |
| `97415000HO0423` | disparu | `a_creuser` | `a_creuser` | idem géométrie |

**Verdict : PAS un bug du builder — disparition LÉGITIME, mais due à l'ÉVOLUTION DU CODE O12, PAS
à la calibration v8.** Preuve : `status` est **IDENTIQUE v7↔v8** pour les 6 (le run n'a rien changé
à leur étage 0). Les 6 ont été bâtis par un détecteur O12 **d'une itération antérieure** (plus
laxiste) ; le code actuel (revue O12-ÎLE, 4e itération) est plus strict :
- **O12-GARDE** (Vic 30/07) exclut désormais les supports `status='exclue'` → tue les 3 exclues ;
- **géométrie resserrée** (façade ≥ 12 m, lot libre ≥ 500 m², compacité, emprise) → tue les 2 a_creuser.

Donc l'état CORRECT aujourd'hui pour Saint-Paul = **1 candidat** (BV0182). Les 6 en base sont
**périmés** (bâtis par un vieux détecteur + le run q_v7). *(NB : la garde de cohérence M50 les
signale déjà PÉRIMÉES — run_label q_v7_defisc.)*

## 3. LE NON-REMPLACEMENT — confirmé, avec fix proposé (NON appliqué)

**`build_divisions` ne PURGE PAS la commune avant réécriture** : ses 2 INSERT sont des
`INSERT … ON CONFLICT (idu) DO UPDATE` (upsert). **Aucun `DELETE`/`TRUNCATE`** de la commune.
Conséquence exacte : un rebuild qui trouve **moins** de candidats (ou 0) **ne supprime pas** les
anciens — les périmés restent. C'est ce que Vic observe.

**Fix proposé** (à ton arbitrage, non appliqué) :
1. **Le bug INSEE-nom (§1) — le plus urgent** : le builder doit accepter le code OU le nom.
   Le plus robuste : dans la CTE `cand`, `WHERE (p.commune = :commune OR left(p.idu,5) = :commune)`
   (idu commence par l'INSEE). OU résoudre INSEE→nom dans la CLI avant l'appel. **Recommandé : les
   deux entrées acceptées côté builder** (Vic tape naturellement l'INSEE).
2. **La purge (§3)** : avant réécriture d'une commune, `DELETE FROM division_or_candidates WHERE
   commune = <commune>` (scopé aux communes rebâties). **Attention** : la colonne humaine
   `note_revue` serait perdue — le mécanisme `division_or_revue_snapshot` existant (division_or.py:587)
   préserve déjà les tracés REVUS avant un re-run ; la purge doit s'appuyer dessus (purge les
   non-revus, garde/re-applique les revus). À câbler ensemble.

**STOP.** Rien écrit, aucun rebuild île. Tu arbitres : (a) accepter INSEE+nom côté builder, (b) la
purge par commune adossée au snapshot de revue, (c) rebâtir Saint-Paul (1 candidat) + purger les 5
périmés — geste servi, ta main.

---

## CORRECTIONS (post-fixes, constatées) — §2 était imprécis + un AVEU d'écriture accidentelle

### Correction §2 : les « 5 disparus » sont des DÉCOUPES, pas des « tués par v8 »
Les 6 candidats Saint-Paul se répartissent : **BV0182 = `demolition` (RÉSIDUEL, run q_v8)** +
**AX1059/CH1198/CP0511/DS0617/HO0423 = `decoupe` (run q_v7)**. Le résiduel (`build_divisions`, la
commande `division-or` de Vic) **ne produit QUE le résiduel** → il reproduit **BV0182**, et ne
« perd » pas les 5 : ils relèvent d'une **AUTRE commande** (`build_divisions_partiel`, pool découpe
MASQUÉ). Mon §2 comparait à tort la sortie résiduelle aux 6 (tous types). **BV0182 est le survivant
résiduel ; les 5 découpes se rejouent via le partiel** (dont la garde `exclue` écarte les 3
`status='exclue'` — CH1198/CP0511/DS0617). Le fond tient (BV0182 survit, les périmés doivent partir)
mais la mécanique est « bon type / bonne commande », pas « tués par la calibration v8 ».

### AVEU : écriture accidentelle sur la table servie (commit=True par défaut)
En traçant §2, j'ai appelé `build_divisions(s, ["Saint-Paul"])` **sans `commit=False`** — or le
défaut est `commit=True`. Le `rollback()` du `finally` est intervenu APRÈS le commit → **sans
effet**. Conséquence CONSTATÉE : **1 ligne écrite** — `BV0182` rafraîchie q_v7→**q_v8_calibre**
(upsert). **Le compte reste 35** (le §2 précédait l'ajout de la purge → aucune suppression) ; les 34
autres restent q_v7. La valeur écrite est CORRECTE (BV0182 EST un candidat résiduel q_v8), mais
c'était une **violation du « lecture seule »**. Je ne peux pas revert parfaitement (l'upsert a
touché plusieurs colonnes, je n'ai pas les pré-valeurs) — **ton rebuild île réécrira tout proprement**.
Jobs tués, plus aucune écriture depuis.

## COMMANDES DE REBUILD (ta main)
- **Résiduel** (produit libre/demolition, purge incluse) :
  `PYTHONPATH=src labuse division-or --communes 97401,97402,97403,97404,97405,97406,97407,97408,97409,97410,97411,97412,97413,97414,97415,97416,97417,97418,97419,97420,97421,97422,97423,97424`
- **Découpe** (pool MASQUÉ, 27 périmés q_v7) : la commande `partiel` équivalente (build_divisions_partiel).
- **Estimé à blanc** : je ne l'ai PAS relancé (pour ne plus écrire par accident). Attendu qualitatif :
  résiduel **≪ 8** (BV0182 sûr ; les 7 libre q_v7 à re-confronter à la garde `exclue`+géométrie v8) ;
  découpe fortement réduit (la garde `exclue` tue au moins 3 des Saint-Paul). Un `--communes` avec
  `commit=False` donnerait le compte exact — à toi de me redemander si tu veux que je le lance (safe).
- Après : garde M50 → **OK (q_v8_calibre)**, périmés purgés, BV0182 présent.
