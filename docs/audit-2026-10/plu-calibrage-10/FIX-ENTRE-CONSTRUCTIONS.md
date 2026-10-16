# PLU-CALIBRAGE-10 — FIX : l'injection des feuilles `entre_constructions` cassait la résolution de zone

## Symptôme

Push refusé (filet `pre-push`) : `tests/test_plu_calibrage4_zonage.py::test_au_st_non_constructible`
rouge. Les Avirons **AUes** (zone gelée, listée en `zones_au_st`) se résolvait en
« estimation générique (PLU non outillé) » avec `constructible_neuf = True`, au lieu de la
branche gelée non constructible.

## Cause racine

PLU-10 (point 1, « calibrage exhaustif entre_constructions ») a ajouté une feuille
`retraits.entre_constructions` (implantation des constructions d'une même unité foncière, ex-art. 8)
sur de nombreuses zones — y compris des zones **non constructibles** qui n'avaient AUCUN bloc
`regles` auparavant.

Or `resolve_zone` reconnaît une zone « calibrée » (correspondance directe, étape 1) dès qu'elle
figure dans `regles_commune` — c.-à-d. dès qu'elle porte un bloc `regles`, **quel qu'en soit le
contenu**. Une zone gelée qui ne gagnait qu'une feuille `entre_constructions` :

1. devenait un « hit direct » (étape 1), court-circuitant la branche dédiée `zones_au_st` (étape 2) ;
2. comme la feuille `entre_constructions` ne porte **pas** de hauteur exploitable, la résolution
   retombait sur `_zone_generique` → préfixe `AU`/`U` = **constructible** (mode progressif), ou pire
   restait « calibrée constructible » par défaut (mode strict, Saint-Paul).

`entre_constructions` n'est jamais consommée par le calcul de capacité : elle n'est lue que par le
contrôle d'implantation (`labuse.implantation.regles`). Elle ne doit donc **rien** changer à la
résolution de zone.

**8 zones régressées** (vérifié par rejeu avant/après sur les 24 communes, graine de zones figée) :

| Commune | Zone | Avant PLU-10 | Après PLU-10 (cassé) |
|---|---|---|---|
| 97401 Les Avirons | AUes | gelée, non constructible | générique **constructible** |
| 97402 Bras-Panon | AUst | gelée, non constructible | générique **constructible** |
| 97407 Le Port | Ue, Up | gelées, non constructibles | génériques **constructibles** |
| 97408 La Possession | AUst | gelée, non constructible | générique **constructible** |
| 97415 Saint-Paul | AU6st | gelée, non constructible | calibrée **constructible** (strict) |
| 97415 Saint-Paul | N | hors calibrage → `None` | calibrée **constructible** (strict) |
| 97423 Trois-Bassins | AUs | gelée, non constructible | générique **constructible** |

## Correctif (robuste, générique — pas un rustine par zone)

`entre_constructions` est une rubrique **hors enveloppe** : elle ne calibre pas une zone pour le
gabarit. Une zone dont le bloc `regles` ne porte QUE de telles feuilles se résout désormais comme si
elle n'avait pas de `regles` (gelée → non constructible, renvoi → règles de la mère, sinon
strict→`None` / progressif→estimation), **exactement comme avant l'injection**. Les feuilles restent
dans le YAML (lues par l'implantation, validées par V6a) — **aucune règle de distance n'est retirée**.

- `src/labuse/plu/destinations.py`
  - `_RUBRIQUES_HORS_ENVELOPPE = {("retraits", "entre_constructions")}` ;
  - `regles_portent_enveloppe(regles)` — vrai ssi au moins une feuille PÈSE sur l'enveloppe
    (hauteur / emprise / reculs voie·limites / stationnement / mixité / pleine terre) ;
  - `zones_calibrees(commune)` — zones portant l'enveloppe (bâti sur `regles_commune`/`regles_zone`,
    même point de lecture que `resolve_zone`) ;
  - `renvois_commune` — une zone renvoi + feuille descriptive seule reste un renvoi (sinon le renvoi
    était masqué et la zone retombait en estimation générique).
