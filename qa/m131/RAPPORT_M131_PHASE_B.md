# M131 — Phase B/C : gravure (Option 1 appliquée)

Branche `feat/m131-dette-hauteur`. Option 1 retenue par Vic : le contrôle
« `git diff plu_rules.py` vide » est **levé pour ce cas précis** et remplacé par
les trois contrôles ci-dessous. Portée autorisée dans `plu_rules.py` : **la seule
lecture de `constructible_neuf` dans `_to_rules`**. Rien d'autre.

Gravé : `Us` (Saint-Pierre) + `2AUa–e` (Le Tampon), gel conservé partout ; Phase C
(renvois `Uazi`/`Ucm`) dans la même passe. CC ne merge pas.

---

## Contrôle 1 — `git diff plu_rules.py` (intégral)

Limité à la lecture de `constructible_neuf` (+ son commentaire de dette). Le
correctif M130-12 (`else None`, repli 4 m supprimé) reste intact.

```diff
@@ -155,6 +155,11 @@ def _to_rules(code: str, v: dict) -> ZoneRules:
         pleine_terre_pct=_num(v.get("pleine_terre_pct")),
         hauteur_mode=v.get("hauteur_mode"),
         habitat=v.get("habitat"),
+        # M131 : lit un gel EXPLICITE du YAML (défaut True). Permet une entrée `zones:` propre qui
+        # porte une hauteur PAR ZONE (renvoi) tout en gardant `constructible_neuf=False` (zone AU*st
+        # gelée : Us, 2AU). NE FABRIQUE aucune valeur numérique — honore une clé explicite. Piège
+        # consigné en dette : sur une zone gelée, OMETTRE cette clé la rend constructible en silence.
+        constructible_neuf=v.get("constructible_neuf", True),
         notes=[n for n in notes if n], sources=srcs, raw=v,
     )
```

*Ruff* : 3 avertissements pré-existants (`I001`/`F401` sur le bloc d'import
`est_famille`, lignes 193/263) — **identiques sur `origin/main`**, non introduits
par M131. Les corriger toucherait d'autres lignes → **hors périmètre** (« Rien
d'autre »). Laissés tels quels.

## Contrôle 2 — grep de non-retour (aucun défaut de hauteur codé)

```
$ grep -nE 'hauteur_max_m.*,\s*4|get\(.hauteur_max_m.,\s*[0-9]' src/labuse/faisabilite/plu_rules.py
  → (aucune occurrence)
```

La branche `zones_au_st` conserve `hf_m = float(_hmax) if _hmax is not None else
None` (M130-12) : **aucun repli 4 m ré-introduit**.

## Contrôle 3 — inventaire gel avant / après

`resolve_zone(code, commune)` dumpé pour les **51 zones** des deux communes, avant
et après gravure (`/tmp/gel_before.json` → `/tmp/gel_after.json`), puis differ.

**Résultat strict — conforme :**

- **Gel changes : 0.** `constructible_neuf` **identique sur les 51 zones**, sans
  exception. Aucune zone ne passe à `True`.
- **Height gains : 6**, exactement les cibles :

  | Zone | `constructible_neuf` | hé/hf avant → après |
  |---|---|---|
  | `Saint-Pierre\|Us` | `False` (inchangé) | `None/None` → `6.0/11.0` |
  | `Le Tampon\|2AUa` | `False` (inchangé) | `None/None` → `21.0/25.0` |
  | `Le Tampon\|2AUb` | `False` (inchangé) | `None/None` → `13.0/17.0` |
  | `Le Tampon\|2AUc` | `False` (inchangé) | `None/None` → `9.0/13.0` |
  | `Le Tampon\|2AUd` | `False` (inchangé) | `None/None` → `7.0/11.0` |
  | `Le Tampon\|2AUe` | `False` (inchangé) | `None/None` → `12.0/None` |

---

## Gravures (YAML)

**`config/plu_le_tampon.yaml`** — cinq entrées `zones:` `2AUa–e` (gel + hauteur par
renvoi `AUindicée 10, p.86` → `U`-indice ; libellé unique « via renvoi (ZONE
AUindicée, p.83) », offset PDF↔imprimée +2). `zones_au_st.liste` **vidée** (`[]`)
— plus aucune zone du Tampon ne passe par ce mécanisme. `2AUe` : égout seul
(`hf_m: null`), rien inféré.

**`config/plu_saint_pierre.yaml`** — entrée `zones:` `Us` (`6/11`,
`Art. Us3 §5, p.134`, `constructible_neuf: false`). `Us` **retiré** de
`zones_au_st.liste` (restent `AU01/AU02/AU03/AU0c-1`). Citation corrigée p.130 →
**p.134** (p.130 = `Us1` destinations).

**Phase C** — mention « via renvoi » ajoutée aux `hauteur_src` de `Uazi`
(Saint-Pierre) et `Ucm` (Le Tampon) : **affichage seul**, valeur et article
inchangés (vérifié : hé/hf identiques à l'inventaire).

---

## Contrôles au rendu (P1–P4 régénérés, figeage 2026-08-22)

- **Faîtage 4 m = 0** : aucune ligne hauteur « 4 m » sur P1–P4.
- **Inversion 2AU assumée (8/8)** : les 8 parcelles 2AU de P2 (2×`2AUc`, 1×`2AUd`,
  5×`2AUe`) **servent** désormais une hauteur (avant : « non renseignée »). **0**
  ligne « non renseignée » sur les 2AU de P2. Chacune garde sa **SDP « aucune
  (zone fermée à l'urbanisation) »**.
- **`2AUe`** rend « égout 12 m · faîtage non réglementé ».
- **EP 1044 (P3)** : sert « égout 6 m · faîtage 11 m · Art. Us3 §5 … p.134 »,
  zone `Us — urbaine`, **SDP « aucune » conservée**.
- **Zones non gravées** (A/N Saint-Pierre) restent « non renseignée au PLU
  calibré ».
- **Phase C au rendu** : `Ucm` (P2) et `Uazi` affichent la mention « via renvoi ».
- **Non-régression M130-12** : `sans objet` = 0 ; `peut exister` = 0 ; aucune
  ligne **Hauteur** « reste à instruire » (0) ; `part X —` = **5** (1 Ua, 2 Uc,
  2 Uf) ; ancres `BI1097`/`CW1056`/`BV2471` présentes ; incise P3 intacte. Revue
  des libellés hauteur : servie / « faîtage non réglementé » / « non renseignée au
  PLU calibré » / « part X — … » — **aucune** forme parasite.

---

## Dette

`qa/m130/DETTE_HAUTEUR_PLU.md` mis à jour : `Us`/`2AU` **sortent de dette** (§1,
avec source) ; renvois `Uazi`/`Ucm` **apurés** (§3) ; **nouvelle dette §4** — le
gel implicite par défaut : `_to_rules` lit `constructible_neuf` avec **défaut
`True`**, donc sur une zone AU\*st, **omettre** `constructible_neuf: false` dans
une entrée `zones:` la rend constructible **en silence** (invisible au rendu
projet, car la SDP vient du cache). Vérification à refaire à chaque nouvelle
entrée `zones:` sur une zone AU\*st : présence de la clé + inventaire gel
avant/après (toute zone → `True` = échec). Rejoint M130-6 F.2 et M131 Phase D.
