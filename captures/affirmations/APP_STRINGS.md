# Task2 — app : avant / après des 7 affirmations corrigées + sentinelle

Les chaînes de l'app rendent dans des surfaces conditionnées par les données (barre de tri → résultats,
section « preuve », modale scoring, légende carte). Captures en situation non produites ici pour **ne pas
démarrer le backend contre la base de dev partagée** (écritures `create_all`/caches) juste avant le run du
soir, sur une machine 8 Go. Preuve de rendu : `tsc -b` **vert** + `vitest` **256/256 vert** (les tests de
composants montent ces chaînes). Avant/après exact ci‑dessous + `APP_DIFF.patch`.

## B1 — nombre figé « 431 663 » → arrondi vrai « plus de 430 000 » (drift‑proof)
Parc vivant servi = 433 229 (`/accueil/chiffres`), brut 434 582 ; « 431 663 » était le `n_eval` du run q_v14 gelé.

| Fichier:ligne | Avant | Après |
|---|---|---|
| `frontend/src/lib/layers.ts:88` | « Les **431 663** parcelles cadastrales de l'île… » | « **Toutes les** parcelles cadastrales de l'île (**plus de 430 000**, source DGFiP)… » |
| `frontend/src/lib/strings.ts:287` | « Échantillon : les **431 663** parcelles. » | « Échantillon : **toutes les parcelles de l'île (plus de 430 000)**. » |
| `frontend/src/lib/strings.ts:387` | « Il trie **431 663** parcelles… » | « Il trie **plus de 430 000** parcelles… » |

## B2 — fenêtre d'apprentissage fausse → vraie (FREEZE q_v14 : train 2017‑2023, calib 2024, test 2025)
Le texte disait « 2017‑2024 (calibrée sur 2025) » ; or 2025 est l'année **de test** tenue hors apprentissage.
L'audit (AFFIRMATIONS.csv) n'avait relevé que 210 et 371 ; **179 et 219 portaient la même erreur** et sont corrigées aussi.

| Fichier:ligne | Avant | Après |
|---|---|---|
| `strings.ts:179` (fractionBadge) | « …ventes réelles **2017‑2024, calibrée sur 2025**. » | « …ventes réelles **2017‑2023, calibrée sur 2024 et vérifiée sur 2025**. » |
| `strings.ts:210` (rangTip) | « …apprise sur les ventes réelles **2017‑2024 (calibrée sur 2025)**… » | « …apprise sur les ventes réelles **2017‑2023, calibrée sur 2024 et vérifiée sur 2025 (année tenue à l'écart)**… » |
| `strings.ts:219` (lunettes) | « …**calibrée sur** les ventes réelles **2017‑2024 (calibrée sur 2025)**. » | « …**apprise sur** les ventes réelles **2017‑2023, calibrée sur 2024 et vérifiée sur 2025**. » |
| `strings.ts:371` (« Comment ») | « …les mutations **2017‑2024**, calibré sur les millésimes les plus récents… » | « …les mutations **2017‑2023, calibré sur 2024 et vérifié sur 2025, l'année tenue à l'écart**… » |

## sentinelle.py — libellé de commune (97410 = Saint‑Benoît, PAS Saint‑Pierre)
Données inchangées (le témoin sonde bien 97410) ; seuls les commentaires mentaient.

| Fichier:ligne | Avant | Après |
|---|---|---|
| `src/labuse/sentinelle.py:214` | « seconde commune témoin, **Saint‑Pierre** » | « seconde commune témoin, **Saint‑Benoît** » |
| `src/labuse/sentinelle.py:587` | « second chef‑lieu témoin : **Saint‑Pierre** (97410) » | « second chef‑lieu témoin : **Saint‑Benoît** (97410) » |
| `src/labuse/sentinelle.py:604` | « (Saint‑Denis 97411 + **Saint‑Pierre** 97410) » | « (Saint‑Denis 97411 + **Saint‑Benoît** 97410) » |

## À signaler à Vic (NON corrigé — changerait un nombre servi, hors « corriger les phrases »)
- `src/labuse/api/accueil.py:29` **`TRAIN_ANNEES = (2017, 2024)`** diverge du FREEZE (train finit **2023**) : le compteur
  servi `ventes_train` compte les ventes 2017→2024, incluant 2024 (année de **calibration**, pas d'entraînement).
  À aligner sur (2017, 2023) — mais c'est un **changement de donnée servie**, pas une phrase : laissé à ton arbitrage.
- `frontend/src/components/outils/CommunesTable.test.tsx:13` : fixture de test qui étiquette `insee '97410'` comme
  `'Saint-Pierre'` (même erreur, données de test arbitraires, hors périmètre).