- `src/labuse/faisabilite/zonage.py` — `reg_zones = D.zones_calibrees(ins)` (au lieu de « toute zone
  portant un `regles` »).

## Vérification

- **Rejeu avant/après sur les 24 communes, toutes zones** : **0 écart** de résolution vs le commit
  pré-PLU-10 `e193d7e5` (famille, constructibilité, calibrée/générique). Le correctif neutralise
  exactement l'effet de l'injection sur `resolve_zone`.
- **Nombre de zones calibrées par commune identique avant / après PLU-10** (ci-dessous). Colonne
  « calibrées (enveloppe) » = `zones_calibrees` (le périmètre que pilote le fix) ; colonnes
  résolues AVANT / APRÈS = sorties `resolve_zone` sur les clés de zone de chaque fichier.

| INSEE | fichier | zones | calibrées (enveloppe) | calibrées résolues av./ap. | génériques av./ap. |
|---|---|---|---|---|---|
| 97401 | 97401 les avirons | 27 | 19 | 21 / 21 | 6 / 6 |
| 97402 | 97402 bras panon | 29 | 14 | 19 / 19 | 10 / 10 |
| 97403 | 97403 entre deux | 16 | 5 | 6 / 6 | 10 / 10 |
| 97404 | 97404 l etang sale | 24 | 12 | 13 / 13 | 11 / 11 |
| 97405 | 97405 petite ile | 34 | 15 | 20 / 20 | 14 / 14 |
| 97406 | 97406 la plaine des palmistes | 22 | 9 | 9 / 9 | 13 / 13 |
| 97407 | 97407 le port | 27 | 13 | 21 / 21 | 6 / 6 |
| 97408 | 97408 la possession | 30 | 22 | 20 / 20 | 10 / 10 |
| 97409 | 97409 saint andre | 25 | 8 | 15 / 15 | 10 / 10 |
| 97410 | 97410 saint benoit | 75 | 5 | 0 / 0 | 75 / 75 |
| 97411 | 97411 saint denis | 35 | 21 | 21 / 21 | 14 / 14 |
| 97412 | 97412 saint joseph | 60 | 24 | 44 / 44 | 16 / 16 |
| 97413 | 97413 saint leu | 37 | 18 | 18 / 18 | 19 / 19 |
| 97414 | 97414 saint louis | 51 | 18 | 35 / 35 | 16 / 16 |
| 97415 | 97415 saint paul | 67 | 31 | 55 / 55 | 0 / 0 |
| 97416 | 97416 saint pierre | 45 | 27 | 30 / 30 | 15 / 15 |
| 97418 | 97418 sainte marie | 32 | 19 | 22 / 22 | 10 / 10 |
| 97419 | 97419 sainte rose | 22 | 9 | 13 / 13 | 9 / 9 |
| 97420 | 97420 sainte suzanne | 24 | 12 | 14 / 14 | 10 / 10 |
| 97421 | 97421 salazie | 15 | 10 | 10 / 10 | 5 / 5 |
| 97422 | 97422 le tampon | 30 | 20 | 20 / 20 | 10 / 10 |
| 97423 | 97423 les trois bassins | 30 | 9 | 13 / 13 | 17 / 17 |
| 97424 | 97424 cilaos | 15 | 8 | 9 / 9 | 6 / 6 |

> Note : Saint-Benoît (97410) résout 75/75 en générique **avant comme après** — commune du corpus
> « lu au PDF » non calibrée pour l'enveloppe ; le fix ne change pas son état (0 régression).

- **Garde-fou** `tests/test_plu_calibrage10_entre_constructions.py` : les 23 fichiers se chargent ;
  le nombre de zones calibrées par commune est figé (toute casse de fichier — ou une feuille
  descriptive promue à tort en calibrage — le fait bouger) ; `regles_portent_enveloppe` ignore
  `entre_constructions` ; AUes porte bien sa règle de distance ET reste non constructible.
- **Suite unitaire** (`pytest -m "not db and not local and not reel and not network"`) : **verte**
  (2607 passed, 0 échec, le reste deselected/skipped environnement).
